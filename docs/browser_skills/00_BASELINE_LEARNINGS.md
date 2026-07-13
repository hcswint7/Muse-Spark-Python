# Baseline Learnings - Google Search Trial

## Date: 2026-07-13 (from previous run)

### What Was Tested
Ran `agent_step.py "go to google.com and search for the weather in New York"`

### Failures Observed & Fixes
1. **CHROME_PROFILE_DIR env var with ${HOME} literal**
   - `.env` had `CHROME_PROFILE_DIR="${HOME}/Library/Application Support/Google/Chrome"`
   - `os.path.expanduser` does NOT expand `${HOME}`. It stays literal.
   - Fix: Override env var at launch: `CHROME_PROFILE_DIR="$HOME/chrome-debug-profile"`
   - Future tip: Use `os.path.expandvars(os.path.expanduser(...))` in code

2. **SingletonLock after timeout**
   - Persistent context doesn't close on timeout/kill, leaves lock files: `SingletonLock`, `SingletonCookie`, `SingletonSocket` in profile dir
   - Next launch fails with "Chrome is already running"
   - Fix: `rm ~/chrome-debug-profile/Singleton*` before launch + `pkill -f agent_step.py`

3. **fill_text locator `input:near(:text('Search'))` fails**
   - Resolved to hidden file input `<input hidden type="file" accept="image/...">` on Google
   - Playwright error: `element is not visible`
   - Fix implemented:
     ```python
     locators_to_try = [
        "textarea[name='q']",
        "input[name='q']",
        "textarea[aria-label*='Search' i]",
        "input[aria-label*='Search' i]",
        "input[type='search']"
     ]
     # try role first
     page.get_by_role("combobox", name="Search").first.fill(value)
     # then loop selectors
     # then fallback near logic
     # press Enter after fill
     ```

4. **Output buffering hides logs**
   - Original bash call had no `-u` flag, no output until timeout
   - Fix: `python -u` unbuffered + `PYTHONUNBUFFERED=1`

5. **Model loops after successful search**
   - After search, model did `goto https://www.google.com` again instead of `done`
   - Cause: page_text snippet only 3000 chars, may not show weather widget clearly
   - Fix: Increase snippet? Add check for final URL containing `search?q=` as success signal in prompt

### Success After Fix
```
Action1 goto https://www.google.com → title Google
Action2 fill_text Search=weather in New York → navigates to https://www.google.com/search?q=weather+in+New+York...
Action3 done → reports "82°F, Mostly sunny"
```

### Screen Placements Memorized - Google
- Logo centered top 40%
- Search box: textarea centered, `name='q'`, height ~56px, width ~582px, `aria-label='Search'`
- Search box is combobox role, not plain input near text
- Search button below or hidden; pressing Enter is more reliable than clicking button

### Tips for Future Agents
- ALWAYS press Enter after filling search, don't look for button
- NEVER rely solely on `get_by_text` for inputs; inputs have no text, use placeholder, name, aria-label, role
- Add `page.wait_for_timeout(1500)` after goto, `2000` after fill+Enter
- Log `page.url` and `page.title` after each action for debugging
- Delete Singleton locks before launch
- Use `~/chrome-debug-profile` not main Chrome profile to avoid corrupting main browser
