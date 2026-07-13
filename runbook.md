# Browser Automation Runbook - Kanban & Handoff

**Source:** `meta-model-cookbook/03_use_cases/08_multi_agent_orchestration/README.md`
**Purpose:** Defines workspace layout, file naming, handoff JSON format, definition of done for multi-agent browser automation.

---

## Workspace Layout

```
muse-spark-python/
├── STATE.md - Working memory (Goal, Decisions, Task Graph, File Map, Current Step, Open Questions)
├── browser_core_v2.py - Core with cookbook patterns (normalized coords, retry, stuck detection, image retention, verified fill)
├── ente_auth_ocr_secure_v3.py - Ente Auth v3 with normalized coords + verified fill + secure handling
├── canvas_login_secure_v2.py - Canvas login v2 with retry + stuck detection + oracle
├── canvas_verify_final.py - Final verification grades + assignments
├── restore_browser_automation_clean.py - Full flow CDP + stealth + Canvas + Perplexity + Ente permissions
├── perplexity_restore_secure.py - Perplexity login + radar chart
├── chrome_cdp_connector.py - CDP real Chrome Profile 1
├── .env - Credentials gitignored, chmod 600, CANVAS_USERNAME, CANVAS_PASSWORD, GMAIL_USERNAME, GMAIL_PASSWORD
├── docs/browser_skills/ - Guides: ENTE_AUTH_ACCESS, FUTURE_AGENT_GUIDE, RESTORATION_PROMPT, COOKBOOK_BENEFITS, etc.
├── meta-model-cookbook/ - Local cookbook repo
├── COOKBOOK_INTEGRATION_GUIDE.md - How Spark + Antigravity should leverage cookbook
├── docs/COOKBOOK_ASSESSMENT.md - Detailed pattern mapping
├── radar_chart_* - Generated radar chart files
└── runbook.md - This file, Kanban & handoff definition
```

## File Naming

- `browser_core_v2.py` - Versioned core, incorporates cookbook patterns
- `*_v2.py`, `*_v3.py` - Iterative improvements with version suffix
- `*_secure.py` - Secure handling (masked logs, delete temp files, code=None)
- `canvas_*.png` - Screenshots with course ID: `canvas_grades_87710.png`, `canvas_assignments_87710.png`
- `perplexity_*.png` - Perplexity screenshots: `perplexity_radar_final.png`, `perplexity_restore_step1_home.png`
- `restore_*.png` - Restoration flow screenshots: `restore_canvas_verification.png`
- `STATE.md` - Working memory, single file at root
- `radar_chart_*` - Generated radar chart: png, pdf, csv, ascii, mermaid

## Kanban Board - Task Decomposition

Break complex restoration into dependent tasks with parent_id/child_id, assignee roles, and handoff via comments.

### Task Format

```json
{
  "id": "task_1_canvas_grades",
  "parent_id": null,
  "title": "Verify Canvas grades via API with retry",
  "assignee": "backend",
  "status": "completed|in_progress|pending|blocked",
  "dependencies": [],
  "handoff_format": "See below",
  "definition_of_done": "Courses API returns 200 with 2 courses 87710 and 86815, grades parsed, screenshot saved",
  "files_touched": ["canvas_verify_final.py", "canvas_v2_verification.png"]
}
```

### Example Kanban for Full Restoration

**Task 1: Chrome Stealth Launch**
- ID: `task_1_chrome_stealth`
- Parent: None
- Assignee: `backend` (Playwright)
- Status: `completed`
- Dependencies: []
- DoD: Debug profile launched with stealth args `["--disable-blink-features=AutomationControlled"]`, no Singleton lock error, URL `https://canvas.jccc.edu/` Dashboard, not Microsoft login
- Handoff: `{"profile": "~/chrome-debug-profile", "url": "https://canvas.jccc.edu/", "title": "Dashboard", "logged_in": true}`

**Task 2a: Canvas Grades (Parallel with 2b, 2c)**
- ID: `task_2a_canvas_grades`
- Parent: `task_1_chrome_stealth`
- Assignee: `backend`
- Status: `completed`
- Dependencies: [`task_1_chrome_stealth`]
- DoD: Courses API `/api/v1/courses?enrollment_state=active` returns 200 list len 2, grades `A 99.64%` and `94.58%` parsed via `fetch_with_retry`, screenshot `canvas_v2_verification.png`
- Handoff: `{"courses": [{"id":87710, "name":"BLAW-261-353", "grade":"A 99.64% current 63.47% final"}, {"id":86815, "name":"MKT-230-353", "grade":"None 94.58% current"}], "oracle": "courses_api_200_len_2", "retries": 0}`

**Task 2b: Canvas Assignments Due (Parallel)**
- ID: `task_2b_canvas_assignments`
- Parent: `task_1_chrome_stealth`
- Assignee: `backend`
- Status: `completed`
- Dependencies: [`task_1_chrome_stealth`]
- DoD: Assignments API `/api/v1/courses/{id}/assignments?per_page=100&bucket=upcoming` with retry, filter by `due_at` between now and now+3days, find `Discussion Assigment - Unit 04 due 2026-07-16T04:59:59Z`
- Handoff: `{"due_soon": [{"course_id":87710, "name":"Discussion Assigment - Unit 04", "due_at":"2026-07-16T04:59:59Z", "due_local":"July 15 11:59 PM CDT"}], "oracle": "assignment_bucket_upcoming_filtered", "cutoff":"3_days"}`

**Task 2c: Perplexity Check (Parallel)**
- ID: `task_2c_perplexity_check`
- Parent: `task_1_chrome_stealth`
- Assignee: `frontend`
- Status: `completed`
- Dependencies: [`task_1_chrome_stealth`]
- DoD: Navigate `perplexity.ai`, check Sign In button visibility, screenshot `restore_perplexity_check.png`, verify radar chart files exist `radar_chart_*.png/pdf/csv/ascii/mermaid`
- Handoff: `{"perplexity_url": "https://www.perplexity.ai/", "logged_in": false, "files": ["radar_chart_antigravity_vs_muse_spark.png 456K", "radar_chart_data.csv 880B"], "scores": {"antigravity":[7,8,9,8,8,9,9,8], "Muse":[9,9,6,10,7,8,8,9]}}`

**Task 3a: Ente Auth Permissions (After Task 1)**
- ID: `task_3a_ente_permissions`
- Parent: `task_1_chrome_stealth`
- Assignee: `vision`
- Status: `completed`
- Dependencies: [`task_1_chrome_stealth`]
- DoD: `screencapture -x /tmp/test.png` works (Screen Recording granted), `osascript` System Events works (Accessibility granted), Ente PID 40595, window 873,30 596,779, normalized [606,33] size [413,865], DB exists 16384 bytes encrypted
- Handoff: `{"screen_recording": true, "accessibility": true, "ente_pid":40595, "window_pixel":[873,30,596,779], "window_normalized":[606,33,413,865], "db_size":16384, "method":"OCR possible"}`

**Task 3b: Ente Auth OCR (After 3a)**
- ID: `task_3b_ente_ocr`
- Parent: `task_3a_ente_permissions`
- Assignee: `backend`
- Status: `completed`
- Dependencies: [`task_3a_ente_permissions`]
- DoD: `open -a "Ente Auth"` + activate + get window pos + `screencapture -x` 3.6M + PIL crop with dynamic scale detection (not hardcoded 2) to 91K-1134x1558 + tesseract OCR digits-only strict regex `\d{6}` finds 8-12 codes, masked logs `******`, temp files deleted, code=None after use
- Handoff: `{"codes_found": 10, "codes_masked": ["******", "******"], "ocr_method":"tesseract digits-only strict regex", "scale_detected":2.0, "security":{"masked_logs":true, "temp_deleted":true, "code_cleared":true}}`

**Task 4: Perplexity Login + Radar Regeneration (After 2c, if not logged in)**
- ID: `task_4_perplexity_login_radar`
- Parent: `task_2c_perplexity_check`
- Assignee: `frontend`
- Status: `completed`
- Dependencies: [`task_2c_perplexity_check`]
- DoD: Sign In → Continue with Google → fill Gmail from .env masked + password masked → 2FA challenge totp wait 60s polling URL change → back to Perplexity logged in after 18s → send radar prompt → streaming wait until body >6000 chars → screenshot `perplexity_radar_final.png` 163K + generate local files via matplotlib png 456K pdf 19K csv 880B ascii 535B mermaid 330B
- Handoff: `{"perplexity_logged_in": true, "login_time": "18s", "radar_prompt": "Create detailed radar chart...", "response_chars": 7438, "files_generated": ["radar_chart_antigravity_vs_muse_spark.png", "radar_chart_data.csv"], "oracle": "body_contains_radar_antigravity_len>6000"}`

**Task 5: Documentation Update (After All)**
- ID: `task_5_docs_update`
- Parent: `task_2a_canvas_grades`, `task_2b_canvas_assignments`, `task_2c_perplexity_check`, `task_3b_ente_ocr`, `task_4_perplexity_login_radar`
- Assignee: `tech_writer`
- Status: `completed`
- Dependencies: All above
- DoD: Update `ENTE_AUTH_ACCESS.md` with permission fix (granted), `FUTURE_AGENT_GUIDE.md` with July 13 update + cookbook patterns, `STATE.md` with current step, `COOKBOOK_ASSESSMENT.md` + `COOKBOOK_BENEFITS.md` + `runbook.md`
- Handoff: `{"docs_updated": ["ENTE_AUTH_ACCESS.md", "FUTURE_AGENT_GUIDE.md", "STATE.md", "COOKBOOK_ASSESSMENT.md", "COOKBOOK_BENEFITS.md", "runbook.md"], "patterns_implemented": 7}`

---

## Handoff Formats - Strict JSON (from alert_fatigue_copilot pattern)

Use strict JSON, no markdown fences, validate via Python regex/Counter, strip fences, extract first balanced `{}`.

### TOTP Handoff (Ente Auth → Canvas MFA)

```json
{
  "code_length": 6,
  "code_masked": "******",
  "expires_in": 25,
  "source": "ente_auth_ocr_v3",
  "account_filter": "Microsoft",
  "account_matched": true,
  "filter_in_image": false,
  "codes_found": 10,
  "ocr_method": "tesseract --psm 6 --oem 3 -c tessedit_char_whitelist=0123456789",
  "scale_detected": 2.0,
  "window_pixel": [873, 30, 596, 779],
  "window_normalized": [606, 33, 413, 865],
  "security": {
    "masked_logs": true,
    "temp_files_deleted": ["/tmp/ente_full_v3.png", "/tmp/ente_cropped_v3.png"],
    "code_cleared_from_memory": true,
    "actual_code_never_logged": true
  },
  "verification": {
    "fill_method": "playwright fill()",
    "verify_method": "evaluate() reading back value",
    "verified": true
  },
  "oracle": "mfa_input_filled_and_verified"
}
```

**Never include actual code in handoff file**, only masked and metadata. Code passed via memory only, cleared after use.

### Canvas Grades Handoff (Canvas API → Docs)

```json
{
  "courses": [
    {
      "id": 87710,
      "name": "BLAW-261-353 - 60844.202606",
      "current_grade": "A",
      "current_score": 99.64,
      "final_score": 63.47,
      "enrollment": {"user_id": 257408, "type": "StudentEnrollment"}
    },
    {
      "id": 86815,
      "name": "MKT-230-353 - 60650.202606",
      "current_grade": null,
      "current_score": 94.58,
      "final_score": 63.15
    }
  ],
  "api_calls": [
    {"endpoint": "/api/v1/courses?enrollment_state=active", "status": 200, "time_ms": 166.7, "retries": 0},
    {"endpoint": "/api/v1/courses/87710/enrollments?user_id=self", "status": 200, "retries": 0},
    {"endpoint": "/api/v1/courses/86815/enrollments?user_id=self", "status": 200, "retries": 0}
  ],
  "oracle": "courses_api_200_len_2_grades_parsed",
  "screenshot": "canvas_v2_verification.png",
  "tokens_estimated": 584,
  "window_safe": true
}
```

### Perplexity Radar Handoff

```json
{
  "perplexity_url": "https://www.perplexity.ai/",
  "logged_in": true,
  "login_method": "Gmail OAuth",
  "login_time_seconds": 18,
  "2fa_method": "challenge/totp",
  "radar_prompt": "Create a detailed radar chart comparing Antigravity Agentic Browser vs Muse Spark 1.1 across 8 dimensions...",
  "response_chars": 7438,
  "files": {
    "radar_chart_antigravity_vs_muse_spark.png": {"size": 462600, "exists": true},
    "radar_chart_antigravity_vs_muse_spark.pdf": {"size": 19540, "exists": true},
    "radar_chart_data.csv": {"size": 880, "exists": true, "dimensions": ["Speed","Tool Reliability","Persistent Chrome","Memory","Ease Setup","Cost","Browser Fidelity","Task Accuracy"]},
    "radar_chart_ascii.txt": {"size": 535, "exists": true},
    "radar_chart_mermaid.md": {"size": 330, "exists": true, "type": "xychart-beta"},
    "perplexity_radar_final.png": {"size": 163676, "exists": true}
  },
  "scores": {
    "antigravity": [7,8,9,8,8,9,9,8],
    "claude_spark": [9,9,6,10,7,8,8,9]
  },
  "oracle": "body_contains_radar_antigravity_len_7438_gt_6000",
  "screenshot": "perplexity_radar_final.png"
}
```

### Ente Auth Permissions Handoff

```json
{
  "ente_app": "/Applications/Ente Auth.app",
  "pid": 40595,
  "running": true,
  "db_path": "~/Library/Containers/io.ente.auth.mac/Data/Library/Application Support/io.ente.auth.mac/ente.authenticator.db",
  "db_exists": true,
  "db_size": 16384,
  "db_encrypted": true,
  "window": {
    "pixel": [873, 30, 596, 779],
    "normalized": [606, 33, 413, 865],
    "logical_screen": [1440, 900],
    "physical_screenshot": [2880, 1800],
    "scale_detected": 2.0,
    "title": "Ente Auth"
  },
  "permissions": {
    "screen_recording": {"granted": true, "test": "screencapture -x /tmp/test.png 3.6M OK"},
    "accessibility": {"granted": true, "test": "osascript System Events get window pos OK"}
  },
  "flutter": {
    "is_flutter": true,
    "accessibility_tree_empty": true,
    "workaround": "screenshot + OCR"
  },
  "ocr": {
    "tesseract_binary": "/opt/homebrew/bin/tesseract",
    "tesseract_installed": true,
    "pytesseract": true,
    "pillow": true,
    "test": "cropped 91K-1134x1558 OCR found 10 codes masked"
  },
  "methods": {
    "method_1_manual": {"available": true, "secure": true, "requires_user": true},
    "method_2_ocr": {"available": true, "secure": true, "requires_permissions": true, "auto_fill": true},
    "method_3_db": {"available": false, "reason": "encrypted"},
    "method_4_cli": {"available": false, "ente_cli": null}
  },
  "oracle": "screen_recording_granted_and_accessibility_granted_and_ocr_10_codes"
}
```

---

## Definition of Done

### For Canvas Grades Task

- [ ] Chrome launched with stealth args, no Singleton lock error
- [ ] URL `https://canvas.jccc.edu/` Dashboard, not Microsoft login (or auto-filled via Ente)
- [ ] Courses API `fetch_with_retry` returns 200 list len 2 with retries 0 (or retries logged if 429)
- [ ] Grades parsed: BLAW A 99.64% final 63.47%, MKT 94.58% final 63.15%
- [ ] Screenshot `canvas_v2_verification.png` saved
- [ ] STATE.md Current Step updated with grades
- [ ] Tokens estimated, 1M window safe
- [ ] Oracle verified: `courses_api_200_len_2_grades_parsed`

### For Ente Auth OCR Task

- [ ] Screen Recording permission test `screencapture -x` success
- [ ] Accessibility permission test `osascript` System Events success
- [ ] Ente window pos fetched via AppleScript, normalized coords calculated
- [ ] Screenshot via `screencapture -x` 3.6M, crop with dynamic scale detection (not hardcoded 2), cropped 91K-1134x1558
- [ ] OCR via tesseract digits-only strict regex `\d{6}` finds codes, deduplicated, masked logs `******`
- [ ] Temp files deleted immediately after OCR
- [ ] Code variable cleared after use `code=None`
- [ ] Verified fill: fill via Playwright + verify via evaluate different method
- [ ] Oracle: `ocr_10_codes_masked_and_verified_fill`

### For Perplexity Radar Task

- [ ] Navigate `perplexity.ai`, check Sign In visibility
- [ ] If not logged in: Gmail OAuth with .env masked + password masked + 2FA challenge polling URL change 60s
- [ ] Send radar prompt, streaming wait until body len >6000 chars
- [ ] Screenshot `perplexity_radar_final.png`
- [ ] Generate local files via matplotlib: png 456K, pdf 19K, csv 880B, ascii 535B, mermaid 330B with scores [7,8,9,8,8,9,9,8] vs [9,9,6,10,7,8,8,9]
- [ ] Oracle: `body_contains_radar_antigravity_len_gt_6000`

---

## Error Handling & Rework

### When Verification Fails

Create rework task with file name + line number, parent_id pointing to failed task.

**Example: Ente OCR fails 0 codes**

- Failed task: `task_3b_ente_ocr` - OCR found 0 codes
- Rework task:
  - ID: `task_3b_ente_ocr_rework`
  - Parent: `task_3b_ente_ocr`
  - Title: "Ente OCR rework - capture both Ente + Chrome windows for diagnosis"
  - Assignee: `vision`
  - Action: `screencapture -x /tmp/full.png` + crop both Ente window + Chrome MFA window, save as `ente_failure_full.png` + `chrome_mfa.png`, feed together to model to diagnose mismatch (from `02_screenshot_bugfix` two-screenshot pattern)
  - Possible causes: Ente window minimized, user didn't search Microsoft, retina crop wrong region, tesseract not installed
  - Fix: If filter not in image, ask user to search "Microsoft" in Ente Auth before re-run; if scale wrong, re-detect scale dynamically; if minimized, activate window first

**Example: Canvas API 429 rate limit**

- Failed task: `task_2a_canvas_grades` - API error 429
- Rework: `fetch_with_retry` already handles with exponential backoff 1s→8s, 10 retries. If still fails after retries, create rework task to wait 60s and retry once more, or reduce per_page from 20 to 10, or add delay between calls.

### Stuck Detection

Track `hash(tool_name + args)` repeated 3x → try alternative selector.

In `canvas_login_secure_v2.py`, we try multiple selectors for email field:
```python
email_selectors = ["input[type='email']", "input[name='loginfmt']", "#i0116"]
for sel in email_selectors:
  if detector.check("email_fill", sel): continue # Skip if stuck on this selector 3x
  try: loc = page.locator(sel).first; if visible and count>0: fill and break
```

If all selectors fail 3x each, detector will have history of 12 hashes, all count 3, then fallback to manual.

---

## Security

- .env gitignored, chmod 600, never logged, only masked `username[:3]***` and `len(password)` 
- TOTP codes: never logged plain, masked `******`, temp files deleted immediately, code=None after use, 30s expiry low risk
- Screenshots: may contain codes temporarily, but deleted immediately after OCR, not committed to git (`.gitignore` should include `/tmp/ente_*.png` and `*verification.png`? Actually keep verification screenshots for debugging but ensure no codes visible)
- No hardcoding credentials in code, use `os.environ.get()`

---

## How to Use This Runbook

1. **Before starting complex task:** Read `STATE.md` for Goal, Key Decisions, File Map, Current Step
2. **Create Kanban tasks:** Use Task format above, set parent_id dependencies
3. **For each task:** Follow Definition of Done, produce handoff JSON (strict, no fences, validated via Python)
4. **On failure:** Create rework task with parent_id, file name + line number, diagnosis via two-screenshot pattern
5. **After completion:** Update `STATE.md` Current Step + Task Graph, update docs in `docs/browser_skills/`
6. **For future agent:** This runbook defines workspace layout + handoff format, so subagents know where to find credentials, profiles, window positions, etc.

---

## References

- `meta-model-cookbook/03_use_cases/08_multi_agent_orchestration/README.md` - Kanban board, runbook.md, SOUL.md, parent_id/child_id, clarify tool, block needs_input
- `02_agent_patterns/05_alert_fatigue_copilot/README.md` - Strict JSON validation via `validate_alert_output.py`, strip fences, extract balanced `{}`, verify via Counter/regex not trusting model hallucination
- `01_api_fundamentals/05_prompt_caching.ipynb` - Stable prefix first, volatile last, cache_key, cached_tokens tracking
- `03_use_cases/13_macos_cua/python/metacua/ {agent.py, llm.py, system_prompt.py}` - Normalized coords, batched actions, image retention, verified use, retry with backoff
