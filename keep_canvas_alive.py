import time, os
from playwright.sync_api import sync_playwright
profile=os.path.expanduser("~/chrome-debug-profile")
# Don't clean locks while chrome alive - skip
from dotenv import load_dotenv
load_dotenv(override=True)
with sync_playwright() as p:
    # Connect to existing if possible? For now launch new if needed
    try:
        ctx = p.chromium.launch_persistent_context(
            profile,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled","--disable-infobars","--no-first-run","--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print(f"keeper attached url={page.url}", flush=True)
        # Infinite resilient loop - never close on user click
        while True:
            try:
                time.sleep(5)
                try:
                    url = page.url
                except:
                    url = "unknown"
                    # try to get first page
                    if ctx.pages:
                        page = ctx.pages[0]
                        url = page.url
                try:
                    title = page.title()
                except:
                    title = "no title"
                print(f"[keep {time.strftime('%H:%M:%S')}] {url[:100]} | {title[:50]}", flush=True)
            except Exception as e:
                print(f"keep error {e}, retrying", flush=True)
                time.sleep(2)
    except Exception as e:
        print(f"keeper failed {e}", flush=True)
