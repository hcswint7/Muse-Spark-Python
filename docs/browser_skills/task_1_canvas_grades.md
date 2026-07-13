# Task 1 - Canvas Grades Extraction - Learnings

## Date: 2026-07-13

### Objective
Access canvas.jccc.edu and report grades for both classes

### Discovery via History SQLite
- Checked `~/chrome-debug-profile/Default/History` SQLite
- Found courses: 86815 (MKT-230-353) and 87710 (BLAW-261-353)
- Also found canvas.ku.edu but not active
- Perplexity history confirmed debug profile is used

### Problem 1: Env Var Points to Main Profile
- `.env` had `CHROME_PROFILE_DIR="${HOME}/Library/Application Support/Google/Chrome"`
- `expanduser` doesn't expand `${HOME}`, so script fails or uses wrong dir
- Fix: Force `~/chrome-debug-profile` in code, with `clean_locks()` for that dir

### Problem 2: Session Expired → Microsoft SSO
- Navigating to https://canvas.jccc.edu/ redirected to `login.microsoftonline.com/15244239-dcf2-45e7-aefd-127b69fc5438/saml2?...`
- Title: "Sign in to your account"
- Body: "Sign in / Can't access your account? / Sign-in options"
- API call `/api/v1/courses` returned 404 when not authenticated (because not on canvas origin)
- This is JCCC's Azure AD SAML flow

### Solution: Secure Manual Login Polling
- Instead of `input()` which blocks bash tool, implemented polling loop 150s
- Detect login page via:
  ```python
  "login.microsoftonline.com" in url
  "sign in to your account" in title.lower()
  "can't access your account" in body.lower()
  ```
- On detection:
  - Screenshot `canvas_login_required.png`
  - Print instructions for manual login in visible Chrome window
  - Poll every 3s for URL change away from login domains
  - No password in .env, session cookies retained in debug profile for days/weeks

- **Result**: User logged in at ~120s, script detected URL change to `https://canvas.jccc.edu/` and continued

### Grades Extraction - Two Methods Tested

#### Method A: UI Scraping (Fragile)
- Navigate to `/courses/{id}/grades`
- `page.locator("body").inner_text()` length ~7k-12k
- Scroll via `page.mouse.wheel(0, 800)` 3-4 times to load lazy content
- Screenshot full_page
- Issue: Grade table is React-rendered, sometimes hidden behind tabs

#### Method B: Canvas API via page.evaluate (Robust) - WINNER
```python
page.evaluate("""async () => {
  const res = await fetch('/api/v1/courses?enrollment_state=active&per_page=20', {credentials: 'include'});
  return await res.json();
}""")
```
- Works because we're same-origin (canvas.jccc.edu) after login, credentials include cookies
- No need for API token
- Returns JSON with course list
- Then `/api/v1/courses/{id}/enrollments?user_id=self` returns grades:
  ```json
  {
    "grades": {
      "current_grade": "A",
      "current_score": 99.64,
      "final_grade": "D",
      "final_score": 63.47
    }
  }
  ```

### Results (Verified Live)

**Course 87710 - BLAW-261-353 - Business Law (60844.202606)**
- Current: A (99.64%)
- Final (projected): D (63.47%) - indicates many assignments not yet counted in final divisor
- Enrollment ID 1718066

**Course 86815 - MKT-230-353 - Marketing (60650.202606)**
- Current: No letter grade (professor hasn't set grading scheme letter?), Score 94.58%
- Final: None, 63.15%
- Enrollment ID 1718067

Screenshots saved:
- `canvas_dashboard_authenticated.png`
- `canvas_grades_87710.png`
- `canvas_grades_86815.png`
- Text dumps: `canvas_grades_{id}_full.txt`

### Screen Placements Memorized - Canvas JCCC

- Login: Microsoft SSO centered modal 440x500, at login.microsoftonline.com
- After login → Canvas Dashboard: `https://canvas.jccc.edu/` - left nav 84px wide dark blue, icons: Dashboard, Courses, Calendar, Inbox
- Courses list: Cards grid, each card 300x200, link `/courses/{id}`
- Grades page: `/courses/{id}/grades` - left course nav, main content table with `Course Grade` header, `Assignment` column left, `Score` right
- Grades API is fastest: avoid UI parsing when possible

### Tips for Future Agents

1. **Always force debug profile** `~/chrome-debug-profile` not main
2. **Clean Singleton locks** before launch: `rm ~/chrome-debug-profile/Singleton*`
3. **Detect Microsoft SSO** not just Canvas login - check for `login.microsoftonline.com`
4. **Do not ask for password in env** - use polling manual login, cookies persist
5. **Prefer Canvas API via `page.evaluate(fetch)`** over scraping - more stable, returns structured data
6. **Use `credentials: 'include'`** in fetch to send cookies
7. **Scroll before screenshot** - Canvas lazy loads grade rows
8. **Check both current_score and final_score** - final includes 0s for missing assignments causing low final_score even with high current
9. **Handle no letter grade** - MKT course returns `current_grade: None` but has score; display score instead

### Code Snippet for Future

```python
def get_canvas_grades(page, course_id):
    data = page.evaluate(f"""async () => {{
        const r = await fetch('/api/v1/courses/{course_id}/enrollments?user_id=self', {{credentials:'include'}});
        return await r.json();
    }}""")
    if isinstance(data, list):
        return data[0]['grades']
```

### What Worked vs Failed

- ✅ API approach, manual login polling, forced debug profile, screenshots
- ❌ Initial attempt using `CHROME_PROFILE_DIR` from .env (main profile locked), `input()` blocking, body text parsing only
