#!/usr/bin/env python
"""Write the comprehensive InvestIQ test v2 with correct URLs"""

script_content = """import asyncio
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://investiq.com.br"
EMAIL = "test@investiq.com"
PASSWORD = "Test1234!"
results = {}
CHROMIUM = "C:/Users/acq20/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe"


def log(msg, status="info"):
    labels = {"ok": "[OK]", "fail": "[FAIL]", "info": "[INFO]", "warn": "[WARN]"}
    print(labels.get(status, "[INFO]") + " " + str(msg), flush=True)


async def wait_and_screenshot(page, path, wait=2):
    await asyncio.sleep(wait)
    await page.screenshot(path=path)


async def main():
    log("=== InvestIQ Comprehensive Test v2 ===")
    log(f"User: {EMAIL} (upgraded to premium)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROMIUM,
            headless=True,
            args=["--no-sandbox"],
        )
        ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await ctx.new_page()
        cons_errors = []
        failed_requests = []

        def handle_console(m):
            if m.type == "error":
                cons_errors.append(m.text)

        def handle_request_failed(req):
            failed_requests.append(f"{req.method} {req.url}")

        page.on("console", handle_console)
        page.on("pageerror", lambda e: cons_errors.append(f"PAGEERROR: {e}"))
        page.on("requestfailed", handle_request_failed)

        # =================== TEST 1: AUTH ===================
        log("\\n=== 1. AUTH ===")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_01_login.png")
        results["login_page_renders"] = "login" in page.url
        log(f"Login page URL: {page.url}", "ok" if results["login_page_renders"] else "fail")

        await page.fill("input[type=email]", EMAIL)
        await page.fill("input[type=password]", PASSWORD)
        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await wait_and_screenshot(page, "C:/tmp/t2_01b_after_login.png", wait=3)
        results["login_success"] = "login" not in page.url
        log(f"After login: {page.url}", "ok" if results["login_success"] else "fail")

        if not results["login_success"]:
            log("Cannot continue - login failed", "fail")
            content = await page.content()
            for kw in ["senha", "credencial", "invalid", "incorrect"]:
                if kw.lower() in content.lower():
                    log(f"  Error hint: '{kw}' found in page")
            await browser.close()
            return

        # =================== TEST 2: DASHBOARD ===================
        log("\\n=== 2. DASHBOARD ===")
        await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_02_dashboard.png", wait=3)
        log(f"Dashboard URL: {page.url}")

        content = await page.content()
        indicators = [i for i in ["SELIC", "CDI", "IPCA", "PTAX"] if i in content]
        results["macro_indicators_present"] = len(indicators) >= 3
        log(f"Macro indicators in HTML: {indicators}", "ok" if results["macro_indicators_present"] else "fail")

        # Check actual values from page text
        # Try getting visible text via evaluate
        text_content = await page.evaluate("() => document.body.innerText")

        selic_matches = re.findall(r"SELIC[\\s\\S]{0,50}?(\\d+[.,]\\d+)\\s*%", text_content[:5000])
        cdi_matches = re.findall(r"CDI[\\s\\S]{0,50}?(\\d+[.,]\\d+)\\s*%", text_content[:5000])
        ipca_matches = re.findall(r"IPCA[\\s\\S]{0,50}?(\\d+[.,]\\d+)\\s*%", text_content[:5000])

        log(f"SELIC text values: {selic_matches[:3]}")
        log(f"CDI text values: {cdi_matches[:3]}")
        log(f"IPCA text values: {ipca_matches[:3]}")

        if selic_matches:
            val = float(selic_matches[0].replace(",", "."))
            results["selic_annual_rate"] = val > 5.0
            if val > 5.0:
                log(f"SELIC={val}% - annual rate CORRECT", "ok")
            else:
                log(f"SELIC={val}% - DAILY RATE BUG (should be ~14%)", "fail")
        else:
            log("SELIC value not extractable from page text", "warn")
            results["selic_annual_rate"] = None

        results["portfolio_summary"] = any(k in text_content for k in ["Patrimônio", "PATRIMÔNIO", "Carteira", "R$ 0"])
        results["dashboard_sections"] = any(k in text_content for k in ["ALOCAÇÃO", "Evolução", "Configure"])
        log(f"Portfolio summary: {results['portfolio_summary']}", "ok" if results["portfolio_summary"] else "fail")
        log(f"Dashboard sections: {results['dashboard_sections']}", "ok" if results["dashboard_sections"] else "fail")

        # =================== TEST 3: PORTFOLIO ===================
        log("\\n=== 3. PORTFOLIO (Portfólio) ===")
        await page.goto(f"{BASE_URL}/portfolio", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_03_portfolio.png", wait=3)
        log(f"Portfolio URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        log(f"Portfolio page title area: {text_content[:200].strip()}")

        pnl_kw = ["P&L", "PnL", "Custo", "Preço", "Quantidade", "QTD", "ATIVO", "Carteira"]
        found_pnl = [k for k in pnl_kw if k in text_content]
        results["portfolio_table"] = len(found_pnl) >= 1
        log(f"Portfolio table keywords: {found_pnl}", "ok" if results["portfolio_table"] else "fail")

        # =================== TEST 4: TRANSACTIONS ===================
        log("\\n=== 4. TRANSACTIONS ===")
        await page.goto(f"{BASE_URL}/portfolio/transactions", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_04_transactions.png", wait=3)
        log(f"Transactions URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        log(f"Transactions page text: {text_content[:300].strip()}")

        # Look for add transaction button
        add_btns = page.locator("button:has-text('Adicionar'), button:has-text('Nova'), button:has-text('+')")
        btn_count = await add_btns.count()
        log(f"Add buttons: {btn_count}")
        results["transactions_page"] = "Transaç" in text_content or "transac" in text_content.lower() or btn_count > 0

        if btn_count > 0:
            await add_btns.first.click()
            await asyncio.sleep(1)
            await page.screenshot(path="C:/tmp/t2_04b_add_modal.png")
            log("Add transaction modal opened", "ok")
            results["add_transaction_btn"] = True

            # Fill form
            ticker_in = page.locator("input#ticker, input[name='ticker'], input[placeholder*='VALE' i], input[placeholder*='ticker' i]")
            if await ticker_in.count() > 0:
                await ticker_in.first.fill("VALE3")
                log("Filled ticker: VALE3", "ok")

                qty_in = page.locator("input[name='quantity'], input[placeholder*='quantidade' i], input[placeholder*='qty' i]")
                if await qty_in.count() > 0:
                    await qty_in.first.fill("10")

                price_in = page.locator("input[name='price'], input[placeholder*='preço' i], input[placeholder*='price' i]")
                if await price_in.count() > 0:
                    await price_in.first.fill("50.00")

                await page.screenshot(path="C:/tmp/t2_04c_form_filled.png")

                # Submit
                submit_btn = page.locator("button[type='submit']:has-text('Adicionar'), button[type='submit']:has-text('Salvar'), button[type='submit']:has-text('Confirmar')")
                if await submit_btn.count() > 0:
                    await submit_btn.first.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path="C:/tmp/t2_04d_after_submit.png")
                    text_after = await page.evaluate("() => document.body.innerText")
                    results["transaction_added"] = "VALE3" in text_after or "sucesso" in text_after.lower()
                    log(f"Transaction added: {results['transaction_added']}", "ok" if results.get('transaction_added') else "fail")
                else:
                    await page.keyboard.press("Escape")
            else:
                log("No ticker input found in modal", "warn")
                await page.keyboard.press("Escape")
        else:
            results["add_transaction_btn"] = False
            log("No add transaction button found", "fail")

        # =================== TEST 5: WATCHLIST ===================
        log("\\n=== 5. WATCHLIST ===")
        await page.goto(f"{BASE_URL}/watchlist", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_05_watchlist.png", wait=3)
        log(f"Watchlist URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        results["watchlist_page"] = "Watchlist" in text_content or "watchlist" in text_content.lower()
        log(f"Watchlist page: {results['watchlist_page']}", "ok" if results["watchlist_page"] else "fail")

        # Check if prices are loading (or showing N/D)
        if "N/D" in text_content or "N/A" in text_content:
            log("WARNING: Watchlist prices showing N/D - market data may not be loading", "warn")
            results["watchlist_prices"] = False
        elif "R$" in text_content:
            log("Watchlist prices showing R$ values", "ok")
            results["watchlist_prices"] = True
        else:
            log("Watchlist has no tickers or prices unclear", "warn")
            results["watchlist_prices"] = None

        # Try adding PETR4
        ticker_input = page.locator("input[placeholder*='VALE' i], input[placeholder*='TICKER' i], input[placeholder*='ticker' i]")
        if await ticker_input.count() > 0:
            await ticker_input.first.fill("PETR4")
            add_btn = page.locator("button:has-text('Adicionar'), button:has-text('+')")
            if await add_btn.count() > 0:
                await add_btn.first.click()
                await asyncio.sleep(2)
                await page.screenshot(path="C:/tmp/t2_05b_watchlist_added.png")
                text_after = await page.evaluate("() => document.body.innerText")
                results["watchlist_add_ticker"] = "PETR4" in text_after
                log(f"PETR4 added: {results['watchlist_add_ticker']}", "ok" if results.get('watchlist_add_ticker') else "fail")

        # =================== TEST 6: SCREENER ===================
        log("\\n=== 6. SCREENER ===")
        await page.goto(f"{BASE_URL}/screener", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_06_screener.png", wait=3)
        log(f"Screener URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        log(f"Screener text (first 300): {text_content[:300]}")

        # Check if premium gate or actual screener
        if "Premium" in text_content and "upgrade" in text_content.lower():
            log("Screener still behind premium gate (user may need re-login)", "warn")
            results["screener_page"] = False
            results["screener_premium_gate"] = True
        else:
            sc_kw = ["Screener", "ações", "filtro", "P/L", "Goldman"]
            found_sc = [k for k in sc_kw if k in text_content]
            results["screener_page"] = len(found_sc) >= 1
            log(f"Screener keywords: {found_sc}", "ok" if results["screener_page"] else "fail")

            # Try to run screener
            run_btn = page.locator("button:has-text('Filtrar'), button:has-text('Buscar'), button:has-text('Executar'), button:has-text('Run')")
            if await run_btn.count() > 0:
                await run_btn.first.click()
                await asyncio.sleep(4)
                await page.screenshot(path="C:/tmp/t2_06b_screener_results.png")
                text_after = await page.evaluate("() => document.body.innerText")
                results["screener_results"] = len(text_after) > len(text_content) or any(k in text_after for k in ["VALE", "PETR", "ITUB"])
                log(f"Screener results: {results.get('screener_results')}", "ok" if results.get("screener_results") else "fail")

        # =================== TEST 7: INSIGHTS ===================
        log("\\n=== 7. INSIGHTS ===")
        await page.goto(f"{BASE_URL}/insights", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_07_insights.png", wait=3)
        log(f"Insights URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        ins_kw = ["Insight", "insight", "Copiloto", "alerta", "oportunidade", "concentração"]
        found_ins = [k for k in ins_kw if k in text_content]
        results["insights_page"] = len(found_ins) >= 1
        log(f"Insights keywords: {found_ins}", "ok" if results["insights_page"] else "fail")

        if results["insights_page"]:
            card_count = await page.locator("[class*='insight'], [class*='card']").count()
            log(f"Insight cards found: {card_count}")
            results["insights_cards"] = card_count > 0

        # =================== TEST 8: AI ANALYSIS ===================
        log("\\n=== 8. AI ANALYSIS (CRITICAL) ===")
        await page.goto(f"{BASE_URL}/ai", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_08_ai.png", wait=3)
        log(f"AI page URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        log(f"AI page text (first 500): {text_content[:500]}")

        if "Premium" in text_content and "upgrade" in text_content.lower():
            log("AI still showing premium gate - need session refresh", "warn")
            results["ai_page"] = False
            results["ai_premium_gate"] = True
        else:
            ai_kw = ["Análise de IA", "Análise de Ativo", "Histórico", "Analisar", "Impacto Macro"]
            found_ai = [k for k in ai_kw if k in text_content]
            results["ai_page"] = len(found_ai) >= 1
            log(f"AI keywords: {found_ai}", "ok" if results["ai_page"] else "fail")

            if results["ai_page"]:
                # Fill ticker
                ticker_in = page.locator("input#ticker-input, input[placeholder='VALE3'], input[placeholder*='VALE' i]")
                t_count = await ticker_in.count()
                log(f"Ticker inputs: {t_count}")

                if t_count > 0:
                    await ticker_in.first.fill("VALE3")
                    analyze_btn = page.locator("button:has-text('Analisar')")
                    if await analyze_btn.count() > 0:
                        await analyze_btn.first.click()
                        log("Submitted VALE3 for analysis", "ok")
                        results["ai_analysis_submitted"] = True

                        # Poll for up to 120s
                        log("Polling for AI job completion...")
                        completed = False
                        for i in range(24):
                            await asyncio.sleep(5)
                            t = await page.evaluate("() => document.body.innerText")
                            is_running = "Analisando..." in t
                            is_pending = any(s in t.lower() for s in ["pendente", "pending", "processando"])
                            is_failed = any(s in t for s in ["falhou", "falha", "failed", "Tente novamente"])
                            is_done = any(s in t for s in ["DCF", "Fluxo de Caixa", "Valuation", "Lucros"]) and not is_running
                            elapsed = (i+1)*5

                            if is_failed:
                                log(f"AI job FAILED at {elapsed}s", "fail")
                                results["ai_job_completed"] = False
                                await page.screenshot(path="C:/tmp/t2_08b_ai_failed.png")
                                completed = True
                                break
                            elif is_done:
                                log(f"AI job COMPLETED at {elapsed}s!", "ok")
                                results["ai_job_completed"] = True
                                await page.screenshot(path="C:/tmp/t2_08c_ai_done.png")
                                completed = True
                                break
                            else:
                                log(f"  {elapsed}s - running={is_running}, pending={is_pending}")

                        if not completed:
                            log("AI job TIMED OUT (120s)", "fail")
                            results["ai_job_completed"] = False
                            await page.screenshot(path="C:/tmp/t2_08d_ai_timeout.png")
                    else:
                        log("No 'Analisar' button found on AI page", "fail")
                        results["ai_analysis_submitted"] = False
                else:
                    log("No ticker input found on AI page", "fail")

        # =================== TEST 9: AI ADVISOR ===================
        log("\\n=== 9. AI ADVISOR ===")
        await page.goto(f"{BASE_URL}/ai/advisor", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_09_advisor.png", wait=3)
        log(f"Advisor URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        log(f"Advisor text (first 400): {text_content[:400]}")
        advisor_kw = ["Advisor", "advisor", "Carteira", "análise", "portfólio"]
        found_adv = [k for k in advisor_kw if k in text_content]
        results["advisor_page"] = len(found_adv) >= 1
        log(f"Advisor keywords: {found_adv}", "ok" if results["advisor_page"] else "fail")

        # Try macro analysis button
        macro_btn = page.locator("button:has-text('Analisar Impacto Macro'), button:has-text('Analisar')")
        if await macro_btn.count() > 0:
            log("Found macro analysis button", "ok")
            # Don't submit unless AI is working to avoid queue spam

        # =================== TEST 10: PROFILE ===================
        log("\\n=== 10. PROFILE ===")
        await page.goto(f"{BASE_URL}/profile", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_10_profile.png", wait=3)
        log(f"Profile URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        prof_kw = ["Perfil", "perfil", "objetivo", "horizonte", "risco", "Investidor"]
        found_prof = [k for k in prof_kw if k in text_content]
        results["profile_page"] = len(found_prof) >= 1
        log(f"Profile keywords: {found_prof}", "ok" if results["profile_page"] else "fail")

        # Try saving profile
        if results["profile_page"]:
            # Look for select or radio inputs
            selects = page.locator("select")
            sel_count = await selects.count()
            log(f"Profile form selects: {sel_count}")
            if sel_count > 0:
                # Try to select first option for each
                for idx in range(min(sel_count, 3)):
                    try:
                        options = await selects.nth(idx).evaluate("el => Array.from(el.options).map(o => o.value)")
                        if options and len(options) > 1:
                            await selects.nth(idx).select_option(options[1])
                    except:
                        pass

                save_btn = page.locator("button[type='submit']:has-text('Salvar'), button:has-text('Salvar perfil')")
                if await save_btn.count() > 0:
                    await save_btn.first.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path="C:/tmp/t2_10b_profile_saved.png")
                    text_after = await page.evaluate("() => document.body.innerText")
                    results["profile_saved"] = "salvo" in text_after.lower() or "sucesso" in text_after.lower()
                    log(f"Profile saved: {results['profile_saved']}", "ok" if results.get('profile_saved') else "warn")

        # =================== TEST 11: PLANS ===================
        log("\\n=== 11. PLANS ===")
        await page.goto(f"{BASE_URL}/planos", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(page, "C:/tmp/t2_11_plans.png", wait=3)
        log(f"Plans URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        plan_kw = ["Plano", "plano", "Premium", "preço", "mensal", "anual", "R$"]
        found_plan = [k for k in plan_kw if k in text_content]
        results["plans_page"] = len(found_plan) >= 3
        log(f"Plans keywords: {found_plan}", "ok" if results["plans_page"] else "fail")

        # =================== TEST 12: IMPORTS ===================
        log("\\n=== 12. IMPORTS ===")
        await page.goto(f"{BASE_URL}/imports", wait_until="networkidle", timeout=30000)
        await wait_and_screenshot(path="C:/tmp/t2_12_imports.png", wait=3)
        log(f"Imports URL: {page.url}")

        text_content = await page.evaluate("() => document.body.innerText")
        imp_kw = ["Import", "import", "CSV", "arquivo", "planilha", "Importar"]
        found_imp = [k for k in imp_kw if k in text_content]
        results["imports_page"] = len(found_imp) >= 1
        log(f"Imports keywords: {found_imp}", "ok" if results["imports_page"] else "fail")

        # Console errors summary
        log(f"\\n=== CONSOLE ERRORS ({len(cons_errors)} total) ===")
        for e in cons_errors[:20]:
            print(f"  ERROR: {e}")

        if failed_requests:
            log(f"\\n=== FAILED REQUESTS ({len(failed_requests)} total) ===")
            for r in failed_requests[:10]:
                print(f"  {r}")

        await browser.close()

    # Final summary
    print("\\n" + "="*60)
    print("FINAL TEST RESULTS:")
    print("="*60)
    passed = 0
    failed = 0
    warned = 0
    for k, v in results.items():
        if v is True:
            status = "PASS"
            passed += 1
        elif v is False:
            status = "FAIL"
            failed += 1
        else:
            status = "N/A"
            warned += 1
        print(f"  [{status}] {k}")
    print(f"\\nPASS: {passed} | FAIL: {failed} | N/A: {warned}")
    print(f"Total: {passed}/{passed+failed} testable passed")

    with open("C:/tmp/test_results_v2.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results: C:/tmp/test_results_v2.json")


asyncio.run(main())
"""

# Fix the imports call - missing page arg
script_content = script_content.replace(
    '        await wait_and_screenshot(path="C:/tmp/t2_12_imports.png", wait=3)',
    '        await wait_and_screenshot(page, "C:/tmp/t2_12_imports.png", wait=3)'
)

with open("C:/tmp/test_investiq_v2.py", "w", encoding="utf-8") as f:
    f.write(script_content)

print("v2 test script written to C:/tmp/test_investiq_v2.py")
