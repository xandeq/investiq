"""IR Helper router.

Endpoints:
  GET /ir-helper/summary?month=YYYY-MM  — Calcula DARF mensal de swing trade
  GET /ir-helper/history                 — Histórico mensal de P&L e DARF
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.portfolio.models import Transaction, TransactionType

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
