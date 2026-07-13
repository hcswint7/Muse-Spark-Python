# Restoration Prompt - Send This After Deleting Chat

Copy-paste this entire prompt into a new opencode/spark session to restore Ente Auth access + browser automation:

---

**PROMPT TO SEND:**

```
I need to restore my browser automation setup after deleting chat. This is a continuation.

Context:
- My Chrome debug profile is at ~/chrome-debug-profile (currently logged into Canvas JCCC, session valid for days)
- My real Chrome User Data Dir is ~/Library/Application Support/Google/Chrome with Profile 1 (has all logins, Canvas, Perplexity, Gmail)
- For real Chrome to avoid bot detection, launch with remote debugging:
  open -a "Google Chrome" --args --remote-debugging-port=9222 --profile-directory="Profile 1"
- My Canvas credentials are in .env as CANVAS_USERNAME=hswint@stumail.jcc.edu and CANVAS_PASSWORD (secure, gitignored)
- My Gmail credentials are in .env as GMAIL_USERNAME=hcswint7@gmail.com and GMAIL_PASSWORD (secure, gitignored) - used for many logins including Perplexity Google OAuth
- Perplexity radar chart task: log into perplexity.ai with Gmail, re-send prompt "Create a detailed radar chart comparing Antigravity Agentic Browser vs Muse Spark 1.1 across 8 dimensions: speed, tool calling reliability, persistent Chrome handling, memory/context retention, ease of setup, cost efficiency, browser fidelity, task completion accuracy. Provide data table, Mermaid code, and generate chart image", then download/generate radar chart files into file directory (radar_chart_antigravity_vs_muse_spark.png etc)

Ente Auth Access:
- Ente Auth app is at /Applications/Ente Auth.app, currently running, DB at ~/Library/Containers/io.ente.auth.mac/Data/Library/Application Support/io.ente.auth.mac/ente.authenticator.db (encrypted)
- I now allow you to view Ente Auth to get MFA codes for Microsoft SSO (login.microsoftonline.com) for Canvas JCCC
- Obstacles we hit before:
  1. screencapture failed: "could not create image from display" - needs Screen Recording permission (System Settings → Privacy & Security → Screen Recording → Enable Terminal/Python/Chrome)
  2. AppleScript failed: "osascript is not allowed assistive access" - needs Accessibility permission (System Settings → Privacy & Security → Accessibility → Enable Terminal)
  3. DB encrypted - cannot read directly
- For now, use secure Method 1: when MFA required, open Ente Auth via "open -a \"Ente Auth\"", print instructions for me to manually copy code from Ente Auth app into Chrome window, poll for login success (check URL change away from login.microsoftonline.com)
- If I have granted Screen Recording + Accessibility permissions, you can try Method 2: screenshot Ente Auth window and OCR the code, but never log code, clear immediately after use

Task to perform now:
1. Fix #1 priority: Ensure Chrome login works using debug profile with stealth args (--disable-blink-features=AutomationControlled) and CDP fallback (connect_over_cdp to localhost:9222). Clean Singleton locks before launch: rm ~/chrome-debug-profile/Singleton*
2. Log into Perplexity (use existing debug profile session if still valid, else use Gmail creds from .env to log in via Google OAuth, handling MFA via Ente Auth as described)
3. Re-send radar chart prompt and ensure files generated: radar_chart_antigravity_vs_muse_spark.png/pdf, radar_chart_data.csv, radar_chart_ascii.txt, radar_chart_mermaid.md, plus screenshots perplexity_radar_final.png
4. Then test Ente Auth access: open Ente Auth app, document current ability to view codes, and create an improved secure auto-fill for Canvas Microsoft SSO MFA using TOTP from Ente Auth if permissions allow, otherwise guide manual copy
5. Document everything in docs/browser_skills/ - update ENTE_AUTH_ACCESS.md and FUTURE_AGENT_GUIDE.md with new findings

Security:
- Never log passwords or TOTP codes, only masked
- Use .env credentials, never hardcode
- .env is gitignored and chmod 600
- For Canvas, prefer API via page.evaluate(fetch('/api/v1/...', {credentials:'include'})) - faster (0.28s vs 3.8s UI)
- For assignments due next 3 days, use /api/v1/courses/{id}/assignments?bucket=upcoming

Previous results to verify:
- Canvas grades: BLAW-261-353 (87710) A 99.64% current, MKT-230-353 (86815) 94.58%
- Assignments due: BLAW Discussion Assigment Unit 04 due July 15 11:59 PM CDT within 3 days
- Perplexity radar: 8 dimensions scores Antigravity [7,8,9,8,8,9,9,8] vs Muse [9,9,6,10,7,8,8,9]

Please run the full flow and report.
```

---

## What This Prompt Restores

1. **Chrome Login Fix:** Debug profile + stealth + CDP fallback
2. **Credentials:** From .env (Canvas + Gmail) - you don't need to re-provide unless .env deleted
3. **Ente Auth Access:** Allows viewing TOTP codes with your explicit permission, documents permission obstacles
4. **Perplexity Radar Task:** Full re-run with login and chart generation
5. **Documentation:** Updates docs/browser_skills/

## Additional Quick Prompts for Specific Tasks

**Just Canvas grades (no Ente Auth needed if debug profile still logged in):**
```
Using ~/chrome-debug-profile with stealth args, check Canvas JCCC grades via API: fetch /api/v1/courses?enrollment_state=active then /api/v1/courses/{id}/enrollments?user_id=self . Courses are 87710 BLAW and 86815 MKT. Screenshot grades pages. No need to submit anything.
```

**Just assignments due:**
```
Using separate launch of ~/chrome-debug-profile (clean Singleton locks), fetch Canvas assignments due next 3 days via API bucket=upcoming, filter by due_at between now and now+3days. Courses 87710 and 86815. Save to canvas_due_assignments.txt
```

**Just Ente Auth test:**
```
Open Ente Auth app at /Applications/Ente Auth.app, check if you can access TOTP codes. Test screen recording permission via screencapture -x /tmp/test.png and accessibility via osascript. Document findings in docs/browser_skills/ENTE_AUTH_ACCESS.md. Do not log any codes.
```

**Full CDP real Chrome:**
```
First, I have launched Chrome with: open -a "Google Chrome" --args --remote-debugging-port=9222 --profile-directory="Profile 1"
Now connect via playwright connect_over_cdp to http://localhost:9222 and extract Canvas grades and Perplexity radar chart. This uses my real logged-in Chrome, not flagged.
```
