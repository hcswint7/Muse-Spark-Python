import os, time, json, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)

from playwright.sync_api import sync_playwright

mem_path=Path("smartbook_memorized.jsonl")
lesson_path=Path("smartbook_lesson.md")
practice_test_path=Path("smartbook_practice_test.md")

# Clear and start fresh for this session but keep old
# mem_path.write_text("")  # don't clear, append

def save(q_num, question, options, answer, explanation, progress, screenshot, url):
    data={
        "q_num":q_num,
        "question":question,
        "options":options,
        "answer":answer,
        "explanation":explanation,
        "progress":progress,
        "screenshot":screenshot,
        "url":url,
        "ts":time.time()
    }
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n---\n\n## Q{q_num} [{progress}] - {question[:500]}\n\n**Type:** {'Fill-in-Blank' if not options else 'Multiple Choice'}\n**Options:** {options}\n**Correct Answer:** **{answer}**\n\n### Teaching:\n{explanation}\n\n**Screenshot:** {screenshot}\n**URL:** {url[:100]}\n\n")
    print(f"Saved Q{q_num}", flush=True)
    return data

def analyze(question, options, full_text):
    """
    Master analyzer for Ch 11-12 Pricing (Marketing: The Core)
    Returns (answer, explanation)
    """
    q = (question or "").lower()
    ft = (full_text or "").lower()
    text = (q + " " + ft).lower()

    # Normalize
    def contains(*words):
        return all(w.lower() in text for w in words)

    # --- Pricing definitions ---
    if "money or other considerations exchanged for the ownership or use" in text and "is its" in text:
        return "price", """**Concept:** Definition of Price

**Full Definition:** Price is the money or other considerations (including other products, services, or time) exchanged for the ownership or use of a good or service.

**Teaching:**
- This is the foundational definition from Ch 11.
- Price = what customer gives up to get product.
- Can be monetary or barter.
- This is why price is unique - it's the value exchange point.

**Answer: price**

**Memory hook:** M-O-O-U = Money for Ownership or Use = Price"""

    if "element of the marketing mix has a unique role" in text and "all other business decisions come together" in text:
        return "price", """**Concept:** Price's Unique Role in 4Ps

**Teaching:**
- 4Ps: Product, Price, Place, Promotion
- Product, Place, Promotion = COSTS to company
- Price = ONLY element that generates REVENUE
- All other decisions converge at price: product development cost affects price, channel costs (place) affect price, ad spend affects price, etc.
- Price captures value.

**Answer: price**"""

    if "value" in text and "benefit" in text and ("ratio" in text or "perception" in text or "trade-off" in text):
        # Value = perceived benefits / price
        return "value", """**Concept:** Customer Value

**Formula:** Value = Perceived Benefits / Price (or Benefits - Costs)

**Teaching:** Customers weigh what they get (functional, emotional, social benefits) vs what they give (price, time, effort). Higher benefits or lower price = higher value. This drives pricing strategy.

**Answer depends on blank but concept is Value**
"""

    # Break-even
    if "break-even" in text or "break even" in text:
        if "fixed" in text and "variable" in text:
            return "price", "Break-even: Fixed Costs / (Unit Price - Variable Cost per unit) = units needed. But question might ask blank for price. Teaching: Break-even point where total revenue = total costs."

    # Price elasticity
    if "elasticity" in text:
        if "sensitive" in text or "change" in text:
            return "elastic", "Elasticity measures responsiveness of demand to price. Elastic = sensitive (luxuries). Inelastic = insensitive (necessities, gas). Formula: % change qty / % change price."

    # Demand curve types
    if "demand curve" in text:
        return "demand curve", "Demand curve shows relationship price vs quantity demanded - typically downward sloping."

    # Pricing strategies
    if "skimming" in text:
        return "price skimming", """**Skimming:** High initial price to skim cream of market (early adopters, innovators) who pay premium for new product, then gradually lower. Example: iPhone launch $999 then drops. Goal: maximize profit per unit early, recover R&D."""

    if "penetration pricing" in text:
        return "penetration pricing", """**Penetration:** Low initial price to penetrate market quickly, gain market share, deter competitors, achieve economies of scale. Example: Spotify $0.99 intro, Netflix low start. Risk: perceived low quality, hard to raise later."""

    if "cost-based pricing" in text or "cost plus" in text:
        return "cost-based pricing", "Cost-based: add markup to cost. Simple but ignores demand/value."

    if "competition-based" in text:
        return "competition-based pricing", "Set price based on competitors."

    if "value-based" in text:
        return "value-based pricing", "Value-based: set price based on perceived customer value, not cost. Most strategic."

    # Marketing mix
    if "4 ps" in text or "marketing mix" in text:
        return "marketing mix", "The 4Ps: Product, Price, Place, Promotion - controllable factors to satisfy target market."

    # Fill blank generic for price definition occurrences
    if "money" in text and "ownership" in text and "use" in text:
        return "price", "Definition of price: money/other considerations exchanged for ownership/use."

    # If multiple choice with options product, price, promotion, place and question about revenue
    if "revenue" in text and any("product" in o.lower() for o in options) and any("price" in o.lower() for o in options):
        return "price", "Only price generates revenue."

    # For Fill blank where options empty, try to infer from sentence structure
    # If blank sentence contains "is its ____" and context is money exchanged => price
    # If blank is about place where all decisions come together => price

    # Default: if options include price and question about money/value, choose price
    if not options:  # fill blank
        # Try keyword mapping
        if "money" in text or "revenue" in text or "ownership" in text:
            return "price", "Money/ownership exchange = price definition."

    # For multiple choice, pick most likely
    if options:
        # If one option is price and question contains unique/revenue/money
        if "price" in opts_lower(options) and ("money" in text or "revenue" in text or "unique" in text):
            return get_opt(options, "price"), f"Question about revenue/money/unique role => price. Q: {question}"
    
    return None, f"Need manual teaching for: {question[:500]} | Full: {full_text[:2000]}"

def opts_lower(options):
    return [o.lower() for o in options]

def get_opt(options, target):
    for o in options:
        if target.lower() in o.lower():
            return o
    return options[0] if options else target

with sync_playwright() as p:
    print("Connecting to stable Chrome 9222...", flush=True)
    browser=p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=browser.contexts[0]
    # Find player
    player=None
    for pg in ctx.pages:
        if "learning.mheducation.com" in pg.url:
            player=pg
            break
    if not player:
        print("No player found, listing pages", flush=True)
        for pg in ctx.pages:
            print(f"  {pg.url[:150]}")
        exit(1)

    player.bring_to_front()
    print(f"Player url: {player.url} title: {player.title()}", flush=True)

    def extract(page):
        js="""
        () => {
            let out={};
            out.url=location.href;
            out.title=document.title;
            out.fullText=document.body.innerText.slice(0,15000);
            // Find question - multiple strategies
            let q="";
            // For fill blank, find text before input
            let inputEl=document.querySelector('input.fitb-input, input[type="text"]');
            if(inputEl){
                // Walk up to find container text
                let container=inputEl.closest('div, p, section');
                let tries=0;
                while(container && tries<5){
                    let t=container.innerText?.trim();
                    if(t && t.length>20 && t.length<1000){
                        q=t;
                        break;
                    }
                    container=container.parentElement;
                    tries++;
                }
                if(!q){
                    // fallback: preceding sibling text
                    let prev=inputEl.parentElement?.innerText || "";
                    q=prev.slice(0,2000);
                }
            }
            // If not fill, find ? question
            if(!q){
                let cands=[];
                document.querySelectorAll('p, div, h2, h3').forEach(el=>{
                    let t=el.innerText?.trim();
                    if(t && t.length>25 && t.length<600 && t.includes('?')){
                        if(!t.includes('Concepts completed') && !t.includes('Need help')){
                            if((t.match(/\\?/g)||[]).length<=2) cands.push({text:t, top:el.getBoundingClientRect().top});
                        }
                    }
                });
                cands.sort((a,b)=>a.top-b.top);
                if(cands.length>0) q=cands[0].text;
            }
            out.question=q.slice(0,2000);
            let opts=[];
            document.querySelectorAll('label, [role="radio"]').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>0 && t.length<120){
                    if(!t.includes('Need help') && !t.includes('Read About') && !t.includes('Privacy') && !t.includes('Exit') && !t.includes('Progress')){
                        opts.push(t);
                    }
                }
            });
            out.options=[...new Set(opts)].slice(0,12);
            let fillInputs=[];
            document.querySelectorAll('input[type="text"], input.fitb-input, input:not([type])').forEach(inp=>{
                fillInputs.push({placeholder: inp.placeholder||inp.getAttribute('aria-label')||'', value: inp.value, id: inp.id});
            });
            out.fillInputs=fillInputs;
            let btns=[];
            document.querySelectorAll('button').forEach(b=>{
                let t=b.innerText?.trim();
                if(t && t.length<60) btns.push(t);
            });
            out.buttons=[...new Set(btns)];
            out.progress=(document.body.innerText.match(/\\d+ of \\d+ Concepts completed/)||[""])[0];
            return out;
        }
        """
        try:
            return page.evaluate(js)
        except Exception as e:
            print(f"extract fail {e}", flush=True)
            return {"question":"", "options":[], "fillInputs":[], "buttons":[], "fullText":"", "progress":""}

    def click_option(page, ans):
        if not ans: return False
        try:
            radio=page.get_by_role("radio", name=ans, exact=False).first
            if radio.count()>0:
                radio.click(timeout=3000)
                print(f"Clicked radio {ans}", flush=True)
                return True
        except: pass
        try:
            lab=page.locator(f"label:has-text('{ans}')").first
            if lab.count()>0 and lab.is_visible(timeout=1500):
                lab.click(timeout=3000)
                print(f"Clicked label {ans}", flush=True)
                return True
        except: pass
        try:
            txt=page.get_by_text(ans, exact=False).first
            if txt.count()>0:
                txt.click(timeout=3000)
                print(f"Clicked text {ans}", flush=True)
                return True
        except: pass
        return False

    def fill_blank(page, ans):
        if not ans: return False
        try:
            inp=page.locator('input.fitb-input, input[type="text"], input:not([type])').first
            if inp.count()>0:
                inp.fill(ans, timeout=3000)
                print(f"Filled blank with '{ans}'", flush=True)
                return True
        except Exception as e:
            print(f"fill blank fail {e}", flush=True)
        return False

    def click_conf(page, level="High"):
        try:
            btn=page.get_by_role("button", name=level, exact=False).first
            if btn.count()>0:
                for _ in range(8):
                    try:
                        if not btn.is_disabled():
                            btn.click(timeout=3000)
                            print(f"Clicked confidence {level}", flush=True)
                            return True
                    except: pass
                    page.wait_for_timeout(500)
                print(f"Confidence {level} still disabled after wait", flush=True)
        except Exception as e:
            print(f"confidence {level} fail {e}", flush=True)
        return False

    def click_cont(page):
        for txt in ["Continue", "Next", "Next Question", "Got it", "I Understand", "Continue Reading", "Done"]:
            try:
                b=page.get_by_role("button", name=txt, exact=False).first
                if b.count()>0 and b.is_visible(timeout=1200):
                    print(f"Clicking {txt}", flush=True)
                    b.click(timeout=3000)
                    return True
            except: pass
        return False

    q_num=0
    seen=set()
    consecutive_fails=0

    for iter in range(100):
        print(f"\n===== ITER {iter} =====\n", flush=True)
        # Ensure player is front
        for pg in reversed(ctx.pages):
            if "learning.mheducation.com" in pg.url and "coversheet" not in pg.url:
                player=pg
        try:
            player.bring_to_front()
        except: pass

        info=extract(player)
        q_text=info.get('question','')
        opts=info.get('options',[])
        full=info.get('fullText','')
        progress=info.get('progress','')
        fill_inputs=info.get('fillInputs',[])
        buttons=info.get('buttons',[])

        print(f"Progress: {progress}", flush=True)
        print(f"Q: {q_text[:600]}", flush=True)
        print(f"Opts: {opts}", flush=True)
        print(f"FillInputs: {fill_inputs}", flush=True)
        print(f"Buttons: {buttons}", flush=True)

        # Screenshot
        ts=int(time.time())
        shot=f"master_q_{iter}_{ts}.png"
        try:
            player.screenshot(path=shot)
        except:
            shot=None

        # If no question but has continue button (feedback screen), continue
        if not q_text or len(q_text)<10:
            # Check if feedback screen after correct/incorrect
            if any(b in ["Continue", "Next", "Next Question"] for b in buttons):
                if click_cont(player):
                    time.sleep(3)
                    continue
            # If empty and no continue, wait
            print("No question found, waiting 3s", flush=True)
            time.sleep(3)
            consecutive_fails+=1
            if consecutive_fails>5:
                print("Too many fails, trying to refresh logic", flush=True)
                consecutive_fails=0
            continue

        consecutive_fails=0
        h=hash(q_text[:200])
        if h in seen:
            print("Seen before, trying to advance", flush=True)
            if not click_cont(player):
                click_conf(player, "High")
            time.sleep(3)
            continue

        seen.add(h)
        q_num+=1

        answer, explanation = analyze(q_text, opts, full)

        print(f"\n>>> Q{q_num} ANALYSIS <<<\nQuestion: {q_text}\nFullContext: {full[:1000]}\nOptions: {opts}\nFillInputs: {fill_inputs}\nProgress: {progress}\n", flush=True)
        print(f"Proposed Answer: {answer}\nExplanation: {explanation}\n", flush=True)

        save(q_num, q_text, opts, answer, explanation, progress, shot, player.url)

        # Now perform actions: analyze, click answer, click confidence
        if fill_inputs:  # fill blank
            if answer:
                if fill_blank(player, answer):
                    time.sleep(1)
                    if click_conf(player, "High"):
                        print("Submitted fill blank with High", flush=True)
                        time.sleep(4)
                        player.screenshot(path=f"master_after_q{q_num}.png")
                        # After submit, click Continue
                        for _ in range(5):
                            if click_cont(player):
                                time.sleep(2)
                            else:
                                time.sleep(1)
            else:
                print(f"No answer for fill blank Q{q_num}, skipping", flush=True)
        else:  # multiple choice
            if answer:
                # Normalize answer to match option text
                matched=None
                for opt in opts:
                    if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                        matched=opt
                        break
                if not matched and opts:
                    # If answer is exact like "price", find option that equals price
                    matched=answer if answer in opts else get_opt_fallback(opts, answer)
                else:
                    matched=answer

                if click_option(player, matched):
                    time.sleep(1)
                    if click_conf(player, "High"):
                        print(f"Submitted Q{q_num} with High", flush=True)
                        time.sleep(4)
                        player.screenshot(path=f"master_after_q{q_num}.png")
                        for _ in range(6):
                            if click_cont(player):
                                time.sleep(2)
                            else:
                                time.sleep(1)
                else:
                    print(f"Failed to click option {matched}", flush=True)
            else:
                print(f"No answer determined for Q{q_num}", flush=True)

        time.sleep(3)

    print("Finished loop, KEEPING BROWSER OPEN - not closing", flush=True)
    # Keep python alive but not closing browser
    while True:
        time.sleep(30)
        try:
            print(f"[keep] {player.url[:100]} q_num={q_num} progress={player.evaluate('()=>{return document.body.innerText.match(/\\\\d+ of \\\\d+ Concepts completed/)?.[0]||\"\"}')} ", flush=True)
        except:
            print("[keep] player check fail", flush=True)

def get_opt_fallback(options, target):
    for o in options:
        if target.lower() in o.lower():
            return o
    return options[0] if options else target
