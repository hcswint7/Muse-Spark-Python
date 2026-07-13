# Task 3 - Canvas Assignments Due Next 3 Days - Learnings

## Date: 2026-07-13

### Objective
Access Canvas again separately and note assignments due in both classes in next 3 days

### Why Separate Launch?
User explicitly requested "separately" – to test that login persists across restarts, and to document orchestration of multiple independent runs.

### Approach

#### Using Fixed Debug Profile (After Login Fix)
- Used `~/chrome-debug-profile` with stealth args (already proven logged in)
- Cleaned Singleton locks before launch: `rm ~/chrome-debug-profile/Singleton*`
- Launched with:
  ```python
  launch_persistent_context(
    debug_profile,
    executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless=False,
    no_viewport=True,
    args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
  )
  page.add_init_script("webdriver = undefined")
  ```
- Result: `URL: https://canvas.jccc.edu/, Title: Dashboard` – no login required, session still valid from Task 1 manual login

#### API Approach (Winner) vs UI Scraping

**UI Scraping Attempt (Fragile):**
- Navigate to `/courses/{id}/assignments`
- Scroll and parse assignment list DOM
- Issue: Canvas assignments page is React, infinite scroll, filters, assignee-specific visibility

**API Approach (Robust):**
```python
page.evaluate("""async () => {
  const r = await fetch('/api/v1/courses/86815/assignments?per_page=100&order_by=due_at&bucket=upcoming', {credentials:'include'});
  return await r.json();
}""")
```
- Same-origin fetch with credentials includes cookies – no API token needed
- Returns structured JSON with `name`, `due_at`, `html_url`, `points_possible`
- Filter by date in Python

#### Date Logic
```python
now = datetime.datetime.now(timezone.utc)
three_days_later = now + timedelta(days=3)
for assignment in assignments:
    due_at = assignment.get('due_at')  # ISO like "2026-07-16T04:59:59Z"
    due_dt = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
    if now <= due_dt <= three_days_later:
        # Due soon
```

### Results (Verified Live 2026-07-13 17:06:47 CDT)

**Current time:** 2026-07-13T22:06:47 UTC (2026-07-13 17:06:47 CDT)
**Window:** Next 3 days → until 2026-07-16T22:06:47 UTC (July 16 17:06 CDT)

**Course 87710: BLAW-261-353 - Business Law (60844.202606)**
- Found 16 assignments via API
- **DUE SOON (within 3 days):**
  - Discussion Assignment - Unit 04 – Due 2026-07-16T04:59:59Z (July 15 11:59 PM CDT) – 10 pts – https://canvas.jccc.edu/courses/87710/assignments/2292586
- Future beyond 3 days (July 17-18):
  - Chapter 8 INTELLECTUAL PROPERTY... Due July 17 04:59:00Z
  - Chapter 23 PERSONAL PROPERTY... Due July 17
  - Chapter 24 REAL PROPERTY Due July 17
  - Chapter 25 LANDLORD AND TENANT Due July 17
  - Intellectual Property: Copyright/Patent/Trademark Due July 17
  - Property Law: Landlord-Tenant, Real Property Due July 17
  - Extra Credit Unit 04 Due July 17 11:59 PM
  - QU-Ch08, Ch23, Ch24, Ch25 Due July 17 11:59 PM
  - Exam Unit 04 Due July 18 11:59 PM

**Course 86815: MKT-230-353 - Marketing (60650.202606)**
- Found 5 assignments via API
- **No assignments due within next 3 days**
- Next due:
  - Costco Strategy for Success Due 2026-07-17T04:59:59Z (July 17 11:59 PM) – 4 days away
  - The Right Ad at Right Time Due July 17 11:59 PM
  - Ch 11-12 Assessment, Assignment, SmartBook Due July 20

### Screenshots & Files Saved
- `canvas_assignments_87710.png` full_page
- `canvas_assignments_86815.png` full_page
- `canvas_due_assignments.txt` summary file

### Screen Placements Memorized - Canvas Assignments

- Assignments list: `/courses/{id}/assignments` – main content center, filter dropdown top right "Show by Type", "Upcoming" vs "Past"
- Each assignment row: 100% width, left: assignment name + points, right: due date in gray, e.g., "Due Jul 15, 2026 11:59pm"
- API endpoint faster: `/api/v1/courses/{id}/assignments?per_page=100&bucket=upcoming` – returns only upcoming, but check all then filter manually for precise 3-day window
- Calendar view alternative: `/calendar` shows all courses but harder to parse

### Tips for Future Agents

1. **Separate launches prove session persistence**: After Task 1 manual login, Task 3 (separate process, 1 hour later) still logged in – debug profile retains cookies
2. **Use API not UI**: `fetch('/api/v1/courses/{id}/assignments')` with credentials include is 10x more reliable than scraping
3. **Handle timezones**: Canvas `due_at` is UTC Zulu, convert to local (America/Chicago) for user display – use `astimezone()` 
4. **Bucket=upcoming**: Canvas API bucket filters to not include past, but still may include beyond 3 days – filter manually in Python after fetch
5. **Clean locks before each separate launch**: `rm ~/chrome-debug-profile/Singleton*` – otherwise launch fails with "Chrome already running"
6. **Screenshot assignments page even if using API**: Provides visual verification for user
7. **Check both courses**: Use `/api/v1/courses?enrollment_state=active` to get active course IDs dynamically, fallback to known IDs 86815, 87710

### Code Snippet for Future

```python
def get_due_assignments(page, course_id, days=3):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)
    assignments = page.evaluate(f"""async () => {{
        const r = await fetch('/api/v1/courses/{course_id}/assignments?per_page=100&bucket=upcoming', {{credentials:'include'}});
        return await r.json();
    }}""")
    due_soon = []
    for a in assignments:
        if not a.get('due_at'): continue
        due = datetime.fromisoformat(a['due_at'].replace('Z', '+00:00'))
        if now <= due <= cutoff:
            due_soon.append(a)
    return due_soon
```

### Orchestration Lesson

- Task 3 intentionally separate from Task 1 to test isolated runs
- Both used same debug profile but different Python processes
- Cleaning locks between runs is essential
- Keeping browser open 10s after task allows user to visually verify before close
