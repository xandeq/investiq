# Phase 13: Core Analysis Engine - Research

**Researched:** 2026-03-31
**Status:** Ready for planning

---

## 1. BRAPI API - Fundamentals Data

### 1.1 Existing Integration

The project already has `BrapiClient` at `backend/app/modules/market_data/adapters/brapi.py` with:
- Token resolution: constructor arg > `BRAPI_TOKEN` env var > AWS SM `tools/brapi` > empty (free tier)
- Retry on 429/5xx with 5s backoff
- 200ms sleep between batch calls
- Methods: `fetch_quotes()`, `fetch_fundamentals()`, `fetch_historical()`, `fetch_ibovespa()`

The existing `fetch_fundamentals()` only returns `pl`, `pvp`, `dy`, `ev_ebitda`. Phase 13 needs a much richer extraction.

### 1.2 Quote Endpoint with Modules

**Endpoint:** `GET https://brapi.dev/api/quote/{TICKER}?modules={modules}&token={token}`

**Modules needed for Phase 13:**

| Module | Fields Extracted | Used By |
|--------|-----------------|---------|
| `summaryProfile` | `sector`, `sectorKey`, `industry` | Sector peers (D-26) |
| `defaultKeyStatistics` | `priceToBook`, `trailingPE`, `earningsPerShare`, `beta`, `enterpriseValue`, `enterpriseToEbitda`, `bookValue`, `pegRatio`, `yield` | DCF, Earnings, Dividends, Sector |
| `financialData` | `totalRevenue`, `ebitda`, `freeCashflow`, `totalDebt`, `totalCash`, `debtToEquity`, `profitMargins`, `returnOnEquity`, `currentRatio`, `dividendYield` | DCF, Earnings, Sector |
| `incomeStatementHistory` | `totalRevenue`, `costOfRevenue`, `grossProfit`, `ebit`, `netIncome` (per year, 16 years available) | Earnings history, growth CAGR |
| `cashflowHistory` | `operatingCashFlow`, `investmentCashFlow`, `financingCashFlow`, `freeCashFlow` (per year, 16 years available) | DCF (FCF), Earnings quality |

**Single call for all analysis types:**
```
GET /quote/{TICKER}?modules=summaryProfile,defaultKeyStatistics,financialData,incomeStatementHistory,cashflowHistory&fundamental=true&dividends=true&token={token}
```

### 1.3 Response Field Mapping (Verified from Live API)

```python
# From summaryProfile
sector = result["summaryProfile"]["sector"]           # "Energia"
sector_key = result["summaryProfile"]["sectorKey"]     # "energia"
industry = result["summaryProfile"]["industry"]        # "Petroleo e Gas Integrado"

# From defaultKeyStatistics
price_to_book = result["defaultKeyStatistics"]["priceToBook"]       # 1.533
trailing_pe = result["defaultKeyStatistics"]["trailingPE"]          # 6.368
eps = result["defaultKeyStatistics"]["earningsPerShare"]            # 8.582
beta = result["defaultKeyStatistics"].get("beta")                   # null for some tickers
enterprise_value = result["defaultKeyStatistics"]["enterpriseValue"]# 1264262300000
ev_ebitda = result["defaultKeyStatistics"].get("enterpriseToEbitda")
book_value = result["defaultKeyStatistics"]["bookValue"]            # 32.399
div_yield_stat = result["defaultKeyStatistics"].get("yield")        # 0.06

# From financialData
total_revenue = result["financialData"]["totalRevenue"]             # 497549000000
ebitda = result["financialData"]["ebitda"]                          # 230015990000
free_cash_flow = result["financialData"]["freeCashflow"]            # 94680000000
total_debt = result["financialData"]["totalDebt"]                   # 674687000000
total_cash = result["financialData"]["totalCash"]                   # 50608000000
debt_to_equity = result["financialData"]["debtToEquity"]            # 1.616
profit_margins = result["financialData"]["profitMargins"]           # 0.222
roe = result["financialData"]["returnOnEquity"]                     # 0.265
current_ratio = result["financialData"]["currentRatio"]             # 0.706

# From incomeStatementHistory (array, most recent first)
for stmt in result["incomeStatementHistory"]:
    year = stmt["endDate"]  # or inferred from array position
    revenue = stmt["totalRevenue"]
    net_income = stmt["netIncome"]
    gross_profit = stmt["grossProfit"]
    ebit = stmt["ebit"]

# From cashflowHistory (array, most recent first)
for cf in result["cashflowHistory"]:
    operating_cf = cf["operatingCashFlow"]
    fcf = cf["freeCashFlow"]
    investing_cf = cf["investmentCashFlow"]
    financing_cf = cf["financingCashFlow"]

# From dividendsData.cashDividends (array)
for div in result["dividendsData"]["cashDividends"]:
    rate = div["rate"]                # BRL per share
    payment_date = div["paymentDate"] # ISO 8601
    ex_date = div["lastDatePrior"]    # ex-dividend date
    label = div["label"]              # "DIVIDENDO" | "JCP" | "RENDIMENTO"
```

### 1.4 Value Extraction Gotcha

BRAPI sometimes returns values as raw numbers, sometimes as `{"raw": 1.53, "fmt": "1.53"}` dicts. The existing `_extract()` helper in `brapi.py` handles this:

```python
def _extract(d: dict, key: str) -> float | None:
    val = d.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        return val.get("raw")
    return val
```

Phase 13 must reuse this pattern for all field extractions.

### 1.5 Sector Peer Discovery

**Endpoint:** `GET https://brapi.dev/api/quote/list?sector={sector_name}&token={token}`

**Response structure:**
```json
{
  "stocks": [
    {
      "stock": "PETR4",
      "name": "Petrobras PN",
      "close": 48.67,
      "change": 0.5,
      "volume": 45000000,
      "market_cap": 640000000000,
      "sector": "Energy Minerals",
      "type": "stock",
      "logo": "https://..."
    }
  ],
  "availableSectors": ["Energy Minerals", "Finance", ...],
  "currentPage": 1,
  "totalPages": 10,
  "totalCount": 93
}
```

**Important:** The `sector` field in `/quote/list` uses English names ("Energy Minerals") while `summaryProfile.sector` returns Portuguese ("Energia"). Need mapping or use `sectorKey` for matching.

**Peer selection algorithm:**
1. Fetch ticker's `summaryProfile` to get `sector` + `industry`
2. Call `/quote/list?sector={sector}` to get all stocks in sector
3. Filter: same `type=stock`, exclude the target ticker, exclude `market_cap=null`
4. Sort by market cap proximity to target
5. Take top 10 peers
6. If <3 peers in exact sector, broaden search (drop industry filter)
7. For each peer, fetch `defaultKeyStatistics` + `financialData` for P/E, P/B, DY, EV/EBITDA

**API call budget per sector comparison:** 1 (target profile) + 1 (list) + N (peer fundamentals) = ~12 calls. With 200ms sleep = ~2.4s network time.

### 1.6 Caching Strategy

Per D-08: Cache all BRAPI fundamentals in Redis with 24h TTL per ticker.

```python
CACHE_KEY_PATTERN = "brapi:fundamentals:{ticker}"
CACHE_TTL = 86400  # 24 hours

# On fetch:
cached = redis.get(f"brapi:fundamentals:{ticker}")
if cached:
    return json.loads(cached)
data = brapi_client.fetch_full_fundamentals(ticker)
redis.setex(f"brapi:fundamentals:{ticker}", CACHE_TTL, json.dumps(data))
return data
```

---

## 2. BCB API - SELIC Rate

### 2.1 Endpoint

**URL:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/{N}?formato=json`

- Series 432 = SELIC target rate (meta)
- No authentication required
- No rate limiting documented (public API)
- Returns JSON array

### 2.2 Response Format

```json
[
  {
    "data": "25/04/2026",
    "valor": "14.75"
  },
  {
    "data": "28/04/2026",
    "valor": "14.75"
  }
]
```

- `data`: Brazilian date format `DD/MM/YYYY`
- `valor`: Rate as string (annualized percentage, e.g., "14.75" means 14.75%)
- Entries are daily (business days only)
- Fetch `ultimos/1` to get the current rate

### 2.3 Implementation

```python
import requests
from datetime import datetime

BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"

def fetch_selic_rate() -> tuple[float, str]:
    """Fetch current SELIC rate from BCB API.

    Returns:
        (rate_decimal, date_str) e.g. (0.1475, "2026-04-28")
    """
    resp = requests.get(BCB_SELIC_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    entry = data[-1]  # most recent
    rate_pct = float(entry["valor"])
    rate_decimal = rate_pct / 100.0
    # Parse DD/MM/YYYY to YYYY-MM-DD
    date_obj = datetime.strptime(entry["data"], "%d/%m/%Y")
    date_str = date_obj.strftime("%Y-%m-%d")
    return (rate_decimal, date_str)
```

### 2.4 Caching

Per D-07: Cache 24h (SELIC changes ~6x/year via COPOM meetings).

```python
SELIC_CACHE_KEY = "bcb:selic:current"
SELIC_CACHE_TTL = 86400  # 24 hours

def get_selic_rate() -> tuple[float, str]:
    cached = redis.get(SELIC_CACHE_KEY)
    if cached:
        data = json.loads(cached)
        return (data["rate"], data["date"])
    rate, date = fetch_selic_rate()
    redis.setex(SELIC_CACHE_KEY, SELIC_CACHE_TTL, json.dumps({"rate": rate, "date": date}))
    return (rate, date)
```

### 2.5 Fallback

If BCB API is unreachable, use a hardcoded fallback with a warning flag:

```python
SELIC_FALLBACK = 0.1475  # Updated manually when COPOM changes rate
SELIC_FALLBACK_DATE = "2026-03-19"

def get_selic_rate_safe() -> tuple[float, str, bool]:
    """Returns (rate, date, is_fallback)."""
    try:
        rate, date = get_selic_rate()
        return (rate, date, False)
    except Exception:
        logger.warning("BCB API unreachable — using SELIC fallback %s", SELIC_FALLBACK)
        return (SELIC_FALLBACK, SELIC_FALLBACK_DATE, True)
```

---

## 3. DCF: 2-Stage FCFF with CAPM WACC

### 3.1 WACC Calculation (CAPM)

Per D-03: `Ke = SELIC + Beta * ERP(7%)`

```python
ERP_BRAZIL = 0.07  # Equity Risk Premium for Brazil (Damodaran ~7%)

def calculate_wacc(
    selic: float,      # e.g. 0.1475
    beta: float,       # from BRAPI defaultKeyStatistics
    debt: float,       # totalDebt from financialData
    equity: float,     # market_cap
    tax_rate: float = 0.34,  # Brazilian corporate tax (IR+CSLL)
) -> float:
    """Calculate WACC using CAPM for cost of equity.

    Ke = SELIC + Beta * ERP
    Kd = SELIC + 2% spread (assumption for investment-grade BR companies)
    WACC = Ke * (E/(D+E)) + Kd * (1-T) * (D/(D+E))
    """
    ke = selic + beta * ERP_BRAZIL
    kd = selic + 0.02  # simplified debt cost
    total_capital = debt + equity
    if total_capital <= 0:
        return ke  # fallback to all-equity
    weight_equity = equity / total_capital
    weight_debt = debt / total_capital
    wacc = ke * weight_equity + kd * (1 - tax_rate) * weight_debt
    return wacc
```

**Beta fallback:** BRAPI returns `beta: null` for some tickers. Use `1.0` (market average) when missing, flagged in `data_completeness`.

### 3.2 2-Stage FCFF Model

Per D-01/D-02:
- Stage 1: 5-year explicit growth using user-provided or default growth rate
- Stage 2: Terminal value with perpetual growth

```python
def calculate_dcf(
    fcf_current: float,       # Most recent annual FCF from cashflowHistory
    shares_outstanding: float, # market_cap / current_price
    growth_rate: float,        # Default 5% (D-05), user can override
    wacc: float,               # From CAPM calculation above
    terminal_growth: float,    # Default 3% (D-05), user can override
) -> dict:
    """2-Stage FCFF DCF valuation.

    Returns dict with fair_value, projected_fcfs, terminal_value, etc.
    """
    if wacc <= terminal_growth:
        raise ValueError("WACC must exceed terminal growth rate")

    # Stage 1: Project FCFs for years 1-5
    projected_fcfs = []
    fcf = fcf_current
    for year in range(1, 6):
        fcf = fcf * (1 + growth_rate)
        pv = fcf / (1 + wacc) ** year
        projected_fcfs.append({
            "year": year,
            "fcf": fcf,
            "present_value": pv,
        })

    # Stage 2: Terminal Value
    fcf_year5 = projected_fcfs[-1]["fcf"]
    terminal_value = fcf_year5 * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** 5

    # Enterprise Value
    pv_fcfs = sum(p["present_value"] for p in projected_fcfs)
    enterprise_value = pv_fcfs + pv_terminal

    # Equity Value (simplified: EV - net debt)
    # Note: net_debt = total_debt - total_cash (from financialData)
    # Passed in separately or computed outside

    # Fair Value per share
    fair_value_per_share = enterprise_value / shares_outstanding

    return {
        "fair_value": round(fair_value_per_share, 2),
        "enterprise_value": round(enterprise_value, 2),
        "pv_stage1": round(pv_fcfs, 2),
        "pv_terminal": round(pv_terminal, 2),
        "terminal_value": round(terminal_value, 2),
        "projected_fcfs": projected_fcfs,
        "assumptions": {
            "growth_rate": growth_rate,
            "wacc": round(wacc, 4),
            "terminal_growth": terminal_growth,
        },
    }
```

### 3.3 Sensitivity Analysis (Fair Value Range)

Per D-04: Vary growth +/-2pp and discount rate +/-2pp for low/base/high.

```python
def calculate_dcf_with_sensitivity(
    fcf_current: float,
    shares_outstanding: float,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
    net_debt: float,
) -> dict:
    """Run 3 DCF scenarios: bear (low), base, bull (high)."""

    scenarios = {
        "low": {  # Bear: lower growth, higher discount
            "growth_rate": max(0, growth_rate - 0.02),
            "wacc": wacc + 0.02,
            "terminal_growth": terminal_growth,
        },
        "base": {
            "growth_rate": growth_rate,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
        },
        "high": {  # Bull: higher growth, lower discount
            "growth_rate": growth_rate + 0.02,
            "wacc": max(terminal_growth + 0.01, wacc - 0.02),
            "terminal_growth": terminal_growth,
        },
    }

    results = {}
    for scenario_name, params in scenarios.items():
        dcf = calculate_dcf(
            fcf_current=fcf_current,
            shares_outstanding=shares_outstanding,
            **params,
        )
        # Adjust for net debt: equity_value = EV - net_debt
        equity_value = dcf["enterprise_value"] - net_debt
        fair_value = equity_value / shares_outstanding
        results[scenario_name] = {
            "fair_value": round(fair_value, 2),
            "assumptions": params,
        }

    base_fv = results["base"]["fair_value"]

    return {
        "fair_value": base_fv,
        "fair_value_range": {
            "low": results["low"]["fair_value"],
            "high": results["high"]["fair_value"],
        },
        "scenarios": results,
        # D-11: key drivers — which input moves FV most
        "key_drivers": _identify_key_drivers(results),
    }

def _identify_key_drivers(scenarios: dict) -> list[str]:
    """Identify which assumption has the biggest impact on fair value."""
    base = scenarios["base"]["fair_value"]
    low = scenarios["low"]["fair_value"]
    high = scenarios["high"]["fair_value"]

    # Growth sensitivity: high uses +2pp growth, low uses -2pp growth
    # Discount sensitivity: high uses -2pp WACC, low uses +2pp WACC
    # Since both vary together, approximate:
    spread = high - low
    if spread > 0:
        return [
            f"Fair value range R${low:.2f} - R${high:.2f} ({spread/base*100:.0f}% spread)",
            "Growth rate assumption has significant impact on valuation",
            "Discount rate (WACC) sensitivity amplifies in high-debt companies",
        ]
    return ["Valuation is relatively stable across scenarios"]
```

### 3.4 Growth Rate Default Estimation

Per D-05 (Claude's Discretion): Use historical FCF CAGR when available.

```python
def estimate_growth_rate(cashflow_history: list[dict], default: float = 0.05) -> float:
    """Estimate growth rate from historical FCF CAGR.

    Uses last 5 years of FCF data. Falls back to default if:
    - Less than 3 years of data
    - Negative FCF in base year
    - CAGR is unreasonably high (>30%) or negative
    """
    fcfs = []
    for cf in cashflow_history[:5]:  # Most recent 5 years
        fcf = cf.get("freeCashFlow")
        if fcf is not None and fcf > 0:
            fcfs.append(fcf)

    if len(fcfs) < 3:
        return default

    # CAGR = (end/start)^(1/n) - 1
    start = fcfs[-1]  # oldest
    end = fcfs[0]     # newest
    n = len(fcfs) - 1

    if start <= 0 or end <= 0:
        return default

    cagr = (end / start) ** (1 / n) - 1

    # Clamp to reasonable range
    if cagr < 0 or cagr > 0.30:
        return default

    return round(cagr, 4)
```

---

## 4. Earnings Quality Analysis

### 4.1 EPS History with Growth Rates (D-12)

```python
def calculate_earnings_history(
    income_history: list[dict],
    shares_outstanding: float,
) -> dict:
    """Build 5-year EPS history with YoY growth and CAGR.

    Uses incomeStatementHistory from BRAPI (netIncome per year).
    """
    entries = []
    for i, stmt in enumerate(income_history[:5]):
        net_income = stmt.get("netIncome", 0)
        eps = net_income / shares_outstanding if shares_outstanding > 0 else 0
        revenue = stmt.get("totalRevenue", 0)

        entry = {
            "year": stmt.get("endDate", f"Y-{i}"),
            "net_income": net_income,
            "eps": round(eps, 2),
            "revenue": revenue,
            "yoy_growth": None,  # Filled below
        }
        entries.append(entry)

    # Calculate YoY growth (comparing consecutive years)
    for i in range(len(entries) - 1):
        current_eps = entries[i]["eps"]
        previous_eps = entries[i + 1]["eps"]
        if previous_eps != 0:
            entries[i]["yoy_growth"] = round(
                (current_eps - previous_eps) / abs(previous_eps), 4
            )

    # 5-year EPS CAGR
    cagr = None
    if len(entries) >= 2:
        newest = entries[0]["eps"]
        oldest = entries[-1]["eps"]
        n = len(entries) - 1
        if oldest > 0 and newest > 0:
            cagr = round((newest / oldest) ** (1 / n) - 1, 4)

    return {
        "eps_history": entries,
        "eps_cagr_5y": cagr,
    }
```

### 4.2 Accrual Ratio (D-13)

The accrual ratio measures the portion of earnings not backed by cash. Lower is better.

**Formula:** `Accrual Ratio = (Net Income - Operating Cash Flow) / Total Assets`

```python
def calculate_accrual_ratio(
    net_income: float,
    operating_cash_flow: float,
    total_assets: float,
) -> float | None:
    """Calculate accrual ratio.

    Interpretation (per D-13):
    - < 0.20: Good (high cash quality)
    - 0.20 - 0.40: Moderate
    - > 0.40: Poor (earnings not backed by cash)

    Note: Can be negative (very good — cash exceeds reported earnings).
    """
    if total_assets <= 0:
        return None
    return round((net_income - operating_cash_flow) / total_assets, 4)
```

**Data source:** `netIncome` from `incomeStatementHistory[0]`, `operatingCashFlow` from `cashflowHistory[0]`. For `totalAssets`, use `balanceSheetHistory` module or approximate from `totalDebt + totalCash + (market_cap * bookValue_ratio)`.

Simplified approach (avoids extra API call): use `totalDebt + totalCash` from `financialData` as a proxy denominator when `balanceSheetHistory` is not available. Flag as approximate in `data_completeness`.

### 4.3 FCF Conversion Rate (D-13)

**Formula:** `FCF Conversion = Free Cash Flow / Net Income`

```python
def calculate_fcf_conversion(
    free_cash_flow: float,
    net_income: float,
) -> float | None:
    """Calculate FCF conversion rate.

    Interpretation (per D-13):
    - > 0.80: Good (healthy cash generation)
    - 0.50 - 0.80: Moderate
    - < 0.50: Poor (earnings not converting to cash)
    - > 1.50: Investigate (possibly unsustainable capex cuts)

    Returns None if net_income <= 0 (negative earnings make ratio meaningless).
    """
    if net_income <= 0:
        return None
    return round(free_cash_flow / net_income, 4)
```

### 4.4 Earnings Quality Flag

```python
def assess_earnings_quality(
    accrual_ratio: float | None,
    fcf_conversion: float | None,
) -> str:
    """Return 'high', 'medium', or 'low' earnings quality assessment.

    Rules (per D-13):
    - high: accrual < 0.20 AND fcf_conversion > 0.80
    - low: accrual > 0.40 OR fcf_conversion < 0.50
    - medium: everything else
    """
    if accrual_ratio is None or fcf_conversion is None:
        return "medium"  # Insufficient data, default to middle

    if accrual_ratio < 0.20 and fcf_conversion > 0.80:
        return "high"
    if accrual_ratio > 0.40 or fcf_conversion < 0.50:
        return "low"
    return "medium"
```

---

## 5. Dividend Sustainability Analysis

### 5.1 Data Extraction from BRAPI

BRAPI dividend data comes from `dividendsData.cashDividends` array when `?dividends=true`. Each entry has:
- `rate`: BRL per share
- `paymentDate`: ISO 8601
- `label`: "DIVIDENDO" | "JCP" | "RENDIMENTO"
- `lastDatePrior`: ex-dividend date

To compute annual DPS: sum `rate` for all entries within each calendar year.

```python
from collections import defaultdict
from datetime import datetime

def aggregate_annual_dividends(cash_dividends: list[dict]) -> dict[int, float]:
    """Aggregate per-share dividends by calendar year.

    Groups by paymentDate year, sums rate across all types
    (DIVIDENDO + JCP + RENDIMENTO).
    """
    by_year = defaultdict(float)
    for div in cash_dividends:
        try:
            dt = datetime.fromisoformat(div["paymentDate"].replace("Z", "+00:00"))
            by_year[dt.year] += div["rate"]
        except (KeyError, ValueError):
            continue
    return dict(sorted(by_year.items(), reverse=True))
```

### 5.2 Dividend Coverage Ratio (D-16)

**Formula:** `Coverage Ratio = EPS / DPS`

```python
def calculate_dividend_coverage(eps: float, dps: float) -> float | None:
    """Calculate dividend coverage ratio.

    Interpretation:
    - > 2.0: Very safe
    - 1.5 - 2.0: Safe
    - 1.2 - 1.5: Adequate
    - < 1.2: Warning — company paying more than it earns
    """
    if dps <= 0:
        return None  # No dividends paid
    return round(eps / dps, 2)
```

### 5.3 Payout Ratio (D-16)

**Formula:** `Payout Ratio = DPS / EPS` (inverse of coverage)

```python
def calculate_payout_ratio(dps: float, eps: float) -> float | None:
    """Payout ratio as decimal (0.0 to 1.0+).

    > 1.0 means paying more than earnings (unsustainable long-term).
    """
    if eps <= 0:
        return None
    return round(dps / eps, 4)
```

### 5.4 Consistency Score (D-17)

```python
def calculate_consistency_score(annual_dividends: dict[int, float], years: int = 5) -> dict:
    """5-year dividend consistency: how many of the last 5 years had dividends.

    Returns:
        {"paid_years": 4, "total_years": 5, "score": 0.80}
    """
    current_year = datetime.now().year
    target_years = list(range(current_year - years, current_year))
    paid_years = sum(1 for y in target_years if annual_dividends.get(y, 0) > 0)
    return {
        "paid_years": paid_years,
        "total_years": years,
        "score": round(paid_years / years, 2),
    }
```

### 5.5 Sustainability Assessment (D-18)

```python
def assess_dividend_sustainability(
    payout_ratio: float | None,
    coverage_ratio: float | None,
    annual_dividends: dict[int, float],
) -> str:
    """Return 'safe', 'warning', or 'risk'.

    Rules (per D-18):
    - risk: payout > 80% OR coverage < 1.2x OR dividend cut in last 3 years
    - warning: payout > 60% OR coverage < 1.5x
    - safe: everything else
    """
    # Check for dividend cut in last 3 years
    current_year = datetime.now().year
    recent = [annual_dividends.get(y, 0) for y in range(current_year - 3, current_year)]
    has_cut = False
    for i in range(len(recent) - 1):
        if recent[i + 1] > 0 and recent[i] < recent[i + 1] * 0.80:
            has_cut = True
            break

    if has_cut:
        return "risk"
    if payout_ratio is not None and payout_ratio > 0.80:
        return "risk"
    if coverage_ratio is not None and coverage_ratio < 1.2:
        return "risk"
    if payout_ratio is not None and payout_ratio > 0.60:
        return "warning"
    if coverage_ratio is not None and coverage_ratio < 1.5:
        return "warning"
    return "safe"
```

---

## 6. Sector Peer Comparison

### 6.1 Peer Discovery Algorithm

```
1. GET /quote/{TICKER}?modules=summaryProfile → sector, industry
2. GET /quote/list?sector={sector} → list of tickers in same sector
3. Filter: type=stock, market_cap not null, exclude target ticker
4. Sort by market_cap proximity to target
5. Take top 10
6. If < 3 results, retry without industry filter (broader sector)
7. For each peer: GET /quote/{PEER}?modules=defaultKeyStatistics,financialData
```

**Sector name mapping issue:** `/quote/list` uses English sector names ("Energy Minerals") while `summaryProfile.sector` returns Portuguese ("Energia"). Solution: maintain a mapping dict or use the `sectorKey` field.

```python
# Sector mapping: summaryProfile.sector (PT) -> /quote/list sector param (EN)
SECTOR_MAP_PT_TO_EN = {
    "Energia": "Energy Minerals",
    "Financeiro": "Finance",
    "Materiais Basicos": "Non-Energy Minerals",
    "Saude": "Health Services",
    "Tecnologia": "Technology Services",
    "Consumo Ciclico": "Consumer Durables",
    "Consumo Nao Ciclico": "Consumer Non-Durables",
    "Industrial": "Producer Manufacturing",
    "Utilidades Publicas": "Utilities",
    "Comunicacoes": "Communications",
    "Imobiliario": "Finance",  # REITs classified under Finance in BRAPI
    # Add more as discovered
}
```

**Alternative approach:** Use `/quote/list` with no sector filter, paginate all stocks, and match by the `sector` field in the response (which is in English). This avoids the mapping problem but requires more API calls.

**Recommended approach:** Call `/quote/list?sector={english_sector}` using the mapping. Cache the full sector stock list for 24h in Redis (sector compositions change infrequently).

### 6.2 Metrics Table (D-21)

For each peer, extract:

| Metric | Source | Field |
|--------|--------|-------|
| P/E | `defaultKeyStatistics` | `trailingPE` |
| P/B | `defaultKeyStatistics` | `priceToBook` |
| DY | `financialData` or `defaultKeyStatistics` | `dividendYield` or `yield` |
| EV/EBITDA | `defaultKeyStatistics` | `enterpriseToEbitda` |

### 6.3 Peer Ranking (D-22)

```python
def rank_stock_in_peers(
    target_ticker: str,
    target_metrics: dict,
    peers_metrics: list[dict],
) -> dict:
    """Rank target stock within peer group for each metric.

    Returns rank and percentile for P/E, P/B, DY, EV/EBITDA.
    Lower P/E rank = cheaper. Higher DY rank = more attractive.
    """
    all_stocks = [{"ticker": target_ticker, **target_metrics}] + peers_metrics
    total = len(all_stocks)

    rankings = {}
    for metric in ["pe", "pb", "dy", "ev_ebitda"]:
        # Filter stocks with non-null values
        valid = [s for s in all_stocks if s.get(metric) is not None]
        if not valid:
            continue

        # Sort: for PE/PB/EV_EBITDA lower is cheaper; for DY higher is better
        reverse = metric == "dy"
        sorted_stocks = sorted(valid, key=lambda s: s[metric], reverse=reverse)

        rank = next(
            (i + 1 for i, s in enumerate(sorted_stocks) if s["ticker"] == target_ticker),
            None,
        )
        if rank:
            pct = round((total - rank) / (total - 1) * 100) if total > 1 else 50
            label = "cheaper" if metric != "dy" else "higher yield"
            rankings[f"{metric}_rank"] = f"{rank}/{len(valid)}, {label} than {pct}%"

    return rankings
```

### 6.4 Data Completeness (D-23, D-24)

```python
def assess_peer_completeness(peers_data: list[dict]) -> dict:
    """Assess data completeness for peer comparison.

    Returns per-peer completeness flag and aggregate summary.
    """
    required_metrics = ["pe", "pb", "dy", "ev_ebitda"]

    peer_status = []
    complete_count = 0
    for peer in peers_data:
        available = [m for m in required_metrics if peer.get(m) is not None]
        missing = [m for m in required_metrics if peer.get(m) is None]
        is_complete = len(missing) == 0
        if is_complete:
            complete_count += 1
        peer_status.append({
            "ticker": peer["ticker"],
            "complete": is_complete,
            "available": available,
            "missing": missing,
        })

    total = len(peers_data)
    return {
        "peers": peer_status,
        "summary": f"{complete_count}/{total} peers with complete data",
        "completeness_pct": round(complete_count / total * 100) if total > 0 else 0,
    }
```

---

## 7. Data Gap Handling (D-29 through D-32)

### 7.1 Unified Data Completeness Object

Per D-30, every analysis response includes:

```python
def build_data_completeness(
    available_fields: list[str],
    missing_fields: list[str],
    warnings: list[str] | None = None,
) -> dict:
    """Build data_completeness object for any analysis type.

    Example:
    {
        "available": ["fcf", "eps", "pe", "revenue"],
        "missing": ["beta"],
        "completeness": "80%",
        "warnings": ["Beta unavailable — using market average (1.0)"]
    }
    """
    total = len(available_fields) + len(missing_fields)
    pct = round(len(available_fields) / total * 100) if total > 0 else 0
    return {
        "available": available_fields,
        "missing": missing_fields,
        "completeness": f"{pct}%",
        "warnings": warnings or [],
    }
```

### 7.2 Per-Analysis-Type Required Fields

| Analysis | Hard Required (blocks if missing) | Soft Required (partial analysis ok) |
|----------|----------------------------------|-------------------------------------|
| DCF | `freeCashFlow`, `market_cap` | `beta`, `totalDebt`, `totalCash` |
| Earnings | `netIncome` (at least 1 year) | `totalRevenue`, `operatingCashFlow`, `totalAssets` |
| Dividend | `dividendsData` (at least 1 entry) | `eps`, `payout_ratio` |
| Sector | `sector` from summaryProfile | Any peer metric can be null (flagged) |

Per D-31: DCF requires FCF. If missing, return error for DCF but other analysis types proceed independently.

---

## 8. New Celery Tasks Architecture

### 8.1 Task Pattern (Reuse from `run_dcf`)

All 4 tasks follow the identical pattern from `tasks.py`:

```
@shared_task(name="analysis.run_{type}")
def run_{type}(job_id, tenant_id, ticker, ...):
    1. _check_and_increment_quota(tenant_id)
    2. _update_job(job_id, "running")
    3. fetch_fundamentals(ticker)        # shared, replaces stub
    4. compute_{type}_analysis(...)      # type-specific logic
    5. call_analysis_llm(prompt)         # shared, different prompt per type
    6. build result with data versioning # shared pattern
    7. _update_job(job_id, "completed")
    8. log_analysis_cost(...)            # shared
```

### 8.2 Task Registration

New tasks (auto-discovered by Celery from `analysis.tasks` module):
- `analysis.run_dcf` (exists, replace stubs)
- `analysis.run_earnings` (new)
- `analysis.run_dividend` (new)
- `analysis.run_sector` (new)

### 8.3 Shared `_fetch_fundamentals()` (Replaces Stub)

```python
def _fetch_fundamentals(ticker: str) -> dict:
    """Fetch comprehensive fundamentals from BRAPI with Redis caching.

    Single API call fetches all modules needed by all 4 analysis types.
    Cached 24h per ticker in Redis.

    Returns normalized dict with consistent field names.
    Replaces _fetch_fundamentals_stub from Phase 12.
    """
    cache_key = f"brapi:fundamentals:{ticker}"
    # Check Redis cache first
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from BRAPI
    client = BrapiClient()
    data = client._get(
        f"/quote/{ticker}",
        params={
            "modules": "summaryProfile,defaultKeyStatistics,financialData,"
                       "incomeStatementHistory,cashflowHistory",
            "fundamental": "true",
            "dividends": "true",
        },
    )

    result = data.get("results", [{}])[0]

    # Normalize into a consistent structure
    fundamentals = _normalize_brapi_response(result)

    # Cache in Redis
    redis_client.setex(cache_key, 86400, json.dumps(fundamentals, default=str))

    return fundamentals
```

### 8.4 New Router Endpoints

Following the existing `/dcf` pattern in `router.py`:

```python
# POST /analysis/earnings — create earnings analysis job
# POST /analysis/dividend — create dividend analysis job
# POST /analysis/sector — create sector comparison job
```

Each endpoint needs a request schema:

```python
class EarningsRequest(BaseModel):
    ticker: str = Field(min_length=4, max_length=10)

class DividendRequest(BaseModel):
    ticker: str = Field(min_length=4, max_length=10)

class SectorRequest(BaseModel):
    ticker: str = Field(min_length=4, max_length=10)
    max_peers: int = Field(default=10, ge=3, le=15)
```

### 8.5 LLM Prompts per Analysis Type

All prompts in PT-BR, 2-3 sentences, actionable (per D-15/D-20/D-25):

```python
DCF_PROMPT = """Forneça uma narrativa breve sobre a avaliação DCF de {ticker}.
Preço atual: R${price}. Valor justo estimado: R${fair_value} (range R${low}-R${high}).
Upside: {upside}%. WACC: {wacc}%. Crescimento: {growth}%.
Seja conciso, 2-3 frases em PT-BR. Foque em se a ação parece sub ou sobrevalorizada."""

EARNINGS_PROMPT = """Analise brevemente a qualidade dos lucros de {ticker}.
EPS atual: R${eps}. CAGR 5 anos: {cagr}%. Accrual ratio: {accrual}.
Conversão FCF: {fcf_conv}%. Qualidade: {quality}.
2-3 frases em PT-BR. Destaque tendência e sustentabilidade."""

DIVIDEND_PROMPT = """Comente a sustentabilidade dos dividendos de {ticker}.
DY atual: {dy}%. Payout: {payout}%. Cobertura: {coverage}x.
Consistência: {consistency}/5 anos. Avaliação: {assessment}.
2-3 frases em PT-BR. Indique se o dividendo é seguro."""

SECTOR_PROMPT = """Compare {ticker} com seus pares do setor {sector}.
P/L: {pe} (rank {pe_rank}). P/VP: {pb} (rank {pb_rank}).
DY: {dy}% (rank {dy_rank}). EV/EBITDA: {ev_ebitda} (rank {ev_rank}).
2-3 frases em PT-BR. A ação está cara ou barata vs pares?"""
```

---

## 9. Data Attribution (D-09)

Per D-09, every response includes:

```python
def build_data_attribution(selic_date: str | None = None, is_selic_fallback: bool = False) -> list[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attrs = [f"Data: BRAPI EOD {today}"]
    if selic_date:
        prefix = "Risk-free (fallback)" if is_selic_fallback else "Risk-free"
        attrs.append(f"{prefix}: BCB SELIC {selic_date}")
    return attrs
```

---

## 10. Validation Architecture

### 10.1 Test Strategy

All tests use `pytest` with mocked external dependencies (BRAPI API, BCB API, Redis, LLM providers). No real API calls in CI.

**Test file structure:**
```
backend/tests/
  test_phase13_dcf.py          # DCF calculation + sensitivity
  test_phase13_earnings.py     # Earnings quality metrics
  test_phase13_dividends.py    # Dividend sustainability
  test_phase13_sector.py       # Sector peer comparison
  test_phase13_data_fetch.py   # BRAPI/BCB fetch + caching
  test_phase13_integration.py  # Full task pipeline (end-to-end with mocks)
  fixtures/
    brapi_petr4_full.json      # Real BRAPI response fixture (sanitized)
    bcb_selic_response.json    # BCB SELIC response fixture
```

### 10.2 DCF Test Cases

```python
# test_phase13_dcf.py

import pytest
from unittest.mock import patch, MagicMock

# --- WACC Calculation ---

class TestWACCCalculation:
    def test_wacc_basic(self):
        """WACC with SELIC=14.75%, beta=1.0, 50/50 D/E."""
        wacc = calculate_wacc(
            selic=0.1475, beta=1.0,
            debt=500_000, equity=500_000, tax_rate=0.34,
        )
        # Ke = 0.1475 + 1.0 * 0.07 = 0.2175
        # Kd = 0.1475 + 0.02 = 0.1675
        # WACC = 0.2175 * 0.5 + 0.1675 * 0.66 * 0.5
        expected = 0.2175 * 0.5 + 0.1675 * 0.66 * 0.5
        assert abs(wacc - expected) < 0.001

    def test_wacc_zero_debt(self):
        """All-equity firm: WACC = Ke."""
        wacc = calculate_wacc(selic=0.1475, beta=1.2, debt=0, equity=1_000_000)
        ke = 0.1475 + 1.2 * 0.07
        assert abs(wacc - ke) < 0.001

    def test_wacc_high_beta(self):
        """High beta (2.0) should increase WACC significantly."""
        wacc = calculate_wacc(selic=0.1475, beta=2.0, debt=100_000, equity=900_000)
        assert wacc > 0.25  # Must be above 25% for aggressive stock

    def test_wacc_beta_fallback_when_none(self):
        """When beta is None, should use 1.0 default."""
        # This tests the calling code, not calculate_wacc itself
        beta = None
        effective_beta = beta if beta is not None else 1.0
        wacc = calculate_wacc(selic=0.1475, beta=effective_beta, debt=100_000, equity=900_000)
        assert wacc > 0

# --- DCF Calculation ---

class TestDCFCalculation:
    def test_dcf_basic(self):
        """Basic DCF with known inputs should produce positive fair value."""
        result = calculate_dcf(
            fcf_current=50_000_000_000,
            shares_outstanding=13_000_000_000,
            growth_rate=0.05,
            wacc=0.15,
            terminal_growth=0.03,
        )
        assert result["fair_value"] > 0
        assert len(result["projected_fcfs"]) == 5
        assert result["projected_fcfs"][0]["year"] == 1

    def test_dcf_terminal_value_dominates(self):
        """Terminal value should be > 50% of total EV for typical inputs."""
        result = calculate_dcf(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.05,
            wacc=0.12,
            terminal_growth=0.03,
        )
        total_ev = result["pv_stage1"] + result["pv_terminal"]
        assert result["pv_terminal"] / total_ev > 0.50

    def test_dcf_wacc_equals_terminal_growth_raises(self):
        """WACC == terminal_growth should raise ValueError (division by zero)."""
        with pytest.raises(ValueError, match="WACC must exceed"):
            calculate_dcf(
                fcf_current=10_000_000_000,
                shares_outstanding=1_000_000_000,
                growth_rate=0.05,
                wacc=0.03,
                terminal_growth=0.03,
            )

    def test_dcf_higher_growth_increases_fair_value(self):
        """Higher growth rate should produce higher fair value."""
        base = {"fcf_current": 10e9, "shares_outstanding": 1e9, "wacc": 0.12, "terminal_growth": 0.03}
        fv_low = calculate_dcf(growth_rate=0.03, **base)["fair_value"]
        fv_high = calculate_dcf(growth_rate=0.08, **base)["fair_value"]
        assert fv_high > fv_low

    def test_dcf_higher_wacc_decreases_fair_value(self):
        """Higher WACC should produce lower fair value."""
        base = {"fcf_current": 10e9, "shares_outstanding": 1e9, "growth_rate": 0.05, "terminal_growth": 0.03}
        fv_low_wacc = calculate_dcf(wacc=0.10, **base)["fair_value"]
        fv_high_wacc = calculate_dcf(wacc=0.20, **base)["fair_value"]
        assert fv_low_wacc > fv_high_wacc

# --- Sensitivity ---

class TestDCFSensitivity:
    def test_sensitivity_three_scenarios(self):
        """Sensitivity should return low < base < high."""
        result = calculate_dcf_with_sensitivity(
            fcf_current=50e9, shares_outstanding=13e9,
            growth_rate=0.05, wacc=0.15, terminal_growth=0.03,
            net_debt=200e9,
        )
        assert result["fair_value_range"]["low"] < result["fair_value"]
        assert result["fair_value"] < result["fair_value_range"]["high"]

    def test_sensitivity_key_drivers_present(self):
        """Key drivers list should be non-empty."""
        result = calculate_dcf_with_sensitivity(
            fcf_current=50e9, shares_outstanding=13e9,
            growth_rate=0.05, wacc=0.15, terminal_growth=0.03,
            net_debt=200e9,
        )
        assert len(result["key_drivers"]) > 0

# --- Growth Rate Estimation ---

class TestGrowthRateEstimation:
    def test_estimate_from_history(self):
        """Should calculate CAGR from 5 years of positive FCF."""
        history = [
            {"freeCashFlow": 100e9},
            {"freeCashFlow": 90e9},
            {"freeCashFlow": 80e9},
            {"freeCashFlow": 70e9},
            {"freeCashFlow": 60e9},
        ]
        rate = estimate_growth_rate(history)
        # CAGR = (100/60)^(1/4) - 1 ≈ 13.6%
        assert 0.10 < rate < 0.18

    def test_fallback_on_insufficient_data(self):
        """Should return default 5% if < 3 years data."""
        rate = estimate_growth_rate([{"freeCashFlow": 100e9}])
        assert rate == 0.05

    def test_fallback_on_negative_fcf(self):
        """Negative FCF should trigger default fallback."""
        history = [
            {"freeCashFlow": -10e9},
            {"freeCashFlow": 50e9},
            {"freeCashFlow": 40e9},
        ]
        rate = estimate_growth_rate(history)
        assert rate == 0.05
```

### 10.3 Earnings Test Cases

```python
# test_phase13_earnings.py

class TestAccrualRatio:
    def test_high_quality(self):
        """Net income closely backed by cash flow → low accrual ratio."""
        ratio = calculate_accrual_ratio(
            net_income=100e9, operating_cash_flow=95e9, total_assets=500e9,
        )
        assert ratio < 0.20  # 0.01

    def test_poor_quality(self):
        """Large gap between income and cash flow → high accrual ratio."""
        ratio = calculate_accrual_ratio(
            net_income=100e9, operating_cash_flow=40e9, total_assets=200e9,
        )
        assert ratio > 0.20  # 0.30

    def test_negative_accrual(self):
        """Cash flow exceeds income (very good) → negative ratio."""
        ratio = calculate_accrual_ratio(
            net_income=50e9, operating_cash_flow=80e9, total_assets=500e9,
        )
        assert ratio < 0

    def test_zero_assets_returns_none(self):
        """Zero total assets → None (can't calculate)."""
        assert calculate_accrual_ratio(100e9, 80e9, 0) is None


class TestFCFConversion:
    def test_healthy_conversion(self):
        """FCF > 80% of net income → good."""
        ratio = calculate_fcf_conversion(90e9, 100e9)
        assert ratio > 0.80

    def test_poor_conversion(self):
        """FCF < 50% of net income → poor."""
        ratio = calculate_fcf_conversion(30e9, 100e9)
        assert ratio < 0.50

    def test_negative_income_returns_none(self):
        """Negative net income → None."""
        assert calculate_fcf_conversion(50e9, -10e9) is None

    def test_fcf_exceeds_income(self):
        """FCF > net income (possible but flags for investigation)."""
        ratio = calculate_fcf_conversion(200e9, 100e9)
        assert ratio > 1.50


class TestEarningsQuality:
    def test_high_quality(self):
        assert assess_earnings_quality(0.10, 0.90) == "high"

    def test_medium_quality(self):
        assert assess_earnings_quality(0.25, 0.70) == "medium"

    def test_low_quality_high_accrual(self):
        assert assess_earnings_quality(0.50, 0.70) == "low"

    def test_low_quality_low_conversion(self):
        assert assess_earnings_quality(0.15, 0.40) == "low"

    def test_none_values_default_medium(self):
        assert assess_earnings_quality(None, None) == "medium"


class TestEPSHistory:
    def test_five_year_history(self):
        """Should build 5-year EPS with YoY growth."""
        income = [
            {"netIncome": 100e9, "totalRevenue": 500e9, "endDate": "2025"},
            {"netIncome": 90e9, "totalRevenue": 480e9, "endDate": "2024"},
            {"netIncome": 80e9, "totalRevenue": 450e9, "endDate": "2023"},
            {"netIncome": 70e9, "totalRevenue": 420e9, "endDate": "2022"},
            {"netIncome": 60e9, "totalRevenue": 400e9, "endDate": "2021"},
        ]
        result = calculate_earnings_history(income, shares_outstanding=13e9)
        assert len(result["eps_history"]) == 5
        assert result["eps_cagr_5y"] is not None
        assert result["eps_cagr_5y"] > 0
        # YoY should be calculated for years 0..3 (not the oldest)
        assert result["eps_history"][0]["yoy_growth"] is not None
        assert result["eps_history"][-1]["yoy_growth"] is None  # oldest has no prior
```

### 10.4 Dividend Test Cases

```python
# test_phase13_dividends.py

class TestAnnualDividendAggregation:
    def test_basic_aggregation(self):
        """Sum multiple payments in same year."""
        dividends = [
            {"rate": 1.50, "paymentDate": "2025-06-15T00:00:00.000Z", "label": "DIVIDENDO"},
            {"rate": 0.80, "paymentDate": "2025-12-20T00:00:00.000Z", "label": "JCP"},
            {"rate": 1.20, "paymentDate": "2024-06-15T00:00:00.000Z", "label": "DIVIDENDO"},
        ]
        result = aggregate_annual_dividends(dividends)
        assert abs(result[2025] - 2.30) < 0.01
        assert abs(result[2024] - 1.20) < 0.01

    def test_empty_dividends(self):
        """No dividends → empty dict."""
        assert aggregate_annual_dividends([]) == {}


class TestDividendCoverage:
    def test_safe_coverage(self):
        """EPS 8.0 / DPS 3.0 = 2.67x coverage (safe)."""
        assert calculate_dividend_coverage(8.0, 3.0) == 2.67

    def test_risky_coverage(self):
        """EPS 2.0 / DPS 1.8 = 1.11x (risk)."""
        assert calculate_dividend_coverage(2.0, 1.8) == 1.11

    def test_no_dividends(self):
        assert calculate_dividend_coverage(8.0, 0) is None


class TestPayoutRatio:
    def test_healthy_payout(self):
        """DPS 3.0 / EPS 8.0 = 37.5%."""
        ratio = calculate_payout_ratio(3.0, 8.0)
        assert abs(ratio - 0.375) < 0.001

    def test_excessive_payout(self):
        """DPS > EPS → payout > 100%."""
        ratio = calculate_payout_ratio(10.0, 8.0)
        assert ratio > 1.0

    def test_negative_earnings(self):
        assert calculate_payout_ratio(3.0, -5.0) is None


class TestConsistencyScore:
    def test_perfect_consistency(self):
        """Paid dividends every year for 5 years."""
        annual = {2021: 2.0, 2022: 2.5, 2023: 3.0, 2024: 2.8, 2025: 3.2}
        result = calculate_consistency_score(annual, years=5)
        assert result["score"] == 1.0
        assert result["paid_years"] == 5

    def test_partial_consistency(self):
        """Skipped 2 years."""
        annual = {2021: 2.0, 2023: 3.0, 2025: 3.2}
        result = calculate_consistency_score(annual, years=5)
        assert result["paid_years"] == 3
        assert result["score"] == 0.6


class TestSustainabilityAssessment:
    def test_safe(self):
        annual = {2023: 3.0, 2024: 3.2, 2025: 3.5}
        assert assess_dividend_sustainability(0.40, 2.5, annual) == "safe"

    def test_warning_high_payout(self):
        annual = {2023: 3.0, 2024: 3.2, 2025: 3.5}
        assert assess_dividend_sustainability(0.70, 1.6, annual) == "warning"

    def test_risk_very_high_payout(self):
        annual = {2023: 3.0, 2024: 3.2, 2025: 3.5}
        assert assess_dividend_sustainability(0.85, 1.1, annual) == "risk"

    def test_risk_dividend_cut(self):
        """20%+ cut triggers risk regardless of other metrics."""
        annual = {2023: 5.0, 2024: 3.0, 2025: 3.5}  # Cut from 5.0 to 3.0
        assert assess_dividend_sustainability(0.40, 2.0, annual) == "risk"
```

### 10.5 Sector Comparison Test Cases

```python
# test_phase13_sector.py

class TestPeerRanking:
    def test_cheapest_stock(self):
        """Stock with lowest P/E should rank #1."""
        target = {"pe": 5.0, "pb": 1.0, "dy": 0.08, "ev_ebitda": 4.0}
        peers = [
            {"ticker": "PEER1", "pe": 10.0, "pb": 2.0, "dy": 0.04, "ev_ebitda": 8.0},
            {"ticker": "PEER2", "pe": 15.0, "pb": 3.0, "dy": 0.02, "ev_ebitda": 12.0},
        ]
        rankings = rank_stock_in_peers("TARGET", target, peers)
        assert "1/3" in rankings["pe_rank"]

    def test_null_metrics_excluded(self):
        """Peers with null P/E should not count in ranking."""
        target = {"pe": 10.0, "pb": 2.0, "dy": 0.05, "ev_ebitda": 6.0}
        peers = [
            {"ticker": "PEER1", "pe": None, "pb": 1.5, "dy": 0.06, "ev_ebitda": 5.0},
            {"ticker": "PEER2", "pe": 12.0, "pb": 2.5, "dy": 0.03, "ev_ebitda": 7.0},
        ]
        rankings = rank_stock_in_peers("TARGET", target, peers)
        assert "2" in rankings["pe_rank"]  # Only 2 stocks with PE


class TestPeerCompleteness:
    def test_all_complete(self):
        peers = [
            {"ticker": "A", "pe": 10, "pb": 2, "dy": 0.05, "ev_ebitda": 6},
            {"ticker": "B", "pe": 12, "pb": 2.5, "dy": 0.04, "ev_ebitda": 7},
        ]
        result = assess_peer_completeness(peers)
        assert result["completeness_pct"] == 100
        assert "2/2" in result["summary"]

    def test_partial_data(self):
        peers = [
            {"ticker": "A", "pe": 10, "pb": 2, "dy": 0.05, "ev_ebitda": 6},
            {"ticker": "B", "pe": None, "pb": 2.5, "dy": None, "ev_ebitda": 7},
        ]
        result = assess_peer_completeness(peers)
        assert result["completeness_pct"] == 50
        assert result["peers"][1]["complete"] is False
        assert "pe" in result["peers"][1]["missing"]

    def test_empty_peers(self):
        result = assess_peer_completeness([])
        assert result["completeness_pct"] == 0


class TestSectorMapping:
    def test_known_sectors(self):
        """Known PT sectors should map to EN equivalents."""
        assert SECTOR_MAP_PT_TO_EN["Energia"] == "Energy Minerals"
        assert SECTOR_MAP_PT_TO_EN["Financeiro"] == "Finance"

    def test_unknown_sector_fallback(self):
        """Unknown sector should use original value or raise clear error."""
        sector_pt = "Setor Desconhecido"
        en = SECTOR_MAP_PT_TO_EN.get(sector_pt)
        assert en is None  # Caller handles None by using sector_pt directly
```

### 10.6 Data Fetch Test Cases

```python
# test_phase13_data_fetch.py

from unittest.mock import patch, MagicMock

class TestFetchFundamentals:
    @patch("app.modules.analysis.tasks.redis_client")
    @patch("app.modules.market_data.adapters.brapi.BrapiClient._get")
    def test_cache_hit(self, mock_get, mock_redis):
        """Should return cached data without calling BRAPI."""
        mock_redis.get.return_value = '{"current_price": 48.67}'
        result = _fetch_fundamentals("PETR4")
        assert result["current_price"] == 48.67
        mock_get.assert_not_called()

    @patch("app.modules.analysis.tasks.redis_client")
    @patch("app.modules.market_data.adapters.brapi.BrapiClient._get")
    def test_cache_miss_fetches_brapi(self, mock_get, mock_redis):
        """Cache miss should call BRAPI and store result."""
        mock_redis.get.return_value = None
        mock_get.return_value = {
            "results": [{
                "regularMarketPrice": 48.67,
                "marketCap": 640e9,
                "defaultKeyStatistics": {"earningsPerShare": 8.58},
                "financialData": {"freeCashflow": 94.68e9},
                "summaryProfile": {"sector": "Energia"},
                "incomeStatementHistory": [],
                "cashflowHistory": [],
                "dividendsData": {"cashDividends": []},
            }]
        }
        result = _fetch_fundamentals("PETR4")
        assert result["current_price"] == 48.67
        mock_redis.setex.assert_called_once()

    @patch("app.modules.analysis.tasks.redis_client")
    @patch("app.modules.market_data.adapters.brapi.BrapiClient._get")
    def test_brapi_failure_no_cache(self, mock_get, mock_redis):
        """BRAPI failure with empty cache should raise."""
        mock_redis.get.return_value = None
        mock_get.side_effect = Exception("BRAPI down")
        with pytest.raises(Exception, match="BRAPI down"):
            _fetch_fundamentals("PETR4")


class TestFetchSELIC:
    @patch("requests.get")
    def test_parse_bcb_response(self, mock_get):
        """Should parse BCB date format and convert rate to decimal."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"data": "28/03/2026", "valor": "14.75"}],
        )
        mock_get.return_value.raise_for_status = MagicMock()
        rate, date = fetch_selic_rate()
        assert rate == 0.1475
        assert date == "2026-03-28"

    @patch("requests.get")
    def test_bcb_timeout_uses_fallback(self, mock_get):
        """BCB timeout should trigger fallback rate."""
        mock_get.side_effect = Exception("timeout")
        rate, date, is_fallback = get_selic_rate_safe()
        assert is_fallback is True
        assert rate == SELIC_FALLBACK
```

### 10.7 Integration Test Cases (Full Task Pipeline)

```python
# test_phase13_integration.py

from unittest.mock import patch, MagicMock, AsyncMock

class TestRunDCFTask:
    """End-to-end test for the run_dcf Celery task with real logic."""

    @patch("app.modules.analysis.tasks.log_analysis_cost")
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.call_analysis_llm", new_callable=AsyncMock)
    @patch("app.modules.analysis.tasks._fetch_fundamentals")
    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True)
    def test_full_dcf_pipeline(
        self, mock_quota, mock_fetch, mock_llm, mock_update, mock_cost
    ):
        mock_fetch.return_value = {
            "current_price": 48.67,
            "market_cap": 640e9,
            "free_cash_flow": 94.68e9,
            "total_debt": 674e9,
            "total_cash": 50e9,
            "beta": 1.2,
            "eps": 8.58,
            "cashflow_history": [{"freeCashFlow": f} for f in [94e9, 85e9, 80e9, 70e9, 60e9]],
        }
        mock_llm.return_value = ("Narrativa DCF em PT-BR.", {"provider_used": "groq", "model": "llama"})

        run_dcf("job-123", "tenant-456", "PETR4", assumptions=None)

        # Should complete successfully
        calls = mock_update.call_args_list
        assert calls[0][0][1] == "running"
        assert calls[1][0][1] == "completed"
        # Result should contain fair_value
        result_json = calls[1][1].get("result_json") or calls[1][0][2]
        assert "fair_value" in str(result_json)

    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=False)
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.log_analysis_cost")
    def test_quota_exhausted(self, mock_cost, mock_update, mock_quota):
        run_dcf("job-123", "tenant-456", "PETR4")
        mock_update.assert_called_with("job-123", "failed", error="Analysis quota exhausted")


class TestRunEarningsTask:
    @patch("app.modules.analysis.tasks.log_analysis_cost")
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.call_analysis_llm", new_callable=AsyncMock)
    @patch("app.modules.analysis.tasks._fetch_fundamentals")
    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True)
    def test_full_earnings_pipeline(
        self, mock_quota, mock_fetch, mock_llm, mock_update, mock_cost
    ):
        mock_fetch.return_value = {
            "current_price": 48.67,
            "market_cap": 640e9,
            "eps": 8.58,
            "income_history": [
                {"netIncome": 110e9, "totalRevenue": 497e9, "endDate": "2025"},
                {"netIncome": 37e9, "totalRevenue": 490e9, "endDate": "2024"},
                {"netIncome": 125e9, "totalRevenue": 511e9, "endDate": "2023"},
                {"netIncome": 189e9, "totalRevenue": 641e9, "endDate": "2022"},
                {"netIncome": 107e9, "totalRevenue": 452e9, "endDate": "2021"},
            ],
            "cashflow_history": [
                {"operatingCashFlow": 150e9, "freeCashFlow": 94e9},
            ],
            "total_assets_approx": 800e9,
        }
        mock_llm.return_value = ("Narrativa earnings.", {"provider_used": "groq", "model": "llama"})

        run_earnings("job-earn-1", "tenant-456", "PETR4")

        calls = mock_update.call_args_list
        assert calls[-1][0][1] == "completed"


class TestRunDividendTask:
    @patch("app.modules.analysis.tasks.log_analysis_cost")
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.call_analysis_llm", new_callable=AsyncMock)
    @patch("app.modules.analysis.tasks._fetch_fundamentals")
    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True)
    def test_full_dividend_pipeline(
        self, mock_quota, mock_fetch, mock_llm, mock_update, mock_cost
    ):
        mock_fetch.return_value = {
            "current_price": 48.67,
            "eps": 8.58,
            "dividend_yield": 0.06,
            "dividends_data": [
                {"rate": 1.55, "paymentDate": "2025-12-23T00:00:00Z", "label": "DIVIDENDO"},
                {"rate": 0.80, "paymentDate": "2025-06-15T00:00:00Z", "label": "JCP"},
                {"rate": 1.20, "paymentDate": "2024-12-20T00:00:00Z", "label": "DIVIDENDO"},
                {"rate": 1.00, "paymentDate": "2023-12-18T00:00:00Z", "label": "DIVIDENDO"},
                {"rate": 2.00, "paymentDate": "2022-12-15T00:00:00Z", "label": "DIVIDENDO"},
                {"rate": 1.50, "paymentDate": "2021-12-14T00:00:00Z", "label": "DIVIDENDO"},
            ],
        }
        mock_llm.return_value = ("Narrativa dividendos.", {"provider_used": "groq", "model": "llama"})

        run_dividend("job-div-1", "tenant-456", "PETR4")

        calls = mock_update.call_args_list
        assert calls[-1][0][1] == "completed"


class TestRunSectorTask:
    @patch("app.modules.analysis.tasks.log_analysis_cost")
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.call_analysis_llm", new_callable=AsyncMock)
    @patch("app.modules.analysis.tasks._fetch_fundamentals")
    @patch("app.modules.analysis.tasks._fetch_sector_peers")
    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True)
    def test_full_sector_pipeline(
        self, mock_quota, mock_peers, mock_fetch, mock_llm, mock_update, mock_cost
    ):
        mock_fetch.return_value = {
            "current_price": 48.67,
            "sector": "Energia",
            "pe": 6.37,
            "pb": 1.53,
            "dy": 0.06,
            "ev_ebitda": 5.5,
        }
        mock_peers.return_value = [
            {"ticker": "CSAN3", "pe": 12.0, "pb": 2.0, "dy": 0.03, "ev_ebitda": 8.0},
            {"ticker": "UGPA3", "pe": 15.0, "pb": 2.5, "dy": 0.025, "ev_ebitda": 10.0},
            {"ticker": "VBBR3", "pe": 8.0, "pb": 1.8, "dy": 0.05, "ev_ebitda": 6.0},
        ]
        mock_llm.return_value = ("Narrativa setor.", {"provider_used": "groq", "model": "llama"})

        run_sector("job-sec-1", "tenant-456", "PETR4", max_peers=10)

        calls = mock_update.call_args_list
        assert calls[-1][0][1] == "completed"

    @patch("app.modules.analysis.tasks._fetch_sector_peers")
    @patch("app.modules.analysis.tasks._fetch_fundamentals")
    @patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True)
    @patch("app.modules.analysis.tasks._update_job")
    @patch("app.modules.analysis.tasks.log_analysis_cost")
    def test_insufficient_peers(
        self, mock_cost, mock_update, mock_quota, mock_fetch, mock_peers
    ):
        """< 3 peers after broadening should still complete with warning."""
        mock_fetch.return_value = {"sector": "NichoSetor", "pe": 10, "pb": 2, "dy": 0.05, "ev_ebitda": 6}
        mock_peers.return_value = [
            {"ticker": "ONLY1", "pe": 12, "pb": 2.5, "dy": 0.03, "ev_ebitda": 8},
        ]

        run_sector("job-sec-2", "tenant-456", "RARE4", max_peers=10)

        # Should still complete (partial analysis per D-29)
        calls = mock_update.call_args_list
        last_status = calls[-1][0][1]
        assert last_status == "completed"
```

---

## 11. API Call Budget & Performance

### 11.1 Calls per Analysis Type

| Analysis | BRAPI Calls | BCB Calls | Total Network | Est. Time |
|----------|-------------|-----------|---------------|-----------|
| DCF | 1 (full modules) | 1 (SELIC) | 2 | ~1.5s |
| Earnings | 1 (full modules) | 0 | 1 | ~1.0s |
| Dividend | 1 (full modules) | 0 | 1 | ~1.0s |
| Sector | 1 (target) + 1 (list) + N (peers) | 0 | 2+N (~12) | ~3.5s |

With Redis caching (24h TTL), repeated analyses for the same ticker hit cache and skip BRAPI calls entirely. LLM call adds 5-20s depending on provider.

### 11.2 Total Task Time Budget

Target: 30-60s per AI-15.

| Phase | Time |
|-------|------|
| Quota check | <50ms |
| BRAPI fetch (cache miss) | 1-4s |
| BCB fetch (cache miss) | 0.5-1s |
| Computation | <100ms |
| LLM narrative | 5-20s |
| DB writes | <100ms |
| **Total** | **7-25s** |

Well within the 30-60s target.

---

## 12. File Change Summary

### New Files
- `backend/app/modules/analysis/brapi_fundamentals.py` — `_fetch_fundamentals()`, `_fetch_sector_peers()`, BRAPI response normalization
- `backend/app/modules/analysis/bcb.py` — SELIC fetch, caching, fallback
- `backend/app/modules/analysis/calculations.py` — All pure math: DCF, WACC, earnings quality, dividend metrics, peer ranking
- `backend/tests/test_phase13_dcf.py`
- `backend/tests/test_phase13_earnings.py`
- `backend/tests/test_phase13_dividends.py`
- `backend/tests/test_phase13_sector.py`
- `backend/tests/test_phase13_data_fetch.py`
- `backend/tests/test_phase13_integration.py`
- `backend/tests/fixtures/brapi_petr4_full.json`
- `backend/tests/fixtures/bcb_selic_response.json`

### Modified Files
- `backend/app/modules/analysis/tasks.py` — Replace `_fetch_fundamentals_stub` and `_calculate_dcf_stub` with real implementations; add `run_earnings`, `run_dividend`, `run_sector` tasks
- `backend/app/modules/analysis/schemas.py` — Add `EarningsRequest`, `DividendRequest`, `SectorRequest` schemas
- `backend/app/modules/analysis/router.py` — Add `POST /analysis/earnings`, `POST /analysis/dividend`, `POST /analysis/sector` endpoints
- `backend/app/modules/analysis/versioning.py` — Add BCB to `get_data_sources()` list
- `backend/app/modules/analysis/constants.py` — Add sector mapping dict, ERP constant, SELIC fallback

### Unchanged (Reused As-Is)
- `backend/app/modules/analysis/models.py` — `AnalysisJob` already supports all 4 analysis types
- `backend/app/modules/analysis/providers.py` — LLM chain reused, different prompts per type
- `backend/app/modules/analysis/cost.py` — Cost logging reused for all tasks
- `backend/app/modules/analysis/quota.py` — Quota checking reused for all tasks
- `backend/app/modules/market_data/adapters/brapi.py` — Existing `BrapiClient` reused (extend with full modules call)

---

*Research completed: 2026-03-31*
*Phase: 13-core-analysis-engine*
