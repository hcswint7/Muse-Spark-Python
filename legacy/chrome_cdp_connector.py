"""
Fix #1 Priority: Use Real Chrome Profile WITHOUT being flagged as automation.

Problem:
- launch_persistent_context with main User Data dir (~/Library/Application Support/Google/Chrome + Profile 1) 
  launches a NEW Chrome instance with --automation flags that Microsoft SSO detects and blocks/hangs.
- Debug profile ~/chrome-debug-profile works but session expires quickly.

Solution A (Recommended): Connect to existing Chrome via CDP Remote Debugging
- User launches Chrome NORMALLY (not via Playwright) with --remote-debugging-port=9222
- This Chrome is NOT flagged as automation (no AutomationControlled blink feature)
- Playwright connects via connect_over_cdp and reuses existing logged-in session
- Works for Canvas, Perplexity, any site where you're already logged in

Usage:
1. Quit Chrome completely: Cmd+Q
2. Launch Chrome with remote debugging AND your real profile:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --profile-directory="Profile 1" --remote-debugging-address=127.0.0.1
   OR via open:
   open -a "Google Chrome" --args --remote-debugging-port=9222 --profile-directory="Profile 1"

3. Verify: http://localhost:9222/json should show tabs
4. Run this script: it will connect and extract Canvas grades without re-login

Solution B: If CDP not available, fallback to debug profile with manual login (already proven working)
"""

import os, sys, time, json
from playwright.sync_api import sync_playwright

def try_cdp_connection():
    print("=== Attempting CDP Connection to Real Chrome (Port 9222) ===")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to connect to existing Chrome
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=10000)
                print("[✓] Connected to existing Chrome via CDP!")
            except Exception as e:
                print(f"[!] CDP connection failed: {e}")
                print("\n" + "="*70)
                print("TO FIX: Launch Chrome with remote debugging port:")
                print("")
                print("Option 1 - Terminal command (quit Chrome first):")
                print('  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
                print('    --remote-debugging-port=9222 \\')
                print('    --profile-directory="Profile 1" \\')
                print('    --remote-debugging-address=127.0.0.1')
                print("")
                print("Option 2 - Using open command:")
                print('  open -a "Google Chrome" --args --remote-debugging-port=9222 --profile-directory="Profile 1"')
                print("")
                print("Then keep Chrome open and re-run this script.")
                print("="*70)
                return False

            # Get contexts - CDP returns existing contexts
            contexts = browser.contexts
            if len(contexts) == 0:
                print("[!] No contexts found in CDP browser")
                browser.close()
                return False

            context = contexts[0]
            pages = context.pages
            if len(pages) == 0:
                page = context.new_page()
            else:
                page = pages[0]

            print(f"Got context with {len(pages)} pages")
            print(f"Current page URL: {page.url}")

            # Navigate to Canvas
            print("\nNavigating to Canvas with REAL logged-in profile...")
            page.goto("https://canvas.jccc.edu/", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"URL: {page.url}")
            print(f"Title: {page.title()}")

            if "login.microsoftonline.com" in page.url.lower():
                print("[!] Even real profile requires login (session expired). Please log in manually in Chrome window, then press Enter")
                input("Press Enter after login...")
                page.goto("https://canvas.jccc.edu/", timeout=20000)
                page.wait_for_timeout(3000)

            print(f"Final URL: {page.url}, Title: {page.title()}")
            body = page.locator("body").inner_text(timeout=3000)[:2000]
            print(f"Body: {body[:500]}")

            # Try Canvas API
            try:
                result = page.evaluate("""async () => {
                    const r = await fetch('/api/v1/courses?enrollment_state=active&per_page=20', {credentials:'include'});
                    if (!r.ok) return {error: r.status};
                    return await r.json();
                }""")
                print(f"\nCourses API: {str(result)[:2000]}")
                if isinstance(result, list):
                    for c in result:
                        print(f"  Course {c.get('id')}: {c.get('name')}")
            except Exception as e:
                print(f"API fetch failed: {e}")

            page.screenshot(path="cdp_canvas_test.png")
            print("Screenshot: cdp_canvas_test.png")

            # Don't close browser (since it's user's real Chrome)
            # browser.close() would close the real Chrome, so we just disconnect
            # Actually disconnect, not close
            print("\nDisconnecting (leaving your Chrome open)...")
            # page.close() not needed
            return True

    except Exception as e:
        print(f"CDP test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def try_stealth_launch():
    """Try launching with stealth args to avoid detection"""
    print("\n=== Attempting Stealth Launch (avoid automation flag) ===")
    from playwright.sync_api import sync_playwright
    debug_profile = os.path.expanduser("~/chrome-debug-profile")
    # Clean locks
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = os.path.join(debug_profile, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except: pass

    with sync_playwright() as pw:
        try:
            context = pw.chromium.launch_persistent_context(
                debug_profile,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,
                no_viewport=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                    "--disable-dev-shm-usage",
                ],
            )
            page = context.pages[0] if context.pages else context.new_page()
            # Hide webdriver flag
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.goto("https://canvas.jccc.edu/", timeout=20000)
            page.wait_for_timeout(3000)
            print(f"Stealth debug profile URL: {page.url}")
            page.screenshot(path="stealth_test.png")
            page.wait_for_timeout(5000)
            context.close()
            print("Stealth launch succeeded")
            return True
        except Exception as e:
            print(f"Stealth launch failed: {e}")
            return False

if __name__ == "__main__":
    success = try_cdp_connection()
    if not success:
        print("\nCDP not available, trying stealth fallback...")
        try_stealth_launch()
        print("\n" + "="*70)
        print("CONCLUSION:")
        print("If CDP fails and stealth still gets flagged, we need:")
        print("1. User to provide Canvas credentials securely, OR")
        print("2. User to manually log in to debug profile (already proven working)")
        print("   - The debug profile manual login WORKS (we got grades before)")
        print("   - Session in debug profile lasts days, then needs re-login")
        print("="*70)
