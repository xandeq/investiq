from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/investiq"
    # AUTH_DATABASE_URL: superuser connection used by auth endpoints (register/login/verify).
    # Auth queries look up users by email without a tenant context, so they must bypass RLS.
    # Defaults to the same as DATABASE_URL (postgres superuser bypasses RLS by default).
    AUTH_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/investiq"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    JWT_PRIVATE_KEY: str = ""   # RSA PEM — loaded from AWS SM at runtime
    JWT_PUBLIC_KEY: str = ""    # RSA PEM — loaded from AWS SM at runtime
    # Email — Resend (primary, 3k/mo free) or Brevo (legacy fallback)
    RESEND_API_KEY: str = ""          # set this to use Resend API (resend.com)
    BREVO_API_KEY: str = ""           # legacy — used only when RESEND_API_KEY is empty
    BREVO_FROM_EMAIL: str = "noreply@investiq.com.br"
    BREVO_FROM_NAME: str = "InvestIQ"
    APP_URL: str = "http://localhost:3100"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3100"]
    # Stripe billing — fetched from AWS SM tools/stripe at runtime
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""    # whsec_... from Stripe Dashboard or CLI
    STRIPE_PREMIUM_PRICE_ID: str = ""  # price_... BRL monthly price ID
    ADMIN_EMAILS: list[str] = []       # hardcoded admin email list for v1


settings = Settings()
