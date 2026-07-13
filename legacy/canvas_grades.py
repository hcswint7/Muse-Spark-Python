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
                print(f"Removed lock {f} in {profile}")
            except Exception as e:
                print(f"Failed removing {f}: {e}")

# Force debug profile to avoid conflict with main Chrome
forced_profile = os.path.expanduser("~/chrome-debug-profile")
clean_locks(forced_profile)
user_data_dir = forced_profile
print(f"Using profile: {user_data_dir} (forced to avoid main Chrome lock)")

with sync_playwright() as p:
    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            no_viewport=True,
        )
    except Exception as e:
        print(f"[!] Chrome launch failed: {e}")
        print("Please quit Chrome completely (Cmd+Q) and rerun.")
        sys.exit(1)

    page = context.pages[0] if context.pages else context.new_page()

    # Go to Canvas
    print("Navigating to https://canvas.jccc.edu/")
    page.goto("https://canvas.jccc.edu/", timeout=30000)
    page.wait_for_timeout(3000)
    page.wait_for_load_state("domcontentloaded", timeout=10000)

    print(f"Current URL: {page.url}")
    print(f"Title: {page.title()}")

    # Check if login required
    body_text = page.locator("body").inner_text(timeout=5000)[:5000]
    print("Body snippet:", body_text[:1000])

    if "log in" in body_text.lower() and ("jccc" in page.url.lower() or "canvas" in page.url.lower()):
        # Could be login page - check for login form
        if "login" in page.url.lower() or "saml" in page.url.lower() or "username" in body_text.lower():
            print("\n[!] Canvas requires login. Session may have expired.")
            print("Please manually log in to JCCC Canvas in the visible Chrome window.")
            print("After logging in and seeing Dashboard, press Enter here to continue...")
            try:
                input(">> Press Enter after manual login (or type 'abort' to exit): ")
            except:
                pass
            print("Continuing... waiting 3s")
            page.wait_for_timeout(3000)
            print(f"Now URL: {page.url}, Title: {page.title()}")

    # Attempt to find courses
    # Canvas Dashboard has course cards
    print("\n=== Checking Dashboard for courses ===")
    page.goto("https://canvas.jccc.edu/", timeout=20000)
    page.wait_for_timeout(3000)
    
    # Screenshot dashboard
    page.screenshot(path="canvas_dashboard.png", full_page=False)
    print("Screenshot saved: canvas_dashboard.png")

    # Try to get courses via API if authenticated (more reliable)
    # Use page.evaluate to fetch Canvas API
    def fetch_api(path):
        try:
            result = page.evaluate(f"""async () => {{
                try {{
                    const res = await fetch('{path}', {{ credentials: 'include' }});
                    if (!res.ok) return {{error: res.status + ' ' + res.statusText}};
                    const data = await res.json();
                    return data;
                }} catch (e) {{
                    return {{error: e.toString()}};
                }}
            }}""")
            return result
        except Exception as e:
            print(f"API fetch {path} failed: {e}")
            return {"error": str(e)}

    print("\n=== Fetching courses via Canvas API (if logged in) ===")
    courses = fetch_api("/api/v1/courses?enrollment_state=active&per_page=20")
    print(f"Courses API result type: {type(courses)}")
    if isinstance(courses, list):
        for c in courses:
            print(f"Course: {c.get('id')} - {c.get('name')} - {c.get('course_code')}")
            # Also fetch enrollment / grades
    else:
        print("Courses API response:", str(courses)[:1000])

    # Known course IDs from history: 86815, 87710
    target_course_ids = [86815, 87710]
    if isinstance(courses, list) and len(courses)>0:
        # Use IDs from API if available
        target_course_ids = [c['id'] for c in courses[:5]]  # take first 5 active

    grades_results = {}

    for cid in target_course_ids:
        print(f"\n=== Processing course {cid} ===")
        url = f"https://canvas.jccc.edu/courses/{cid}/grades"
        print(f"Navigating to {url}")
        page.goto(url, timeout=20000)
        page.wait_for_timeout(4000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        print(f"URL after nav: {page.url}, Title: {page.title()}")

        # Scroll
        for i in range(3):
            page.mouse.wheel(0, 800)
            page.wait_for_timeout(500)

        page.screenshot(path=f"canvas_grades_{cid}.png", full_page=True)
        print(f"Screenshot saved canvas_grades_{cid}.png")

        # Try to extract grades via API too
        enrollments = fetch_api(f"/api/v1/courses/{cid}/enrollments?user_id=self")
        print(f"Enrollments for {cid}: {str(enrollments)[:1500]}")

        # Body text
        try:
            body = page.locator("body").inner_text(timeout=5000)
            print(f"Body length {len(body)}")
            # Save truncated
            with open(f"canvas_grades_{cid}_text.txt", "w") as f:
                f.write(body[:20000])
            grades_results[cid] = body[:8000]
            # Look for grade patterns
            # Common Canvas grades table shows "Total: XX%"
            total_match = re.search(r"Total.*?(\d+\.?\d*%?)", body, re.IGNORECASE)
            if total_match:
                print(f"Found total grade snippet: {total_match.group(0)[:200]}")
        except Exception as e:
            print(f"Failed to get body for {cid}: {e}")

    print("\n=== Summary ===")
    for cid, text in grades_results.items():
        print(f"\n--- Course {cid} ---")
        print(text[:2000])

    print("\nDone. Keeping browser open for 15s for manual inspection, then closing...")
    page.wait_for_timeout(15000)
    context.close()
