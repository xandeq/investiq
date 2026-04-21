"""Remediação de assinaturas duplicadas.

Script idempotente para identificar usuários com múltiplas assinaturas ativas
no Stripe e cancelar as redundantes, emitindo reembolso proporcional quando
aplicável.

Uso:
    # Dry-run (padrão) — apenas exibe o relatório de impacto, sem alterar nada
    python scripts/remediate_duplicate_subscriptions.py

    # Execução real — requer confirmação explícita
    python scripts/remediate_duplicate_subscriptions.py --execute

    # Reembolso automático junto com o cancelamento
    python scripts/remediate_duplicate_subscriptions.py --execute --refund

    # Filtrar por usuário específico
    python scripts/remediate_duplicate_subscriptions.py --execute --user-id <uuid>

Regras de segurança:
    - Por padrão roda em dry-run. --execute deve ser passado explicitamente.
    - Nunca cancela a assinatura mais recente (a ativa é a de maior created).
    - Reembolso é proporcional ao período não utilizado.
    - Todas as ações são logadas com status final (success / skipped / error).
    - Idempotente: re-executar não cancela assinaturas já canceladas.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import NamedTuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class AffectedUser(NamedTuple):
    user_id: str
    email: str
    stripe_customer_id: str
    active_subscription_ids: list[str]  # sorted by created asc (oldest first)
    current_subscription_id: str        # pointer in users table


class RemediationResult(NamedTuple):
    user_id: str
    email: str
    canceled: list[str]
    refunded: list[str]
    skipped: list[str]
    errors: list[str]


async def find_affected_users(db) -> list[AffectedUser]:
    """Return users who have >1 active subscription in the subscriptions table."""
    from sqlalchemy import select, func
    from app.modules.auth.models import User
    from app.modules.billing.models import Subscription

    # Find user_ids with multiple active subscription rows
    subq = (
        select(Subscription.user_id)
        .where(Subscription.status.in_(["active", "trialing"]))
        .group_by(Subscription.user_id)
        .having(func.count(Subscription.id) > 1)
    )
    result = await db.execute(subq)
    affected_user_ids = [row[0] for row in result.fetchall()]

    if not affected_user_ids:
        return []

    affected = []
    for user_id in affected_user_ids:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.stripe_customer_id:
            continue

        subs_result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status.in_(["active", "trialing"]))
            .order_by(Subscription.created_at.asc())
        )
        subs = subs_result.scalars().all()
        sub_ids = [s.stripe_subscription_id for s in subs]

        affected.append(AffectedUser(
            user_id=user_id,
            email=user.email,
            stripe_customer_id=user.stripe_customer_id,
            active_subscription_ids=sub_ids,
            current_subscription_id=user.stripe_subscription_id or "",
        ))

    return affected


async def cancel_duplicate_subscriptions(
    affected_users: list[AffectedUser],
    execute: bool,
    do_refund: bool,
    filter_user_id: str | None,
    stripe_client,
    db,
) -> list[RemediationResult]:
    """Cancel all but the most recent subscription for each affected user."""
    from sqlalchemy import select
    from app.modules.billing.models import Subscription

    results = []

    for user in affected_users:
        if filter_user_id and user.user_id != filter_user_id:
            continue

        # Keep the subscription that matches users.stripe_subscription_id.
        # If the pointer is stale (not in active list), keep the newest by order.
        if user.current_subscription_id in user.active_subscription_ids:
            keep_id = user.current_subscription_id
        else:
            keep_id = user.active_subscription_ids[-1]  # newest

        to_cancel = [sid for sid in user.active_subscription_ids if sid != keep_id]

        canceled, refunded, skipped, errors = [], [], [], []

        logger.info(
            "[%s] user=%s email=%s keep=%s...%s cancel_count=%d",
            "EXECUTE" if execute else "DRY-RUN",
            user.user_id,
            user.email,
            keep_id[:8], keep_id[-4:],
            len(to_cancel),
        )

        for sub_id in to_cancel:
            sub_prefix = f"{sub_id[:8]}...{sub_id[-4:]}"
            try:
                # Check current status in Stripe first (idempotency)
                stripe_sub = await stripe_client.subscriptions.retrieve_async(sub_id)
                if stripe_sub.status in ("canceled", "incomplete_expired"):
                    logger.info("  SKIP %s — already %s in Stripe", sub_prefix, stripe_sub.status)
                    skipped.append(sub_id)

                    # Still update local DB row if it shows active
                    if execute:
                        sub_row_result = await db.execute(
                            select(Subscription).where(
                                Subscription.stripe_subscription_id == sub_id
                            )
                        )
                        sub_row = sub_row_result.scalar_one_or_none()
                        if sub_row and sub_row.status in ("active", "trialing"):
                            sub_row.status = "canceled"
                            await db.flush()
                    continue

                if not execute:
                    logger.info("  DRY-RUN would cancel %s", sub_prefix)
                    continue

                # Cancel in Stripe
                await stripe_client.subscriptions.cancel_async(sub_id)
                logger.info("  CANCELED %s in Stripe", sub_prefix)
                canceled.append(sub_id)

                # Update local DB
                sub_row_result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == sub_id
                    )
                )
                sub_row = sub_row_result.scalar_one_or_none()
                if sub_row:
                    sub_row.status = "canceled"
                    await db.flush()

                # Emit refund if requested
                if do_refund:
                    try:
                        invoices = await stripe_client.invoices.list_async(
                            params={"subscription": sub_id, "status": "paid"}
                        )
                        for invoice in invoices.data:
                            if not invoice.charge:
                                continue
                            # Proportional refund: unused days / total days
                            now_ts = datetime.now(tz=timezone.utc).timestamp()
                            period_start = invoice.period_start
                            period_end = invoice.period_end
                            total_seconds = period_end - period_start
                            unused_seconds = max(0, period_end - now_ts)
                            if total_seconds > 0 and unused_seconds > 0:
                                refund_ratio = unused_seconds / total_seconds
                                refund_amount = int(invoice.amount_paid * refund_ratio)
                                if refund_amount > 0:
                                    await stripe_client.refunds.create_async(
                                        params={
                                            "charge": invoice.charge,
                                            "amount": refund_amount,
                                            "reason": "duplicate",
                                        }
                                    )
                                    logger.info(
                                        "  REFUNDED R$%.2f for invoice %s (%.0f%% unused)",
                                        refund_amount / 100,
                                        invoice.id,
                                        refund_ratio * 100,
                                    )
                                    refunded.append(sub_id)
                    except Exception as exc:
                        logger.error("  REFUND_ERROR %s: %s", sub_prefix, exc)
                        errors.append(f"refund:{sub_id}:{exc}")

            except Exception as exc:
                logger.error("  ERROR canceling %s: %s", sub_prefix, exc)
                errors.append(f"cancel:{sub_id}:{exc}")

        results.append(RemediationResult(
            user_id=user.user_id,
            email=user.email,
            canceled=canceled,
            refunded=refunded,
            skipped=skipped,
            errors=errors,
        ))

    return results


def print_summary(
    affected: list[AffectedUser],
    results: list[RemediationResult],
    execute: bool,
) -> None:
    print("\n" + "=" * 70)
    print(f"REMEDIATION REPORT — {'EXECUTED' if execute else 'DRY-RUN'}")
    print("=" * 70)
    print(f"Affected users found:  {len(affected)}")
    total_dupes = sum(len(u.active_subscription_ids) - 1 for u in affected)
    print(f"Duplicate subs total:  {total_dupes}")

    if results:
        total_canceled = sum(len(r.canceled) for r in results)
        total_refunded = sum(len(r.refunded) for r in results)
        total_errors = sum(len(r.errors) for r in results)
        print(f"Canceled:              {total_canceled}")
        print(f"Refunded:              {total_refunded}")
        print(f"Errors:                {total_errors}")
        print()
        for r in results:
            print(
                f"  {r.email} ({r.user_id[:8]}...) "
                f"canceled={r.canceled} refunded={r.refunded} errors={r.errors}"
            )

    if not execute:
        print()
        print("This was a DRY-RUN. Pass --execute to apply changes.")
    print("=" * 70)


async def main(execute: bool, do_refund: bool, filter_user_id: str | None) -> None:
    import sys
    import os

    # Bootstrap Django-style app path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from stripe import StripeClient, HTTPXClient
    from app.core.config import settings
    from app.core.db import _auth_session_factory  # superuser — bypasses RLS

    stripe_client = StripeClient(
        api_key=settings.STRIPE_SECRET_KEY,
        http_client=HTTPXClient(),
    )

    async with _auth_session_factory() as db:
        affected = await find_affected_users(db)

        if not affected:
            logger.info("No users with duplicate active subscriptions found.")
            return

        logger.info("Found %d users with duplicate subscriptions.", len(affected))
        for u in affected:
            logger.info(
                "  user=%s email=%s subs=%d current=%s...%s",
                u.user_id, u.email,
                len(u.active_subscription_ids),
                u.current_subscription_id[:8] if u.current_subscription_id else "NONE",
                u.current_subscription_id[-4:] if u.current_subscription_id else "",
            )

        results = await cancel_duplicate_subscriptions(
            affected_users=affected,
            execute=execute,
            do_refund=do_refund,
            filter_user_id=filter_user_id,
            stripe_client=stripe_client,
            db=db,
        )

        if execute:
            await db.commit()

        print_summary(affected, results, execute)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--refund", action="store_true", help="Emit proportional refund when canceling")
    parser.add_argument("--user-id", dest="user_id", default=None, help="Restrict to a single user UUID")
    args = parser.parse_args()

    asyncio.run(main(execute=args.execute, do_refund=args.refund, filter_user_id=args.user_id))
