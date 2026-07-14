import os, time, sys
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

def expand(p): return os.path.expanduser(os.path.expandvars(p))
profile = expand("~/chrome-debug-profile")
for f in ["SingletonLock","SingletonCookie","SingletonSocket"]:
    fp = os.path.join(profile, f)
    try:
        if os.path.exists(fp) or os.path.islink(fp):
            os.remove(fp)
            print(f"cleaned {f}", flush=True)
    except Exception as e:
        print(e, flush=True)

from playwright.sync_api import sync_playwright
import hashlib

class StuckDetector:
    def __init__(self): self.history={}
    def check(self, tool, args):
        key=hashlib.md5(f"{tool}:{args}".encode()).hexdigest()
        c=self.history.get(key,0)+1
        self.history[key]=c
        return c>=3

def is_ms_login(page):
    url=page.url.lower()
    return "login.microsoftonline.com" in url or "login.windows.net" in url or "saml" in url.lower()[:200]

def handle_login_if_needed(page):
    if not is_ms_login(page):
        print(f"[info] Not on MS login, url={page.url}", flush=True)
        return True
    print(f"[login] Detected MS login at {page.url[:100]}", flush=True)
    username=os.getenv("CANVAS_USERNAME")
    password=os.getenv("CANVAS_PASSWORD")
    if not username or not password:
        print("[login] No creds, waiting for manual", flush=True)
        for i in range(40):
            time.sleep(3)
            if not is_ms_login(page):
                print(f"[login] manual success after {i*3}s -> {page.url}", flush=True)
                return True
        return False
    print(f"[login] attempting auto for {username[:3]}***", flush=True)
    det=StuckDetector()
    # email
    for sel in ["input[type='email']","input[name='loginfmt']","#i0116"]:
        if det.check("email",sel): continue
        try:
            loc=page.locator(sel).first
            if loc.count()>0 and loc.is_visible(timeout=2000):
                print(f"[login] fill email via {sel}", flush=True)
                loc.fill(username, timeout=5000)
                break
        except Exception as e:
            print(f"email {sel} fail {e}", flush=True)
            continue
    # next
    for sel in ["input[type='submit']","#idSIButton9","button:has-text('Next')"]:
        try:
            btn=page.locator(sel).first
            if btn.count()>0 and btn.is_visible(timeout=2000):
                btn.click(timeout=5000)
                print(f"[login] clicked next {sel}", flush=True)
                break
        except: continue
    page.wait_for_timeout(3000)
    # pw
    for sel in ["input[type='password']","input[name='passwd']","#i0118"]:
        if det.check("pw",sel): continue
        try:
            loc=page.locator(sel).first
            loc.wait_for(state="visible", timeout=8000)
            print(f"[login] fill pw via {sel} len {len(password)}", flush=True)
            loc.fill(password, timeout=5000)
            break
        except: continue
    for sel in ["input[type='submit']","#idSIButton9"]:
        try:
            btn=page.locator(sel).last
            if btn.count()>0 and btn.is_visible(timeout=2000):
                btn.click(timeout=5000)
                print(f"[login] clicked signin {sel}", flush=True)
                break
        except: continue
    page.wait_for_timeout(5000)
    # MFA attempt via Ente v3
    try:
        sys.path.insert(0, "/Users/hswin/muse-spark-python/examples")
        from ente_auth_ocr_secure_v3 import fill_microsoft_mfa_v3
        print("[login] trying Ente MFA v3", flush=True)
        if fill_microsoft_mfa_v3(page, "Microsoft"):
            print("[login] MFA auto success", flush=True)
            return True
    except Exception as e:
        print(f"[login] MFA v3 error {e}", flush=True)
        import traceback; traceback.print_exc()

    print("[login] polling for manual MFA 90s", flush=True)
    for i in range(30):
        time.sleep(3)
        if not is_ms_login(page):
            print(f"[login] success after MFA wait {i*3}s {page.url}", flush=True)
            return True
        if i%3==0:
            print(f"[login] wait {i*3}s url {page.url[:80]}", flush=True)
    return "canvas.jccc.edu" in page.url.lower()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        profile,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        no_viewport=True,
        args=["--disable-blink-features=AutomationControlled","--disable-infobars","--no-first-run","--disable-dev-shm-usage"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    except: pass

    page.goto("https://canvas.jccc.edu/", timeout=30000)
    page.wait_for_timeout(3000)
    print(f"Initial URL: {page.url} Title: {page.title()}", flush=True)

    if is_ms_login(page):
        handle_login_if_needed(page)
    else:
        print(f"[info] Already in Canvas", flush=True)

    # Now go to dashboard for fresh grades etc.
    page.goto("https://canvas.jccc.edu/", timeout=20000)
    page.wait_for_timeout(2000)
    print(f"Final URL: {page.url} Title: {page.title()}", flush=True)

    # Fetch courses via API with retry
    js = """async () => { const r=await fetch('/api/v1/courses?enrollment_state=active&per_page=20',{credentials:'include'}); if(!r.ok) return {error:r.status}; return await r.json(); }"""
    try:
        courses = page.evaluate(js)
        if isinstance(courses, list):
            print(f"[canvas] API ok {len(courses)} courses", flush=True)
            for c in courses:
                print(f"  {c['id']} {c['name']}", flush=True)
        else:
            print(f"[canvas] API returned {str(courses)[:200]}", flush=True)
    except Exception as e:
        print(f"[canvas] API fail {e}", flush=True)

    page.screenshot(path="canvas_live.png")
    print("screenshot canvas_live.png", flush=True)
    print("=== BROWSER IS UP IN CANVAS. READY FOR YOUR DIRECTION ===", flush=True)
    # alive loop for instructions - report every 10s
    for i in range(180): # 15 min
        time.sleep(10)
        try:
            url = page.url
            title = page.title()
            print(f"[alive {i*10}s] {url[:120]} | {title[:80]}", flush=True)
        except Exception as e:
            print(f"[alive] exception {e}, maybe closed", flush=True)
            break
    print("Exiting after alive loop", flush=True)
    ctx.close()
