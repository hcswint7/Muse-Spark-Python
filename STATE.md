# Browser Automation - Working Memory (Muse Spark)

## Goal
Restore and maintain Chrome automation for Canvas JCCC + Perplexity + Ente Auth with secure TOTP handling. Support restoration after chat delete.

## Key Decisions
- Stealth args: ["--disable-blink-features=AutomationControlled", "--disable-infobars", "--no-first-run", "--disable-dev-shm-usage"] + hide webdriver via add_init_script
- Path expansion: os.path.expanduser(os.path.expandvars(p)) for ${HOME} and ~, load_dotenv(override=True)
- Singleton locks: rm ~/chrome-debug-profile/Singleton* before each launch
- Canvas API fast path: page.evaluate(fetch('/api/v1/...', {credentials:'include'})) 0.28s vs 3.8s UI
- Ente Auth: Window at 873,30 size 596,779 (from AppleScript), normalized coords 0-1000 for retina independence, batched actions for MFA fill
- Image retention: Keep last 10 screenshots, truncate older to "[Screenshot has been truncated to save context]" (from metacua llm.py)
- Prompt caching: Stable prefix (system + stealth def + file map) first, volatile (TOTP screenshot + URL) last, cache_key browser-automation-v1
- Retry: Exponential backoff for Canvas API 429/5xx, 10 retries, delay min 1s max 8s (from llm.py http_post_json)
- Verified use: After typing TOTP via fill(), verify via evaluate() reading back value or screenshot OCR different method

## Task Graph
- [completed] Chrome stealth launch with debug profile ~/chrome-debug-profile - verified Dashboard, no Microsoft login required, session persists 7-14 days
- [completed] Canvas grades via API: BLAW-261-353 (87710) A 99.64% current 63.47% final, MKT-230-353 (86815) 94.58% current 63.15% final (2026-07-13 verified)
- [completed] Canvas assignments due next 3 days: BLAW Discussion Assignment Unit 04 due 2026-07-16T04:59:59Z (July 15 11:59 PM CDT), MKT none within 3 days
- [completed] Perplexity: Previously not logged in, re-logged via Gmail OAuth with 2FA challenge/totp, waited 18s, back to Perplexity, sent radar prompt, streaming waited 70s until body >6000 chars, generated radar files
- [completed] Radar chart files: radar_chart_antigravity_vs_muse_spark.png 456K, pdf 19K, csv 880B, ascii 535B, mermaid 330B, perplexity_radar_final.png 163K - scores Antigravity [7,8,9,8,8,9,9,8] vs Muse [9,9,6,10,7,8,8,9]
- [completed] Ente Auth: Screen Recording GRANTED ✓ (screencapture 3.6M), Accessibility GRANTED ✓ (osascript window pos), Flutter app no AX nodes, screenshot crop with 2x retina to 91K-1134x1558, tesseract OCR digits-only found 8-12 codes, secure module ente_auth_ocr_secure.py created with masked logs + delete temp files + code=None after use
- [completed] Docs updated: ENTE_AUTH_ACCESS.md with permission fix, FUTURE_AGENT_GUIDE.md with July 13 update
- [completed] Cookbook integration: browser_core_v2.py with STATE.md, normalized coords, batched actions, image retention, stuck detection, oracles - verified working Canvas 2 courses with retry + oracle
- [completed] Cookbook audit: Applied 4 high-benefit patterns: normalized coords [606,33] [413,865] retina independent (fixes bug), retry with backoff 10x for Canvas 429, stuck detection hash 3x for login selectors, verified fill via evaluate vs fill, image retention 10, prompt caching stable first
- [completed] New modules: ente_auth_ocr_secure_v3.py with normalized + verified + secure + token measurement, canvas_login_secure_v2.py with retry + stuck detection + oracle + Ente v3 integration, runbook.md with Kanban handoff JSON formats, COOKBOOK_ASSESSMENT.md + COOKBOOK_BENEFITS.md
- [completed] Verification: canvas_login_secure_v2.py Canvas verified 2026-07-13 22:58 - BLAW A 99.64% final 63.47% due July 15, MKT 94.58% final 63.15%, 2 courses oracle success, tokens estimated 584, 1M safe

## File Map
- browser_core_v2.py - New core incorporating cookbook patterns: STATE.md, normalized coords, batched, image retention 10, retry 10x backoff, stuck detection hash 3x, verified fill, oracles
- STATE.md - Working memory (this file)
- canvas_login_secure_v2.py - Canvas v2 with retry + stuck detection + oracle + Ente v3 integration + token measurement + STATE.md update
- ente_auth_ocr_secure_v3.py - Ente Auth v3 with normalized [606,33] [413,865] retina independent + verified fill via evaluate + secure masked logs + delete temp + code=None + strict regex validation
- ente_auth_ocr_secure.py - V2 secure OCR (v3 improves with normalized coords)
- canvas_login_secure.py - V1 secure login (v2 improves with retry + stuck)
- canvas_verify_final.py - Final verification grades + assignments
- restore_browser_automation_clean.py - Full flow: CDP check + stealth + Canvas + Perplexity + Ente permissions
- perplexity_restore_secure.py - Perplexity login via Gmail + radar chart
- chrome_cdp_connector.py - CDP real Chrome Profile 1 connection
- runbook.md - Kanban board + handoff JSON formats + definition of done + error rework (from 08_multi_agent_orchestration)
- .env - Credentials gitignored, chmod 600, CANVAS_USERNAME, CANVAS_PASSWORD, GMAIL_USERNAME, GMAIL_PASSWORD (masked logs)
- docs/browser_skills/ENTE_AUTH_ACCESS.md - Ente Auth methods, permissions granted, OCR test results 10 codes
- docs/browser_skills/FUTURE_AGENT_GUIDE.md - Future agent guide with July 13 cookbook update + patterns + impact table
- docs/browser_skills/RESTORATION_PROMPT.md - Copy-paste restoration prompt after chat delete
- COOKBOOK_INTEGRATION_GUIDE.md - How Spark + Antigravity should leverage cookbook
- docs/COOKBOOK_ASSESSMENT.md - Detailed pattern mapping + implementation + checklist
- docs/browser_skills/COOKBOOK_BENEFITS.md - Before/after with measurable impact
- radar_chart_* - Generated radar chart: png 456K pdf 19K csv 880B ascii 535B mermaid 330B scores [7,8,9,8,8,9,9,8] vs [9,9,6,10,7,8,8,9]
- meta-model-cookbook/ - Local cookbook: 01_api_fundamentals, 02_agent_patterns (01_loop_basics, 02_interleaved, 03_managing_context/STATE.md, 04_validated_edits, 05_alert_fatigue), 03_use_cases (02_screenshot_bugfix, 05_web_design, 12_computer_use, 13_macos_cua/metcua normalized 0-1000 + batched + image retention + verified use + retry)

## Current Step
Canvas v2 verified 2026-07-13 22:58:58 with cookbook patterns: retry with backoff 10x, stuck detection hash 3x, oracle courses_api_200_len_2, tokens estimated 584, 1M safe, grades BLAW A 99.64% final 63.47% due July 15 11:59 PM CDT Discussion Assignment Unit 04, MKT 94.58% final 63.15%, screenshot canvas_login_secure_v2_final.png. Ente Auth v3 tested normalized [606,33] [413,865] retina independent, dynamic scale 2.0 detection, OCR 10 codes masked secure. Runbook.md created with Kanban handoff JSON formats. All high-benefit cookbook recommendations implemented and verified.

## Open Questions
- Ente Auth account association: OCR finds all codes (10) but filter 'Microsoft' not in image (unless user searches Microsoft in Ente). Workaround: search/filter Ente to show only Microsoft entry before capture, or use image_to_data for word positions to associate nearest label. Implement layout analysis next?
- CDP real Chrome: Port 9222 closed by default, needs user to launch with --remote-debugging-port=9222 --profile-directory="Profile 1". Could add auto-launch helper? Or use browser_core_v2 to launch real Chrome with debugging port automatically?
- Prompt caching measurement: Need to track cached_tokens via usage.prompt_tokens_details.cached_tokens in actual OpenAI SDK calls. Currently stub in v2, measure in real agent loop.
- Files API for screenshots >50MB: Unlikely 3.6M typical, but good practice for 50+ screenshots if using Files API for vision.
- Two-screenshot diagnosis: On Ente OCR failure, capture both Ente + Chrome MFA windows together for model diagnosis - implement in next failure case.
- Serve folder pattern: For radar chart visual verification, use python -m http.server background + Playwright navigate to verify PNG not blank.
