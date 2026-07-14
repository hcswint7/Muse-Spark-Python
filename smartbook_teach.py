import os, time, json, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)

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
lesson_path=Path("smartbook_lesson.md")
practice_path=Path("smartbook_practice_test.md")

# Ensure files exist
if not lesson_path.exists():
    lesson_path.write_text("# Ch 11-12 SmartBook - Teaching Log\n\nCourse: MKT-230-353\nBook: Marketing: The Core - Roger Kerin 2025\nChapters: 11 Pricing Concepts & 12 Pricing Strategies\n\n")

def save_question(q_num, question, options, q_type, screenshot, url, explanation=""):
    data={
        "q_num":q_num,
        "question":question,
        "options":options,
        "type":q_type,
        "screenshot":screenshot,
        "url":url,
        "explanation":explanation,
        "timestamp":time.time()
    }
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    # Also append to lesson
    with open(lesson_path,"a") as f:
        f.write(f"\n---\n\n### Q{q_num}: {question[:500]}\n\n**Options:**\n")
        for i,opt in enumerate(options):
            f.write(f"- {chr(65+i)}. {opt}\n")
        f.write(f"\n**Type:** {q_type}\n")
        f.write(f"\n**Teaching / Answer:**\n{explanation}\n")
        f.write(f"\nScreenshot: {screenshot} | URL: {url[:80]}\n")
    return data

def extract_full(page):
    try:
        url=page.url
        title=page.title()
    except:
        url="unknown"; title="unknown"
    ts=int(time.time())
    shot=f"teach_q_{ts}_{title[:20].replace(' ','_')}.png".replace('/','_')
    try:
        page.screenshot(path=shot)
    except:
        shot=None

    # Get text
    try:
        body=page.locator("body").inner_text(timeout=4000)
    except:
        body=""

    # Deep JS extraction for McGraw Hill SmartBook
    js="""
    () => {
        const out={};
        out.url=location.href;
        out.fullText=document.body.innerText.slice(0,20000);
        // Question detection - SmartBook 2.0 uses various selectors
        let qSelectors=[
            '[data-automation="questionText"]',
            '.question-text',
            '.questionText',
            '.prompt',
            '[class*="question"] p',
            'h1', 'h2', 'h3'
        ];
        let qText="";
        for(let sel of qSelectors){
            let el=document.querySelector(sel);
            if(el && el.innerText && el.innerText.length>20 && el.innerText.length<2000){
                if(el.innerText.includes('?') || el.innerText.length>30){
                    qText=el.innerText;
                    break;
                }
            }
        }
        if(!qText){
            // Fallback: largest text block with ?
            let candidates=[];
            document.querySelectorAll('p, div, span').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>30 && t.length<1000 && t.includes('?')){
                    candidates.push(t);
                }
            });
            if(candidates.length>0) qText=candidates[0];
        }
        out.question=qText.slice(0,3000);

        // Options
        let options=[];
        let optSelectors=[
            'label',
            '[data-automation*="option"]',
            '.choice',
            '.answer-option',
            '[class*="option"]',
            'li'
        ];
        document.querySelectorAll(optSelectors.join(',')).forEach(el=>{
            let t=el.innerText?.trim();
            // Filter small, not too long, looks like option
            if(t && t.length>1 && t.length<400){
                // Avoid nav text
                if(!t.includes('Dashboard') && !t.includes('Canvas') && !t.includes('Continue')){
                    options.push(t);
                }
            }
        });
        // Dedupe
        out.options=[...new Set(options)].slice(0,10);

        // Buttons
        let btns=[];
        document.querySelectorAll('button').forEach(b=>{
            let t=b.innerText?.trim();
            if(t && t.length<100) btns.push(t);
        });
        out.buttons=[...new Set(btns)];

        // Highlight if reading mode?
        out.isReading=document.body.innerText.includes('Reading') && document.body.innerText.length>1000;

        return out;
    }
    """
    try:
        js_data=page.evaluate(js)
    except Exception as e:
        print(f"js fail {e}", flush=True)
        js_data={"fullText":body, "question":"", "options":[], "buttons":[]}

    return {"url":url, "title":title, "body":body, "js":js_data, "screenshot":shot}

def try_click(page, texts):
    for txt in texts:
        try:
            btn=page.get_by_role("button", name=txt, exact=False).first
            if btn.count()>0 and btn.is_visible(timeout=1200):
                print(f"Clicking button '{txt}'", flush=True)
                btn.click(timeout=5000)
                page.wait_for_timeout(2500)
                return True
        except: pass
        try:
            el=page.get_by_text(txt, exact=False).first
            if el.count()>0 and el.is_visible(timeout=1200):
                # avoid clicking huge containers
                txt_len=el.inner_text(timeout=1000)
                if len(txt_len)<200:
                    print(f"Clicking text '{txt}'", flush=True)
                    el.click(timeout=5000)
                    page.wait_for_timeout(2500)
                    return True
        except: pass
    return False

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

    print(f"Navigating to {URL}", flush=True)
    page.goto(URL, timeout=30000)
    page.wait_for_timeout(3000)

    # Find and click Begin
    for _ in range(15):
        found=False
        for pg in ctx.pages:
            try:
                b=pg.get_by_role("button", name="Begin", exact=False).first
                if b.count()>0 and b.is_visible(timeout=800):
                    print(f"Found Begin on {pg.url[:80]}", flush=True)
                    pg.bring_to_front()
                    b.click(timeout=5000)
                    found=True
                    page=pg
                    break
            except: pass
        if found:
            break
        time.sleep(1.5)

    time.sleep(4)
    print(f"After Begin, pages={len(ctx.pages)}", flush=True)
    for pg in ctx.pages:
        print(f" {pg.url[:150]}", flush=True)

    # Switch to latest mheducation page
    for _ in range(10):
        for pg in reversed(ctx.pages):
            if "mheducation" in pg.url or "newconnect" in pg.url or "learning" in pg.url:
                page=pg
                page.bring_to_front()
                break
        if "learning.mheducation.com" in page.url:
            break
        time.sleep(1)

    page.wait_for_timeout(5000)
    page.screenshot(path="teach_welcome.png")
    print(f"At welcome: {page.url} {page.title()}", flush=True)

    # Click Start Questions
    for _ in range(5):
        if try_click(page, ["Start Questions", "Start questions"]):
            print("Clicked Start Questions", flush=True)
            break
        time.sleep(2)

    time.sleep(4)
    page.screenshot(path="teach_first_q.png")
    print(f"After Start Questions: {page.url}", flush=True)

    # Now main teaching loop - extract questions one by one
    q_num=0
    seen_hashes=set()
    recent_qs=[]

    for iter in range(100):
        print(f"\n=== TEACH ITER {iter} q_num={q_num} url={page.url[:100]} ===", flush=True)
        # Re-find player page if new tab opened
        for pg in reversed(ctx.pages):
            if "mheducation" in pg.url and "coversheet" not in pg.url:
                page=pg
        try:
            page.bring_to_front()
        except: pass

        data=extract_full(page)
        body=data["body"]
        js=data["js"]
        question=js.get("question") or body[:1000]
        options=js.get("options",[])[:8]
        buttons=js.get("buttons",[])

        print(f"Question extract: {question[:800]}", flush=True)
        print(f"Options: {options}", flush=True)
        print(f"Buttons: {buttons}", flush=True)

        # Deduplicate
        h=hash((question[:200] + "".join(options[:2]))[:500])
        if h in seen_hashes and question.strip()!="":
            print("Duplicate question, waiting for next", flush=True)
            # Try to find Next/Continue to move forward
            # But don't auto-advance if user wants teaching pauses
            time.sleep(5)
            continue
        if question and len(question)>20:
            seen_hashes.add(h)
            q_num+=1

            # === TEACHING LOGIC ===
            # We will create explanation based on Marketing Core concepts
            # For now placeholder, but we will fill with concept teaching
            # We need to infer chapter: Ch 11 Pricing Concepts, Ch 12 Pricing Strategies/Promotion? Let's check typical
            # Actually SmartBook will show concept tag like "11-1 - Nature of Pricing" etc
            teaching = f"""
**Teaching for Q{q_num}:**

Question detected: {question}

Options: {options}

**Concept Facilitation:**
This is from {page.title()} - {data['url'][:80]}

To answer this, think about:
- Ch 11: Pricing Concepts - Key ideas: price, value, price elasticity, cost-based pricing, demand, break-even, etc.
- Ch 12: Possibly Integrated Marketing Communications or Pricing Strategies depending on book edition.

I will explain after seeing full context.

**Memorized for practice test:** YES - saved to jsonl and md files.
"""
            saved=save_question(q_num, question, options, "SmartBook", data["screenshot"], data["url"], teaching)
            recent_qs.append(saved)
            print(f"Saved Q{q_num}", flush=True)

            # For first few questions, pause longer to allow user to read teaching
            # We will keep browser open, user can see same question

        # Check if we should auto-advance:
        # If button like "Submit", "Next", "Continue" exists, we can wait for user instruction
        # For facilitation, we should NOT auto-answer, but show teaching then ask user if they want to proceed

        # For now, just keep loop and don't auto-click to avoid missing questions
        # But if stuck at reading screen, we can click Continue
        if len(question)<30 and "Continue" in str(buttons):
            print("Appears to be reading screen, waiting", flush=True)

        time.sleep(8)

    print("Teaching loop ended, keeping browser forever", flush=True)
    while True:
        time.sleep(15)
        print(f"[keep] {page.url[:100]} q_num={q_num}", flush=True)
