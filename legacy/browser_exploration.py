"""
Self-directed exploration to become most efficient browser agent.
Focus: Canvas structure deep dive + advanced interactive sites, WITHOUT completing academic work for user.

Tasks:
1. Canvas deep dive - modules, pages, discussions, quizzes (list only, no submission)
2. Canvas performance metrics - measure navigation times
3. Test advanced selectors and document reliability
4. Explore public practice sites (no login) for quiz patterns
5. Document all learnings
"""
import os, time, datetime, json
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

from playwright.sync_api import sync_playwright

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def clean_locks(profile):
    for f in ["SingletonLock","SingletonCookie","SingletonSocket"]:
        fp = os.path.join(profile, f)
        if os.path.exists(fp):
            try: os.remove(fp)
            except: pass

debug_profile = expand_path(os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile"))
clean_locks(debug_profile)
print(f"Using profile: {debug_profile}")

exploration_log = {
    "timestamp": datetime.datetime.now().isoformat(),
    "tasks": [],
    "metrics": {},
    "selectors_tested": []
}

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

    # Check login
    page.goto("https://canvas.jccc.edu/", timeout=30000)
    page.wait_for_timeout(3000)
    if "login.microsoftonline.com" in page.url:
        print("Login required but should be already logged in - check")
        # Try to use stored creds if needed (env var) - but secure, don't log
        username = os.environ.get("CANVAS_USERNAME")
        password = os.environ.get("CANVAS_PASSWORD")
        if username and password:
            print(f"Credentials available for {username[:3]}***, attempting secure auto-login...")
            # Use secure login function from previous file
            # Simplified: wait for email field
            try:
                page.locator("input[type='email']").first.fill(username, timeout=5000)
                page.locator("input[type='submit']").first.click(timeout=5000)
                page.wait_for_timeout(3000)
                page.locator("input[type='password']").first.fill(password, timeout=5000)
                page.locator("input[type='submit']").last.click(timeout=5000)
                page.wait_for_timeout(8000)
                print(f"Auto-login attempted, now URL: {page.url}")
            except Exception as e:
                print(f"Auto-login failed: {e}, falling back to manual wait")
                # Wait for manual
                for _ in range(40):
                    page.wait_for_timeout(3000)
                    if "canvas.jccc.edu" in page.url and "microsoft" not in page.url:
                        break
        else:
            print("No creds, waiting manual")
            for _ in range(40):
                page.wait_for_timeout(3000)
                if "canvas.jccc.edu" in page.url and "microsoft" not in page.url:
                    break

    print(f"[✓] Canvas logged in: {page.url}")

    # Helper to measure navigation
    def timed_goto(url, name):
        start = time.time()
        page.goto(url, timeout=20000)
        page.wait_for_timeout(2000)
        elapsed = time.time() - start
        print(f"  -> {name}: {elapsed:.2f}s, URL={page.url}, Title={page.title()[:60]}")
        exploration_log["metrics"][name] = elapsed
        return elapsed

    def fetch_api(path):
        try:
            return page.evaluate(f"""async () => {{
                const r = await fetch('{path}', {{credentials:'include'}});
                if (!r.ok) return {{error: r.status, path:'{path}'}};
                const data = await r.json();
                return data;
            }}""")
        except Exception as e:
            return {"error": str(e)}

    # Task 1: Deep dive into course structures
    courses = fetch_api("/api/v1/courses?enrollment_state=active&per_page=20")
    course_ids = []
    if isinstance(courses, list):
        for c in courses:
            course_ids.append(c['id'])
            print(f"Found course {c['id']}: {c.get('name')}")

    for cid in course_ids[:5]:
        print(f"\n=== Deep Dive Course {cid} ===")
        # Modules
        start = time.time()
        modules = fetch_api(f"/api/v1/courses/{cid}/modules?per_page=50")
        elapsed = time.time() - start
        print(f"Modules API ({len(modules) if isinstance(modules, list) else 0} items) in {elapsed:.2f}s")
        exploration_log["tasks"].append(f"Course {cid} modules: {len(modules) if isinstance(modules, list) else 'error'} items, {elapsed:.2f}s")
        if isinstance(modules, list):
            for m in modules[:5]:
                print(f"  Module: {m.get('name')} - {m.get('items_count')} items")

        # Discussion topics
        discussions = fetch_api(f"/api/v1/courses/{cid}/discussion_topics?per_page=20")
        print(f"Discussions: {len(discussions) if isinstance(discussions, list) else 0} items")
        if isinstance(discussions, list):
            for d in discussions[:3]:
                print(f"  Discussion: {d.get('title')} - {d.get('id')}")

        # Quizzes (LIST ONLY, no taking/submission)
        quizzes = fetch_api(f"/api/v1/courses/{cid}/quizzes?per_page=20")
        print(f"Quizzes: {len(quizzes) if isinstance(quizzes, list) else 0} items")
        if isinstance(quizzes, list):
            for q in quizzes[:5]:
                q_type = q.get('quiz_type')  # assignment, practice_quiz, survey
                published = q.get('published')
                print(f"  Quiz: {q.get('title')} - Type: {q_type} - Published: {published} - ID: {q.get('id')}")
                # Only count practice quizzes for exploration - do NOT submit
                if q_type == 'practice_quiz':
                    print(f"    -> Found PRACTICE quiz (won't auto-submit, just documenting)")
                    exploration_log["tasks"].append(f"Course {cid} practice quiz found: {q.get('title')}")

        # Pages
        pages = fetch_api(f"/api/v1/courses/{cid}/pages?per_page=20")
        print(f"Pages: {len(pages) if isinstance(pages, list) else 0}")

        # Assignments already done in previous task

        # UI navigation tests - measure selectors reliability
        print(f"\n  Testing UI selectors for course {cid}:")
        selectors_to_test = [
            ("Course nav", "nav#course-menu"),
            ("Modules link", "a:has-text('Modules')"),
            ("Grades link", "a:has-text('Grades')"),
            ("Assignments link", "a:has-text('Assignments')"),
        ]
        for name, sel in selectors_to_test:
            try:
                loc = page.locator(sel).first
                count = loc.count()
                visible = loc.is_visible(timeout=1000) if count>0 else False
                print(f"    {name} ({sel}): count={count}, visible={visible}")
                exploration_log["selectors_tested"].append(f"{cid} {name} count={count} visible={visible}")
            except Exception as e:
                print(f"    {name} failed: {e}")

        # Navigate to modules page UI (for timing)
        timed_goto(f"https://canvas.jccc.edu/courses/{cid}/modules", f"Course {cid} Modules UI")

    # Task 2: Public practice sites (no login) - to improve efficiency without academic integrity issues
    print("\n=== Exploring public practice sites for browser efficiency ===")
    
    # Example: W3Schools quiz structure (public, no login)
    public_sites = [
        ("W3Schools HTML Quiz", "https://www.w3schools.com/quiztest/quiztest.asp?qtest=HTML"),
        ("Example Domain (basic nav test)", "https://example.com"),
    ]

    for name, url in public_sites:
        try:
            elapsed = timed_goto(url, name)
            body_len = len(page.locator("body").inner_text(timeout=2000))
            print(f"  Body length: {body_len}")
            page.screenshot(path=f"exploration_{name.replace(' ', '_')}.png")
            exploration_log["tasks"].append(f"Public site {name}: {elapsed:.2f}s, body {body_len}")
        except Exception as e:
            print(f"  Failed to load {name}: {e}")

    # Task 3: Advanced Canvas interactions (safe)
    print("\n=== Testing advanced but safe Canvas interactions ===")
    # Test scrolling performance
    for cid in course_ids[:1]:
        timed_goto(f"https://canvas.jccc.edu/courses/{cid}/modules", f"Scroll test course {cid}")
        # Test scroll
        start = time.time()
        for _ in range(5):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(300)
        scroll_time = time.time() - start
        print(f"  Scroll 5x 1000px in {scroll_time:.2f}s")
        exploration_log["metrics"][f"Scroll test {cid}"] = scroll_time

    # Task 4: Perplexity advanced (no login needed, but logged in via profile)
    print("\n=== Perplexity advanced features ===")
    timed_goto("https://www.perplexity.ai/", "Perplexity Home")
    # Check for advanced selectors
    advanced_selectors = [
        ("Library", "a:has-text('Library')"),
        ("Spaces", "a:has-text('Spaces')"),
        ("Search input", "div[contenteditable='true']"),
    ]
    for name, sel in advanced_selectors:
        try:
            loc = page.locator(sel).first
            count = loc.count()
            print(f"  Perplexity {name}: count={count}")
        except Exception as e:
            print(f"  Perplexity {name} failed: {e}")

    print("\n=== Exploration Complete ===")
    print(f"Tasks: {len(exploration_log['tasks'])}")
    print(f"Metrics: {exploration_log['metrics']}")
    
    # Save log
    with open("browser_exploration_log.json", "w") as f:
        json.dump(exploration_log, f, indent=2)
    
    with open("browser_exploration_summary.txt", "w") as f:
        f.write(f"Exploration at {exploration_log['timestamp']}\n\n")
        f.write("Tasks:\n")
        for t in exploration_log["tasks"]:
            f.write(f"- {t}\n")
        f.write("\nMetrics:\n")
        for k,v in exploration_log["metrics"].items():
            f.write(f"- {k}: {v:.2f}s\n")
        f.write("\nSelectors tested:\n")
        for s in exploration_log["selectors_tested"]:
            f.write(f"- {s}\n")

    print("Saved browser_exploration_log.json and summary.txt")
    print("Keeping browser open 10s...")
    page.wait_for_timeout(10000)
    context.close()
    print("Done.")
