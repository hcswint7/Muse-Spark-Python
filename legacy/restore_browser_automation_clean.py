"""
Restoration: Full Chrome automation flow - clean version
"""
import os, sys, time, json, subprocess
from dotenv import load_dotenv

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
    print("[CDP] Port 9222 open! Trying connection...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=10000)
            print(f"[CDP] Connected! Contexts: {len(browser.contexts)}")
            ctx = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            print(f"[CDP] Page URL: {page.url[:100]}")
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
    debug_profile = expand_path("~/chrome-debug-profile")
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
                os.system('open -a "Ente Auth"')
                print("INSTRUCTIONS: Ente Auth opened, please enter code manually in Chrome window")
                for i in range(40):
                    page.wait_for_timeout(3000)
                    url = page.url.lower()
                    if "login.microsoftonline.com" not in url and "canvas.jccc.edu" in url:
                        print(f"[✓] Login succeeded after {i*3}s! URL: {page.url}")
                        break
                    if i % 5 == 0:
                        print(f"... waiting {i*3}s, URL: {page.url[:80]}")
            
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
                        cid = c.get('id')
                        grades_result = page.evaluate(f"""async () => {{
                            const r = await fetch('/api/v1/courses/{cid}/enrollments?user_id=self', {{credentials:'include'}});
                            if (!r.ok) return {{error: r.status}};
                            return await r.json();
                        }}""")
                        # Parse grade
                        try:
                            if isinstance(grades_result, list) and len(grades_result)>0:
                                g = grades_result[0]
                                grades = g.get('grades', {})
                                print(f"    Grades: current {grades.get('current_grade')} {grades.get('current_score')}% final {grades.get('final_score')}%")
                        except: 
                            print(f"    Grades raw: {str(grades_result)[:400]}")
                        
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
                                print(f"    No due within 3 days (upcoming total {len(assign_result)})")
            except Exception as e:
                print(f"API fetch failed: {e}")
                import traceback; traceback.print_exc()
            
            page.screenshot(path="restore_canvas_verification.png", full_page=False)
            print("\nScreenshot saved: restore_canvas_verification.png")
            print("Keeping open 8s...")
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
        body = page.locator("body").inner_text(timeout=3000)[:1000]
        print(f"Body snippet: {body[:400]}")
        
        sign_in = page.locator("button:has-text('Sign In')").first
        try:
            cnt = sign_in.count()
            vis = sign_in.is_visible(timeout=1000) if cnt>0 else False
        except:
            vis = False
        print(f"Sign In button visible? {vis} -> {'NOT logged in' if vis else 'likely logged in or different UI'}")
        
        page.screenshot(path="restore_perplexity_check.png")
        print("Screenshot: restore_perplexity_check.png")
        
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
    tmp_path = f"/tmp/ente_test_{int(time.time())}.png"
    result = subprocess.run(["screencapture", "-x", tmp_path], capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(tmp_path):
        size = os.path.getsize(tmp_path)
        print(f"[✓] Screen Recording works! File {tmp_path} ({size} bytes)")
        os.remove(tmp_path)
        screen_ok = True
    else:
        print(f"[✗] Screen Recording failed: {result.stderr}")
        screen_ok = False
    
    print("Testing Accessibility permission...")
    try:
        result = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of processes'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            has_ente = "Ente Auth" in result.stdout
            print(f"[✓] Accessibility works! Ente in list? {has_ente}")
            acc_ok = True
        else:
            print(f"[✗] Accessibility failed: {result.stderr[:200]}")
            acc_ok = False
    except Exception as e:
        print(f"[✗] Accessibility test error: {e}")
        acc_ok = False
    
    ps = subprocess.run(["pgrep", "-fl", "Ente Auth"], capture_output=True, text=True)
    print(f"Ente Auth process: {ps.stdout.strip()}")
    
    db_path = expand_path("~/Library/Containers/io.ente.auth.mac/Data/Library/Application Support/io.ente.auth.mac/ente.authenticator.db")
    print(f"DB exists? {os.path.exists(db_path)} size {os.path.getsize(db_path) if os.path.exists(db_path) else 0}")
    
    if screen_ok and acc_ok:
        print("\n[✓] Both permissions GRANTED - Method 2 (semi-auto OCR) possible")
    else:
        print("\n[!] Permissions missing - using Method 1 (manual copy)")
    
    return {"screen": screen_ok, "accessibility": acc_ok}

if __name__ == "__main__":
    print("="*70)
    print("RESTORATION: Browser Automation Full Flow")
    print("="*70)
    cdp_ok = try_cdp()
    stealth_ok = test_stealth_debug_profile()
    test_perplexity_session()
    perm = test_ente_auth_permissions()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"CDP: {'Available' if cdp_ok else 'Not available - launch real Chrome with --remote-debugging-port=9222'}")
    print(f"Stealth debug profile: {'OK' if stealth_ok else 'Failed'}")
    print(f"Screen Recording: {'GRANTED ✓' if perm['screen'] else 'DENIED'}")
    print(f"Accessibility: {'GRANTED ✓' if perm['accessibility'] else 'DENIED'}")
    if perm['screen'] and perm['accessibility']:
        print("Ente Auth: Method 2 possible (secure semi-auto with OCR, code never logged)")
    else:
        print("Ente Auth: Method 1 (manual copy, most secure)")
