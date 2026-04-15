from datetime import datetime

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class MetricsResponse(BaseModel):
    free_users: int
    pro_users: int
    active_subscriptions: int
    past_due_subscriptions: int
    canceled_subscriptions: int
    total_conversions: int  # checkout.session.completed events with status=success
    churn_rate_pct: float  # canceled / (canceled + active) * 100


class UsageResponse(BaseModel):
    imports_this_month: int
    imports_limit: int
    transactions_total: int
    transactions_limit: int
    plan: str


class SubscriberInfo(BaseModel):
    user_id: str
    email: str
    plan: str
    subscription_status: str | None
    stripe_customer_id: str | None
    subscription_current_period_end: datetime | None
    created_at: datetime
