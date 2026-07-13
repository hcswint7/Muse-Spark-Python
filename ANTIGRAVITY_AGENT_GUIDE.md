# Building an Autonomous Browser Agent with the Google Antigravity (AGY) SDK

This guide explains how to build a custom, repeatable CLI agent using the **Google Antigravity SDK** that connects to your **live Chrome browser and tabs** and automates browsing tasks based on simple terminal prompts.

---

## 1. What is the Antigravity (AGY) SDK?
The Google Antigravity SDK is a Python framework designed by Google Deepmind for building autonomous agents. 

Unlike standard scripts, an Antigravity agent:
* Runs an active, stateful loop (retaining memory).
* Can call built-in or custom Python functions as "tools".
* Integrates directly with Gemini models to make intelligent decisions.

---

## 2. Prerequisites & Setup

Ensure you have your environment set up:

1. **Gemini API Key**: Get an API key from [Google AI Studio](https://aistudio.google.com/app/api-keys).
2. **Add to `.env`**:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   CHROME_PROFILE_DIR=~/chrome-debug-profile
   ```
3. **Install Dependencies**:
   ```bash
   .venv/bin/pip install google-antigravity playwright python-dotenv
   .venv/bin/playwright install chromium
   ```
4. **Model note**: The agent uses `gemini-3.5-flash`. Older models like `gemini-2.5-flash` are no longer available for new users.

---

## 3. Creating the Agent Script (`antigrav_agent.py`)

Create a script `antigrav_agent.py` that instantiates an Antigravity agent, launches Playwright connected to your live Chrome profile, and exposes page control actions as tools.

```python
import asyncio
import os
import sys
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, BuiltinTools
from google.antigravity import types as ag_types
from google.antigravity.hooks import policy
from playwright.async_api import async_playwright

load_dotenv()

# Ensure we have our API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[!] GEMINI_API_KEY is missing from environment. Please add it to your .env file.")
    sys.exit(1)

# Global variables to hold Playwright browser reference
browser = None
page = None

# --- DEFINE TOOLS FOR THE ANTIGRAVITY AGENT ---

async def navigate_to(url: str) -> str:
    """Navigates the browser to the specified URL."""
    global page
    try:
        await page.goto(url, timeout=10000)
        await page.wait_for_load_state("networkidle", timeout=5000)
        return f"Successfully navigated to {url}. Title is: '{await page.title()}'"
    except Exception as e:
        return f"Failed to navigate to {url}: {e}"

async def click_element_with_text(text: str) -> str:
    """Clicks the first visible button, link, or element with the given text.
    Tries role-based locators first, then falls back to text match."""
    global page
    strategies = [
        page.get_by_role("button", name=text, exact=False),
        page.get_by_role("link", name=text, exact=False),
        page.locator("button:has-text('{text}'), a:has-text('{text}'), [role='option']:has-text('{text}')"),
        page.get_by_text(text),
    ]
    for locator in strategies:
        try:
            el = locator.first
            if await el.count() > 0 and await el.is_visible():
                await el.scroll_into_view_if_needed()
                await el.click(timeout=5000)
                await page.wait_for_timeout(1500)
                return f"Successfully clicked element with text: '{text}'"
        except Exception:
            continue
    return f"Failed to click element with text '{text}': element not found or not visible."

async def fill_input_field(label_or_placeholder: str, text_to_type: str) -> str:
    """Fills an input box or text field. Tries placeholder, label, aria-label, then near-text."""
    global page
    strategies = [
        page.get_by_placeholder(label_or_placeholder),
        page.get_by_label(label_or_placeholder),
        page.get_by_role("textbox", name=label_or_placeholder),
        page.locator(f"input:near(:text('{label_or_placeholder}'))"),
        page.locator(f"textarea:near(:text('{label_or_placeholder}'))"),
    ]
    for locator in strategies:
        try:
            el = locator.first
            if await el.count() > 0 and await el.is_visible():
                await el.click(timeout=2000)
                await el.fill(text_to_type, timeout=3000)
                return f"Filled '{label_or_placeholder}' with '{text_to_type}'"
        except Exception:
            continue
    return f"Failed to fill field '{label_or_placeholder}': no visible input found."

async def read_page_content() -> str:
    """Returns the visible page text, prefixed with the title and URL."""
    global page
    try:
        title = await page.title()
        url = page.url
        text = await page.locator("body").inner_text(timeout=2000)
        return f"Title: {title}\nURL: {url}\n---\n{text[:4000]}"
    except Exception as e:
        return f"Failed to read page content: {e}"

async def scroll_page(direction: str) -> str:
    """Scrolls the page. Valid: down, up, bottom, top."""
    global page
    d = direction.strip().lower()
    actions = {
        "bottom": "window.scrollTo(0, document.body.scrollHeight)",
        "top": "window.scrollTo(0, 0)",
        "down": "window.scrollBy(0, window.innerHeight * 0.8)",
        "up": "window.scrollBy(0, -window.innerHeight * 0.8)",
    }
    if d not in actions:
        return f"Invalid direction '{d}'. Use: down, up, bottom, top"
    try:
        await page.evaluate(actions[d])
        await page.wait_for_timeout(500)
        return f"Scrolled {d}."
    except Exception as e:
        return f"Failed to scroll: {e}"

async def go_back() -> str:
    """Navigates back one page."""
    global page
    try:
        await page.go_back(timeout=10000)
        await page.wait_for_load_state("networkidle", timeout=5000)
        return f"Back. Title: '{await page.title()}'"
    except Exception as e:
        return f"Failed to go back: {e}"

async def press_key(key: str) -> str:
    """Presses a keyboard key (Enter, Escape, Tab, ArrowDown, etc.)."""
    global page
    try:
        await page.keyboard.press(key)
        await page.wait_for_timeout(500)
        return f"Pressed '{key}'."
    except Exception as e:
        return f"Failed to press '{key}': {e}"

async def take_screenshot() -> str:
    """Saves a screenshot PNG and returns the file path."""
    global page
    try:
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="screenshot_")
        path = f.name
        f.close()
        await page.screenshot(path=path, full_page=False)
        return f"Screenshot: {path}"
    except Exception as e:
        return f"Failed to screenshot: {e}"

async def get_current_url() -> str:
    """Returns the current URL."""
    global page
    try:
        return f"Current URL: {page.url}"
    except Exception as e:
        return f"Failed to get URL: {e}"

# --- MAIN AGENT LOOP ---

async def run_agent_loop():
    global browser, page

    config = LocalAgentConfig(
        model="gemini-3.5-flash",
        api_key=api_key,
        system_instructions=(
            "You are an autonomous browser agent. Navigate, click, fill, scroll, "
            "go back, press keys, screenshot, and read pages to complete the user's task."
        ),
        tools=[
            navigate_to, click_element_with_text, fill_input_field, read_page_content,
            scroll_page, go_back, press_key, take_screenshot, get_current_url,
        ],
        capabilities=CapabilitiesConfig(disabled_tools=BuiltinTools.all_tools()),
        policies=[policy.allow_all()],
        workspaces=[],
    )

    async with async_playwright() as p:
        print("Initializing live Chrome browser connection...")
        profile_dir = os.environ.get("CHROME_PROFILE_DIR", "~/chrome-debug-profile")
        user_data_dir = os.path.expanduser(profile_dir)

        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,
                no_viewport=True,
            )
        except Exception as e:
            print(f"[!] Failed to launch Chrome with '{user_data_dir}': {e}")
            print("Try: rm -rf ~/chrome-debug-profile/Singleton*")
            print("Or quit Chrome (Cmd+Q) and retry.")
            return

        page = browser.pages[0] if browser.pages else await browser.new_page()
        print("Browser connected!")
        print("Type 'exit' to quit.\n")

        async with Agent(config) as agent:
            while True:
                try:
                    user_task = await asyncio.to_thread(input, "antigrav-agent> ")
                except (EOFError, KeyboardInterrupt):
                    break
                if not user_task.strip():
                    continue
                if user_task.lower() == "exit":
                    break

                print(f"\n[Working on: '{user_task}']\n")
                response = await agent.chat(user_task)
                text_parts = []
                async for chunk in response.chunks:
                    if isinstance(chunk, ag_types.Thought):
                        print(f"[thinking] {chunk.text}", end="", flush=True)
                    elif isinstance(chunk, ag_types.Text):
                        print(chunk.text, end="", flush=True)
                        text_parts.append(chunk.text)
                    elif isinstance(chunk, ag_types.ToolCall):
                        print(f"\n[tool] {chunk.name}({chunk.args})", flush=True)
                if "".join(text_parts).strip():
                    print()
                print()

        await browser.close()

def main():
    asyncio.run(run_agent_loop())

if __name__ == "__main__":
    main()
```

---

## 4. How to Run It

1. **Ensure Chrome is closed** (Cmd+Q), or if the profile `~/chrome-debug-profile` exists from a prior run, clear its lock files:
   ```bash
   rm -rf ~/chrome-debug-profile/Singleton*
   ```
2. Execute the script:
   ```bash
   .venv/bin/python antigrav_agent.py
   ```
3. Type your instructions. The agent will call tools, read pages, perform actions, and stream thoughts and tool calls live.
4. **Streaming**: You will see `[thinking] ...` for model reasoning and `[tool] tool_name(args)` each time the agent invokes a browser action.
