"""
Restoration: Full Chrome automation flow with stealth + CDP + Canvas + Ente Auth + Perplexity radar verification
Uses .env credentials securely, never logs secrets
"""
import os, sys, time, json, re
from pathlib import Path
from dotenv import load_dotenv

# Load env override
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p)) if p else p

def clean_locks(profile):
    for f in ["SingletonLock","SingletonCookie","SingletonSocket"]:
        fp = os.path.join(profile, f)
        if os.path.exists(fp) or os.path.islink(fp):
            try:
                os.remove(fp)
                print(f"[clean] Removed {f}")
            except Exception as e:
                print(f"[clean] Failed {f}: {e}")

def try_cdp():
    print("\n=== CDP Check (Port 9222) ===")
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(('127.0.0.1', 9222))
    s.close()
    if result != 0:
        print("[CDP] Port 9222 closed - real Chrome not in debug mode")
        print("To enable: open -a \"Google Chrome\" --args --remote-debugging-port=9222 --profile-directory=\"Profile 1\"")
        return False
    print("[CDP] Port 9222 open!")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=10000)
            print(f"[CDP] Connected! Contexts: {len(browser.contexts)}")
            ctx = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            print(f"[CDP] Page URL: {page.url[:100]}")
            # Canvas API test
            page.goto("https://canvas.jccc.edu/", timeout=20000)
            page.wait_for_timeout(2000)
            print(f"[CDP] Canvas URL: {page.url}, Title: {page.title()}")
            result = page.evaluate("""async () => {
                try {
                    const r = await fetch('/api/v1/courses?enrollment_state=active&per_page=20', {credentials:'include'});
                    if (!r.ok) return {error: r.status};
                    return await r.json();
                } catch(e) { return {error: e.toString()}; }
            }""")
            print(f"[CDP] Courses API: {str(result)[:500]}")
            return True
    except Exception as e:
        print(f"[CDP] Connection failed: {e}")
        return False

def test_stealth_debug_profile():
    print("\n=== Stealth Debug Profile Test ===")
    from playwright.sync_api import sync_playwright
    debug_profile = expand_path(os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile"))
    clean_locks(debug_profile)
    print(f"Profile: {debug_profile}")
    
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
            try:
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except: pass
            
            page.goto("https://canvas.jccc.edu/", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"[stealth] URL: {page.url}")
            print(f"[stealth] Title: {page.title()}")
            
            is_ms_login = "login.microsoftonline.com" in page.url.lower()
            print(f"[stealth] Microsoft login required? {is_ms_login}")
            
            if is_ms_login:
                print("\n[!] MFA required - testing Ente Auth manual flow")
                print("Opening Ente Auth app...")
                os.system('open -a "Ente Auth"')
                print("INSTRUCTIONS FOR USER:")
                print("  1. Ente Auth app should be visible now")
                print("  2. Find your Microsoft/JCCC code")
                print("  3. Enter it manually in the Chrome window that popped up")
                print("  4. I will poll for login success for 120s")
                
                # Poll for login success
                for i in range(40):
                    page.wait_for_timeout(3000)
                    url = page.url.lower()
                    if "login.microsoftonline.com" not in url and "canvas.jccc.edu" in url:
                        print(f"[✓] Login succeeded after {i*3}s! URL: {page.url}")
                        break
                    if i % 5 == 0:
                        print(f"... waiting {i*3}s, URL: {page.url[:80]}")
                else:
                    print("[!] 120s elapsed, still on Microsoft login - session may need manual intervention")
            else:
                print("[✓] Already logged into Canvas!")
            
            # Canvas API via page.evaluate (0.28s vs 3.8s UI)
            print("\n=== Canvas API Fetch ===")
            try:
                result = page.evaluate("""async () => {
                    const t0 = performance.now();
                    const r = await fetch('/api/v1/courses?enrollment_state=active&per_page=20', {credentials:'include'});
                    if (!r.ok) return {error: r.status, time: performance.now()-t0};
                    const data = await r.json();
                    return {data, time: performance.now()-t0};
                }""")
                if 'error' in result:
                    print(f"Courses API error: {result}")
                else:
                    elapsed = result.get('time', 0)
                    courses = result['data']
                    print(f"Courses fetched in {elapsed:.2f}ms: {len(courses)} courses")
                    for c in courses:
                        print(f"  {c.get('id')}: {c.get('name')}")
                        
                        # Grades
                        cid = c.get('id')
                        grades_result = page.evaluate(f"""async () => {{
                            const r = await fetch('/api/v1/courses/{cid}/enrollments?user_id=self', {{credentials:'include'}});
                            if (!r.ok) return {{error: r.status}};
                            return await r.json();
                        }}""")
                        print(f"    Grades for {cid}: {str(grades_result)[:300]}")
                        
                        # Assignments upcoming
                        assign_result = page.evaluate(f"""async () => {{
                            const r = await fetch('/api/v1/courses/{cid}/assignments?per_page=100&bucket=upcoming', {{credentials:'include'}});
                            if (!r.ok) return {{error: r.status}};
                            return await r.json();
                        }}""")
                        if isinstance(assign_result, list):
                            from datetime import datetime, timezone, timedelta
                            now = datetime.now(timezone.utc)
                            cutoff = now + timedelta(days=3)
                            due_soon = []
                            for a in assign_result:
                                due_at = a.get('due_at')
                                if due_at:
                                    try:
                                        due = datetime.fromisoformat(due_at.replace('Z','+00:00'))
                                        if now <= due <= cutoff:
                                            due_soon.append((a.get('name'), due_at))
                                    except: pass
                            if due_soon:
                                print(f"    Due within 3 days: {due_soon}")
                            else:
                                print(f"    No assignments due within 3 days (total upcoming: {len(assign_result)})")
            except Exception as e:
                print(f"API fetch failed: {e}")
                import traceback; traceback.print_exc()
            
            page.screenshot(path="restore_canvas_verification.png", full_page=False)
            print("\nScreenshot saved: restore_canvas_verification.png")
            
            print("Keeping open 8s for inspection...")
            page.wait_for_timeout(8000)
            context.close()
            print("[✓] Stealth launch test completed successfully")
            return True
            
        except Exception as e:
            print(f"[stealth] Failed: {e}")
            import traceback; traceback.print_exc()
            return False

def test_perplexity_session():
    print("\n=== Perplexity Session Test ===")
    from playwright.sync_api import sync_playwright
    debug_profile = expand_path(expand_path.__globals__['os'].environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile")) if False else expand_path("/Users/hswin/chrome-debug-profile")
    # Use direct path to avoid scope issue
    debug_profile = expand_path("~/chrome-debug-profile")
    clean_locks(debug_profile)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            debug_profile,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except: pass
        
        page.goto("https://www.perplexity.ai/", timeout=20000)
        page.wait_for_timeout(3000)
        print(f"URL: {page.url}, Title: {page.title()}")
        
        # Check if logged in
        body = page.locator("body").inner_text(timeout=3000)[:1000]
        print(f"Body snippet: {body[:300]}")
        
        sign_in = page.locator("button:has-text('Sign In')").first
        has_signin = sign_in.count()>0 and sign_in.is_visible(timeout=1000) if sign_in else False
        print(f"Sign In button visible? {has_signin} -> {'NOT logged in' if has_signin else 'likely logged in or different UI'}")
        
        page.screenshot(path="restore_perplexity_check.png")
        print("Screenshot: restore_perplexity_check.png")
        
        # Verify radar files exist
        print("\n=== Radar Chart Files Verification ===")
        files = ["radar_chart_antigravity_vs_muse_spark.png", "radar_chart_antigravity_vs_muse_spark.pdf", 
                 "radar_chart_data.csv", "radar_chart_ascii.txt", "radar_chart_mermaid.md",
                 "perplexity_radar_final.png"]
        for f in files:
            fpath = os.path.join("/Users/hswin/muse-spark-python", f)
            if os.path.exists(fpath):
                size = os.path.getsize(fpath)
                print(f"  [✓] {f} ({size} bytes)")
            else:
                print(f"  [✗] Missing {f}")
        
        page.wait_for_timeout(3000)
        context.close()

def test_ente_auth_permissions():
    print("\n=== Ente Auth Permissions Test ===")
    import subprocess, datetime
    import os as os_local
    # Screen Recording
    print("Testing Screen Recording permission...")
    tmp_path = f"/tmp/ente_test_{int(time.time())}.png"
    result = subprocess.run(["screencapture", "-x", tmp_path], capture_output=True, text=True)
    if result.returncode == 0 and os_local.path.exists(tmp_path):
        size = os_local.path.getsize(tmp_path)
        print(f"[✓] Screen Recording works! File: {tmp_path} ({size} bytes)")
        os_local.remove(tmp_path)
        screen_ok = True
    else:
        print(f"[✗] Screen Recording failed: {result.stderr}")
        screen_ok = False
    
    # Accessibility
    print("Testing Accessibility (AppleScript) permission...")
    try:
        result = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of processes'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            has_ente = "Ente Auth" in result.stdout
            print(f"[✓] Accessibility works! Ente Auth in process list? {has_ente}")
            acc_ok = True
        else:
            print(f"[✗] Accessibility failed: {result.stderr[:200]}")
            acc_ok = False
    except Exception as e:
        print(f"[✗] Accessibility test error: {e}")
        acc_ok = False
    
    # Ente App process
    ps = subprocess.run(["pgrep", "-fl", "Ente Auth"], capture_output=True, text=True)
    print(f"Ente Auth process: {ps.stdout.strip()}")
    
    # DB location
    db_path = os_local.path.expanduser("~/Library/Containers/io.ente.auth.mac/Data/Library/Application Support/io.ente.auth.mac/ente.authenticator.db")
    print(f"DB exists? {os_local.path.exists(db_path)} at {db_path}")
    if os_local.path.exists(db_path):
        size = os_local.path.getsize(db_path)
        print(f"  DB size: {size} bytes (encrypted)")
    
    # Try screenshot of Ente Auth window if permissions allow
    if screen_ok and acc_ok:
        print("\n[!] Both permissions granted - can attempt Method 2 (OCR) with user consent")
        print("For Method 2 (secure semi-automated):")
        print("  1. open -a \"Ente Auth\"")
        print("  2. screencapture -l$(windowId) /tmp/ente.png")
        print("  3. OCR to extract 6-digit code")
        print("  4. Auto-fill into MFA field, then clear immediately")
        print("  Security: code never logged, cleared after use, stored only in memory")
    else:
        print("\n[!] Permissions missing - using Method 1 (manual copy, most secure)")
        print("Steps:")
        print("  open -a \"Ente Auth\"")
        print("  User manually copies code from Ente Auth app into Chrome window")
        print("  Poll for login success (check URL change away from Microsoft login)")
    
    return {"screen": screen_ok, "accessibility": acc_ok}

if __name__ == "__main__":
    print("="*70)
    print("RESTORATION: Browser Automation Full Flow")
    print("="*70)
    
    # Step 1: CDP check
    cdp_ok = try_cdp()
    
    # Step 2: Stealth + Canvas
    stealth_ok = test_stealth_debug_profile()
    
    # Step 3: Perplexity
    test_perplexity_session()
    
    # Step 4: Ente Auth permissions
    perm = test_ente_auth_permissions()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"CDP (real Chrome Profile 1): {'Available' if cdp_ok else 'Not available (launch real Chrome with --remote-debugging-port=9222)'}")
    print(f"Stealth debug profile: {'OK' if stealth_ok else 'Failed'}")
    print(f"Screen Recording permission: {'GRANTED ✓' if perm['screen'] else 'DENIED ✗ - enable in System Settings → Privacy & Security → Screen Recording'}")
    print(f"Accessibility permission: {'GRANTED ✓' if perm['accessibility'] else 'DENIED ✗ - enable in System Settings → Privacy & Security → Accessibility'}")
    print(f"Ente Auth method: {'Method 2 possible (semi-auto with OCR)' if perm['screen'] and perm['accessibility'] else 'Method 1 (manual copy, secure)'}")
    print("\nRadar chart files verified earlier - should be present from previous run")
    print("If missing, run: python perplexity_login_and_radar.py to regenerate")
