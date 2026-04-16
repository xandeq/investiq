"""Billing transactional email templates for InvestIQ.

Each function returns a (subject, html_content) tuple ready to pass
directly to brevo_email_sender().  All content is in Brazilian Portuguese.
All CSS is inline — external stylesheets are not supported in email clients.
"""
from __future__ import annotations

from datetime import datetime


# ---------------------------------------------------------------------------
# Shared layout helpers
# ---------------------------------------------------------------------------

_FONT = "'Segoe UI', Helvetica, Arial, sans-serif"
_BLUE = "#3B82F6"
_DARK = "#111827"
_WHITE = "#FFFFFF"
_LIGHT_BG = "#F9FAFB"
_GRAY_TEXT = "#6B7280"
_BODY_TEXT = "#374151"


def _build_email(*, header_title: str, body_html: str) -> str:
    """Wrap body content in the shared InvestIQ email shell."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{header_title}</title>
</head>
<body style="margin:0;padding:0;background-color:{_LIGHT_BG};font-family:{_FONT};">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background-color:{_LIGHT_BG};padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0"
               style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background-color:{_DARK};border-radius:12px 12px 0 0;padding:24px 32px;">
              <table role="presentation" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <span style="display:inline-block;background-color:{_BLUE};
                                 color:{_WHITE};font-weight:700;font-size:16px;
                                 border-radius:6px;padding:6px 10px;
                                 font-family:{_FONT};letter-spacing:-0.5px;">IQ</span>
                  </td>
                  <td style="vertical-align:middle;padding-left:10px;">
                    <span style="color:{_WHITE};font-size:20px;font-weight:700;
                                 font-family:{_FONT};letter-spacing:-0.3px;">InvestIQ</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background-color:{_WHITE};padding:32px;border-radius:0;">
              {body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:{_LIGHT_BG};border-radius:0 0 12px 12px;
                       padding:20px 32px;border-top:1px solid #E5E7EB;">
              <p style="margin:0;font-family:{_FONT};font-size:12px;color:{_GRAY_TEXT};
                         text-align:center;line-height:1.5;">
                Você recebeu este email porque possui uma conta InvestIQ.<br>
                &copy; 2026 InvestIQ &mdash; Todos os direitos reservados.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _cta_button(label: str, url: str) -> str:
    return (
        f'<a href="{url}" target="_blank" '
        f'style="display:inline-block;margin-top:24px;padding:14px 28px;'
        f'background-color:{_BLUE};color:{_WHITE};border-radius:8px;'
        f'text-decoration:none;font-weight:600;font-size:15px;'
        f'font-family:{_FONT};">'
        f"{label}</a>"
    )


def _format_date(dt: datetime | None) -> str:
    """Format a datetime as DD/MM/YYYY, or return a fallback string."""
    if dt is None:
        return "em breve"
    return dt.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Template functions
# ---------------------------------------------------------------------------


def welcome_premium_email(
    user_email: str, period_end: datetime | None
) -> tuple[str, str]:
    """Returns (subject, html_content) for the welcome-to-premium email.

    Sent after checkout.session.completed when the user first upgrades.
    """
    subject = "Bem-vindo ao InvestIQ Premium!"
    period_str = _format_date(period_end)

    body = f"""
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        Seu plano Premium est&#225; ativo! &#127881;
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Ol&#225;! Obrigado por assinar o InvestIQ Premium.
        Sua conta j&#225; est&#225; liberada com todos os recursos.
      </p>

      <!-- Benefits list -->
      <table role="presentation" cellspacing="0" cellpadding="0"
             style="margin:24px 0;width:100%;">
        <tr>
          <td style="background-color:{_LIGHT_BG};border-radius:8px;padding:20px 24px;">
            <p style="margin:0 0 12px;font-family:{_FONT};font-size:13px;font-weight:700;
                       color:{_GRAY_TEXT};text-transform:uppercase;letter-spacing:0.5px;">
              O que voc&#234; acaba de desbloquear
            </p>
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%">
              {"".join(
                f'<tr><td style="padding:4px 0;font-family:{_FONT};font-size:14px;color:{_BODY_TEXT};">'
                f'&#10003;&nbsp; {benefit}</td></tr>'
                for benefit in [
                    "An&#225;lises com Intelig&#234;ncia Artificial ilimitadas",
                    "Importa&#231;&#245;es de extrato sem limite",
                    "Transa&#231;&#245;es ilimitadas",
                    "Relat&#243;rios avan&#231;ados de imposto de renda",
                    "Suporte priorit&#225;rio",
                ]
              )}
            </table>
          </td>
        </tr>
      </table>

      <p style="margin:16px 0 0;font-family:{_FONT};font-size:14px;color:{_GRAY_TEXT};">
        Pr&#243;xima renova&#231;&#227;o: <strong style="color:{_BODY_TEXT};">{period_str}</strong>
      </p>

      {_cta_button("Acessar minha conta", "https://investiq.com.br/dashboard")}
    """

    return subject, _build_email(header_title=subject, body_html=body)


def payment_received_email(
    user_email: str, period_end: datetime | None
) -> tuple[str, str]:
    """Returns (subject, html_content) for a recurring payment confirmation.

    Sent on invoice.paid to confirm the renewal charge went through.
    """
    subject = "Pagamento confirmado — InvestIQ Premium"
    period_str = _format_date(period_end)

    body = f"""
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        Pagamento confirmado &#10003;
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Seu pagamento foi processado com sucesso. Seu acesso Premium continua
        ativo sem interrup&#231;&#245;es.
      </p>

      <table role="presentation" cellspacing="0" cellpadding="0"
             style="margin:24px 0;width:100%;">
        <tr>
          <td style="background-color:{_LIGHT_BG};border-radius:8px;padding:20px 24px;">
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%">
              <tr>
                <td style="font-family:{_FONT};font-size:14px;color:{_GRAY_TEXT};
                            padding-bottom:8px;">Plano</td>
                <td align="right" style="font-family:{_FONT};font-size:14px;
                             font-weight:600;color:{_BODY_TEXT};padding-bottom:8px;">
                  InvestIQ Premium
                </td>
              </tr>
              <tr>
                <td style="font-family:{_FONT};font-size:14px;color:{_GRAY_TEXT};">
                  Pr&#243;xima renova&#231;&#227;o
                </td>
                <td align="right" style="font-family:{_FONT};font-size:14px;
                             font-weight:600;color:{_BODY_TEXT};">
                  {period_str}
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      {_cta_button("Acessar minha conta", "https://investiq.com.br/dashboard")}
    """

    return subject, _build_email(header_title=subject, body_html=body)


def payment_failed_email(user_email: str) -> tuple[str, str]:
    """Returns (subject, html_content) for a payment failure warning.

    Sent on invoice.payment_failed to prompt the user to update their
    payment method before access is downgraded.
    """
    subject = "Problema com seu pagamento — InvestIQ"

    body = f"""
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        N&#227;o conseguimos processar seu pagamento &#9888;&#65039;
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Houve um problema ao cobrar sua assinatura InvestIQ Premium.
        Atualize seu m&#233;todo de pagamento para manter o acesso Premium.
      </p>

      <!-- Warning box -->
      <table role="presentation" cellspacing="0" cellpadding="0"
             style="margin:24px 0;width:100%;">
        <tr>
          <td style="background-color:#FEF3C7;border-left:4px solid #F59E0B;
                     border-radius:0 8px 8px 0;padding:16px 20px;">
            <p style="margin:0;font-family:{_FONT};font-size:14px;
                       color:#92400E;line-height:1.5;">
              <strong>Aten&#231;&#227;o:</strong> sem a regulariza&#231;&#227;o do pagamento,
              sua conta ser&#225; automaticamente movida para o plano Gratuito.
            </p>
          </td>
        </tr>
      </table>

      <p style="margin:0;font-family:{_FONT};font-size:14px;color:{_GRAY_TEXT};
                 line-height:1.5;">
        Clique no bot&#227;o abaixo para atualizar seu cart&#227;o ou escolher
        outra forma de pagamento.
      </p>

      {_cta_button("Atualizar pagamento", "https://investiq.com.br/planos")}
    """

    return subject, _build_email(header_title=subject, body_html=body)


def verification_email(user_email: str, verify_url: str) -> tuple[str, str]:
    """Returns (subject, html_content) for email address verification on registration."""
    subject = "Verifique seu email — InvestIQ"

    body = f"""
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        Bem-vindo ao InvestIQ!
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Você criou sua conta com sucesso. Clique no botão abaixo para verificar seu
        endereço de email e ativar o acesso ao InvestIQ.
      </p>
      <p style="margin:12px 0 0;font-family:{_FONT};font-size:14px;color:{_GRAY_TEXT};">
        Você tem <strong>14 dias de trial Premium</strong> gratuito a partir de hoje.
      </p>

      {_cta_button("Verificar meu email", verify_url)}

      <p style="margin:24px 0 0;font-family:{_FONT};font-size:13px;color:{_GRAY_TEXT};line-height:1.5;">
        Se você não criou uma conta no InvestIQ, ignore este email.<br>
        Este link expira em <strong>24 horas</strong>.
      </p>
    """

    return subject, _build_email(header_title=subject, body_html=body)


def trial_expiring_soon_email(
    user_email: str, days_remaining: int, trial_ends_at: datetime | None
) -> tuple[str, str]:
    """Returns (subject, html_content) for trial expiry warning.

    Sent 3 days before trial_ends_at. Uses trial_warning_sent flag to prevent
    duplicate sends.
    """
    subject = f"Seu período de teste InvestIQ expira em {days_remaining} {'dia' if days_remaining == 1 else 'dias'}"

    features_html = "".join(
        f'<tr><td style="padding:4px 0;font-family:{_FONT};font-size:14px;color:{_BODY_TEXT};">'
        f'&#10003;&nbsp; {item}</td></tr>'
        for item in [
            "Análise de IA ilimitada (DCF, Valuation, Macro)",
            "Advisor de Carteira personalizado",
            "Screener avançado (Goldman Method)",
            "Importação ilimitada de extratos B3",
            "Alertas de preço por email",
            "Histórico completo e relatórios IR",
        ]
    )

    body = f"""
      <p style="margin:0 0 4px;font-family:{_FONT};font-size:13px;font-weight:600;
                 color:{_BLUE};text-transform:uppercase;letter-spacing:0.5px;">
        Aviso de trial
      </p>
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        Seu trial expira em {days_remaining} {'dia' if days_remaining == 1 else 'dias'}
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Sua avaliação gratuita do InvestIQ Premium termina em
        <strong>{_format_date(trial_ends_at)}</strong>.
        Para continuar tendo acesso a todas as funcionalidades, assine o plano Premium agora.
      </p>

      <!-- Features included -->
      <table role="presentation" cellspacing="0" cellpadding="0"
             style="margin:24px 0;width:100%;">
        <tr>
          <td style="background-color:{_LIGHT_BG};border-radius:8px;padding:20px 24px;">
            <p style="margin:0 0 12px;font-family:{_FONT};font-size:13px;font-weight:700;
                       color:{_GRAY_TEXT};text-transform:uppercase;letter-spacing:0.5px;">
              O que você perde sem o Premium
            </p>
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%">
              {features_html}
            </table>
          </td>
        </tr>
      </table>

      <p style="margin:0;font-family:{_FONT};font-size:15px;color:{_BODY_TEXT};line-height:1.6;">
        Seus dados e carteira ficam preservados independente do plano.
        Assine agora e mantenha seu acesso completo sem interrupção.
      </p>

      {_cta_button("Assinar Premium — Manter Acesso", "https://investiq.com.br/planos")}

      <p style="margin:16px 0 0;font-family:{_FONT};font-size:12px;color:{_GRAY_TEXT};">
        Você recebeu este aviso porque seu trial está próximo do vencimento ({user_email}).
      </p>
    """

    return subject, _build_email(header_title=subject, body_html=body)


def subscription_canceled_email(user_email: str) -> tuple[str, str]:
    """Returns (subject, html_content) for subscription cancellation notice.

    Sent on customer.subscription.updated / .deleted when the plan
    transitions to "free".
    """
    subject = "Sua assinatura InvestIQ foi cancelada"

    body = f"""
      <h1 style="margin:0 0 8px;font-family:{_FONT};font-size:24px;
                 font-weight:700;color:{_DARK};">
        Sua assinatura Premium foi cancelada
      </h1>
      <p style="margin:16px 0 0;font-family:{_FONT};font-size:15px;
                color:{_BODY_TEXT};line-height:1.6;">
        Sentimos sua falta. Sua assinatura InvestIQ Premium foi cancelada
        e sua conta foi movida para o plano Gratuito.
      </p>

      <!-- Free plan limits -->
      <table role="presentation" cellspacing="0" cellpadding="0"
             style="margin:24px 0;width:100%;">
        <tr>
          <td style="background-color:{_LIGHT_BG};border-radius:8px;padding:20px 24px;">
            <p style="margin:0 0 12px;font-family:{_FONT};font-size:13px;font-weight:700;
                       color:{_GRAY_TEXT};text-transform:uppercase;letter-spacing:0.5px;">
              Voc&#234; ainda tem acesso ao plano Gratuito
            </p>
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%">
              {"".join(
                f'<tr><td style="padding:4px 0;font-family:{_FONT};font-size:14px;color:{_BODY_TEXT};">'
                f'&#8226;&nbsp; {item}</td></tr>'
                for item in [
                    "At&#233; 50 transa&#231;&#245;es por m&#234;s",
                    "At&#233; 3 importa&#231;&#245;es de extrato por m&#234;s",
                    "Vis&#227;o geral da carteira",
                ]
              )}
            </table>
          </td>
        </tr>
      </table>

      <p style="margin:0;font-family:{_FONT};font-size:15px;color:{_BODY_TEXT};
                 line-height:1.6;">
        Volte quando quiser &mdash; sua conta e seus dados estar&#227;o aqui
        esperando por voc&#234;.
      </p>

      {_cta_button("Reativar Premium", "https://investiq.com.br/planos")}
    """

    return subject, _build_email(header_title=subject, body_html=body)
