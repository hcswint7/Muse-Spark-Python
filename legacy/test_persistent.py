from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    user_data_dir = os.path.expanduser("~/chrome-debug-profile")
    # Launch Chrome persistently
    context = p.chromium.launch_persistent_context(
        user_data_dir,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        no_viewport=True,
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://example.com")
    print("Opened example.com!")
    context.close()
