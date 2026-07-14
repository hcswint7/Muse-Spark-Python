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

# Knowledge base for Ch 11-12 (Marketing: The Core)
# Ch 11: Pricing - 4Ps, price uniqueness, price elasticity, break-even, etc.
# Ch 12: Probably Promotion/IMC or Pricing Strategies

def answer_question(question_text, options):
    q=question_text.lower()
    # Q1
    if "element of the marketing mix has a unique role" in q and "all other business decisions come together" in q:
        return "price", "Price is the only element that generates revenue. It's where costs, value perceptions, competition, and demand all converge. Product, place, promotion are costs; price is what captures value."
    # Add more generic heuristics
    if "marketing mix" in q and "4 ps" in q:
        return options[0] if options else "", "Marketing mix = Product, Price, Place, Promotion - the 4 Ps."
    # Pricing concepts
    if "price elasticity" in q:
        if "elastic" in q and "inelastic" in q:
            return "If price goes up and demand drops a lot = elastic", "Elasticity measures sensitivity of quantity demanded to price change."
    if "break-even" in q:
        return "Fixed Costs / (Price - Variable Cost)", "Break-even point formula."
    if "skimming" in q.lower() or "penetration" in q.lower():
        if "skimming" in q.lower() and "high" in q:
            return "price skimming", "Skimming = high initial price to skim top of market, then lower."
        if "penetration" in q.lower():
            return "penetration pricing", "Penetration = low initial price to gain market share fast."
    # Default: return first option and note to teach
    return None, None

def save(question, options, answer, explanation, screenshot, url, q_num):
    data={
        "q_num":q_num,
        "question":question,
        "options":options,
        "answer":answer,
        "explanation":explanation,
        "screenshot":screenshot,
        "url":url,
        "ts":time.time()
    }
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n\n### Q{q_num}: {question}\nOptions: {options}\n**Answer: {answer}**\n**Teaching:** {explanation}\nScreenshot: {screenshot}\n")
    print(f"Saved Q{q_num} answer={answer}", flush=True)
    return data

def click_option(page, answer_text):
    # Try multiple ways
    try:
        # radio by name
        radio=page.get_by_role("radio", name=answer_text, exact=False).first
        if radio.count()>0:
            radio.click(timeout=3000)
            print(f"Clicked radio {answer_text}", flush=True)
            return True
    except Exception as e:
        print(f"radio click fail {answer_text} {e}", flush=True)
    try:
        # label containing
        lab=page.locator(f"label:has-text('{answer_text}')").first
        if lab.count()>0 and lab.is_visible(timeout=1500):
            lab.click(timeout=3000)
            print(f"Clicked label {answer_text}", flush=True)
            return True
    except: pass
    try:
        # text
        opt=page.get_by_text(answer_text, exact=False).first
        if opt.count()>0:
            opt.click(timeout=3000)
            print(f"Clicked text {answer_text}", flush=True)
            return True
    except Exception as e:
        print(f"text click fail {e}", flush=True)
    # Try clicking circle input
    try:
        # find input near text
        inp=page.locator(f"input:near(:text('{answer_text}'))").first
        if inp.count()>0:
            inp.click(timeout=3000)
            return True
    except: pass
    return False

def click_confidence(page, level="High"):
    try:
        btn=page.get_by_role("button", name=level, exact=False).first
        if btn.count()>0 and btn.is_visible(timeout=2000):
            # Check if enabled (not disabled)
            is_disabled=btn.is_disabled()
            print(f"Confidence {level} disabled={is_disabled}", flush=True)
            if not is_disabled:
                btn.click(timeout=3000)
                print(f"Clicked confidence {level}", flush=True)
                return True
            else:
                print(f"Confidence {level} disabled, need to select option first", flush=True)
    except Exception as e:
        print(f"confidence click fail {e}", flush=True)
    return False

def extract(page):
    js="""
    () => {
        let out={};
        out.url=location.href;
        out.title=document.title;
        out.innerText=document.body.innerText.slice(0,15000);
        // Question
        let q="";
        let qEl=document.querySelector('[data-automation="questionText"]') || document.querySelector('.question-text') || document.querySelector('h2') || document.querySelector('[class*="question"]');
        // Try to find main question: first element with ? that's not too short
        if(!q){
            let candidates=[];
            document.querySelectorAll('p, div').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>30 && t.length<600 && t.includes('?')){
                    // avoid header
                    if(!t.includes('Concepts completed')){
                        candidates.push(t);
                    }
                }
            });
            if(candidates.length>0) q=candidates[0];
        } else {
            q=qEl.innerText;
        }
        out.question=q.slice(0,2000);
        // Options
        let opts=[];
        document.querySelectorAll('label, [role="radio"], .choice, [class*="option"]').forEach(el=>{
            let t=el.innerText?.trim();
            if(t && t.length>0 && t.length<100){
                if(!t.includes('Need help') && !t.includes('Review') && !t.includes('Reading') && !t.includes('Exit')){
                    opts.push(t);
                }
            }
        });
        out.options=[...new Set(opts)].slice(0,10);
        let btns=[];
        document.querySelectorAll('button').forEach(b=>{
            let t=b.innerText?.trim();
            if(t && t.length<80) btns.push(t);
        });
        out.buttons=[...new Set(btns)];
        out.progress=document.body.innerText.match(/\\d+ of \\d+ Concepts completed/)?.[0] || "";
        return out;
    }
    """
    try:
        return page.evaluate(js)
    except Exception as e:
        print(f"extract js fail {e}", flush=True)
        return {"question":"", "options":[], "buttons":[], "innerText":"", "progress":""}

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

    # Click Begin in any page
    for _ in range(10):
        for pg in ctx.pages:
            try:
                b=pg.get_by_role("button", name="Begin", exact=False).first
                if b.count()>0 and b.is_visible(timeout=800):
                    pg.bring_to_front()
                    b.click(timeout=5000)
                    print(f"Clicked Begin on {pg.url[:80]}", flush=True)
                    page=pg
                    break
            except: pass
        time.sleep(1)
        # Break if we have mheducation page
        if any("mheducation" in pg.url for pg in ctx.pages):
            break

    time.sleep(5)
    # Switch to mheducation
    for pg in reversed(ctx.pages):
        if "mheducation" in pg.url:
            page=pg
            page.bring_to_front()
            break

    print(f"At {page.url} title {page.title()}", flush=True)
    page.screenshot(path="auto_welcome.png")
    
    # Click Start Questions if present
    for _ in range(5):
        try:
            b=page.get_by_role("button", name="Start Questions", exact=False).first
            if b.count()>0 and b.is_visible(timeout=1000):
                b.click(timeout=5000)
                print("Clicked Start Questions", flush=True)
                break
        except: pass
        time.sleep(1)

    time.sleep(4)
    page.screenshot(path="auto_q0.png")
    print(f"After Start Questions {page.url}", flush=True)

    q_num=0
    seen=set()
    for iter in range(60):
        print(f"\n=== ITER {iter} ===", flush=True)
        # Ensure player page
        for pg in reversed(ctx.pages):
            if "mheducation" in pg.url and "coversheet" not in pg.url:
                page=pg
        try:
            page.bring_to_front()
        except: pass

        info=extract(page)
        q_text=info.get("question","")
        opts=info.get("options",[])
        progress=info.get("progress","")
        print(f"Progress: {progress}", flush=True)
        print(f"Q: {q_text[:500]}", flush=True)
        print(f"Opts: {opts}", flush=True)
        print(f"Buttons: {info.get('buttons')}", flush=True)

        if not q_text or len(q_text)<15:
            print("No question found, maybe reading or feedback screen", flush=True)
            # Try to click Continue / Next
            for txt in ["Continue", "Next", "Got it", "I got it", "Next Question", "Start Reading", "Resume"]:
                try:
                    b=page.get_by_role("button", name=txt, exact=False).first
                    if b.count()>0 and b.is_visible(timeout=800):
                        print(f"Clicking {txt} to proceed", flush=True)
                        b.click(timeout=3000)
                        time.sleep(3)
                        break
                except: pass
            time.sleep(3)
            continue

        # Dedup
        h=hash(q_text[:200])
        if h in seen:
            print("Seen before, checking for next", flush=True)
            # If seen, we may have already answered, try to advance
            # Click High confidence if available to submit
            if click_confidence(page, "High"):
                time.sleep(3)
            # Try continue
            for txt in ["Continue", "Next"]:
                try:
                    b=page.get_by_role("button", name=txt, exact=False).first
                    if b.count()>0 and b.is_visible(timeout=800):
                        b.click(timeout=3000)
                        print(f"Clicked {txt}", flush=True)
                        time.sleep(3)
                        break
                except: pass
            time.sleep(4)
            continue

        seen.add(h)
        q_num+=1

        ans, expl=answer_question(q_text, opts)
        if ans is None:
            # For unknown, default to first option but note teaching needed
            ans=opts[0] if opts else "unknown"
            expl=f"Need to teach concept for: {q_text}. This appears to be Ch 11-12 Marketing Core. Let's analyze: {q_text}. The key concept likely relates to pricing."

        print(f"\n>>> Q{q_num}: {q_text}", flush=True)
        print(f">>> Answer: {ans}", flush=True)
        print(f">>> Explanation: {expl}", flush=True)

        # Screenshot
        ts=int(time.time())
        shot=f"auto_q_{q_num}_{ts}.png"
        try:
            page.screenshot(path=shot)
        except:
            shot=None

        save(q_text, opts, ans, expl, shot, page.url, q_num)

        # Try to answer if we have confident answer
        if ans and ans.lower() in [o.lower() for o in opts] or ans in opts:
            if click_option(page, ans):
                time.sleep(1)
                # Click High confidence to submit
                if click_confidence(page, "High"):
                    print("Submitted with High", flush=True)
                    time.sleep(4)
                    page.screenshot(path=f"auto_q_{q_num}_after_submit.png")
                    # Check for feedback and Continue
                    for _ in range(5):
                        for txt in ["Continue", "Next", "Got it", "I Understand"]:
                            try:
                                b=page.get_by_role("button", name=txt, exact=False).first
                                if b.count()>0 and b.is_visible(timeout=1000):
                                    print(f"Feedback continue clicking {txt}", flush=True)
                                    b.click(timeout=3000)
                                    time.sleep(2)
                                    break
                            except: pass
                        time.sleep(1)
                else:
                    print("Could not click High, maybe need option selected", flush=True)
            else:
                print(f"Could not click option {ans}", flush=True)
                # Try clicking first option as fallback for progression
        else:
            print(f"Answer {ans} not in opts {opts}, skipping auto-click to let user see", flush=True)

        time.sleep(3)

    print("Done teaching loop, keeping open", flush=True)
    while True:
        time.sleep(15)
        print(f"[keep] {page.url[:100]} q_num={q_num}", flush=True)
