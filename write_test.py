#!/usr/bin/env python
"""Helper script to write the InvestIQ test file"""

script_content = """import asyncio
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://investiq.com.br"
EMAIL = "test@investiq.com"
PASSWORD = "Test1234!"
results = {}


def log(msg, status="info"):
    labels = {"ok": "[OK]", "fail": "[FAIL]", "info": "[INFO]"}
    print(labels.get(status, "[INFO]") + " " + str(msg), flush=True)


async def goto_valid(page, paths):
    for path in paths:
        try:
            await page.goto(
                f"https://investiq.com.br{path}",
                wait_until="networkidle",
                timeout=10000,
            )
            t = await page.title()
            if "404" not in t and "not found" not in t.lower():
                return True
        except:
            pass
    return False


async def main():
    log("=== InvestIQ Comprehensive Test ===")
    chromium = "C:/Users/acq20/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chromium,
            headless=True,
            args=["--no-sandbox"],
        )
        ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await ctx.new_page()
        cons_errors = []
        page.on("console", lambda m: cons_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: cons_errors.append(str(e)))

        # =================== TEST 1: AUTH ===================
        log("=== 1. AUTH ===")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/01_login.png")
        results["login_page_renders"] = "login" in page.url
        log(f"Login page: {page.url}", "ok" if results["login_page_renders"] else "fail")

        await page.fill("input[type=email]", EMAIL)
        await page.fill("input[type=password]", PASSWORD)
        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/01b_after_login.png")
        results["login_success"] = "login" not in page.url
        log(f"After login: {page.url}", "ok" if results["login_success"] else "fail")

        if not results["login_success"]:
            log("Cannot continue - login failed", "fail")
            content = await page.content()
            for kw in ["senha", "credencial", "inválido", "invalid", "incorrect", "error"]:
                if kw.lower() in content.lower():
                    log(f"Error found: {kw}")
            await browser.close()
            return

        # =================== TEST 2: DASHBOARD ===================
        log("\\n=== 2. DASHBOARD ===")
        await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        await page.screenshot(path="C:/tmp/02_dashboard.png")
        content = await page.content()
        log(f"Dashboard URL: {page.url}")

        indicators = [i for i in ["SELIC", "CDI", "IPCA", "PTAX"] if i in content]
        results["macro_indicators"] = len(indicators) >= 2
        log(f"Macro indicators: {indicators}", "ok" if results["macro_indicators"] else "fail")

        results["portfolio_summary"] = any(
            k in content.lower() for k in ["carteira", "portf", "patrimônio", "patrimonio"]
        )
        results["recent_transactions"] = any(
            k in content.lower() for k in ["transação", "transacao", "histórico", "operação"]
        )
        log(f"Portfolio summary: {results['portfolio_summary']}", "ok" if results["portfolio_summary"] else "fail")
        log(f"Recent transactions: {results['recent_transactions']}", "ok" if results["recent_transactions"] else "fail")

        # Check for SELIC/CDI actual values (bug: was showing daily 0.06% instead of annual ~13.75%)
        selic_re = re.findall(r"SELIC[\\s\\S]{0,300}?(\\d+[.,]\\d+)\\s*%", content[:10000])
        cdi_re = re.findall(r"CDI[\\s\\S]{0,300}?(\\d+[.,]\\d+)\\s*%", content[:10000])
        log(f"SELIC values in HTML: {selic_re[:3]}")
        log(f"CDI values in HTML: {cdi_re[:3]}")
        if selic_re:
            val = float(selic_re[0].replace(",", "."))
            results["selic_correct_value"] = val > 5.0
            if val > 5.0:
                log(f"SELIC={val}% - annual rate OK", "ok")
            else:
                log(f"SELIC={val}% - DAILY RATE BUG (should be ~13%)", "fail")

        # =================== TEST 3: CARTEIRA ===================
        log("\\n=== 3. CARTEIRA ===")
        await page.goto(f"{BASE_URL}/carteira", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        await page.screenshot(path="C:/tmp/03_carteira.png")
        content = await page.content()
        log(f"Carteira URL: {page.url}")

        pnl_kw = ["PnL", "P&L", "lucro", "resultado", "posição", "ticker", "quantidade"]
        found_pnl = [k for k in pnl_kw if k.lower() in content.lower()]
        results["portfolio_table"] = len(found_pnl) >= 1
        log(f"Portfolio table ({found_pnl})", "ok" if results["portfolio_table"] else "fail")

        add_btns = page.locator("button:has-text('Adicionar'), button:has-text('Nova Transação')")
        btn_count = await add_btns.count()
        log(f"Add buttons found: {btn_count}")

        if btn_count > 0:
            await add_btns.first.click()
            await asyncio.sleep(1)
            await page.screenshot(path="C:/tmp/03b_modal.png")
            results["add_transaction_btn"] = True
            log("Add transaction modal opened", "ok")

            # Try to fill ticker
            ticker_in = page.locator(
                "input[placeholder*='ticker' i], input[placeholder*='ativo' i], input[name='ticker']"
            )
            if await ticker_in.count() > 0:
                await ticker_in.first.fill("VALE3")
                log("Filled VALE3", "ok")
                await page.screenshot(path="C:/tmp/03c_form.png")

            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        else:
            results["add_transaction_btn"] = False
            log("No add button found", "fail")

        # =================== TEST 4: WATCHLIST ===================
        log("\\n=== 4. WATCHLIST ===")
        await goto_valid(page, ["/watchlist", "/lista-observacao", "/monitoramento"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/04_watchlist.png")
        content = await page.content()
        log(f"Watchlist URL: {page.url}")

        found_wl = [k for k in ["watchlist", "observação", "monitorar", "ticker"] if k.lower() in content.lower()]
        results["watchlist_page"] = len(found_wl) >= 1
        log(f"Watchlist ({found_wl})", "ok" if results["watchlist_page"] else "fail")

        # =================== TEST 5: SCREENER ===================
        log("\\n=== 5. SCREENER ===")
        await goto_valid(page, ["/screener", "/filtro", "/scanner"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/05_screener.png")
        content = await page.content()
        log(f"Screener URL: {page.url}")

        found_sc = [k for k in ["screener", "filtro", "scanner", "P/L", "P/VP"] if k.lower() in content.lower()]
        results["screener_page"] = len(found_sc) >= 1
        log(f"Screener ({found_sc})", "ok" if results["screener_page"] else "fail")

        # =================== TEST 6: INSIGHTS ===================
        log("\\n=== 6. INSIGHTS ===")
        await goto_valid(page, ["/insights", "/analises", "/recomendacoes"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/06_insights.png")
        content = await page.content()
        log(f"Insights URL: {page.url}")

        found_ins = [k for k in ["insight", "análise", "analise", "recomend"] if k.lower() in content.lower()]
        results["insights_page"] = len(found_ins) >= 1
        log(f"Insights ({found_ins})", "ok" if results["insights_page"] else "fail")

        # =================== TEST 7: AI FEATURES ===================
        log("\\n=== 7. AI FEATURES (CRITICAL) ===")
        await goto_valid(page, ["/ia", "/ai", "/inteligencia-artificial"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/07_ai.png")
        content = await page.content()
        log(f"AI URL: {page.url}")

        found_ai = [k for k in ["ia", "inteligência", "análise de ativo", "advisor"] if k.lower() in content.lower()]
        results["ai_page"] = len(found_ai) >= 1
        log(f"AI page ({found_ai})", "ok" if results["ai_page"] else "fail")

        if results["ai_page"]:
            ticker_ins = page.locator(
                "input[placeholder*='ticker' i], input[placeholder*='VALE' i], input[placeholder*='ativo' i], input[placeholder*='símbolo' i]"
            )
            t_count = await ticker_ins.count()
            log(f"Ticker inputs on AI page: {t_count}")

            if t_count > 0:
                await ticker_ins.first.fill("VALE3")
                btn = page.locator("button:has-text('Analisar'), button:has-text('Analyze'), button:has-text('Executar')")
                if await btn.count() > 0:
                    await btn.first.click()
                    log("AI analysis submitted for VALE3", "ok")
                    results["ai_analysis_submitted"] = True

                    log("Polling AI job (up to 120s)...")
                    for i in range(24):
                        await asyncio.sleep(5)
                        c = await page.content()
                        is_p = any(t in c.lower() for t in ["pendente", "pending", "processando", "aguardando"])
                        is_e = any(t in c.lower() for t in ["erro interno", "falhou", "failed"]) and not is_p
                        is_d = any(t in c.lower() for t in ["resultado", "recomend", "comprar", "vender", "análise completa"]) and not is_p
                        elapsed = (i + 1) * 5

                        if is_e:
                            log(f"AI job errored at {elapsed}s", "fail")
                            results["ai_job_completed"] = False
                            await page.screenshot(path="C:/tmp/07b_error.png")
                            break
                        elif is_d:
                            log(f"AI job completed at {elapsed}s!", "ok")
                            results["ai_job_completed"] = True
                            await page.screenshot(path="C:/tmp/07c_done.png")
                            break
                        else:
                            log(f"  {elapsed}s - pending={is_p}")
                    else:
                        log("AI job timed out (120s)", "fail")
                        results["ai_job_completed"] = False
                        await page.screenshot(path="C:/tmp/07d_timeout.png")
                else:
                    log("No analyze button found", "fail")
                    results["ai_analysis_submitted"] = False
            else:
                log("No ticker input on AI page", "fail")

        # =================== TEST 8: PROFILE ===================
        log("\\n=== 8. PROFILE ===")
        await goto_valid(page, ["/perfil", "/profile", "/configuracoes", "/settings"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/08_profile.png")
        content = await page.content()
        log(f"Profile URL: {page.url}")

        found_p = [k for k in ["perfil", "profile", "objetivo", "horizonte", "risco"] if k.lower() in content.lower()]
        results["profile_page"] = len(found_p) >= 1
        log(f"Profile ({found_p})", "ok" if results["profile_page"] else "fail")

        # =================== TEST 9: PLANS ===================
        log("\\n=== 9. PLANS ===")
        await goto_valid(page, ["/planos", "/plans", "/pricing", "/assinatura"])
        await asyncio.sleep(2)
        await page.screenshot(path="C:/tmp/09_plans.png")
        content = await page.content()
        log(f"Plans URL: {page.url}")

        found_pl = [k for k in ["plano", "plan", "preço", "premium", "R$"] if k.lower() in content.lower()]
        results["plans_page"] = len(found_pl) >= 2
        log(f"Plans ({found_pl})", "ok" if results["plans_page"] else "fail")

        # Console errors summary
        if cons_errors:
            log(f"\\n=== CONSOLE ERRORS ({len(cons_errors)} total) ===")
            for e in cons_errors[:25]:
                print(f"  {e}")

        await browser.close()

    print("\\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        print(f"  [{status}] {k}")
    print(f"\\nTotal: {passed}/{len(results)} passed")

    with open("C:/tmp/test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to C:/tmp/test_results.json")


asyncio.run(main())
"""

with open("C:/tmp/test_investiq_full.py", "w", encoding="utf-8") as f:
    f.write(script_content)

print("Test script written to C:/tmp/test_investiq_full.py")
