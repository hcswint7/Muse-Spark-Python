"""Final verification after Ente Auth access"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def clean_locks(profile):
    for f in ["SingletonLock","SingletonCookie","SingletonSocket"]:
        fp = os.path.join(profile, f)
        if os.path.exists(fp) or os.path.islink(fp):
            try: os.remove(fp)
            except: pass

from playwright.sync_api import sync_playwright
debug_profile = expand_path("~/chrome-debug-profile")
clean_locks(debug_profile)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        debug_profile,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        no_viewport=True,
        args=["--disable-blink-features=AutomationControlled","--disable-infobars"]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    except: pass
    
    page.goto("https://canvas.jccc.edu/", timeout=20000)
    page.wait_for_timeout(2000)
    print(f"URL: {page.url}, Title: {page.title()}")
    
    # API verification
    result = page.evaluate("""async () => {
        const r = await fetch('/api/v1/courses?enrollment_state=active&per_page=20',{credentials:'include'});
        return await r.json();
    }""")
    print(f"Courses: {len(result)}")
    for c in result:
        cid = c['id']
        print(f"Course {cid}: {c['name']}")
        grades = page.evaluate(f"""async () => {{
            const r = await fetch('/api/v1/courses/{cid}/enrollments?user_id=self',{{credentials:'include'}});
            return await r.json();
        }}""")
        if isinstance(grades, list) and len(grades)>0:
            g = grades[0].get('grades',{})
            print(f"  Grade: {g.get('current_grade')} {g.get('current_score')}% (current) / {g.get('final_score')}% final")
    
    # Assignments upcoming
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=3)
    print(f"\nNow: {now}, cutoff +3days: {cutoff}")
    for c in result:
        cid = c['id']
        assigns = page.evaluate(f"""async () => {{
            const r = await fetch('/api/v1/courses/{cid}/assignments?per_page=100&bucket=upcoming',{{credentials:'include'}});
            return await r.json();
        }}""")
        if isinstance(assigns, list):
            for a in assigns:
                due = a.get('due_at')
                if due:
                    try:
                        due_dt = datetime.fromisoformat(due.replace('Z','+00:00'))
                        if now <= due_dt <= cutoff:
                            print(f"  DUE SOON Course {cid}: {a.get('name')} due {due} (UTC) / local should convert to CDT")
                    except: pass
    
    page.screenshot(path="canvas_final_verification.png")
    print("\nScreenshot: canvas_final_verification.png")
    page.wait_for_timeout(5000)
    ctx.close()
    print("Done")
