import os, time
os.environ.pop('DISPLAY', None)
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
            print(f"cleaned {f}")
    except Exception as e:
        print(e)

from playwright.sync_api import sync_playwright

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

    print(f"Navigating to Canvas... current pages: {len(ctx.pages)}")
    page.goto("https://canvas.jccc.edu/", timeout=30000)
    print(f"URL: {page.url} Title: {page.title()}")
    # keep alive for instructions
    print("Browser is UP. In Canvas. Waiting for user direction. Keeping alive 600s...")
    # screenshot for proof
    page.screenshot(path="canvas_started.png")
    print("screenshot canvas_started.png")
    # keep open
    for i in range(120):
        time.sleep(5)
        try:
            print(f"[alive {i*5}s] url={page.url[:100]} title={page.title()[:50]}")
        except:
            print(f"[alive {i*5}s] page closed?")
            break
    print("Closing after wait")
    ctx.close()
