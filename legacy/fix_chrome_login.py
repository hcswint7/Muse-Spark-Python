import os, sys, time
from playwright.sync_api import sync_playwright

# Test both profile approaches

def clean_locks(profile_path):
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = os.path.join(profile_path, f)
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"Removed {p}")
            except Exception as e:
                print(f"Failed to remove {p}: {e}")

# Option 1: Use main Chrome User Data dir with Profile 1
main_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
clean_locks(main_user_data)
print(f"Trying main user data dir: {main_user_data} with Profile 1")

with sync_playwright() as p:
    try:
        # This should launch Chrome using your real Profile 1 where you're logged into everything
        context = p.chromium.launch_persistent_context(
            main_user_data,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            no_viewport=True,
            args=["--profile-directory=Profile 1"],
        )
        print("SUCCESS: Launched with Profile 1")
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://canvas.jccc.edu/", timeout=20000)
        page.wait_for_timeout(3000)
        print(f"After nav: URL={page.url}, Title={page.title()}")
        body = page.locator("body").inner_text(timeout=3000)[:2000]
        print(f"Body snippet: {body[:1000]}")
        if "login.microsoftonline.com" in page.url:
            print("STILL requires Microsoft login - session expired even in main profile")
        elif "Dashboard" in page.title() or "canvas" in page.url.lower():
            print("SUCCESS: Logged into Canvas with real profile!")
        page.screenshot(path="test_real_profile_canvas.png")
        print("Screenshot saved")
        page.wait_for_timeout(5000)
        context.close()
    except Exception as e:
        print(f"FAILED to launch with main profile: {e}")
        import traceback
        traceback.print_exc()

print("\n--- Now trying debug profile (for comparison) ---")
debug_profile = os.path.expanduser("~/chrome-debug-profile")
clean_locks(debug_profile)
with sync_playwright() as p:
    try:
        context = p.chromium.launch_persistent_context(
            debug_profile,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://canvas.jccc.edu/", timeout=20000)
        page.wait_for_timeout(3000)
        print(f"Debug profile: URL={page.url}, Title={page.title()}")
        page.screenshot(path="test_debug_profile_canvas.png")
        page.wait_for_timeout(3000)
        context.close()
        print("Debug profile launch OK")
    except Exception as e:
        print(f"Debug profile failed: {e}")
