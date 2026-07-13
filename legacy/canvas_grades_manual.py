import os, sys, time, re
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
            except Exception as e:
                print(f"[clean] Failed {f}: {e}")

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

    print("Navigating to https://canvas.jccc.edu/")
    page.goto("https://canvas.jccc.edu/", timeout=30000)
    page.wait_for_timeout(3000)

    def is_login_page():
        url = page.url.lower()
        title = page.title().lower()
        try:
            body = page.locator("body").inner_text(timeout=2000).lower()
        except:
            body = ""
        # Microsoft SSO or Canvas login indicators
        if "login.microsoftonline.com" in url: return True
        if "login" in url and "canvas" in url and ("saml" in url or "jccc" in url): return True
        if "sign in to your account" in title: return True
        if "sign in" in body and "can't access your account" in body: return True
        return False

    # Auto-wait for manual login with polling (no terminal input required)
    wait_seconds = 150  # give user 2.5 minutes to log in manually
    if is_login_page():
        print(f"\n[!] Detected login page: {page.url}")
        print(f"Title: {page.title()}")
        page.screenshot(path="canvas_login_required.png")
        print("Screenshot saved: canvas_login_required.png")
        print("\n" + "="*60)
        print("ACTION REQUIRED (Manual Login):")
        print("Canvas session expired. A Chrome window opened.")
        print("Please manually log in to JCCC Canvas in that window:")
        print("  - JCCC email / password")
        print("  - Complete MFA if prompted")
        print("  - Wait for Dashboard")
        print(f"  - You have {wait_seconds}s to complete login")
        print("="*60)
        print("Polling for successful login... (no Enter needed)")
        start = time.time()
        while time.time() - start < wait_seconds:
            page.wait_for_timeout(3000)
            if not is_login_page():
                print(f"[✓] Login detected! Now at: {page.url}")
                break
            elapsed = int(time.time() - start)
            if elapsed % 15 == 0:
                print(f"... still waiting {elapsed}s elapsed, current URL: {page.url[:100]}")
        else:
            print(f"[!] Still on login page after {wait_seconds}s")
            page.screenshot(path="canvas_login_failed.png")

    if is_login_page():
        print("[!] Still on login page. Cannot proceed without login.")
        print("SECURITY NOTE: Do NOT put password in .env plaintext.")
        print("Secure method: Manual login once retains cookies in ~/chrome-debug-profile")
        print("for future automated runs (valid days/weeks).")
        # Save state for user to retry
        context.close()
        sys.exit(1)

    print("\n[✓] Successfully authenticated! On Canvas.")
    print(f"URL: {page.url}, Title: {page.title()}")
    page.screenshot(path="canvas_dashboard_authenticated.png")
    
    # Fetch courses via API
    def fetch_api(path):
        try:
            result = page.evaluate(f"""async () => {{
                try {{
                    const res = await fetch('{path}', {{ credentials: 'include' }});
                    if (!res.ok) return {{error: res.status + ' ' + res.statusText, url: '{path}'}};
                    const data = await res.json();
                    return data;
                }} catch (e) {{
                    return {{error: e.toString()}};
                }}
            }}""")
            return result
        except Exception as e:
            return {"error": str(e)}

    print("\n=== Fetching courses via Canvas API ===")
    courses = fetch_api("/api/v1/courses?enrollment_state=active&per_page=20")
    course_ids = []
    if isinstance(courses, list):
        for c in courses:
            cid = c.get('id')
            name = c.get('name')
            print(f"Found course: {cid} - {name}")
            course_ids.append(cid)
    else:
        print(f"API returned: {str(courses)[:1000]}")
        # fallback to known IDs from history
        course_ids = [86815, 87710]
        print(f"Using fallback IDs from history: {course_ids}")

    grades_summary = {}

    for cid in course_ids[:5]:  # first 5
        print(f"\n--- Processing course {cid} ---")
        # Try API for grades first (more reliable)
        enrollments = fetch_api(f"/api/v1/courses/{cid}/enrollments?user_id=self")
        print(f"Enrollments API: {str(enrollments)[:2000]}")
        if isinstance(enrollments, list) and len(enrollments)>0:
            e = enrollments[0]
            grades = e.get('grades', {})
            print(f"Grades from API: {grades}")
            grades_summary[cid] = {
                'current_score': grades.get('current_score'),
                'final_score': grades.get('final_score'),
                'current_grade': grades.get('current_grade'),
                'final_grade': grades.get('final_grade'),
            }
        # Also visit grades page for screenshot/text
        url = f"https://canvas.jccc.edu/courses/{cid}/grades"
        page.goto(url, timeout=20000)
        page.wait_for_timeout(3000)
        # Scroll
        for _ in range(4):
            page.mouse.wheel(0, 600)
            page.wait_for_timeout(400)
        page.screenshot(path=f"canvas_grades_{cid}.png", full_page=True)
        try:
            body = page.locator("body").inner_text(timeout=5000)
            with open(f"canvas_grades_{cid}_full.txt", "w") as f:
                f.write(body)
            print(f"Saved body text length {len(body)}")
        except Exception as e:
            print(f"Failed body extract: {e}")

    print("\n=== FINAL GRADES SUMMARY ===")
    for cid, g in grades_summary.items():
        print(f"Course {cid}: {g}")

    print("\nDone. Keeping browser open 20s for inspection...")
    page.wait_for_timeout(20000)
    context.close()
    print("Closed.")
