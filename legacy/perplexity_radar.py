import os, sys, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def clean_locks(profile):
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = os.path.join(profile, f)
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"[clean] Removed {f}")
            except: pass

forced_profile = os.path.expanduser("~/chrome-debug-profile")
clean_locks(forced_profile)
print(f"Using profile: {forced_profile}")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        forced_profile,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        no_viewport=True,
    )
    page = context.pages[0] if context.pages else context.new_page()

    print("Navigating to https://www.perplexity.ai/")
    page.goto("https://www.perplexity.ai/", timeout=30000)
    page.wait_for_timeout(3000)
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    print(f"URL: {page.url}, Title: {page.title()}")
    page.screenshot(path="perplexity_home.png")
    
    # Check if we need to handle login or are already logged in
    body = page.locator("body").inner_text(timeout=3000)[:2000]
    print(f"Body snippet: {body[:500]}")

    # Perplexity input selectors - trial/error learned
    # Observed: bottom centered textarea, placeholder "Ask anything..." or contenteditable
    selectors_to_try = [
        "textarea[placeholder*='Ask' i]",
        "textarea[placeholder*='Search' i]",
        "div[contenteditable='true']",
        "textarea[name='q']",
        "textarea",
        "[data-testid='search-input']",
    ]

    input_locator = None
    for sel in selectors_to_try:
        try:
            loc = page.locator(sel).last
            count = loc.count()
            if count>0:
                # Check visibility
                try:
                    if loc.is_visible(timeout=1000):
                        print(f"Found visible input with selector: {sel}, count {count}")
                        input_locator = loc
                        break
                except:
                    continue
        except Exception as e:
            print(f"Selector {sel} failed: {e}")
            continue

    if not input_locator:
        # Try get_by_placeholder
        try:
            ph = page.get_by_placeholder("Ask anything")
            if ph.count()>0:
                input_locator = ph.first
                print("Found via get_by_placeholder Ask anything")
        except: pass

    if not input_locator:
        try:
            ph = page.get_by_role("textbox").last
            if ph.count()>0:
                input_locator = ph
                print("Found via get_by_role textbox")
        except: pass

    if not input_locator:
        print("[!] Could not find Perplexity input")
        page.screenshot(path="perplexity_no_input.png", full_page=True)
        context.close()
        sys.exit(1)

    prompt_text = """Create a radar chart comparing Antigravity Agentic Browser vs Muse Spark 1.1 across these 8 dimensions: speed, tool calling reliability, persistent Chrome handling, memory/context retention, ease of setup, cost efficiency, browser fidelity (how real the browser feels), task completion accuracy.

Provide:
1. A data table with scores 0-10 for each tool per dimension and rationale
2. Mermaid or ASCII radar chart code if possible
3. Brief recommendation for when to use each
4. Include analysis of Playwright persistent context vs ephemeral

Make it detailed and technical."""

    print(f"\nFilling Perplexity input with prompt...")
    try:
        input_locator.click(timeout=5000)
        page.wait_for_timeout(500)
        input_locator.fill(prompt_text, timeout=10000)
        print("Filled successfully")
        page.wait_for_timeout(1000)
        # Press Enter or click send
        # Perplexity send button is often button with arrow icon
        try:
            page.keyboard.press("Enter")
            print("Pressed Enter")
        except Exception as e:
            print(f"Enter press failed: {e}")
        
        # Also try clicking send button
        send_selectors = [
            "button[aria-label*='Send' i]",
            "button:has-text('Send')",
            "button[type='submit']",
            "[data-testid='submit-button']",
        ]
        for sel in send_selectors:
            try:
                btn = page.locator(sel).last
                if btn.count()>0 and btn.is_visible(timeout=1000):
                    btn.click(timeout=3000)
                    print(f"Clicked send button via {sel}")
                    break
            except:
                continue

    except Exception as e:
        print(f"Fill failed: {e}")
        # Try evaluate fill
        try:
            page.evaluate(f"""(text) => {{
                const ta = document.querySelector('textarea');
                if (ta) {{ ta.value = text; ta.dispatchEvent(new Event('input', {{bubbles:true}})); }}
                const ce = document.querySelector('[contenteditable=\"true\"]');
                if (ce) {{ ce.textContent = text; ce.dispatchEvent(new InputEvent('input', {{bubbles:true}})); }}
            }}""", prompt_text)
            page.keyboard.press("Enter")
        except Exception as e2:
            print(f"Evaluate fill also failed: {e2}")

    print("\nWaiting for Perplexity response (streaming)...")
    # Wait up to 40s for response
    for i in range(20):
        page.wait_for_timeout(2000)
        try:
            # Check if response area has content
            # Perplexity responses are in article or div with many paragraphs
            body_text = page.locator("body").inner_text(timeout=2000)
            if "radar" in body_text.lower() and ("antigravity" in body_text.lower() or "muse" in body_text.lower()):
                print(f"Detected relevant content at {i*2}s, length {len(body_text)}")
                # Continue waiting a bit more for full generation
                if len(body_text) > 3000:
                    break
        except:
            pass
        if i % 5 == 0:
            print(f"... waiting {i*2}s")

    page.wait_for_timeout(3000)
    page.screenshot(path="perplexity_radar_result.png", full_page=True)
    print("Screenshot saved: perplexity_radar_result.png")

    # Try to extract response text
    try:
        full_body = page.locator("body").inner_text(timeout=5000)
        # Save
        with open("perplexity_radar_response.txt", "w") as f:
            f.write(full_body)
        print(f"Saved full body length {len(full_body)} to txt")

        # Try more specific selectors for answer
        selectors_for_answer = [
            "article",
            "[data-testid='answer']",
            "div.prose",
            "main div:has-text('Antigravity')",
        ]
        for sel in selectors_for_answer:
            try:
                loc = page.locator(sel).first
                if loc.count()>0:
                    txt = loc.inner_text(timeout=2000)
                    if len(txt) > 500:
                        print(f"\n=== Extracted via {sel} ===\n{txt[:4000]}")
                        with open(f"perplexity_extract_{sel.replace(' ', '_')}.txt", "w") as f:
                            f.write(txt)
                        break
            except:
                continue

    except Exception as e:
        print(f"Extract failed: {e}")

    print("\nDone. Keeping browser open 15s...")
    page.wait_for_timeout(15000)
    context.close()
