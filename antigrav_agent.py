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
    """Clicks the first visible button, link, or element containing the specified text.
    Tries role-based locators first, then falls back to text match, with scrolling into view."""
    global page
    try:
        locator = page.get_by_role("button", name=text, exact=False).first
        if await locator.count() > 0 and await locator.is_visible():
            await locator.scroll_into_view_if_needed()
            await locator.click(timeout=5000)
            await page.wait_for_timeout(1500)
            return f"Successfully clicked button with text: '{text}'"
    except Exception:
        pass

    try:
        locator = page.get_by_role("link", name=text, exact=False).first
        if await locator.count() > 0 and await locator.is_visible():
            await locator.scroll_into_view_if_needed()
            await locator.click(timeout=5000)
            await page.wait_for_timeout(1500)
            return f"Successfully clicked link with text: '{text}'"
    except Exception:
        pass

    try:
        locator = page.locator(f"button:has-text('{text}'), a:has-text('{text}'), [role='option']:has-text('{text}'), [tabindex]:has-text('{text}')").first
        if await locator.count() > 0:
            await locator.scroll_into_view_if_needed()
            await locator.click(timeout=5000)
            await page.wait_for_timeout(1500)
            return f"Successfully clicked element with text: '{text}'"
    except Exception:
        pass

    try:
        locator = page.get_by_text(text).first
        await locator.scroll_into_view_if_needed()
        await locator.click(timeout=5000)
        await page.wait_for_timeout(1500)
        return f"Successfully clicked element with text: '{text}'"
    except Exception as e:
        return f"Failed to click element with text '{text}': {e}"

async def fill_input_field(label_or_placeholder: str, text_to_type: str) -> str:
    """Fills an input box or text field with the given text.
    Tries placeholder, label, aria-label, then near-text fallback."""
    global page
    strategies = [
        page.get_by_placeholder(label_or_placeholder),
        page.get_by_label(label_or_placeholder),
        page.get_by_role("textbox", name=label_or_placeholder),
        page.locator(f"textarea:near(:text('{label_or_placeholder}'))"),
        page.locator(f"input:near(:text('{label_or_placeholder}'))"),
        page.locator(f"[aria-label*='{label_or_placeholder}']"),
    ]
    for locator in strategies:
        try:
            input_el = locator.first
            if await input_el.count() > 0 and await input_el.is_visible():
                await input_el.click(timeout=2000)
                await input_el.fill(text_to_type, timeout=3000)
                return f"Successfully filled '{label_or_placeholder}' field with '{text_to_type}'"
        except Exception:
            continue

    return f"Failed to fill field '{label_or_placeholder}': could not find a visible input, textarea, or textbox matching that label or placeholder."

async def read_page_content() -> str:
    """Extracts and returns the visible text content of the active page,
    prefixed with the page title and URL."""
    global page
    try:
        title = await page.title()
        current_url = page.url
        text = await page.locator("body").inner_text(timeout=2000)
        snippet = text[:4000]
        return f"Page title: {title}\nURL: {current_url}\n---\n{snippet}"
    except Exception as e:
        return f"Failed to read page content: {e}"

async def scroll_page(direction: str) -> str:
    """Scrolls the page in the given direction. Valid directions: down, up, down, up, bottom, top."""
    global page
    valid = {"down", "up", "bottom", "top"}
    direction = direction.strip().lower()
    if direction not in valid:
        return f"Invalid direction '{direction}'. Choose from: {', '.join(sorted(valid))}"
    try:
        if direction == "bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(500)
            return "Scrolled to the bottom of the page."
        elif direction == "top":
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            return "Scrolled to the top of the page."
        elif direction == "down":
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await page.wait_for_timeout(500)
            return "Scrolled down one viewport height."
        elif direction == "up":
            await page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
            await page.wait_for_timeout(500)
            return "Scrolled up one viewport height."
    except Exception as e:
        return f"Failed to scroll {direction}: {e}"

async def go_back() -> str:
    """Navigates the browser back one page in history."""
    global page
    try:
        await page.go_back(timeout=10000)
        await page.wait_for_load_state("networkidle", timeout=5000)
        return f"Navigated back. Title is now: '{await page.title()}'"
    except Exception as e:
        return f"Failed to go back: {e}"

async def press_key(key: str) -> str:
    """Presses a keyboard key. Common values: Enter, Escape, Tab, ArrowDown, ArrowUp, ArrowLeft, ArrowRight, Backspace, Delete, etc."""
    global page
    try:
        await page.keyboard.press(key)
        await page.wait_for_timeout(500)
        return f"Pressed key: '{key}'"
    except Exception as e:
        return f"Failed to press key '{key}': {e}"

async def take_screenshot() -> str:
    """Takes a screenshot of the current page and saves it as a PNG file. Returns the file path."""
    global page
    try:
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="antigrav_screenshot_")
        path = f.name
        f.close()
        await page.screenshot(path=path, full_page=False)
        return f"Screenshot saved to: {path}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"

async def get_current_url() -> str:
    """Returns the current URL of the active page."""
    global page
    try:
        return f"Current URL is: {page.url}"
    except Exception as e:
        return f"Failed to get URL: {e}"

async def read_local_file(filepath: str) -> str:
    """Reads a local file. Useful for reading logs, exploration summaries, or .env for credentials."""
    try:
        path = os.path.expanduser(filepath)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Truncate to avoid blowing up context window
        return f"File '{filepath}' contents:\n{content[:5000]}"
    except Exception as e:
        return f"Failed to read file '{filepath}': {e}"

# --- MAIN AGENT LOOP ---

async def run_agent_loop():
    global browser, page

    # Load exploration summary for context if it exists
    exploration_context = ""
    try:
        with open(os.path.expanduser("~/muse-spark-python/browser_exploration_summary.txt"), "r") as f:
            exploration_context = f"\n\nPAST EXPLORATION MEMORY:\n{f.read()}"
    except Exception:
        pass

    # Configure the Google Antigravity Agent
    config = LocalAgentConfig(
        model="gemini-3.5-flash",
        api_key=api_key,
        system_instructions=(
            "You are an autonomous browser agent. Your goal is to help the user complete tasks "
            "on their browser. You can navigate, click, fill inputs, scroll, go back, press keys, "
            "take screenshots, and read pages. Use the tools provided to explore the page and "
            "progress the task. When you have finished the task successfully, state what you did "
            "and conclude." + exploration_context
        ),
        tools=[
            navigate_to,
            click_element_with_text,
            fill_input_field,
            read_page_content,
            scroll_page,
            go_back,
            press_key,
            take_screenshot,
            get_current_url,
            read_local_file,
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
            print(f"[!] Failed to launch Chrome with profile '{user_data_dir}': {e}")
            print("Try running: rm -rf ~/chrome-debug-profile/Singleton*")
            print("Or quit Chrome completely (Cmd+Q) and retry.")
            return

        page = browser.pages[0] if browser.pages else await browser.new_page()
        print("Browser successfully connected!")
        print("Type your task at the prompt (e.g. 'Search for recent technology news on google.com')")
        print("Type 'exit' to quit.\n")

        # Instantiate the Antigravity Agent - runs as async context manager
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

                print(f"\n[Agent working on: '{user_task}']\n")

                response = await agent.chat(user_task)
                text_parts = []
                async for chunk in response.chunks:
                    if isinstance(chunk, ag_types.Thought):
                        print(f"\n[thinking] {chunk.text}", end="", flush=True)
                    elif isinstance(chunk, ag_types.Text):
                        print(chunk.text, end="", flush=True)
                        text_parts.append(chunk.text)
                    elif isinstance(chunk, ag_types.ToolCall):
                        args_str = str(chunk.args)
                        print(f"\n[tool] {chunk.name}({args_str})", flush=True)

                final_text = "".join(text_parts)
                if final_text.strip():
                    print(f"\n[Agent Finished]")

        await browser.close()

def main():
    asyncio.run(run_agent_loop())

if __name__ == "__main__":
    main()
