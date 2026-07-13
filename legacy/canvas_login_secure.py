"""
Secure Canvas Login Handler - Supports 3 modes:
1. CDP connection to real Chrome (best, no password needed)
2. Debug profile with manual login polling (already proven working)
3. Automated login with CANVAS_USERNAME/CANVAS_PASSWORD env vars (if provided, secure)

This script will be used for Canvas grades and assignments tasks.
"""
import os, sys, time, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Override=True to ensure new .env values replace old shell env vars
load_dotenv(override=True)
# Also load from this directory explicitly
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def clean_locks(profile):
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        fp = os.path.join(profile, f)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                print(f"[clean] Removed {f}")
            except Exception as e:
                print(f"[clean] Failed {f}: {e}")

def is_microsoft_login(page):
    url = page.url.lower()
    title = page.title().lower()
    try:
        body = page.locator("body").inner_text(timeout=2000).lower()
    except:
        body = ""
    if "login.microsoftonline.com" in url:
        return True
    if "login." in url and "microsoft" in url:
        return True
    if "sign in to your account" in title:
        return True
    if "sign in" in body and "can't access your account" in body:
        return True
    return False

def is_canvas_logged_in(page):
    url = page.url.lower()
    if "canvas.jccc.edu" in url and "login" not in url and "microsoftonline" not in url:
        # Check for dashboard elements
        try:
            body = page.locator("body").inner_text(timeout=2000).lower()
            # Dashboard has "dashboard" or "courses" in text
            if "dashboard" in body or "my courses" in body or "to do" in body:
                return True
            # If URL is exactly canvas.jccc.edu/ and not login page, likely logged in
            if url == "https://canvas.jccc.edu/" or url.startswith("https://canvas.jccc.edu/?"):
                return True
        except:
            pass
        # Even if body check fails, if we're on canvas domain not login, consider logged in
        if "canvas.jccc.edu" in url:
            return True
    return False

def attempt_automated_login(page, username, password):
    """Attempt to fill Microsoft login form with provided credentials"""
    print(f"\n[auto-login] Attempting automated Microsoft SSO login for {username[:3]}***")
    try:
        # Wait for email field
        # Microsoft login has input type="email" or name="loginfmt"
        email_selectors = [
            "input[type='email']",
            "input[name='loginfmt']",
            "input[placeholder*='Email' i]",
            "#i0116",
        ]
        email_filled = False
        for sel in email_selectors:
            try:
                loc = page.locator(sel).first
                if loc.count()>0 and loc.is_visible(timeout=2000):
                    print(f"[auto-login] Found email field via {sel}, filling...")
                    loc.fill(username, timeout=5000)
                    email_filled = True
                    break
            except:
                continue
        
        if not email_filled:
            print("[auto-login] Could not find email field")
            return False

        # Click Next
        next_selectors = [
            "input[type='submit']",
            "button:has-text('Next')",
            "#idSIButton9",
        ]
        for sel in next_selectors:
            try:
                btn = page.locator(sel).first
                if btn.count()>0 and btn.is_visible(timeout=2000):
                    print(f"[auto-login] Clicking Next via {sel}")
                    btn.click(timeout=5000)
                    break
            except:
                continue
        
        page.wait_for_timeout(3000)
        print(f"[auto-login] After email Next, URL: {page.url}, Title: {page.title()}")
        page.screenshot(path="auto_login_after_email.png")

        # Wait for password field
        pw_selectors = [
            "input[type='password']",
            "input[name='passwd']",
            "#i0118",
        ]
        pw_filled = False
        for sel in pw_selectors:
            try:
                loc = page.locator(sel).first
                # Wait up to 5s for password field to appear
                loc.wait_for(state="visible", timeout=8000)
                print(f"[auto-login] Found password field via {sel}, filling...")
                loc.fill(password, timeout=5000)
                pw_filled = True
                break
            except Exception as e:
                print(f"[auto-login] {sel} not found yet: {e}")
                continue

        if not pw_filled:
            print("[auto-login] Could not find password field, maybe MFA or different flow")
            return False

        # Click Sign in
        for sel in next_selectors:
            try:
                btn = page.locator(sel).last
                if btn.count()>0 and btn.is_visible(timeout=2000):
                    print(f"[auto-login] Clicking Sign in via {sel}")
                    btn.click(timeout=5000)
                    break
            except:
                continue

        page.wait_for_timeout(5000)
        print(f"[auto-login] After password, URL: {page.url}, Title: {page.title()}")
        page.screenshot(path="auto_login_after_password.png")

        # Check for MFA - Microsoft often shows "Approve sign-in" or sends code
        # Wait up to 60s for user to approve MFA
        for i in range(20):
            page.wait_for_timeout(3000)
            url = page.url.lower()
            title = page.title().lower()
            try:
                body = page.locator("body").inner_text(timeout=1000).lower()
            except:
                body = ""
            
            if "canvas.jccc.edu" in url and "microsoft" not in url:
                print("[auto-login] SUCCESS - Redirected to Canvas!")
                return True
            
            if "approve" in body or "authenticator" in body or "verification" in body or "mfa" in body:
                print(f"[auto-login] MFA detected ({i*3}s elapsed) - Please approve via Authenticator app / phone")
                print(f"  Body snippet: {body[:300]}")
            
            if i % 3 == 0:
                print(f"[auto-login] Waiting for MFA / redirect... {i*3}s elapsed, current URL: {page.url[:100]}")

        # Final check
        if "canvas.jccc.edu" in page.url:
            return True
        else:
            print(f"[auto-login] Final URL still not Canvas: {page.url}")
            return False

    except Exception as e:
        print(f"[auto-login] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_canvas_context():
    """Main login orchestrator"""
    # Try CDP first
    print("=== Step 1: Try CDP Connection to Real Chrome (Port 9222) ===")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', 9222))
        s.close()
        if result == 0:
            print("[*] CDP port 9222 open, trying to connect...")
            from playwright.sync_api import sync_playwright
            # We need to handle this outside for actual use, return info
            print("[*] CDP available - real Chrome can be used")
            return "cdp_available"
        else:
            print("[*] CDP not available (port 9222 closed) - will use debug profile")
    except Exception as e:
        print(f"[*] CDP check failed: {e}")

    # Use debug profile
    debug_profile = expand_path(os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile"))
    clean_locks(debug_profile)
    print(f"\n=== Step 2: Using Debug Profile {debug_profile} with stealth ===")

    # Check for credentials
    username = os.environ.get("CANVAS_USERNAME") or os.environ.get("JCCC_EMAIL")
    password = os.environ.get("CANVAS_PASSWORD") or os.environ.get("JCCC_PASSWORD")
    
    if username and password:
        print(f"[*] Credentials found in env (username {username[:3]}***), will attempt auto-login if needed")
        print(f"    Password length: {len(password)} (not logged)")
    else:
        print("[*] No credentials in env, will use manual login polling (secure default)")
        print("    To enable auto-login, add to .env:")
        print("    CANVAS_USERNAME=your_email@jccc.edu")
        print("    CANVAS_PASSWORD=your_password")

    return "debug_profile", username, password

if __name__ == "__main__":
    mode = get_canvas_context()
    print(f"\nMode: {mode}")

    # Now actually launch and test
    if isinstance(mode, tuple):
        _, username, password = mode
        debug_profile = expand_path(os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile"))
        
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                debug_profile,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,
                no_viewport=True,
                args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page.goto("https://canvas.jccc.edu/", timeout=30000)
            page.wait_for_timeout(3000)
            
            if is_microsoft_login(page):
                print("[!] Microsoft login required")
                if username and password:
                    success = attempt_automated_login(page, username, password)
                    if success:
                        print("[✓] Auto-login succeeded!")
                    else:
                        print("[!] Auto-login failed, falling back to manual polling")
                        # Manual polling
                        for i in range(50):
                            page.wait_for_timeout(3000)
                            if not is_microsoft_login(page):
                                print(f"[✓] Manual login detected after {i*3}s")
                                break
                            if i%5==0:
                                print(f"... waiting {i*3}s for manual login, URL: {page.url[:80]}")
                else:
                    print("Waiting 150s for manual login in Chrome window...")
                    for i in range(50):
                        page.wait_for_timeout(3000)
                        if not is_microsoft_login(page):
                            print(f"[✓] Login detected!")
                            break
                        if i%5==0:
                            print(f"... {i*3}s elapsed, URL: {page.url[:80]}")
            else:
                print(f"[✓] Already logged in! URL: {page.url}")

            # Test API
            try:
                result = page.evaluate("""async () => {
                    const r = await fetch('/api/v1/courses?enrollment_state=active&per_page=20', {credentials:'include'});
                    if (!r.ok) return {error: r.status};
                    return await r.json();
                }""")
                print(f"\nCourses API result: {str(result)[:1000]}")
            except Exception as e:
                print(f"API failed: {e}")

            page.screenshot(path="final_canvas_test.png")
            print("Screenshot saved, keeping open 10s")
            page.wait_for_timeout(10000)
            context.close()

    elif mode == "cdp_available":
        print("\nCDP available - run with CDP connector script")
        print("Use: python chrome_cdp_connector.py")
