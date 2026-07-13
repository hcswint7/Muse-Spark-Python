"""
Task 3: Access Canvas again (separately) and note assignments due in next 3 days
Uses fixed debug profile with stealth + secure login handling
"""
import os, sys, time, re, datetime
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

from playwright.sync_api import sync_playwright

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def clean_locks(profile):
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        fp = os.path.join(profile, f)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except: pass

def is_login_page(page):
    url = page.url.lower()
    if "login.microsoftonline.com" in url or "microsoft" in url and "login" in url:
        return True
    if "sign in to your account" in page.title().lower():
        return True
    return False

debug_profile = expand_path(os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile"))
clean_locks(debug_profile)
print(f"Using profile: {debug_profile} (separate launch as requested)")

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

    print("Navigating to Canvas...")
    page.goto("https://canvas.jccc.edu/", timeout=30000)
    page.wait_for_timeout(3000)
    print(f"URL: {page.url}, Title: {page.title()}")

    if is_login_page(page):
        print("[!] Login required - waiting 120s for manual login")
        start = time.time()
        while time.time() - start < 120 and is_login_page(page):
            page.wait_for_timeout(3000)
            if int(time.time()-start) % 15 == 0:
                print(f"... waiting {int(time.time()-start)}s, URL: {page.url[:80]}")
        if is_login_page(page):
            print("[!] Still not logged in, aborting")
            context.close()
            sys.exit(1)
        else:
            print("[✓] Manual login success!")

    # Fetch courses
    def fetch_api(path):
        try:
            return page.evaluate(f"""async () => {{
                const r = await fetch('{path}', {{credentials:'include'}});
                if (!r.ok) return {{error: r.status}};
                return await r.json();
            }}""")
        except Exception as e:
            return {"error": str(e)}

    courses = fetch_api("/api/v1/courses?enrollment_state=active&per_page=20")
    course_ids = []
    course_names = {}
    if isinstance(courses, list):
        for c in courses:
            course_ids.append(c['id'])
            course_names[c['id']] = c.get('name', f"Course {c['id']}")
            print(f"Course {c['id']}: {c.get('name')}")
    else:
        course_ids = [86815, 87710]
        course_names = {86815: "MKT-230-353", 87710: "BLAW-261-353"}

    # Date logic for next 3 days
    now = datetime.datetime.now(datetime.timezone.utc)
    three_days_later = now + datetime.timedelta(days=3)
    print(f"\nNow (UTC): {now.isoformat()}")
    print(f"Three days later (UTC): {three_days_later.isoformat()}")
    print(f"Now (local): {datetime.datetime.now().isoformat()}")

    all_due = []

    for cid in course_ids[:5]:
        print(f"\n=== Checking assignments for course {cid} ({course_names.get(cid)}) ===")
        # Fetch assignments via API - more reliable than scraping
        # Use bucket=upcoming and include due dates
        assignments = fetch_api(f"/api/v1/courses/{cid}/assignments?per_page=100&order_by=due_at&bucket=upcoming")
        if isinstance(assignments, dict) and "error" in assignments:
            print(f"API error for {cid}: {assignments}")
            # Try alternative endpoint
            assignments = fetch_api(f"/api/v1/courses/{cid}/assignments?per_page=100")
        
        if isinstance(assignments, list):
            print(f"Found {len(assignments)} assignments via API")
            for a in assignments:
                name = a.get('name')
                due_at = a.get('due_at')
                html_url = a.get('html_url')
                points = a.get('points_possible')
                # Parse due_at
                if due_at:
                    try:
                        # due_at is ISO format like 2026-07-15T05:59:59Z
                        due_dt = datetime.datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        # Check if due within next 3 days
                        if now <= due_dt <= three_days_later:
                            all_due.append({
                                'course_id': cid,
                                'course_name': course_names.get(cid),
                                'assignment_name': name,
                                'due_at': due_at,
                                'due_dt': due_dt,
                                'url': html_url,
                                'points': points,
                            })
                            print(f"  DUE SOON: {name} - Due {due_at} - {html_url}")
                        else:
                            # Also include if overdue by 1 day? No, only next 3 days
                            if due_dt > now:
                                print(f"  Future (beyond 3d): {name} - Due {due_at}")
                    except Exception as e:
                        print(f"  Failed to parse due date {due_at} for {name}: {e}")
                else:
                    # No due date
                    pass
        else:
            print(f"Unexpected assignments format: {str(assignments)[:500]}")

        # Also scrape assignments page for visual confirmation
        page.goto(f"https://canvas.jccc.edu/courses/{cid}/assignments", timeout=20000)
        page.wait_for_timeout(3000)
        page.screenshot(path=f"canvas_assignments_{cid}.png", full_page=True)
        print(f"Screenshot saved for {cid}")

    print("\n" + "="*80)
    print("FINAL RESULT: Assignments due in next 3 days from now:")
    print("="*80)
    if not all_due:
        print("No assignments due in next 3 days (based on Canvas API upcoming bucket)")
        print(f"Checked courses: {course_ids}")
        print(f"Window: {now.isoformat()} to {three_days_later.isoformat()}")
    else:
        # Sort by due date
        all_due_sorted = sorted(all_due, key=lambda x: x['due_dt'])
        for item in all_due_sorted:
            due_local = item['due_dt'].astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
            print(f"- [{item['course_name']}] {item['assignment_name']}")
            print(f"  Due: {due_local} (UTC: {item['due_at']})")
            print(f"  Points: {item['points']}, URL: {item['url']}")
            print()

    # Save to file for documentation
    with open("canvas_due_assignments.txt", "w") as f:
        f.write(f"Checked: {now.isoformat()} to {three_days_later.isoformat()}\n")
        f.write(f"Courses: {course_ids}\n\n")
        if not all_due:
            f.write("No assignments due in next 3 days\n")
        else:
            for item in sorted(all_due, key=lambda x: x['due_dt']):
                f.write(f"{item['course_name']} | {item['assignment_name']} | Due {item['due_at']} | {item['url']}\n")

    print("\nKeeping browser open 10s...")
    page.wait_for_timeout(10000)
    context.close()
    print("Done.")
