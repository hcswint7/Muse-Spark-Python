# Orchestration Plan - Canvas + Perplexity Multi-Task Browser Agent

## User Intent
User asks for 3 sequential browser tasks requiring high-trial/error learning, plus creation of persistent documentation for future agents.

### Tasks Ordered as Requested:
1. **Canvas Grades**: Access canvas.jccc.edu, scroll, tell grades for both classes (86815 and 87710 from history)
2. **Perplexity Radar Chart**: Send message in browser asking to create radar chart comparing Antigravity Agentic Browser use vs Muse Spark 1.1
3. **Canvas Due Assignments**: Access Canvas again separately, note assignments due in next 3 days

User also wants:
- Click "I am not a robot" whenever prompted (CAPTCHA handling)
- Learn Chrome browser processes and make easier for self via trial/error
- Document refined skills into multiple docs + memorize screen placements
- Break into three parts and return once finished with one task, then write notes
- If cannot access Canvas/Perplexity, will add login to env/script

## Security & Policy Constraints

### CAPTCHA / "I am not a robot"
- **Cannot automate bypass of CAPTCHAs** that are designed to block bots. This violates policy against circumventing security.
- What we CAN do:
  - Detect presence of checkbox via `iframe[title*='reCAPTCHA']` or `div.g-recaptcha`
  - Attempt normal click as a regular UI element (if site renders it as standard checkbox)
  - If challenge appears (image selection, Cloudflare Turnstile failure, etc), PAUSE and request human intervention in the visible Chrome window
  - Log location and pattern for future reference
- Documentation will state: **Never use 3rd party CAPTCHA solver services, never attempt to bypass. Request human.**

### Credential Handling
- User suggested adding logins to env. **We must NOT encourage plaintext passwords in .env or scripts.**
- Preferred approach:
  1. Use existing persistent Chrome profile `~/chrome-debug-profile` which already has cookies for canvas.jccc.edu and perplexity.ai (evidenced via History SQLite)
  2. If session expired, instruct user to manually log in in the opened Chrome window, then agent continues (session will be saved)
  3. If automation requires login, use environment variable only for API keys, not passwords. Document secure alternative (e.g., manual login)
- We will not read or exfiltrate password fields.

### Privacy
- Canvas grades are private FERPA data. Only process when explicitly requested by owner.
- Do not store grades in docs, only show in task output unless user asks to persist.

## Execution Strategy: 3 Phases with Note-Taking Gate

### Phase 0: Baseline Refinement (Done with Google test)
- Learned `input:near(:text)` fails for Google, resolves to hidden file inputs
- Fixed with robust selector list: `textarea[name='q']`, `input[name='q']`, `combobox` role, `aria-label*='Search'`
- Learned `page.wait_for_timeout` needed after `goto` and fill + Enter
- Learned persistent context requires deleting SingletonLock files after crash/timeout
- Learned to expand logging: print `page.url`, `page.title`, full action JSON

### Phase 1: Task 1 - Canvas Grades
**Goal**: Extract grades from canvas.jccc.edu/courses/86815 and canvas.jccc.edu/courses/87710

**Steps:**
1. Launch persistent context with `CHROME_PROFILE_DIR=~/chrome-debug-profile` executable `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` headless=False
2. Navigate to `https://canvas.jccc.edu/` - check if authenticated (look for Dashboard, Courses, or Login page)
3. If redirected to `login/saml` or JCCC SSO, PAUSE and ask user to manually log in within the visible Chrome window. Then resume.
4. Once on Dashboard:
   - Click `Courses` → scroll list
   - For each course ID, navigate to `/courses/{id}/grades`
   - Extract grade table: use `page.locator("body").inner_text()` and specific locators `table#grades`, `span.grade`, etc.
   - Take screenshot `canvas_grades_{id}.png`
5. Return result to user
6. Write notes to `docs/browser_skills/canvas_grades.md`

**Risks:**
- Canvas uses heavy SPA React, dynamic loading - need `wait_for_load_state('networkidle')` and scroll
- Grades page may be behind auth check - handle redirect

### Phase 2: Task 2 - Perplexity Radar Chart
**Goal**: Send message to Perplexity asking for radar chart

**Steps:**
1. Reuse same Chrome context (do not close between tasks for efficiency, but per user request "separately" for Task 3 we will do separate launches)
2. Navigate to `https://www.perplexity.ai/` - check auth (Perplexity allows anonymous, but history shows logged-in searches)
3. Locate input: Perplexity uses `textarea[placeholder*='Ask']` or `div[contenteditable='true']` - test both
4. Fill: "Create a radar chart comparing Antigravity Agentic Browser use to Muse Spark 1.1 across dimensions: speed, tool calling, persistent Chrome handling, memory, ease of setup, cost, browser fidelity, task completion. Include data table and rationale."
5. Press Enter, wait 10-15s for generation (Perplexity streaming)
6. Extract final text + note if chart rendered (canvas/svg)
7. Screenshot `perplexity_radar.png`
8. Document in `docs/browser_skills/perplexity_automation.md`

**Selectors learned from trial/error:**
- Do NOT use `input:near` - use `get_by_placeholder`, `get_by_role('textbox')`, `locator('textarea').last`
- Perplexity's send button: `button[aria-label*='Send']`, `button:has-text('Ask')`

### Phase 3: Task 3 - Canvas Due Assignments Next 3 Days
**Goal**: List assignments due in next 3 days for both classes

**Steps:**
1. **Separate launch** per user request: close previous context, delete Singleton locks, relaunch fresh
2. Navigate to Canvas Dashboard → check `To Do` sidebar or `/courses/{id}/assignments?filter=upcoming` or `/courses/{id}/calendar`
3. For robust due-date detection:
   - Use Canvas API via browser: fetch `/api/v1/courses/86815/assignments?bucket=upcoming` via `page.evaluate(() => fetch(...))` if UI fails (still within same origin, authenticated)
   - Else scrape assignment list and parse dates with regex
4. Filter to assignments due within 3 days from `datetime.now()`
5. Screenshot and return list
6. Document in `docs/browser_skills/canvas_assignments.md`

## Note-Taking Protocol
- After each Task, immediately write file: `docs/browser_skills/task_{N}_learnings.md`
- Include: selectors that worked, timing issues, screen placements (e.g., Canvas left nav 72px width, courses at `#courses`, Perplexity input at bottom center 60% width)
- After all tasks, consolidate into `docs/browser_skills/FUTURE_AGENT_GUIDE.md` with tips/tricks and memorized placements

## Improved Browser Agent Design (for refinement)

Current `agent_step.py` limitations:
- Only 4 actions: goto, click_text (by visible text, fragile), fill_text (fixed selector), done
- No scroll, no wait_for_selector, no screenshot, no evaluate

Proposed v2 actions:
- `goto`, `click_text`, `click_selector`, `fill_selector`, `press_key`, `scroll`, `wait_for`, `screenshot`, `get_text`, `evaluate`, `done`
- Use multiple fallback locators per action, log which succeeded
- Add `page.wait_for_load_state('domcontentloaded')` after each navigation

Will implement improved version as `agent_step_v2.py` for high trial/error testing.

## Success Criteria
- Task 1: Return grades text + screenshot, no password stored
- Task 2: Perplexity response captured, radar chart requested
- Task 3: Due assignments list with dates within 3 days, separate launch evidenced
- Docs: 5+ markdown files in `docs/browser_skills/` with actionable tips
