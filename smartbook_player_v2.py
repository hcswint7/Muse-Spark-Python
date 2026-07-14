import os, time, json, re, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

profile=os.path.expanduser("~/chrome-debug-profile")
for f in ["SingletonLock","SingletonCookie","SingletonSocket"]:
    fp=os.path.join(profile,f)
    try:
        if os.path.exists(fp) or os.path.islink(fp):
            os.remove(fp)
    except: pass

from playwright.sync_api import sync_playwright

URL="https://canvas.jccc.edu/courses/86815/assignments/2329275?module_item_id=5531124"

mem_path=Path("smartbook_memorized.jsonl")
mem_path.write_text("")  # clear
lesson_path=Path("smartbook_lesson.md")
lesson_path.write_text("# Ch 11-12 SmartBook - Lesson & Practice Test Source\n\n")

def log_q(data):
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n## Q{data.get('q_num','?')}: {data.get('question','')[:200]}\n")
        f.write(f"- **Type**: {data.get('q_type')}\n")
        f.write(f"- **Options**: {data.get('options')}\n")
        f.write(f"- **Answer & Explanation**: {data.get('explanation','')[:2000]}\n")
        f.write(f"- **Screenshot**: {data.get('screenshot')}\n")

def extract_smartbook_page(page):
    """Try multiple strategies to get SmartBook question"""
    try:
        url=page.url
        title=page.title()
    except:
        url="unknown"; title="unknown"
    print(f"[extract] url={url[:120]} title={title[:80]}", flush=True)

    # screenshot
    ts=int(time.time())
    shot=f"smartbook_q_{ts}.png"
    try:
        page.screenshot(path=shot)
        print(f"screenshot {shot}", flush=True)
    except Exception as e:
        print(f"screenshot fail {e}", flush=True)
        shot=None

    # Try to get all text
    try:
        body=page.locator("body").inner_text(timeout=4000)
    except:
        body=""
    # frames
    frame_texts=[]
    try:
        for fr in page.context.pages:
            if fr==page: continue
            try:
                ft=fr.locator("body").inner_text(timeout=2000)[:10000]
                if len(ft)>50:
                    frame_texts.append((fr.url[:100], ft[:2000]))
            except: pass
        for fr in page.frames:
            try:
                ft=fr.locator("body").inner_text(timeout=2000)[:10000]
                if len(ft)>100 and len(ft)<15000:
                    frame_texts.append((fr.url[:100], ft[:2000]))
            except: pass
    except: pass

    # JS extraction for SmartBook 2.0 specific selectors
    js="""
    () => {
        const out={};
        out.url=location.href;
        out.text=document.body.innerText.slice(0,20000);
        // Try to find question container - McGraw Hill common classes
        let qEl=document.querySelector('[data-automation="question"]') || document.querySelector('.question') || document.querySelector('.sb-question') || document.querySelector('[class*="question"]') || document.querySelector('div[role="main"]');
        if(qEl) out.questionEl=qEl.innerText.slice(0,5000);
        // Options
        let opts=[];
        document.querySelectorAll('[data-automation*="option"], .option, .answer, label, [class*="choice"], button[role="radio"]').forEach(el=>{
            let t=el.innerText?.trim();
            if(t && t.length>0 && t.length<500) opts.push(t.slice(0,500));
        });
        out.options=opts.slice(0,20);
        // Buttons
        let btns=[];
        document.querySelectorAll('button').forEach(b=>{
            let t=b.innerText?.trim();
            if(t) btns.push(t.slice(0,100));
        });
        out.buttons=btns.slice(0,20);
        // Inputs
        out.htmlSnip=document.documentElement.outerHTML.slice(0,20000);
        return out;
    }
    """
    try:
        data=page.evaluate(js)
    except Exception as e:
        print(f"js extract fail {e}", flush=True)
        data={"text":body[:10000]}

    return {"url":url, "title":title, "body":body[:15000], "js":data, "screenshot":shot, "frame_texts":frame_texts}

with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(
        profile,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        no_viewport=True,
        args=["--disable-blink-features=AutomationControlled","--disable-infobars","--no-first-run","--disable-dev-shm-usage"],
    )
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    except: pass

    print(f"Go to {URL}", flush=True)
    page.goto(URL, timeout=30000)
    page.wait_for_timeout(3000)
    
    # Wait for coversheet to appear in any page
    for attempt in range(20):
        print(f"Checking for Begin button attempt {attempt}", flush=True)
        found=False
        for pg in ctx.pages:
            try:
                # Look for Begin button
                btn=pg.get_by_role("button", name="Begin", exact=False).first
                if btn.count()>0 and btn.is_visible(timeout=1000):
                    print(f"Found Begin on page {pg.url[:100]}", flush=True)
                    pg.bring_to_front()
                    btn.click(timeout=5000)
                    print("Clicked Begin", flush=True)
                    found=True
                    page=pg
                    break
                # Also check for link
                link=pg.get_by_text("Begin", exact=False).first
                if link.count()>0 and link.is_visible(timeout=1000):
                    print(f"Found Begin text on {pg.url[:100]}", flush=True)
                    pg.bring_to_front()
                    link.click(timeout=5000)
                    found=True
                    page=pg
                    break
            except Exception as e:
                print(f"check Begin fail {e}", flush=True)
        if found:
            break
        time.sleep(2)
        # Also check if Launch Assignment button in frame 2
        try:
            for pg in ctx.pages:
                try:
                    launch_btn=pg.get_by_role("button", name="Launch Assignment", exact=False).first
                    if launch_btn.count()>0 and launch_btn.is_visible(timeout=1000):
                        print("Found Launch Assignment", flush=True)
                        launch_btn.click(timeout=5000)
                        time.sleep(2)
                except: pass
        except: pass

    print(f"After Begin click, pages: {len(ctx.pages)}", flush=True)
    for pg in ctx.pages:
        print(f"  {pg.url[:150]} | {pg.title()[:80]}", flush=True)

    time.sleep(5)
    # Bring newest page to front (likely SmartBook player)
    if len(ctx.pages)>1:
        page=ctx.pages[-1]
        page.bring_to_front()
        print(f"Switched to newest page: {page.url}", flush=True)

    page.wait_for_timeout(4000)
    page.screenshot(path="smartbook_after_begin.png")
    print("screenshot after_begin", flush=True)

    # Now loop extracting questions
    q_num=0
    seen_texts=set()
    for iter in range(100):  # max 100 questions
        print(f"\n=== Iteration {iter} q_num={q_num} ===", flush=True)
        # Ensure we are on player page (latest)
        if ctx.pages:
            # Find page with SmartBook content (not Canvas)
            for pg in reversed(ctx.pages):
                if "mheducation" in pg.url or "newconnect" in pg.url or "learning" in pg.url:
                    page=pg
                    break
            try:
                page.bring_to_front()
            except: pass

        data=extract_smartbook_page(page)
        body=data.get("body","") or data.get("js",{}).get("text","")
        # Deduplicate by hash of body first 500 chars
        h=hash(body[:500])
        if h in seen_texts and iter>0:
            print("[loop] same content as before, waiting", flush=True)
            # Check if there's a Next/Continue button to click
        else:
            seen_texts.add(h)
            q_num+=1
            print(f"[new] Question {q_num} len {len(body)}", flush=True)
            print(body[:3000], flush=True)
            # Save
            log_q({
                "q_num":q_num,
                "url":data["url"],
                "title":data["title"],
                "question":body[:5000],
                "q_type":"unknown",
                "options":data.get("js",{}).get("options",[])[:10],
                "buttons":data.get("js",{}).get("buttons",[])[:10],
                "explanation":"",
                "screenshot":data.get("screenshot"),
                "timestamp":time.time()
            })
            # Brief pause for teaching - will be continued by user directing
            # For now we continue auto-extract every 10s

        # Try to find Next / Continue / Submit / Check answer buttons to progress
        try:
            # Look for common navigation
            for txt in ["Continue", "Next", "I got it", "Next Question", "Submit", "Check", "Reveal", "Show Answer", "I Understand", "Got it", "Start", "Begin", "Resume", "Continue Reading"]:
                try:
                    btn=page.get_by_role("button", name=txt, exact=False).first
                    if btn.count()>0 and btn.is_visible(timeout=800):
                        print(f"[auto] Found button '{txt}' - NOT auto-clicking yet, logging", flush=True)
                        # Don't auto-click yet, let user direct, but log
                except: pass
        except Exception as e:
            print(f"button scan fail {e}", flush=True)

        print(f"Waiting 12s before next extract (user can direct me to answer/teach)", flush=True)
        time.sleep(12)

    print("Loop ended, keeping browser open forever", flush=True)
    while True:
        time.sleep(10)
        print(f"[keep] {page.url[:100]}", flush=True)
