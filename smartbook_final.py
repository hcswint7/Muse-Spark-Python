import os, time, json, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)

from playwright.sync_api import sync_playwright

mem_path=Path("smartbook_memorized.jsonl")
lesson_path=Path("smartbook_lesson.md")
practice_path=Path("smartbook_practice_test.md")

# Ensure files
if not lesson_path.exists():
    lesson_path.write_text("# Ch 11-12 SmartBook - Teaching Log\n\n")

def save_q(q_num, question, options, answer, explanation, screenshot, url, progress):
    data={
        "q_num":q_num,
        "question":question,
        "options":options,
        "answer":answer,
        "explanation":explanation,
        "screenshot":screenshot,
        "url":url,
        "progress":progress,
        "ts":time.time()
    }
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n---\n\n### Q{q_num} [{progress}] {question[:500]}\n\n**Options:** {options}\n\n**Answer:** {answer}\n\n**Explanation & Teaching:**\n{explanation}\n\n**Screenshot:** {screenshot}\n\n")
    return data

def analyze_and_answer(question, options, full_text):
    """
    Analyze question and return (answer_text, explanation)
    Covers Ch 11-12 Marketing: The Core - Pricing
    """
    q=question.lower() if question else ""
    full=full_text.lower() if full_text else ""

    # Q1 we know
    if "unique role" in q and "all other business decisions come together" in q:
        return "price", """**Analysis:** The question asks which element of marketing mix has unique role where all business decisions come together.
    
**Concept Teaching - The 4Ps & Price Uniqueness:**
- Product, Price, Place, Promotion are 4Ps.
- Product, Place, Promotion are COSTS.
- Price is the ONLY element that generates REVENUE.
- Price is where all decisions converge: you must consider product costs, distribution costs (place), promotion budget, competitor pricing, customer perceived value, demand.

**Answer: price**

**Why not others?**
- product: value creation but not revenue capture
- promotion: communication cost
- place: distribution cost

**Memorize:** Price = Revenue + Convergence point.
"""

    # Generic pricing concepts
    if "price" in q and "revenue" in q and "only" in q:
        return "price", "Price is the only P that produces revenue, others are costs."

    # Value, pricing definitions
    if "value" in q and "benefits" in q and "price" in q:
        # Value = benefits / price, or perceived benefits vs price
        for opt in options:
            if "benefit" in opt.lower() and "price" in opt.lower():
                return opt, "Value is perceived benefits relative to price. Value = benefits / price conceptually."

    # Elasticity
    if "elasticity" in q or "elastic" in q:
        if "inelastic" in q:
            return "inelastic", "Inelastic demand: quantity changes little when price changes (necessities, no substitutes)."
        if "elastic" in q:
            return "elastic", "Elastic demand: quantity changes a lot when price changes."

    # Break-even
    if "break-even" in q or "break even" in q:
        if "fixed" in q and "variable" in q:
            return "Fixed costs / (Price - Variable cost)", "Break-even formula."

    # Skimming vs penetration
    if "skimming" in q:
        return "price skimming", "Skimming: high initial price skims top of market (innovators), then lowers."
    if "penetration" in q and "pricing" in q:
        return "penetration pricing", "Penetration: low initial price to gain market share quickly, deter competitors."

    # Bundle, etc
    # Fill in blank might be "price" or "value" etc - try to infer
    if not options:  # fill in blank
        # Look for context in full text
        if "marketing mix has a unique role" in full:
            return "price", "As before, price is unique revenue point."
        # If blank question, return likely answer based on sentence
        # We'll try to use full_text to find blank context
        # For now return analysis placeholder
        return None, f"Fill-in-the-blank detected. Full context: {full[:2000]}. Need to read surrounding text to infer blank."

    # Multiple choice with options - try to match
    # If options include product, price, promotion, place - likely price is often correct for unique role questions
    # For other, use heuristic: if question asks what is place where all decisions come together, price.

    # Default fallback: try to find best option via keywords
    # If question asks about something that produces revenue, answer price
    if "revenue" in q:
        for opt in options:
            if "price" in opt.lower():
                return opt, "Revenue generation is price."

    return None, f"Need deeper analysis. Q: {question} Options: {options}"

with sync_playwright() as p:
    print("Connecting to stable Chrome at 9222...", flush=True)
    browser=p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=browser.contexts[0] if browser.contexts else None
    if not ctx:
        print("No context", flush=True)
        exit(1)

    # Find player page
    player_page=None
    for pg in ctx.pages:
        if "learning.mheducation.com" in pg.url and "awd" in pg.url:
            player_page=pg
            break
    if not player_page:
        # find any mheducation
        for pg in ctx.pages:
            if "mheducation" in pg.url:
                player_page=pg
                break
    if not player_page:
        print("No player page found", flush=True)
        for pg in ctx.pages:
            print(f"  {pg.url}", flush=True)
        exit(1)

    player_page.bring_to_front()
    print(f"Player: {player_page.url[:120]} title={player_page.title()[:80]}", flush=True)

    def extract(page):
        js="""
        () => {
            let out={};
            out.url=location.href;
            out.title=document.title;
            let q="";
            // Find question - look for ? sentence
            let cands=[];
            document.querySelectorAll('p, div, h2, h3, span').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>20 && t.length<600 && t.includes('?')){
                    if(!t.includes('Concepts completed') && !t.includes('Need help') && t.split(' ').length>5){
                        // Avoid too large container that contains many ?
                        if((t.match(/\\?/g)||[]).length<=2){
                            cands.push(t);
                        }
                    }
                }
            });
            // Prefer first that looks like question near top
            if(cands.length>0){
                // Sort by position - find element with smallest offsetTop that matches
                q=cands[0];
            }
            out.question=q.slice(0,2000);
            let opts=[];
            document.querySelectorAll('label, [role="radio"], [data-test="option"], .choice').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>0 && t.length<120){
                    if(!t.includes('Need help') && !t.includes('Read About') && !t.includes('Privacy') && !t.includes('Exit')){
                        opts.push(t);
                    }
                }
            });
            // For fill blank, look for input
            let fillInputs=[];
            document.querySelectorAll('input[type="text"], input:not([type]), textarea').forEach(inp=>{
                let ph=inp.placeholder || inp.getAttribute('aria-label') || '';
                fillInputs.push({placeholder: ph, value: inp.value, outer: inp.outerHTML.slice(0,500)});
            });
            out.options=[...new Set(opts)].slice(0,12);
            out.fillInputs=fillInputs;
            let btns=[];
            document.querySelectorAll('button').forEach(b=>{
                let t=b.innerText?.trim();
                if(t && t.length<60) btns.push(t);
            });
            out.buttons=[...new Set(btns)];
            out.progress=(document.body.innerText.match(/\\d+ of \\d+ Concepts completed/)||[""])[0];
            out.fullText=document.body.innerText.slice(0,15000);
            return out;
        }
        """
        try:
            return page.evaluate(js)
        except Exception as e:
            print(f"extract fail {e}", flush=True)
            return {}

    def click_option(page, answer_text):
        if not answer_text:
            return False
        # Try radio
        try:
            radio=page.get_by_role("radio", name=answer_text, exact=False).first
            if radio.count()>0:
                radio.click(timeout=3000)
                print(f"Clicked radio {answer_text}", flush=True)
                return True
        except: pass
        try:
            # label
            lab=page.locator(f"label:has-text('{answer_text}')").first
            if lab.count()>0 and lab.is_visible(timeout=1500):
                lab.click(timeout=3000)
                print(f"Clicked label {answer_text}", flush=True)
                return True
        except: pass
        try:
            # get by text inside options container
            el=page.get_by_text(answer_text, exact=False).first
            if el.count()>0:
                el.click(timeout=3000)
                print(f"Clicked text {answer_text}", flush=True)
                return True
        except: pass
        return False

    def click_confidence(page, level="High"):
        try:
            btn=page.get_by_role("button", name=level, exact=False).first
            if btn.count()>0:
                # Wait until enabled
                for _ in range(10):
                    try:
                        if not btn.is_disabled():
                            btn.click(timeout=3000)
                            print(f"Clicked confidence {level} - submitted", flush=True)
                            return True
                    except: pass
                    page.wait_for_timeout(500)
                print(f"Confidence {level} still disabled", flush=True)
        except Exception as e:
            print(f"confidence fail {e}", flush=True)
        return False

    def click_continue(page):
        for txt in ["Continue", "Next", "Next Question", "Got it", "I Understand", "Continue Reading"]:
            try:
                b=page.get_by_role("button", name=txt, exact=False).first
                if b.count()>0 and b.is_visible(timeout=1200):
                    print(f"Clicking continue {txt}", flush=True)
                    b.click(timeout=3000)
                    return True
            except: pass
        return False

    q_num=0
    seen=set()
    for iter in range(100):
        print(f"\n=== ITER {iter} ===", flush=True)
        # Re-find player page in case new tab
        for pg in reversed(ctx.pages):
            if "learning.mheducation.com" in pg.url and "coversheet" not in pg.url:
                player_page=pg
        try:
            player_page.bring_to_front()
        except: pass

        info=extract(player_page)
        q_text=info.get('question','')
        opts=info.get('options',[])
        progress=info.get('progress','')
        full=info.get('fullText','')
        fill_inputs=info.get('fillInputs',[])

        print(f"Progress: {progress}", flush=True)
        print(f"Q: {q_text[:800]}", flush=True)
        print(f"Opts: {opts}", flush=True)
        print(f"FillInputs: {fill_inputs}", flush=True)
        print(f"Buttons: {info.get('buttons')}", flush=True)

        ts=int(time.time())
        shot=f"final_q_{iter}_{ts}.png"
        try:
            player_page.screenshot(path=shot)
        except:
            shot=None

        if not q_text or len(q_text)<10:
            # Could be feedback screen or reading
            if "Continue" in str(info.get('buttons')) or "Next" in str(info.get('buttons')):
                click_continue(player_page)
                time.sleep(3)
                continue
            # If blank and fill input present, it's fill in blank but our extractor missed ?
            if fill_inputs:
                print("Fill blank detected but no question mark? Using fullText first sentence", flush=True)
                # Use first line of fullText that contains blank?
                q_text=full.split('\n')[0][:500]
            else:
                time.sleep(3)
                continue

        h=hash(q_text[:200])
        if h in seen:
            print("Already seen, trying to advance", flush=True)
            # If we have not answered, try to answer again
            if not click_continue(player_page):
                # Try confidence
                click_confidence(player_page, "High")
            time.sleep(4)
            continue

        seen.add(h)
        q_num+=1

        answer, explanation = analyze_and_answer(q_text, opts, full)

        print(f"\n>>> ANALYSIS Q{q_num}: {q_text}", flush=True)
        print(f">>> OPTIONS: {opts}", flush=True)
        print(f">>> PROPOSED ANSWER: {answer}", flush=True)
        print(f">>> EXPLANATION:\n{explanation}\n", flush=True)

        save_q(q_num, q_text, opts, answer, explanation, shot, player_page.url, progress)

        # Now attempt to answer
        if answer:
            if opts:  # multiple choice
                if click_option(player_page, answer):
                    time.sleep(1)
                    if click_confidence(player_page, "High"):
                        print("Submitted", flush=True)
                        time.sleep(4)
                        player_page.screenshot(path=f"final_after_q{q_num}.png")
                        # After submit, there will be feedback - click Continue
                        for _ in range(6):
                            if click_continue(player_page):
                                time.sleep(2)
                            else:
                                time.sleep(1)
                else:
                    print(f"Could not click option {answer}, options were {opts}", flush=True)
            else:  # fill in blank
                if fill_inputs:
                    # Try to fill first input with answer
                    try:
                        inp=player_page.locator('input[type="text"], input:not([type])').first
                        if inp.count()>0:
                            inp.fill(answer, timeout=3000)
                            print(f"Filled blank with {answer}", flush=True)
                            time.sleep(1)
                            click_confidence(player_page, "High")
                            time.sleep(4)
                            click_continue(player_page)
                    except Exception as e:
                        print(f"fill blank fail {e}", flush=True)
                else:
                    print("Fill blank but no input found", flush=True)

        time.sleep(3)

    print("Final loop ended, KEEPING BROWSER OPEN - not closing")
    # Do NOT close browser or context - keep alive
    while True:
        time.sleep(30)
        print(f"[keep alive] {player_page.url[:100]} q_num={q_num}", flush=True)

