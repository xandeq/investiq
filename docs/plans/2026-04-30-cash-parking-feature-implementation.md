# Cash Parking Advisor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow user to ask "where should I park my available cash?" and get a ranked, deterministic recommendation (Tesouro Selic / CDB DI / Fundo DI / Poupança) computed from real DIAX cash-flow data, accounting for IR regressivo, IOF regressivo, and the poupança aniversário rule.

**Architecture:** Variant A pull (InvestIQ FastAPI → DIAX .NET S2S endpoint, X-Integration-Key, 1h Redis cache). New IOFEngine (Decreto 6.306/2007) runs in parallel to existing TaxEngine. New `cash_flow_advisor` module mirrors `comparador` shape. New `/caixa` page + Action Inbox card.

**Tech Stack:** DIAX (.NET 8 / ASP.NET Core / xUnit) · InvestIQ backend (FastAPI / SQLAlchemy / Pydantic / Redis / pytest) · InvestIQ frontend (Next.js 15 / TanStack Query / shadcn).

**Source design docs:**
- InvestIQ side: [docs/plans/2026-04-29-cash-parking-feature-design.md](./2026-04-29-cash-parking-feature-design.md)
- DIAX side: `d:/claude-code/diax-crm/docs/plans/2026-04-29-cash-flow-projection-integration-endpoint.md`

**Phase ordering & dependencies:**

```
Phase 0 (pre-flight)
   │
Phase 1 (DIAX endpoint) ──────────────────────┐
   │                                          │
   ▼                                          ▼
Phase 2 (InvestIQ IOFEngine, no DIAX dep)     Configure DIAX_BASE_URL +
   │                                          DIAX_INTEGRATION_KEY in
   ▼                                          ~/.claude/.secrets.env
Phase 3 (cash_flow_advisor module — needs Phase 1 deployed AND Phase 2)
   │
   ▼
Phase 4 (frontend + inbox card)
```

Phase 2 can run in parallel with Phase 1 (no shared files). Phase 3 needs both. Phase 4 needs Phase 3.

**Total estimated effort:** 6.5 – 8.5 hours.

---

## Phase 0 — Pre-flight

### Task 0.1: Confirm clean working trees & branch

**Files:** none

**Step 1: Check git state in both repos**

```bash
git -C d:/claude-code/investiq status --short
git -C d:/claude-code/diax-crm status --short
```

Expected: only `.claude/`, `backend/app/modules/ai/provider.py`, `backend/app/modules/swing_trade/router.py`, `docs/plans/` shown in InvestIQ. DIAX should be clean or only show unrelated files.

**Step 2: Create feature branches**

```bash
git -C d:/claude-code/investiq switch -c feat/cash-parking-advisor
git -C d:/claude-code/diax-crm switch -c feat/cash-flow-projection-endpoint
```

**Step 3: Verify InvestIQ pytest baseline runs green**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_advisor_health.py -q
```

Expected: PASS (this confirms the existing pattern is healthy before we add to it).

**Step 4: Verify DIAX dotnet test baseline**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~Auth" --nologo --verbosity quiet
```

Expected: PASS (confirms test runner works).

**Step 5: No commit** — branches are now ready.

---

## Phase 1 — DIAX cash-flow-projection endpoint (~2h)

Working directory for this phase: `d:/claude-code/diax-crm/api-core`.

### Task 1.1: Add `Integrations` config block

**Files:**
- Modify: `api-core/src/Diax.Api/appsettings.json`
- Modify: `api-core/src/Diax.Api/appsettings.Development.json` (if it exists; otherwise skip)

**Step 1: Add the config section**

Append to `appsettings.json` (top-level, sibling to existing `Logging`/`InvestIQ` sections):

```json
"Integrations": {
  "InvestIQKey": "",
  "DefaultUserId": ""
}
```

**Step 2: Verify JSON parses**

```bash
python -c "import json; json.load(open('d:/claude-code/diax-crm/api-core/src/Diax.Api/appsettings.json'))"
```

Expected: no output (parses cleanly).

**Step 3: Commit**

```bash
git -C d:/claude-code/diax-crm add api-core/src/Diax.Api/appsettings.json
git -C d:/claude-code/diax-crm commit -m "chore: add Integrations:InvestIQKey/DefaultUserId config block"
```

---

### Task 1.2: Define DTOs for the response

**Files:**
- Create: `api-core/src/Diax.Application/Integrations/Dtos/CashFlowProjectionResponse.cs`

**Step 1: Write the DTO file**

```csharp
namespace Diax.Application.Integrations.Dtos;

public record CashFlowProjectionResponse(
    decimal CurrentBalance,
    decimal AvailableToInvest,
    NextBigOutflow? NextBigOutflow,
    List<DailyBalanceItem> DailyProjection
);

public record NextBigOutflow(DateTime Date, decimal Amount, string Description);

public record DailyBalanceItem(
    DateTime Date,
    decimal OpeningBalance,
    decimal TotalIncome,
    decimal TotalExpenses,
    decimal ClosingBalance,
    bool IsNegative,
    bool HasHighPriorityExpense
);
```

**Step 2: Build to verify it compiles**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet build src/Diax.Application/Diax.Application.csproj --nologo --verbosity quiet
```

Expected: Build succeeded. 0 Error(s).

**Step 3: Commit**

```bash
git -C d:/claude-code/diax-crm add api-core/src/Diax.Application/Integrations/Dtos/CashFlowProjectionResponse.cs
git -C d:/claude-code/diax-crm commit -m "feat(integrations): add CashFlowProjectionResponse DTO"
```

---

### Task 1.3: Service interface + skeleton (red)

**Files:**
- Create: `api-core/src/Diax.Application/Integrations/ICashFlowProjectionIntegrationService.cs`
- Create: `api-core/src/Diax.Application/Integrations/CashFlowProjectionIntegrationService.cs`
- Create: `api-core/tests/Diax.Tests/Integrations/CashFlowProjectionIntegrationServiceTests.cs`

**Step 1: Write the failing test**

```csharp
using Diax.Application.Integrations;
using Diax.Application.Integrations.Dtos;
using FluentAssertions;
using Xunit;

namespace Diax.Tests.Integrations;

public class CashFlowProjectionIntegrationServiceTests
{
    [Fact]
    public async Task GetProjectionAsync_ShouldReturnCurrentBalance_WhenUserHasIncomeAndExpense()
    {
        // Use the existing test harness pattern from Diax.Tests/Customers
        // to seed: 1 income (R$ 5000 today) and 1 expense (R$ 1000 in 5 days).
        // Expected: CurrentBalance = 5000 - 0 (only future expense) = 5000;
        //           AvailableToInvest > 0; NextBigOutflow.Date = today+5.
        var harness = await TestHarness.CreateAsync();
        await harness.SeedIncomeAsync(amount: 5000m, date: DateTime.UtcNow.Date);
        await harness.SeedExpenseAsync(amount: 1000m, date: DateTime.UtcNow.Date.AddDays(5), description: "Aluguel");

        var sut = harness.GetRequiredService<ICashFlowProjectionIntegrationService>();
        var result = await sut.GetProjectionAsync(
            userId: harness.DefaultUserId,
            fromDate: DateTime.UtcNow.Date,
            toDate: DateTime.UtcNow.Date.AddDays(30),
            CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        result.Value.CurrentBalance.Should().Be(5000m);
        result.Value.NextBigOutflow.Should().NotBeNull();
        result.Value.NextBigOutflow!.Description.Should().Be("Aluguel");
    }
}
```

> If `TestHarness` does not exist with these helpers, copy the closest existing harness (likely under `tests/Diax.Tests/Customers/` or `Domain/`). If absolutely no harness exists, write a tiny in-memory mock pattern: mock `IIncomeRepository` and `IExpenseRepository` with a simple list-backed stub. Verify by reading `tests/Diax.Tests/GlobalUsings.cs` and one neighbour test before writing.

**Step 2: Write the interface (minimal)**

```csharp
using Diax.Application.Common;
using Diax.Application.Integrations.Dtos;
using Diax.Shared.Results;

namespace Diax.Application.Integrations;

public interface ICashFlowProjectionIntegrationService : IApplicationService
{
    Task<Result<CashFlowProjectionResponse>> GetProjectionAsync(
        Guid userId,
        DateTime fromDate,
        DateTime toDate,
        CancellationToken cancellationToken);
}
```

**Step 3: Run the test — expect compilation failure on missing service implementation**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~CashFlowProjectionIntegrationServiceTests" --nologo
```

Expected: FAIL — "CashFlowProjectionIntegrationService cannot be resolved" or "type does not exist".

**Step 4: No commit yet** (red, will commit with implementation in Task 1.4).

---

### Task 1.4: Implement the service (green)

**Files:**
- Modify: `api-core/src/Diax.Application/Integrations/CashFlowProjectionIntegrationService.cs`

**Step 1: Write the implementation**

```csharp
using Diax.Application.Common;
using Diax.Application.Finance.Planner;
using Diax.Application.Integrations.Dtos;
using Diax.Domain.Finance.Planner;
using Diax.Shared.Results;
using Microsoft.Extensions.Logging;

namespace Diax.Application.Integrations;

public class CashFlowProjectionIntegrationService : ICashFlowProjectionIntegrationService
{
    private const decimal BigOutflowThreshold = 1000m;

    private readonly CashFlowProjectionService _projector;
    private readonly IIncomeRepository _incomes;          // <-- confirm exact interface name in repo before writing
    private readonly IExpenseRepository _expenses;
    private readonly IRecurringTransactionRepository _recurrings;
    private readonly IFinancialAccountRepository _accounts;
    private readonly ILogger<CashFlowProjectionIntegrationService> _logger;

    public CashFlowProjectionIntegrationService(
        CashFlowProjectionService projector,
        IIncomeRepository incomes,
        IExpenseRepository expenses,
        IRecurringTransactionRepository recurrings,
        IFinancialAccountRepository accounts,
        ILogger<CashFlowProjectionIntegrationService> logger)
    {
        _projector = projector;
        _incomes = incomes;
        _expenses = expenses;
        _recurrings = recurrings;
        _accounts = accounts;
        _logger = logger;
    }

    public async Task<Result<CashFlowProjectionResponse>> GetProjectionAsync(
        Guid userId,
        DateTime fromDate,
        DateTime toDate,
        CancellationToken ct)
    {
        // 1. Current balance = sum of all FinancialAccount balances for user
        var accounts = await _accounts.GetByUserAsync(userId, ct);
        var currentBalance = accounts.Sum(a => a.CurrentBalance);

        // 2. Build ProjectedTransaction list from incomes + expenses + recurring occurrences in [fromDate, toDate]
        var projectedTxns = new List<ProjectedTransaction>();
        // ... aggregate single + recurring into projectedTxns (mirror PersonalFinanceControlService.GetMonthAsync pattern)

        // 3. ProjectDailyBalances
        var dailyBalances = _projector.ProjectDailyBalances(currentBalance, projectedTxns, simulationId: Guid.Empty);

        // 4. AvailableToInvest = TotalIncome - TotalExpenses - sum of card statements in window
        //    (mirror formula at PersonalFinanceController.cs:468)
        var totalIncome = projectedTxns.Where(t => t.Type == TransactionType.Income).Sum(t => t.Amount);
        var totalExpenses = projectedTxns.Where(t => t.Type == TransactionType.Expense).Sum(t => t.Amount);
        var availableToInvest = totalIncome - totalExpenses;

        // 5. NextBigOutflow = first expense ≥ R$ 1000 in window
        var nextBig = projectedTxns
            .Where(t => t.Type == TransactionType.Expense && t.Amount >= BigOutflowThreshold && t.Date >= DateTime.UtcNow.Date)
            .OrderBy(t => t.Date)
            .Select(t => new NextBigOutflow(t.Date, t.Amount, t.Description ?? string.Empty))
            .FirstOrDefault();

        // 6. Map daily balances
        var dailyDtos = dailyBalances.Select(d => new DailyBalanceItem(
            d.Date, d.OpeningBalance, d.TotalIncome, d.TotalExpenses, d.ClosingBalance,
            d.IsNegative, d.HasHighPriorityExpense)).ToList();

        return Result.Success(new CashFlowProjectionResponse(currentBalance, availableToInvest, nextBig, dailyDtos));
    }
}
```

> **DEV NOTE before writing:** before authoring the bullet `// ... aggregate single + recurring into projectedTxns`, read `api-core/src/Diax.Application/Finance/PersonalFinanceControlService.GetMonthAsync` to copy the exact pattern (incomes + expenses + recurring occurrences expansion). Reuse private helpers if they're internal. Do **not** reimplement recurring-occurrence math.

**Step 2: Register the service in DI**

Find the existing `AddApplicationServices` (or equivalent) in `api-core/src/Diax.Application/DependencyInjection.cs` (or wherever `IApplicationService` types are auto-registered — search for `IApplicationService` registration).

If auto-registered via assembly scan: nothing to do, the `IApplicationService` marker handles it.
Otherwise: add `services.AddScoped<ICashFlowProjectionIntegrationService, CashFlowProjectionIntegrationService>();`.

**Step 3: Run the test — expect green**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~CashFlowProjectionIntegrationServiceTests" --nologo
```

Expected: PASS.

**Step 4: Commit**

```bash
git -C d:/claude-code/diax-crm add api-core/src/Diax.Application/Integrations/ api-core/tests/Diax.Tests/Integrations/
git -C d:/claude-code/diax-crm commit -m "feat(integrations): cash flow projection service for InvestIQ pull"
```

---

### Task 1.5: Add edge-case tests

**Files:**
- Modify: `api-core/tests/Diax.Tests/Integrations/CashFlowProjectionIntegrationServiceTests.cs`

**Step 1: Add three more test methods**

```csharp
[Fact]
public async Task GetProjectionAsync_NoTransactions_ReturnsEmptyDailyProjection() { /* ... */ }

[Fact]
public async Task GetProjectionAsync_SmallExpensesOnly_NextBigOutflowIsNull() {
    // seed expenses < R$ 1000 only
    // expect NextBigOutflow == null
}

[Fact]
public async Task GetProjectionAsync_AvailableToInvestParity_MatchesPersonalControlFormula() {
    // seed identical data to a known PersonalControl scenario
    // assert AvailableToInvest equals what PersonalControl page computes
}
```

**Step 2: Run all integration tests**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~CashFlowProjectionIntegrationServiceTests" --nologo
```

Expected: 4 passed.

**Step 3: Commit**

```bash
git -C d:/claude-code/diax-crm add api-core/tests/Diax.Tests/Integrations/
git -C d:/claude-code/diax-crm commit -m "test(integrations): edge cases for cash flow projection"
```

---

### Task 1.6: Controller (red → green)

**Files:**
- Create: `api-core/src/Diax.Api/Controllers/V1/IntegrationsController.cs`
- Create: `api-core/tests/Diax.Tests/Integrations/IntegrationsControllerTests.cs`

**Step 1: Write the failing controller test (integration test, hits HTTP layer)**

```csharp
using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using Xunit;

namespace Diax.Tests.Integrations;

public class IntegrationsControllerTests
{
    [Fact]
    public async Task GetCashFlowProjection_NoHeader_Returns401()
    {
        var harness = await ApiTestHarness.CreateAsync();
        var resp = await harness.Client.GetAsync("/api/v1.0/integrations/cash-flow-projection");
        resp.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task GetCashFlowProjection_BadKey_Returns401()
    {
        var harness = await ApiTestHarness.CreateAsync(integrationKey: "real-key");
        harness.Client.DefaultRequestHeaders.Add("X-Integration-Key", "wrong-key");
        var resp = await harness.Client.GetAsync("/api/v1.0/integrations/cash-flow-projection");
        resp.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task GetCashFlowProjection_KeyNotConfigured_Returns503()
    {
        var harness = await ApiTestHarness.CreateAsync(integrationKey: null);
        harness.Client.DefaultRequestHeaders.Add("X-Integration-Key", "anything");
        var resp = await harness.Client.GetAsync("/api/v1.0/integrations/cash-flow-projection");
        resp.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable);
    }

    [Fact]
    public async Task GetCashFlowProjection_ValidKey_Returns200WithProjection()
    {
        var harness = await ApiTestHarness.CreateAsync(integrationKey: "k", defaultUserId: Guid.NewGuid());
        await harness.SeedIncomeAsync(5000m, DateTime.UtcNow.Date);
        harness.Client.DefaultRequestHeaders.Add("X-Integration-Key", "k");
        var resp = await harness.Client.GetAsync("/api/v1.0/integrations/cash-flow-projection");
        resp.StatusCode.Should().Be(HttpStatusCode.OK);
        var body = await resp.Content.ReadFromJsonAsync<CashFlowProjectionResponse>();
        body!.CurrentBalance.Should().Be(5000m);
    }
}
```

> If `ApiTestHarness` doesn't exist for HTTP-level tests, build it from `WebApplicationFactory<Program>` — pattern is standard ASP.NET Core. Look for any existing controller test in `tests/Diax.Tests/` to copy the harness shape.

**Step 2: Run test — expect 4 failures (controller doesn't exist)**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~IntegrationsControllerTests" --nologo
```

Expected: FAIL on all 4.

**Step 3: Write the controller**

```csharp
using Asp.Versioning;
using Diax.Application.Integrations;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;

namespace Diax.Api.Controllers.V1;

[AllowAnonymous]
[ApiController]
[ApiVersion("1.0")]
[Route("api/v{version:apiVersion}/integrations")]
[Produces("application/json")]
public class IntegrationsController : ControllerBase
{
    private readonly ICashFlowProjectionIntegrationService _service;
    private readonly IConfiguration _config;

    public IntegrationsController(
        ICashFlowProjectionIntegrationService service,
        IConfiguration config)
    {
        _service = service;
        _config = config;
    }

    [HttpGet("cash-flow-projection")]
    public async Task<IActionResult> GetCashFlowProjection(
        [FromHeader(Name = "X-Integration-Key")] string? integrationKey,
        [FromQuery] DateTime? fromDate,
        [FromQuery] DateTime? toDate,
        CancellationToken ct)
    {
        var configuredKey = _config["Integrations:InvestIQKey"];
        var defaultUserIdRaw = _config["Integrations:DefaultUserId"];

        if (string.IsNullOrWhiteSpace(configuredKey) || string.IsNullOrWhiteSpace(defaultUserIdRaw))
            return StatusCode(503, new { error = "Integration not configured" });

        if (string.IsNullOrWhiteSpace(integrationKey) || integrationKey != configuredKey)
            return Unauthorized(new { error = "Invalid integration key" });

        if (!Guid.TryParse(defaultUserIdRaw, out var userId))
            return StatusCode(503, new { error = "Integrations:DefaultUserId is not a valid Guid" });

        var from = fromDate ?? DateTime.UtcNow.Date;
        var to = toDate ?? from.AddDays(90);

        var result = await _service.GetProjectionAsync(userId, from, to, ct);
        return result.IsSuccess ? Ok(result.Value) : StatusCode(502, result.Error);
    }
}
```

**Step 4: Run tests — expect green**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --filter "FullyQualifiedName~IntegrationsControllerTests" --nologo
```

Expected: 4 passed.

**Step 5: Commit**

```bash
git -C d:/claude-code/diax-crm add api-core/src/Diax.Api/Controllers/V1/IntegrationsController.cs api-core/tests/Diax.Tests/Integrations/IntegrationsControllerTests.cs
git -C d:/claude-code/diax-crm commit -m "feat(api): GET /api/v1/integrations/cash-flow-projection endpoint"
```

---

### Task 1.7: Update DIAX project memory

**Files:**
- Modify: `C:/Users/acq20/.claude/projects/D--claude-code-diax-crm/memory/project_investiq-integration.md`

**Step 1: Update the file** to mark the new endpoint as IMPLEMENTED with the route, auth pattern, and config keys.

**Step 2: No test, no commit** — memory only.

---

### Task 1.8: Phase 1 verification

**Step 1: Run full DIAX test suite**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet test tests/Diax.Tests/Diax.Tests.csproj --nologo
```

Expected: All tests pass, including the new ~8 we added.

**Step 2: Manual smoke test**

```bash
cd d:/claude-code/diax-crm/api-core && dotnet run --project src/Diax.Api/Diax.Api.csproj
# In another terminal:
curl -i -H "X-Integration-Key: <dev-key>" "http://localhost:5000/api/v1.0/integrations/cash-flow-projection"
```

Expected: 503 if config empty, 200 once `Integrations:InvestIQKey` and `Integrations:DefaultUserId` are set in `appsettings.Development.json`.

**Step 3: Push branch (no PR yet — wait for symmetric InvestIQ side)**

```bash
git -C d:/claude-code/diax-crm push -u origin feat/cash-flow-projection-endpoint
```

**Step 4: Configure secrets** (one-time, before Phase 3)

```bash
# Append to ~/.claude/.secrets.env
DIAX_BASE_URL=http://localhost:5000        # dev; switch to prod URL when DIAX deployed
DIAX_INTEGRATION_KEY=<random-32-byte-hex>
```

Also set the same value as `Integrations:InvestIQKey` in DIAX's `appsettings.Development.json` (and prod env vars `DIAX_Integrations__InvestIQKey`, `DIAX_Integrations__DefaultUserId`).

✅ **Phase 1 done.**

---

## Phase 2 — InvestIQ IOFEngine (~30 min)

Working directory for this phase and beyond: `d:/claude-code/investiq`.

### Task 2.1: Write IOF table fixture & failing test

**Files:**
- Create: `backend/tests/test_iof_engine.py`

**Step 1: Write the failing tests**

```python
"""IOFEngine — Decreto 6.306/2007 Anexo, tabela regressiva 30 dias."""
from decimal import Decimal

import pytest

from app.modules.market_universe.iof_engine import IOFEngine


# Official table — IOF rate as fraction of rendimento (income), days 1..30
# Source: Decreto 6.306/2007 Anexo. Day 1: 96%, Day 30+: 0%.
_OFFICIAL_TABLE = {
    1: Decimal("0.96"), 2: Decimal("0.93"), 3: Decimal("0.90"), 4: Decimal("0.86"),
    5: Decimal("0.83"), 6: Decimal("0.80"), 7: Decimal("0.76"), 8: Decimal("0.73"),
    9: Decimal("0.70"), 10: Decimal("0.66"), 11: Decimal("0.63"), 12: Decimal("0.60"),
    13: Decimal("0.56"), 14: Decimal("0.53"), 15: Decimal("0.50"), 16: Decimal("0.46"),
    17: Decimal("0.43"), 18: Decimal("0.40"), 19: Decimal("0.36"), 20: Decimal("0.33"),
    21: Decimal("0.30"), 22: Decimal("0.26"), 23: Decimal("0.23"), 24: Decimal("0.20"),
    25: Decimal("0.16"), 26: Decimal("0.13"), 27: Decimal("0.10"), 28: Decimal("0.06"),
    29: Decimal("0.03"), 30: Decimal("0.00"),
}


@pytest.mark.parametrize("day,expected", list(_OFFICIAL_TABLE.items()))
def test_rate_for_days_matches_official_table(day, expected):
    assert IOFEngine().rate_for_days(day) == expected


def test_rate_for_days_above_30_is_zero():
    assert IOFEngine().rate_for_days(31) == Decimal("0.00")
    assert IOFEngine().rate_for_days(365) == Decimal("0.00")


def test_rate_for_days_zero_or_negative_is_zero():
    """No holding = no rendimento = no IOF (defensive)."""
    assert IOFEngine().rate_for_days(0) == Decimal("0.00")
    assert IOFEngine().rate_for_days(-5) == Decimal("0.00")


def test_apply_iof_returns_iof_brl_and_net_brl():
    """Given rendimento bruto, returns (iof_value, net_value)."""
    engine = IOFEngine()
    iof, net = engine.apply(rendimento_bruto=Decimal("100"), days=1)
    assert iof == Decimal("96.00")
    assert net == Decimal("4.00")
```

**Step 2: Run test — expect import error**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_iof_engine.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.modules.market_universe.iof_engine'`.

**Step 3: No commit yet.**

---

### Task 2.2: Implement IOFEngine

**Files:**
- Create: `backend/app/modules/market_universe/iof_engine.py`

**Step 1: Write the implementation**

```python
"""IOFEngine — Decreto 6.306/2007 Anexo, tabela regressiva 30 dias.

IOF incide sobre o RENDIMENTO BRUTO (não sobre o principal) em aplicações de
renda fixa com prazo inferior a 30 dias. A alíquota cai linearmente do dia 1
(96% do rendimento) ao dia 29 (3%), zerando a partir do dia 30.

Não confundir com IR regressivo (TaxEngine), que é um imposto separado e cumulativo.

Uso:
    engine = IOFEngine()
    rate = engine.rate_for_days(15)            # Decimal("0.50")
    iof, net = engine.apply(Decimal("100"), 15) # (Decimal("50.00"), Decimal("50.00"))
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final

# Decreto 6.306/2007 Anexo — IOF como fração do rendimento, dias 1..29.
# Dia 30+ = 0.
_TABLE: Final[dict[int, Decimal]] = {
    1: Decimal("0.96"), 2: Decimal("0.93"), 3: Decimal("0.90"), 4: Decimal("0.86"),
    5: Decimal("0.83"), 6: Decimal("0.80"), 7: Decimal("0.76"), 8: Decimal("0.73"),
    9: Decimal("0.70"), 10: Decimal("0.66"), 11: Decimal("0.63"), 12: Decimal("0.60"),
    13: Decimal("0.56"), 14: Decimal("0.53"), 15: Decimal("0.50"), 16: Decimal("0.46"),
    17: Decimal("0.43"), 18: Decimal("0.40"), 19: Decimal("0.36"), 20: Decimal("0.33"),
    21: Decimal("0.30"), 22: Decimal("0.26"), 23: Decimal("0.23"), 24: Decimal("0.20"),
    25: Decimal("0.16"), 26: Decimal("0.13"), 27: Decimal("0.10"), 28: Decimal("0.06"),
    29: Decimal("0.03"),
}


class IOFEngine:
    @staticmethod
    def rate_for_days(days: int) -> Decimal:
        if days < 1:
            return Decimal("0.00")
        return _TABLE.get(days, Decimal("0.00"))

    @classmethod
    def apply(cls, rendimento_bruto: Decimal, days: int) -> tuple[Decimal, Decimal]:
        """Return (iof_value_brl, net_value_brl) given rendimento bruto."""
        rate = cls.rate_for_days(days)
        iof = (rendimento_bruto * rate).quantize(Decimal("0.01"))
        net = (rendimento_bruto - iof).quantize(Decimal("0.01"))
        return iof, net
```

**Step 2: Run test — expect green**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_iof_engine.py -q
```

Expected: 33 passed.

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/modules/market_universe/iof_engine.py backend/tests/test_iof_engine.py
git -C d:/claude-code/investiq commit -m "feat(market_universe): IOFEngine — Decreto 6.306/2007 30-day table"
```

✅ **Phase 2 done.**

---

## Phase 3 — InvestIQ cash_flow_advisor module (~3-4h)

### Task 3.1: Add settings

**Files:**
- Modify: `backend/app/core/config.py` (around line 41, after `INTEGRATION_TENANT_ID`)

**Step 1: Add the two settings**

```python
    # DIAX CRM — outbound integration (we pull cash flow from DIAX)
    # Symmetric to INTEGRATION_KEY which is the inbound key DIAX uses to call us.
    DIAX_BASE_URL: str = ""
    DIAX_INTEGRATION_KEY: str = ""
```

**Step 2: Verify it imports**

```bash
cd d:/claude-code/investiq && python -c "from app.core.config import settings; print(settings.DIAX_BASE_URL, settings.DIAX_INTEGRATION_KEY)"
```

Expected: prints two empty strings, no error.

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/core/config.py
git -C d:/claude-code/investiq commit -m "chore(config): add DIAX_BASE_URL and DIAX_INTEGRATION_KEY settings"
```

---

### Task 3.2: DiaxClient — schemas + client (red)

**Files:**
- Create: `backend/app/modules/cash_flow_advisor/__init__.py` (empty)
- Create: `backend/app/modules/cash_flow_advisor/schemas.py`
- Create: `backend/app/modules/cash_flow_advisor/client.py`
- Create: `backend/tests/test_cash_flow_advisor_client.py`

**Step 1: Write `schemas.py`** — Pydantic mirror of the DIAX response

```python
"""Pydantic schemas for cash_flow_advisor — DIAX response + ranking output."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyBalanceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    closing_balance: Decimal
    is_negative: bool
    has_high_priority_expense: bool


class NextBigOutflow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: date
    amount: Decimal
    description: str


class CashFlowProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    current_balance: Decimal
    available_to_invest: Decimal
    next_big_outflow: NextBigOutflow | None
    daily_projection: list[DailyBalanceItem]
    fetched_at: datetime


class CashParkingRow(BaseModel):
    label: str
    gross_annual_pct: Decimal
    holding_days: int
    iof_pct: Decimal
    ir_pct: Decimal
    gross_value_brl: Decimal
    iof_value_brl: Decimal
    ir_value_brl: Decimal
    net_value_brl: Decimal
    net_pct: Decimal
    rank: int
    note: str | None = None


class CashParkingResponse(BaseModel):
    amount: Decimal
    holding_days: int
    rows: list[CashParkingRow]
    next_big_outflow: NextBigOutflow | None
    generated_at: datetime
    warnings: list[str] = []
```

> Pydantic uses snake_case field names; DIAX returns PascalCase. We'll add aliases or transform on the client side. The simplest path: configure `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` if PascalCase aliases needed — or normalize keys in the client. Pick whichever is cleaner; default here is to normalize in client.

**Step 2: Write the failing test**

```python
"""DiaxClient — pulls cash flow projection from DIAX."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.modules.cash_flow_advisor.client import DiaxClient, DiaxNotConfigured, DiaxUnreachable


@pytest.mark.asyncio
async def test_get_cash_flow_projection_unconfigured_raises(monkeypatch):
    monkeypatch.setattr(settings, "DIAX_BASE_URL", "")
    monkeypatch.setattr(settings, "DIAX_INTEGRATION_KEY", "")
    with pytest.raises(DiaxNotConfigured):
        async with DiaxClient() as c:
            await c.get_cash_flow_projection()


@pytest.mark.asyncio
async def test_get_cash_flow_projection_returns_parsed_response(monkeypatch, httpx_mock):
    monkeypatch.setattr(settings, "DIAX_BASE_URL", "http://diax.test")
    monkeypatch.setattr(settings, "DIAX_INTEGRATION_KEY", "k")
    httpx_mock.add_response(
        url="http://diax.test/api/v1.0/integrations/cash-flow-projection",
        json={
            "currentBalance": 1500.50,
            "availableToInvest": 800.00,
            "nextBigOutflow": {"date": "2026-05-15", "amount": 1200.0, "description": "Aluguel"},
            "dailyProjection": [],
        },
    )
    async with DiaxClient() as c:
        result = await c.get_cash_flow_projection()
    assert result.current_balance == Decimal("1500.50")
    assert result.available_to_invest == Decimal("800.00")
    assert result.next_big_outflow.description == "Aluguel"


@pytest.mark.asyncio
async def test_get_cash_flow_projection_uses_redis_cache(monkeypatch, fake_redis):
    monkeypatch.setattr(settings, "DIAX_BASE_URL", "http://diax.test")
    monkeypatch.setattr(settings, "DIAX_INTEGRATION_KEY", "k")
    # First call hits HTTP; second call within 1h hits cache
    # ... assert HTTP mock called exactly once
```

**Step 3: Run — expect import error**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_client.py -q
```

Expected: FAIL — module missing.

**Step 4: No commit yet.**

---

### Task 3.3: Implement DiaxClient (green)

**Files:**
- Modify: `backend/app/modules/cash_flow_advisor/client.py`

**Step 1: Write the client**

```python
"""DiaxClient — async HTTP client to DIAX CRM cash-flow-projection endpoint.

- Auth: X-Integration-Key header (settings.DIAX_INTEGRATION_KEY)
- Cache: Redis 1h on `cash_flow_advisor:diax_projection` key
- Errors: DiaxNotConfigured (503-equivalent), DiaxUnreachable (502-equivalent)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Self

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.modules.cash_flow_advisor.schemas import CashFlowProjection

logger = logging.getLogger(__name__)

_CACHE_KEY = "cash_flow_advisor:diax_projection"
_CACHE_TTL_SECONDS = 3600


class DiaxNotConfigured(Exception):
    """DIAX_BASE_URL or DIAX_INTEGRATION_KEY missing in settings."""


class DiaxUnreachable(Exception):
    """DIAX returned non-2xx or network error."""


class DiaxClient:
    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._redis: aioredis.Redis | None = None

    async def __aenter__(self) -> Self:
        if not settings.DIAX_BASE_URL or not settings.DIAX_INTEGRATION_KEY:
            raise DiaxNotConfigured("DIAX_BASE_URL/DIAX_INTEGRATION_KEY not set")
        self._http = httpx.AsyncClient(
            base_url=settings.DIAX_BASE_URL,
            headers={"X-Integration-Key": settings.DIAX_INTEGRATION_KEY},
            timeout=10.0,
        )
        try:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            self._redis = None
        return self

    async def __aexit__(self, *_) -> None:
        if self._http: await self._http.aclose()
        if self._redis: await self._redis.aclose()

    async def get_cash_flow_projection(self) -> CashFlowProjection:
        # 1) Cache hit?
        if self._redis is not None:
            try:
                cached = await self._redis.get(_CACHE_KEY)
                if cached:
                    return CashFlowProjection.model_validate_json(cached)
            except Exception as exc:
                logger.warning("DiaxClient: redis get failed: %s", exc)

        # 2) HTTP call
        assert self._http is not None
        try:
            resp = await self._http.get("/api/v1.0/integrations/cash-flow-projection")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise DiaxUnreachable(f"DIAX request failed: {exc}") from exc

        raw = resp.json()
        normalized = _camel_to_snake(raw)
        normalized["fetched_at"] = datetime.now(tz=timezone.utc).isoformat()
        result = CashFlowProjection.model_validate(normalized)

        # 3) Cache write
        if self._redis is not None:
            try:
                await self._redis.set(_CACHE_KEY, result.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception as exc:
                logger.warning("DiaxClient: redis set failed: %s", exc)

        return result


def _camel_to_snake(d: dict | list | str | int | float | bool | None):
    """Recursively convert PascalCase/camelCase keys to snake_case."""
    import re
    if isinstance(d, dict):
        return {re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower(): _camel_to_snake(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_camel_to_snake(x) for x in d]
    return d
```

**Step 2: Install pytest-httpx if not present**

```bash
cd d:/claude-code/investiq && pip show pytest-httpx 2>&1 | head -1
```

If not installed: `pip install pytest-httpx` and add to `backend/requirements-dev.txt`.

**Step 3: Run — expect green**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_client.py -q
```

Expected: 3 passed (or 2 + 1 cache test if `fake_redis` fixture needs to be added to conftest — see existing `conftest.py`).

**Step 4: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/modules/cash_flow_advisor/ backend/tests/test_cash_flow_advisor_client.py backend/requirements-dev.txt
git -C d:/claude-code/investiq commit -m "feat(cash_flow_advisor): DiaxClient with Redis 1h cache"
```

---

### Task 3.4: CashParkingService — Tesouro Selic + CDB rows (red)

**Files:**
- Create: `backend/app/modules/cash_flow_advisor/service.py`
- Create: `backend/tests/test_cash_flow_advisor_service.py`

**Step 1: Write failing test for Tesouro Selic ranking**

```python
"""CashParkingService — ranks instruments for short-term cash parking."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.modules.cash_flow_advisor.schemas import CashFlowProjection, NextBigOutflow
from app.modules.cash_flow_advisor.service import CashParkingService


@pytest.fixture
def projection_with_outflow_in_17_days():
    return CashFlowProjection(
        current_balance=Decimal("25000"),
        available_to_invest=Decimal("25000"),
        next_big_outflow=NextBigOutflow(
            date=date(2026, 5, 17), amount=Decimal("3500"), description="Cartão"
        ),
        daily_projection=[],
        fetched_at=datetime.now(tz=timezone.utc),
    )


@pytest.mark.asyncio
async def test_rank_options_caps_at_90_days_when_no_outflow():
    """If next_big_outflow is None, holding_days = 90 (cap from design)."""
    proj = CashFlowProjection(
        current_balance=Decimal("10000"), available_to_invest=Decimal("10000"),
        next_big_outflow=None, daily_projection=[],
        fetched_at=datetime.now(tz=timezone.utc),
    )
    svc = CashParkingService(cdi_annual_pct=Decimal("13.65"), selic_annual_pct=Decimal("13.75"))
    result = await svc.rank_options(proj, today=date(2026, 4, 30))
    assert result.holding_days == 90


@pytest.mark.asyncio
async def test_rank_options_returns_iof_zero_at_30_days():
    """At 30 days, IOF column should be 0 across instruments."""
    proj = CashFlowProjection(
        current_balance=Decimal("10000"), available_to_invest=Decimal("10000"),
        next_big_outflow=NextBigOutflow(date=date(2026, 5, 30), amount=Decimal("1000"), description="x"),
        daily_projection=[], fetched_at=datetime.now(tz=timezone.utc),
    )
    svc = CashParkingService(cdi_annual_pct=Decimal("13.65"), selic_annual_pct=Decimal("13.75"))
    result = await svc.rank_options(proj, today=date(2026, 4, 30))
    for row in result.rows:
        if "Poup" not in row.label:                  # Poupança is IOF-exempt anyway
            assert row.iof_pct == Decimal("0.00")


@pytest.mark.asyncio
async def test_rank_options_short_window_iof_dominates(projection_with_outflow_in_17_days):
    """At 17 days, IOF rate is 0.43 — net return should be much lower than CDI."""
    svc = CashParkingService(cdi_annual_pct=Decimal("13.65"), selic_annual_pct=Decimal("13.75"))
    result = await svc.rank_options(
        projection_with_outflow_in_17_days, today=date(2026, 4, 30)
    )
    cdb102 = next(r for r in result.rows if "102" in r.label)
    assert cdb102.iof_pct == Decimal("0.43")
    assert cdb102.net_pct < Decimal("1.0")           # net return is sub-1% in BRL terms


@pytest.mark.asyncio
async def test_rank_options_below_min_amount_returns_empty():
    proj = CashFlowProjection(
        current_balance=Decimal("50"), available_to_invest=Decimal("50"),
        next_big_outflow=None, daily_projection=[], fetched_at=datetime.now(tz=timezone.utc),
    )
    svc = CashParkingService(cdi_annual_pct=Decimal("13.65"), selic_annual_pct=Decimal("13.75"))
    result = await svc.rank_options(proj, today=date(2026, 4, 30))
    assert result.rows == []
    assert any("mínimo" in w for w in result.warnings)
```

**Step 2: Run — expect failure**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_service.py -q
```

Expected: FAIL on import.

**Step 3: No commit.**

---

### Task 3.5: Implement CashParkingService (green)

**Files:**
- Modify: `backend/app/modules/cash_flow_advisor/service.py`

**Step 1: Write the service**

```python
"""CashParkingService — deterministic ranking of cash-parking instruments.

Rules (from design doc § 6.3):
  - holding_days = min((next_big_outflow.date - today).days, 90); fallback 90 if None
  - Skip if available_to_invest < R$ 100
  - Skip if holding_days <= 1 (IOF eats everything)
  - Compound annual rate over holding period: (1 + r)^(d/365) - 1
  - IOF on rendimento_bruto via IOFEngine
  - IR on rendimento_bruto via TaxEngine.get_rate("renda_fixa", days)
  - Poupança: 0.7 * Selic + TR (when Selic > 8.5%); IR-exempt; IOF-exempt;
              applies anniversary rule (returns 0 + note if today + holding < 30d boundary)
  - Sort rows by net_pct desc, assign rank starting at 1
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cash_flow_advisor.schemas import (
    CashFlowProjection, CashParkingResponse, CashParkingRow,
)
from app.modules.market_universe.iof_engine import IOFEngine
from app.modules.market_universe.tax_engine import TaxEngine

logger = logging.getLogger(__name__)

_MIN_AMOUNT_BRL = Decimal("100")
_MAX_HOLDING_DAYS = 90
_POUPANCA_MAX_RATE_THRESHOLD_SELIC_PCT = Decimal("8.5")


class CashParkingService:
    def __init__(
        self,
        *,
        cdi_annual_pct: Decimal,
        selic_annual_pct: Decimal,
        tax_config_rows: Sequence | None = None,
    ) -> None:
        self.cdi = cdi_annual_pct
        self.selic = selic_annual_pct
        self.iof = IOFEngine()
        self.tax = TaxEngine(tax_config_rows or [])

    async def rank_options(
        self,
        projection: CashFlowProjection,
        *,
        today: date,
    ) -> CashParkingResponse:
        warnings: list[str] = []

        amount = projection.available_to_invest
        if amount < _MIN_AMOUNT_BRL:
            warnings.append(f"Valor disponível ({amount}) abaixo do mínimo R$ {_MIN_AMOUNT_BRL}")
            return CashParkingResponse(
                amount=amount, holding_days=0, rows=[],
                next_big_outflow=projection.next_big_outflow,
                generated_at=projection.fetched_at, warnings=warnings,
            )

        if projection.next_big_outflow:
            raw_days = (projection.next_big_outflow.date - today).days
        else:
            raw_days = _MAX_HOLDING_DAYS
        holding_days = min(max(raw_days, 0), _MAX_HOLDING_DAYS)

        if holding_days <= 1:
            warnings.append("Janela menor que 2 dias — IOF inviabiliza o investimento")
            return CashParkingResponse(
                amount=amount, holding_days=holding_days, rows=[],
                next_big_outflow=projection.next_big_outflow,
                generated_at=projection.fetched_at, warnings=warnings,
            )

        instruments = [
            ("Tesouro Selic",      self.selic,                 True,  True,  None),
            ("CDB DI 100% CDI",    self.cdi,                   True,  True,  None),
            ("CDB DI 102% CDI",    self.cdi * Decimal("1.02"), True,  True,  None),
            ("CDB DI 110% CDI",    self.cdi * Decimal("1.10"), True,  True,  None),
            ("Fundo DI 95% CDI",   self.cdi * Decimal("0.95"), True,  True,  None),
            ("Poupança",           self._poupanca_rate(),      False, False, "anniversary"),
        ]

        rows: list[CashParkingRow] = []
        for label, gross_pct, ir_applies, iof_applies, special in instruments:
            row = self._compute_row(
                amount=amount, label=label, gross_annual_pct=gross_pct,
                holding_days=holding_days, ir_applies=ir_applies,
                iof_applies=iof_applies, special=special, today=today,
            )
            rows.append(row)

        rows.sort(key=lambda r: r.net_pct, reverse=True)
        for i, r in enumerate(rows, 1):
            r.rank = i

        return CashParkingResponse(
            amount=amount, holding_days=holding_days, rows=rows,
            next_big_outflow=projection.next_big_outflow,
            generated_at=projection.fetched_at, warnings=warnings,
        )

    def _poupanca_rate(self) -> Decimal:
        if self.selic > _POUPANCA_MAX_RATE_THRESHOLD_SELIC_PCT:
            return Decimal("6.17")  # 0.5% a.m. + TR ≈ 6.17% a.a. when Selic > 8.5
        return self.selic * Decimal("0.7")  # 70% Selic + TR

    def _compute_row(
        self, *, amount: Decimal, label: str, gross_annual_pct: Decimal,
        holding_days: int, ir_applies: bool, iof_applies: bool,
        special: str | None, today: date,
    ) -> CashParkingRow:
        compound_pct = self._compound(gross_annual_pct, holding_days)
        gross_brl = (amount * compound_pct / Decimal("100")).quantize(Decimal("0.01"))

        # Poupança aniversário: zero rendimento se sair antes do aniversário mensal
        note: str | None = None
        if special == "anniversary":
            day_of_month = today.day
            days_to_anniversary = (day_of_month if holding_days < 30 else 0)  # simplified
            if holding_days < 30 and holding_days < days_to_anniversary:
                gross_brl = Decimal("0.00")
                note = "Poupança não rende — saída antes do aniversário mensal"

        iof_pct = self.iof.rate_for_days(holding_days) if iof_applies else Decimal("0.00")
        iof_brl = (gross_brl * iof_pct).quantize(Decimal("0.01"))
        after_iof = gross_brl - iof_brl

        if ir_applies and after_iof > 0:
            ir_pct = Decimal(str(self.tax.get_rate("renda_fixa", holding_days))) / Decimal("100")
        else:
            ir_pct = Decimal("0.00")
        ir_brl = (after_iof * ir_pct).quantize(Decimal("0.01"))
        net_brl = (after_iof - ir_brl).quantize(Decimal("0.01"))

        net_pct = (net_brl / amount * Decimal("100")).quantize(Decimal("0.0001")) if amount > 0 else Decimal("0")

        return CashParkingRow(
            label=label, gross_annual_pct=gross_annual_pct, holding_days=holding_days,
            iof_pct=iof_pct, ir_pct=ir_pct, gross_value_brl=gross_brl,
            iof_value_brl=iof_brl, ir_value_brl=ir_brl, net_value_brl=net_brl,
            net_pct=net_pct, rank=0, note=note,
        )

    @staticmethod
    def _compound(annual_pct: Decimal, holding_days: int) -> Decimal:
        """(1 + r)^(d/365) - 1 in %, mirrors comparador._compound_return."""
        r = float(annual_pct) / 100
        compound = (1 + r) ** (holding_days / 365) - 1
        return Decimal(str(round(compound * 100, 4)))
```

**Step 2: Run tests**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_service.py -q
```

Expected: 4 passed.

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/modules/cash_flow_advisor/service.py backend/tests/test_cash_flow_advisor_service.py
git -C d:/claude-code/investiq commit -m "feat(cash_flow_advisor): CashParkingService ranking logic"
```

---

### Task 3.6: Router (red → green)

**Files:**
- Create: `backend/app/modules/cash_flow_advisor/router.py`
- Modify: `backend/app/main.py` (around line 149, after `advisor_router` registration)
- Create: `backend/tests/test_cash_flow_advisor_router.py`

**Step 1: Write failing endpoint test**

```python
"""GET /advisor/cash-parking — pulls DIAX, ranks, returns."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_cash_parking_returns_503_when_diax_unconfigured(client_with_auth):
    resp = await client_with_auth.get("/advisor/cash-parking")
    assert resp.status_code == 503
    assert "DIAX" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_cash_parking_happy_path(client_with_auth, monkeypatch):
    # mock DiaxClient + redis macro lookup
    # assert 200 + 6 rows + rank 1 has highest net_pct
    ...
```

> Borrow `client_with_auth` fixture from existing `tests/conftest.py` (or look for the pattern in `test_advisor_health.py`).

**Step 2: Run — expect 404**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_router.py -q
```

Expected: FAIL with 404 (route not registered yet).

**Step 3: Write router**

```python
"""GET /advisor/cash-parking — see design doc § 6.3."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.modules.auth.deps import get_current_user
from app.modules.cash_flow_advisor.client import DiaxClient, DiaxNotConfigured, DiaxUnreachable
from app.modules.cash_flow_advisor.schemas import CashParkingResponse
from app.modules.cash_flow_advisor.service import CashParkingService
from app.modules.market_universe.models import TaxConfig
from app.modules.comparador.service import _get_cdi_annual          # reuse
import os

router = APIRouter()


def _get_selic_annual() -> Decimal | None:
    """Mirror _get_cdi_annual but for selic — read market:macro:selic from Redis."""
    import redis as redis_lib
    try:
        r = redis_lib.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        raw = r.get("market:macro:selic")
        return Decimal(str(raw)) if raw else None
    except Exception:
        return None


@router.get("/cash-parking", response_model=CashParkingResponse)
async def get_cash_parking(
    _user=Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> CashParkingResponse:
    cdi = _get_cdi_annual()
    selic = _get_selic_annual()
    if not cdi or not selic:
        raise HTTPException(503, "Macro rates (CDI/Selic) unavailable in Redis")

    try:
        async with DiaxClient() as diax:
            projection = await diax.get_cash_flow_projection()
    except DiaxNotConfigured as exc:
        raise HTTPException(503, f"DIAX integration not configured: {exc}") from exc
    except DiaxUnreachable as exc:
        raise HTTPException(502, f"DIAX unreachable: {exc}") from exc

    tax_rows = (await global_db.execute(select(TaxConfig))).scalars().all()
    svc = CashParkingService(
        cdi_annual_pct=cdi, selic_annual_pct=selic, tax_config_rows=tax_rows,
    )
    return await svc.rank_options(projection, today=date.today())
```

**Step 4: Register router in `main.py`**

Add near line 149 (after `app.include_router(advisor_router, ...)`):

```python
from app.modules.cash_flow_advisor.router import router as cash_parking_router
app.include_router(cash_parking_router, prefix="/advisor", tags=["advisor"])
```

**Step 5: Run tests — expect green**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_cash_flow_advisor_router.py -q
```

Expected: 2 passed.

**Step 6: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/modules/cash_flow_advisor/router.py backend/app/main.py backend/tests/test_cash_flow_advisor_router.py
git -C d:/claude-code/investiq commit -m "feat(advisor): GET /advisor/cash-parking endpoint"
```

---

### Task 3.7: Action Inbox card (red → green)

**Files:**
- Modify: `backend/app/modules/advisor/service.py` (around line 519 — `compute_inbox`)
- Modify: `backend/tests/test_advisor_inbox.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_inbox_includes_cash_parking_card_when_diax_configured(monkeypatch, ...):
    """Mock DiaxClient + redis macro: inbox should yield 1 cash_parking card."""
    # ... setup mocks
    inbox = await compute_inbox(tenant_db=tdb, global_db=gdb, tenant_id=tid, redis_client=r)
    cash_card = next((c for c in inbox.cards if c.source == "cash_parking"), None)
    assert cash_card is not None
    assert "Tesouro Selic" in cash_card.body or "CDB" in cash_card.body
```

**Step 2: Run — expect failure**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_advisor_inbox.py::test_inbox_includes_cash_parking_card_when_diax_configured -q
```

Expected: FAIL.

**Step 3: Add the 6th source to compute_inbox**

In `compute_inbox`, after the swing_signals block (~line 583), add:

```python
    # 6. Cash parking (DIAX-driven) — degrades silently if DIAX not configured
    try:
        cards.extend(await _cash_parking_to_cards(global_db))
        sources_ok.append("cash_parking")
    except Exception as exc:
        logger.warning("inbox.cash_parking_failed tenant_id=%s err=%s", tenant_id, exc)
        sources_failed.append("cash_parking")
```

And implement `_cash_parking_to_cards`:

```python
async def _cash_parking_to_cards(global_db) -> list[InboxCard]:
    """Return 1 InboxCard if DIAX has available cash > R$ 1k AND best instrument > poupança."""
    from datetime import date
    from app.modules.cash_flow_advisor.client import DiaxClient, DiaxNotConfigured
    from app.modules.cash_flow_advisor.service import CashParkingService
    from app.modules.market_universe.models import TaxConfig
    from app.modules.comparador.service import _get_cdi_annual
    from app.modules.cash_flow_advisor.router import _get_selic_annual

    try:
        async with DiaxClient() as diax:
            projection = await diax.get_cash_flow_projection()
    except DiaxNotConfigured:
        return []

    if projection.available_to_invest < Decimal("1000"):
        return []

    cdi = _get_cdi_annual()
    selic = _get_selic_annual()
    if not cdi or not selic:
        return []

    from sqlalchemy import select
    tax_rows = (await global_db.execute(select(TaxConfig))).scalars().all()
    svc = CashParkingService(cdi_annual_pct=cdi, selic_annual_pct=selic, tax_config_rows=tax_rows)
    result = await svc.rank_options(projection, today=date.today())

    if not result.rows:
        return []
    top = result.rows[0]
    if "Poup" in top.label:                  # poupança is never a recommendation
        return []

    return [InboxCard(
        id=f"cash_parking:{top.label}:{result.holding_days}",
        source="cash_parking",
        severity=InboxSeverity.INFO,
        priority=60,
        title=f"R$ {projection.available_to_invest:.0f} parado — aplicar em {top.label}",
        body=f"Janela de {result.holding_days} dias. Rendimento líquido estimado: R$ {top.net_value_brl:.2f} ({top.net_pct:.2f}%).",
        cta=InboxCardCTA(label="Ver opções", url="/caixa"),
        created_at=datetime.now(tz=timezone.utc),
    )]
```

**Step 4: Run — expect green**

```bash
cd d:/claude-code/investiq && pytest backend/tests/test_advisor_inbox.py -q
```

Expected: all existing tests still pass + new one passes.

**Step 5: Commit**

```bash
git -C d:/claude-code/investiq add backend/app/modules/advisor/service.py backend/tests/test_advisor_inbox.py
git -C d:/claude-code/investiq commit -m "feat(advisor): cash_parking source in Action Inbox"
```

---

### Task 3.8: Phase 3 verification

**Step 1: Run full backend test suite**

```bash
cd d:/claude-code/investiq && pytest backend/tests/ -q
```

Expected: all tests pass; ~12 new tests added.

**Step 2: Manual smoke test (requires DIAX running locally with seed data)**

```bash
cd d:/claude-code/investiq && uvicorn app.main:app --reload --port 8000
# In another terminal, with a valid user JWT:
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/advisor/cash-parking | jq
```

Expected: 200 with 6 rows ranked by net_pct desc.

✅ **Phase 3 done.**

---

## Phase 4 — Frontend (~1-2h)

### Task 4.1: TanStack Query hook

**Files:**
- Create: `frontend/src/features/cash_flow_advisor/hooks/useCashParking.ts`

**Step 1: Write the hook**

```ts
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface CashParkingRow {
  label: string;
  gross_annual_pct: string;
  holding_days: number;
  iof_pct: string;
  ir_pct: string;
  gross_value_brl: string;
  iof_value_brl: string;
  ir_value_brl: string;
  net_value_brl: string;
  net_pct: string;
  rank: number;
  note: string | null;
}

export interface CashParkingResponse {
  amount: string;
  holding_days: number;
  rows: CashParkingRow[];
  next_big_outflow: { date: string; amount: string; description: string } | null;
  generated_at: string;
  warnings: string[];
}

export function useCashParking() {
  return useQuery<CashParkingResponse>({
    queryKey: ["advisor", "cash-parking"],
    queryFn: async () => (await apiClient.get("/advisor/cash-parking")).data,
    staleTime: 5 * 60 * 1000,                  // 5 min on the client
  });
}
```

**Step 2: Verify it type-checks**

```bash
cd d:/claude-code/investiq/frontend && npx tsc --noEmit
```

Expected: no errors related to the new file.

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add frontend/src/features/cash_flow_advisor/
git -C d:/claude-code/investiq commit -m "feat(frontend): useCashParking hook"
```

---

### Task 4.2: Components

**Files:**
- Create: `frontend/src/features/cash_flow_advisor/components/CashParkingHero.tsx`
- Create: `frontend/src/features/cash_flow_advisor/components/CashParkingTable.tsx`

**Step 1: Hero card** (top recommendation, large net_pct, "Aplicar em X" CTA)

**Step 2: Table** (all 6 rows, columns: rank, label, gross_pct, holding_days, IOF, IR, net_brl, net_pct, note)

> Mirror `frontend/src/features/comparador/components/ComparadorTable.tsx` for structure (table primitives, formatters, currency display).

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add frontend/src/features/cash_flow_advisor/components/
git -C d:/claude-code/investiq commit -m "feat(frontend): CashParkingHero + CashParkingTable"
```

---

### Task 4.3: /caixa page

**Files:**
- Create: `frontend/src/app/caixa/page.tsx`

**Step 1: Compose the page**

```tsx
"use client";
import { useCashParking } from "@/features/cash_flow_advisor/hooks/useCashParking";
import { CashParkingHero } from "@/features/cash_flow_advisor/components/CashParkingHero";
import { CashParkingTable } from "@/features/cash_flow_advisor/components/CashParkingTable";

export default function CaixaPage() {
  const { data, isLoading, error } = useCashParking();

  if (isLoading) return <div className="p-8">Carregando…</div>;
  if (error || !data) return <div className="p-8 text-destructive">Erro ao carregar.</div>;
  if (data.rows.length === 0) {
    return (
      <div className="p-8 space-y-4">
        <h1 className="text-2xl font-bold">Caixa</h1>
        {data.warnings.map((w, i) => <div key={i} className="text-muted-foreground">{w}</div>)}
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Onde aplicar seu caixa?</h1>
      <CashParkingHero data={data} />
      <CashParkingTable rows={data.rows} />
    </div>
  );
}
```

**Step 2: Smoke test in browser**

```bash
cd d:/claude-code/investiq/frontend && npm run dev
```

Navigate to http://localhost:3100/caixa — verify 6 rows render, rank 1 highlighted in hero.

**Step 3: Commit**

```bash
git -C d:/claude-code/investiq add frontend/src/app/caixa/page.tsx
git -C d:/claude-code/investiq commit -m "feat(frontend): /caixa page"
```

---

### Task 4.4: E2E manual verification

**Step 1: Start DIAX, InvestIQ backend, InvestIQ frontend in three terminals.**

**Step 2: In browser**
- Log into InvestIQ
- Open Action Inbox — verify cash_parking card appears (if DIAX has available_to_invest > R$ 1k)
- Click "Ver opções" — should navigate to /caixa
- Verify hero shows top recommendation, table shows 6 rows, IOF column matches design table for the holding window

**Step 3: Update memory**

Update `C:/Users/acq20/.claude/projects/d--claude-code-investiq/memory/MEMORY.md` and `resume_cash-parking-feature.md`:
- Mark feature as IMPLEMENTED with commit hashes
- Remove from "ACTIVE WORK" section
- Add a one-liner "feat: cash parking advisor" under v1.5 phase progress

**Step 4: PR**

```bash
git -C d:/claude-code/investiq push -u origin feat/cash-parking-advisor
git -C d:/claude-code/diax-crm push -u origin feat/cash-flow-projection-endpoint
gh pr create --repo <investiq-remote> --title "feat: cash parking advisor (/caixa, /advisor/cash-parking)" --body "$(cat <<'EOF'
## Summary
- New deterministic cash-parking advisor: pulls DIAX cash flow → computes IR + IOF + poupança aniversário → ranks 6 instruments
- New IOFEngine (Decreto 6.306/2007 30-day table)
- New /caixa page + Action Inbox card

## Test plan
- [ ] All backend tests green (`pytest backend/tests/`)
- [ ] All DIAX tests green (`dotnet test`)
- [ ] Manual: /caixa renders 6 rows, IOF correct for window
- [ ] Manual: inbox card appears when available_to_invest > R$ 1k

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

✅ **Phase 4 done. Feature shipped.**

---

## Risk register

| Risk | Mitigation |
|---|---|
| DIAX `IIncomeRepository`/`IExpenseRepository` interface names differ from what I wrote | Read the actual interfaces before Task 1.4. Adjust DI signature; don't invent. |
| `TestHarness` / `ApiTestHarness` doesn't exist in DIAX | Build a minimal one from `WebApplicationFactory<Program>`. Look for any existing controller test first. |
| `_get_cdi_annual` import from `comparador.service` introduces a circular dep | If circular, move the function to a shared helper module (`market_universe/macro.py`) and update both call sites in same commit. |
| pytest-httpx not installed | `pip install pytest-httpx` and add to requirements-dev.txt at Task 3.3. |
| Pydantic alias generator + `populate_by_name` not playing nicely with nested models | Already handled — using explicit `_camel_to_snake` recursive normalizer in the client. Skip alias generators entirely. |
| Phase 3 router test needs auth fixture not present in conftest | Copy from `test_advisor_health.py` — it has `client_with_auth` pattern. |
| Poupança anniversary logic is over-simplified | Acceptable for v1; add TODO + memory note for v1.1. |

---

## Execution Handoff

**Plan complete and saved to `docs/plans/2026-04-30-cash-parking-feature-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Parallel Session (separate)** — Open new session with `executing-plans`, batch execution with checkpoints.

**Which approach?**
