"""IR Helper router.

Endpoints:
  GET /ir-helper/summary?month=YYYY-MM     — Calcula DARF mensal de swing trade
  GET /ir-helper/history                    — Histórico mensal de P&L e DARF
  GET /ir-helper/declaration?year=YYYY      — Posições em 31/12 para DIRPF (Bens e Direitos)
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.portfolio.models import Transaction, TransactionType, AssetClass

router = APIRouter()

ISENCAO_MENSAL = Decimal("20000.00")
ALIQUOTA_SWING = Decimal("0.15")
DARF_MINIMO = Decimal("10.00")


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


@router.get("/summary")
async def ir_summary(
    month: str = Query(..., regex=r"^\d{4}-\d{2}$", description="Mês no formato YYYY-MM"),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Calcula DARF mensal de swing trade para o mês indicado.

    Regras brasileiras:
    - Isenção: operações de venda totalizando até R$20.000 no mês → IR = 0
    - Alíquota: 15% sobre lucro líquido (lucro bruto − prejuízos acumulados de meses anteriores)
    - DARF só é emitida se IR ≥ R$10,00
    - Prejuízo acumulado de meses anteriores abate lucro antes do cálculo
    """
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except ValueError:
        raise HTTPException(status_code=422, detail="Formato inválido. Use YYYY-MM.")

    target_month = date(year, mon, 1)

    # Fetch all sell transactions for this tenant (needed to compute accumulated loss)
    result = await db.execute(
        select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type == TransactionType.sell,
            Transaction.deleted_at.is_(None),
        ).order_by(Transaction.transaction_date)
    )
    sells = result.scalars().all()

    # Group by month
    by_month: dict[str, list[Transaction]] = defaultdict(list)
    for tx in sells:
        by_month[_month_key(tx.transaction_date)].append(tx)

    # Compute accumulated loss up to (not including) the selected month
    accumulated_loss = Decimal("0")
    months_sorted = sorted(k for k in by_month if k < month)
    for mk in months_sorted:
        txs = by_month[mk]
        month_total_vendas = sum(t.total_value or Decimal(0) for t in txs)
        month_gross_profit = sum(t.gross_profit or Decimal(0) for t in txs)

        if month_total_vendas >= ISENCAO_MENSAL:
            # Month was taxable — carry loss forward (loss = negative profit)
            net = month_gross_profit + accumulated_loss
            if net < 0:
                accumulated_loss = net
            else:
                accumulated_loss = Decimal("0")
        # If exempt month, accumulated loss is NOT consumed (BR tax rule)

    # Current month calculations
    current_txs = by_month.get(month, [])
    total_vendas = sum(t.total_value or Decimal(0) for t in current_txs)
    lucro_bruto = sum(t.gross_profit or Decimal(0) for t in current_txs)

    isento = total_vendas < ISENCAO_MENSAL

    if isento:
        lucro_liquido = Decimal("0")
        ir_devido = Decimal("0")
        darf_gerado = False
        darf_valor = Decimal("0")
    else:
        lucro_liquido = lucro_bruto + accumulated_loss  # accumulated_loss is negative
        if lucro_liquido <= 0:
            ir_devido = Decimal("0")
            darf_gerado = False
            darf_valor = Decimal("0")
        else:
            ir_devido = (lucro_liquido * ALIQUOTA_SWING).quantize(Decimal("0.01"))
            darf_gerado = ir_devido >= DARF_MINIMO
            darf_valor = ir_devido if darf_gerado else Decimal("0")

    return {
        "month": month,
        "total_vendas": float(total_vendas),
        "lucro_bruto": float(lucro_bruto),
        "prejuizo_acumulado": float(abs(accumulated_loss)) if accumulated_loss < 0 else 0.0,
        "lucro_liquido": float(max(lucro_liquido, Decimal(0))),
        "isento": isento,
        "aliquota": float(ALIQUOTA_SWING),
        "ir_devido": float(ir_devido),
        "darf_gerado": darf_gerado,
        "darf_valor": float(darf_valor),
        "transactions_count": len(current_txs),
        "transactions": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "date": t.transaction_date.isoformat(),
                "quantity": float(t.quantity),
                "unit_price": float(t.unit_price),
                "total_value": float(t.total_value),
                "gross_profit": float(t.gross_profit) if t.gross_profit is not None else None,
            }
            for t in current_txs
        ],
    }


@router.get("/history")
async def ir_history(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[dict]:
    """Retorna histórico mensal de P&L e DARF para todos os meses com vendas."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type == TransactionType.sell,
            Transaction.deleted_at.is_(None),
        ).order_by(Transaction.transaction_date)
    )
    sells = result.scalars().all()
    if not sells:
        return []

    by_month: dict[str, list[Transaction]] = defaultdict(list)
    for tx in sells:
        by_month[_month_key(tx.transaction_date)].append(tx)

    history = []
    accumulated_loss = Decimal("0")

    for mk in sorted(by_month.keys()):
        txs = by_month[mk]
        total_vendas = sum(t.total_value or Decimal(0) for t in txs)
        lucro_bruto = sum(t.gross_profit or Decimal(0) for t in txs)
        isento = total_vendas < ISENCAO_MENSAL

        if isento:
            lucro_liquido = Decimal("0")
            ir_devido = Decimal("0")
            darf_gerado = False
        else:
            lucro_liquido = lucro_bruto + accumulated_loss
            if lucro_liquido <= 0:
                ir_devido = Decimal("0")
                darf_gerado = False
                # Update accumulated loss
                accumulated_loss = lucro_liquido
                lucro_liquido = Decimal("0")
            else:
                ir_devido = (lucro_liquido * ALIQUOTA_SWING).quantize(Decimal("0.01"))
                darf_gerado = ir_devido >= DARF_MINIMO
                accumulated_loss = Decimal("0")

        history.append({
            "month": mk,
            "total_vendas": float(total_vendas),
            "lucro_bruto": float(lucro_bruto),
            "lucro_liquido": float(max(lucro_liquido, Decimal(0))),
            "isento": isento,
            "ir_devido": float(ir_devido),
            "darf_gerado": darf_gerado,
        })

    return history


# ── DIRPF Declaration Helper ──────────────────────────────────────────────────

# ReceitaNet "Bens e Direitos" codes for B3 assets (DIRPF 2024+)
_DIRPF_CODES: dict[str, dict] = {
    AssetClass.acao.value: {"grupo": "03", "codigo": "01", "descricao": "Ações (negociadas em bolsa)"},
    AssetClass.fii.value:  {"grupo": "07", "codigo": "04", "descricao": "Cotas de FII (negociadas em bolsa)"},
    AssetClass.bdr.value:  {"grupo": "03", "codigo": "04", "descricao": "BDR — Brazilian Depositary Receipts"},
    AssetClass.etf.value:  {"grupo": "07", "codigo": "09", "descricao": "Cotas de ETF"},
}
_DEFAULT_CODE = {"grupo": "03", "codigo": "99", "descricao": "Outros bens e direitos"}


def _dirpf_code(asset_class: str) -> dict:
    return _DIRPF_CODES.get(asset_class, _DEFAULT_CODE)


@router.get("/declaration")
async def ir_declaration(
    year: int = Query(..., ge=2020, le=2030, description="Ano-base (ex: 2025 para DIRPF 2026)"),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Retorna posições em 31/12 do ano-base para declaração DIRPF (Bens e Direitos).

    Lógica:
    - Replay de todas as compras e vendas até 31/12/year
    - CMP (custo médio ponderado) recalculado por ativo
    - Retorna apenas posições com quantidade > 0
    - Mapeia para código Receita Federal (grupo + código ReceitaNet)

    Uso: preencher seção "Bens e Direitos" da DIRPF. Para cada item:
    - Discriminação: "<TICKER> — <N> ações/cotas adquiridas via bolsa B3, CNPJ XXXXXXXXXXX"
    - Situação em 31/12/<year-1>: valor de custo no ano anterior
    - Situação em 31/12/<year>: valor de custo no ano-base
    """
    cutoff = date(year, 12, 31)
    prev_cutoff = date(year - 1, 12, 31)

    result = await db.execute(
        select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_([TransactionType.buy, TransactionType.sell]),
            Transaction.deleted_at.is_(None),
        ).order_by(Transaction.transaction_date, Transaction.created_at)
    )
    all_txs = result.scalars().all()

    def _replay_positions(up_to: date) -> dict[str, dict]:
        """Returns {ticker: {qty, avg_cost, total_cost, asset_class}} up to `up_to` inclusive."""
        state: dict[str, dict] = {}
        for tx in all_txs:
            if tx.transaction_date > up_to:
                break
            ticker = tx.ticker.upper()
            tx_type = tx.transaction_type.value if hasattr(tx.transaction_type, "value") else str(tx.transaction_type)
            ac = tx.asset_class.value if hasattr(tx.asset_class, "value") else str(tx.asset_class)

            cur = state.setdefault(ticker, {"qty": Decimal("0"), "avg_cost": Decimal("0"), "asset_class": ac})

            if tx_type == "buy":
                new_qty = cur["qty"] + tx.quantity
                if new_qty > 0:
                    cur["avg_cost"] = (
                        (cur["qty"] * cur["avg_cost"] + tx.quantity * tx.unit_price) / new_qty
                    ).quantize(Decimal("0.000001"))
                cur["qty"] = new_qty
            elif tx_type == "sell":
                cur["qty"] = max(Decimal("0"), cur["qty"] - tx.quantity)
                # avg_cost does not change on sell (CMP rule)

        return {t: v for t, v in state.items() if v["qty"] > Decimal("0")}

    positions_current = _replay_positions(cutoff)
    positions_prev = _replay_positions(prev_cutoff)

    # Build declaration items — one row per ticker
    items = []
    all_tickers = sorted(set(list(positions_current.keys()) + list(positions_prev.keys())))

    for ticker in all_tickers:
        cur = positions_current.get(ticker)
        prev = positions_prev.get(ticker)

        if cur is None and prev is None:
            continue

        asset_class = (cur or prev)["asset_class"]  # type: ignore[index]
        code_info = _dirpf_code(asset_class)

        qty_current = cur["qty"] if cur else Decimal("0")
        avg_cost_current = cur["avg_cost"] if cur else Decimal("0")
        custo_current = (qty_current * avg_cost_current).quantize(Decimal("0.01"))

        qty_prev = prev["qty"] if prev else Decimal("0")
        avg_cost_prev = prev["avg_cost"] if prev else Decimal("0")
        custo_prev = (qty_prev * avg_cost_prev).quantize(Decimal("0.01"))

        # Build discriminação text for ReceitaNet
        if cur:
            discriminacao = (
                f"{ticker} — {float(qty_current):g} {'cotas' if asset_class in ('fii', 'etf') else 'ações'} "
                f"adquiridas em bolsa (B3/Brasil Bolsa Balcão S.A., CNPJ 09.346.601/0001-25). "
                f"Custo médio: R$ {float(avg_cost_current):.2f}/{'cota' if asset_class in ('fii', 'etf') else 'ação'}."
            )
        else:
            discriminacao = f"{ticker} — posição liquidada em {year}."

        items.append({
            "ticker": ticker,
            "asset_class": asset_class,
            "grupo": code_info["grupo"],
            "codigo": code_info["codigo"],
            "descricao_codigo": code_info["descricao"],
            "discriminacao": discriminacao,
            "situacao_ano_anterior": float(custo_prev),
            "situacao_ano_atual": float(custo_current),
            "quantidade_atual": float(qty_current),
            "custo_medio_atual": float(avg_cost_current),
        })

    # Sort: active positions first (custo_atual > 0), then liquidated
    items.sort(key=lambda x: (x["situacao_ano_atual"] == 0, x["ticker"]))

    total_atual = sum(it["situacao_ano_atual"] for it in items)
    total_anterior = sum(it["situacao_ano_anterior"] for it in items)

    return {
        "year": year,
        "reference_date": cutoff.isoformat(),
        "total_declarado_atual": total_atual,
        "total_declarado_anterior": total_anterior,
        "items": items,
        "instrucoes": {
            "ficha": "Bens e Direitos",
            "cnpj_b3": "09.346.601/0001-25",
            "pais": "105 — Brasil",
            "nota": (
                "Preencha uma linha por ativo. "
                "Situação em 31/12 deve refletir o custo de aquisição (CMP), NÃO o valor de mercado. "
                "Lucros e prejuízos realizados são declarados em 'Renda Variável', não aqui."
            ),
        },
    }
