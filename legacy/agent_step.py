import os
import sys
import json
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

api_key = os.environ.get("MODEL_API_KEY")
if not api_key:
    raise ValueError("MODEL_API_KEY is missing")

def ask_model(user_task, page_title, current_url, page_text):
    url = "https://api.meta.ai/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Truncate page text to avoid token limits
    page_text = page_text[:3000]

    prompt = f"""
You are a browser agent.
Your overarching task is: {user_task}

Current page title: {page_title}
Current URL: {current_url}
Visible page text snippet: {page_text}

Choose one next action to progress the task.
Return ONLY valid JSON with this schema:
{{
  "action": "goto" | "click_text" | "fill_text" | "done",
  "target": "string",
  "value": "string"
}}

- goto: Navigate to a URL (target = URL)
- click_text: Click an element containing this text (target = exact text to click)
- fill_text: Fill an input field (target = text near the input or placeholder, value = text to type)
- done: The task is complete
"""

    payload = {
        "model": "muse-spark-1.1",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "stream": False,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error communicating with Meta API: {e}")
        return {"action": "done", "target": "", "value": ""}

    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content["text"].strip()
                    if text.startswith("```json"): text = text[7:]
                    elif text.startswith("```"): text = text[3:]
                    if text.endswith("```"): text = text[:-3]
                    try:
                        return json.loads(text.strip())
                    except:
                        pass
    return {"action": "done", "target": "", "value": ""}

def main():
    print("========================================")
    print("🚀 Starting Spark Muse Browsing Agent...")
    print("========================================")
    
    # Check if a task was passed via command line
    single_shot = False
    cli_task = None
    if len(sys.argv) > 1:
        cli_task = " ".join(sys.argv[1:])
        single_shot = True

    with sync_playwright() as p:
        # Fix #1: Properly expand ${HOME} and ~
        def expand_path(path):
            # Handle ${HOME} and $HOME and ~
            import pathlib
            path = os.path.expandvars(path)  # expands ${HOME} and $HOME
            path = os.path.expanduser(path)  # expands ~
            return path

        # Priority logic:
        # 1. Try CDP connection to real Chrome (not flagged, uses your actual logged-in Chrome)
        # 2. Fallback to debug profile with stealth args (proven working for Canvas)
        use_cdp = False
        cdp_url = os.environ.get("CDP_URL", "http://localhost:9222")
        try:
            # Quick check if CDP port is open
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', 9222))
            s.close()
            if result == 0:
                print(f"[*] CDP port 9222 open, attempting to connect to REAL Chrome (your logged-in profile)...")
                browser = p.chromium.connect_over_cdp(cdp_url, timeout=10000)
                if browser.contexts:
                    context = browser.contexts[0]
                    use_cdp = True
                    print(f"[✓] Connected to REAL Chrome via CDP! Using your actual logged-in account.")
                    print(f"    Contexts: {len(browser.contexts)}, Pages: {len(context.pages)}")
                else:
                    print("[!] CDP connected but no contexts, falling back to debug profile")
                    browser.close()
        except Exception as e:
            print(f"[*] CDP not available ({e}), using debug profile (stealth mode)")

        if not use_cdp:
            profile_dir = os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile")
            user_data_dir = expand_path(profile_dir)
            # Clean locks for debug profile
            for lock_file in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
                lock_path = os.path.join(user_data_dir, lock_file)
                if os.path.exists(lock_path):
                    try:
                        os.remove(lock_path)
                        print(f"[*] Cleaned lock {lock_file}")
                    except Exception as ex:
                        print(f"[!] Could not clean {lock_file}: {ex}")

            print(f"[*] Using debug profile: {user_data_dir} (avoids flagging main profile)")
            print(f"    This profile retains login for days after one manual login.")
            
            try:
                # Launch Chrome persistently with stealth args to avoid detection
                context = p.chromium.launch_persistent_context(
                    user_data_dir,
                    executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    headless=False,
                    no_viewport=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",  # Avoid bot detection
                        "--disable-infobars",
                        "--no-first-run",
                    ],
                )
                # Hide webdriver property
                # Will be applied per page via add_init_script
            except Exception as e:
                print("[!] Chrome is already running or cannot be started.")
                print(f"    Error: {e}")
                print("    Please run: rm -f ~/chrome-debug-profile/Singleton* && try again")
                print("    Or quit Chrome completely (Cmd+Q)")
                return
        except Exception as e:
            print("[!] Chrome is already running or cannot be started.")
            print("Please close any existing Chrome windows and try again.")
            return

        page = context.pages[0] if context.pages else context.new_page()
            # Hide webdriver flag to reduce bot detection
            try:
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
        
        if not single_shot:
            print("\n✅ Browser launched! You can now type your prompts.")
            print("Type 'exit' or 'quit' to close the agent.\n")

        while True:
            if single_shot:
                user_task = cli_task
            else:
                try:
                    user_task = input("spark-muse> ")
                except (EOFError, KeyboardInterrupt):
                    break
                
            if not user_task.strip():
                continue
                
            if not single_shot and user_task.lower() in ["exit", "quit"]:
                break

            print(f"  -> Thinking about how to: {user_task}")

            # Run a small step loop for this task
            for step in range(15):
                try:
                    page_text = page.locator("body").inner_text(timeout=2000)
                except:
                    page_text = ""

                action = ask_model(user_task, page.title(), page.url, page_text)
                print(f"  -> Action {step+1}: {action} | url={page.url} | title={page.title()[:60]}")

                try:
                    if action["action"] == "goto":
                        page.goto(action["target"], timeout=10000)
                        page.wait_for_timeout(1500)
                    elif action["action"] == "click_text":
                        page.get_by_text(action["target"]).first.click(timeout=5000)
                        page.wait_for_timeout(2000)
                    elif action["action"] == "fill_text":
                        filled = False
                        # Try multiple robust locators for search inputs
                        locators_to_try = [
                            "textarea[name='q']",
                            "input[name='q']",
                            "textarea[aria-label*='Search' i]",
                            "input[aria-label*='Search' i]",
                            "input[type='search']",
                            "textarea[type='search']",
                        ]
                        # First try role-based locators
                        try:
                            page.get_by_role("combobox", name="Search").first.fill(action["value"], timeout=2000)
                            filled = True
                        except:
                            pass
                        if not filled:
                            for sel in locators_to_try:
                                try:
                                    loc = page.locator(sel).first
                                    if loc.count() > 0:
                                        loc.fill(action["value"], timeout=3000)
                                        filled = True
                                        break
                                except:
                                    continue
                        # Fallback to original near logic
                        if not filled:
                            try:
                                page.locator(f"input:near(:text('{action['target']}'))").first.fill(action["value"], timeout=3000)
                                filled = True
                            except:
                                pass
                        # Press Enter if filled
                        if filled:
                            try:
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(2000)
                            except:
                                pass
                        else:
                            raise Exception(f"Could not find input for '{action['target']}'")
                    elif action["action"] == "done":
                        print("  -> Task completed!\n")
                        break
                except Exception as e:
                    print(f"  -> [!] Action failed: {e}. Trying again...")
            
            if single_shot:
                break
                    
        print("\nClosing browser and exiting. Goodbye!")
        try:
            if use_cdp:
                print("[*] CDP mode: Disconnecting (leaving your real Chrome open)")
                # Don't close browser in CDP mode - it would close user's real Chrome
                # Just close the context? Actually we shouldn't close context either for CDP
                # So just return
                pass
            else:
                context.close()
        except Exception as e:
            print(f"Close error: {e}")

if __name__ == "__main__":
    main()
