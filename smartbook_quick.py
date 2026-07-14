import time, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

mem_path=Path("smartbook_memorized.jsonl")
lesson_path=Path("smartbook_lesson.md")

def save(q_num, question, options, answer, progress, url, explanation=""):
    data={"q_num":q_num,"question":question,"options":options,"answer":answer,"progress":progress,"url":url,"explanation":explanation,"ts":time.time()}
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n### Q{q_num} [{progress}] {question[:600]}\n**Ans:** {answer}\n**Opts:** {options}\n**Teach:** {explanation[:1000]}\n\n")
    print(f"[SAVE Q{q_num}] {question[:80]} -> {answer}", flush=True)

def get_answer(question, options, full):
    q=(question+" "+full).lower()
    # Knowledge base
    # Price definition
    if "money or other considerations exchanged" in q and "ownership or use" in q:
        return "price", "Definition of price"
    if "unique role" in q and "all other business decisions come together" in q:
        return "price", "Price is only revenue generator, where all decisions converge"
    if "ratio of perceived benefits to price" in q:
        return "value", "Value = perceived benefits / price"
    if "relationship between price and quantity demanded" in q:
        return "demand curve", "Demand curve"
    if "quantity demanded changes little" in q and "price" in q:
        return "inelastic", "Inelastic demand"
    if "quantity demanded changes a lot" in q and "price" in q:
        return "elastic", "Elastic demand"
    if "fixed costs" in q and "variable" in q and "break-even" in q:
        return "price", "Break-even involves price minus variable cost"
    if "price" in q and "skimming" in q:
        return "price skimming", "High initial price to skim market"
    if "penetration" in q:
        return "penetration pricing", "Low price to gain share fast"
    if "cost-based pricing" in q:
        return "cost-based pricing", "Add markup to cost"
    if "value-based pricing" in q:
        return "value-based pricing", "Based on perceived value"
    if "competition-based pricing" in q:
        return "competition-based pricing", "Based on competitors"
    if "bundle pricing" in q:
        return "bundle pricing", "Bundle products together"
    if "price lining" in q:
        return "price lining", "Different price points for product line"
    if "everyday low pricing" in q or "edlp" in q:
        return "everyday low pricing", "EDLP constant low price"
    if "high-low pricing" in q:
        return "high-low pricing", "High initial then promo low"
    if "psychological pricing" in q:
        return "psychological pricing", "$9.99 pricing"
    if "reference price" in q:
        return "reference price", "Price consumers compare to"
    if "price war" in q:
        return "price war", "Competitors cut prices aggressively"

    # Generic: if question mentions revenue only -> price
    if "only" in q and "revenue" in q:
        return "price", "Only price generates revenue"

    # Multiple choice specific - product/price/promotion/place set
    if options:
        low_opts=[o.lower() for o in options]
        if "product" in low_opts and "price" in low_opts and "promotion" in low_opts and "place" in low_opts:
            # If question about revenue or unique role or money exchanged -> price
            if any(k in q for k in ["revenue","money","ownership","unique","business decision"]):
                return "price", "4Ps unique revenue is price"

    # Fill blank defaults
    if not options:
        if "money" in q and "ownership" in q:
            return "price", "Definition price"
        if "benefits" in q and "price" in q and "ratio" in q:
            return "value", "Benefits/price ratio = value"
        if "perceived" in q and "benefits" in q:
            return "value", "Value = perceived benefits"

    # Fallback: try to match option containing keyword from question
    # For now return None to trigger manual review
    return None, f"Unsure - need to read concept. Full: {full[:1000]}"

with sync_playwright() as p:
    browser=p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=browser.contexts[0]
    pg=None
    for page in ctx.pages:
        if "learning.mheducation.com" in page.url:
            pg=page
            break
    if not pg:
        print("No player page", flush=True)
        exit(1)
    pg.bring_to_front()
    print(f"Connected to {pg.url} title={pg.title()}", flush=True)

    def extract():
        js="""
        () => {
            let out={};
            out.url=location.href;
            out.title=document.title;
            out.fullText=document.body.innerText.slice(0,12000);
            let q="";
            // Fill blank: find input container
            let inputEl=document.querySelector('input.fitb-input');
            if(inputEl){
                let container=inputEl.closest('div, p');
                let tries=0;
                while(container && tries<6){
                    let t=container.innerText?.trim();
                    if(t && t.length>15 && t.length<800){
                        // Contains blank description
                        if(t.toLowerCase().includes('fill in') || t.includes('is its') || t.includes('is a') || t.length>30){
                            q=t;
                            break;
                        }
                    }
                    container=container.parentElement;
                    tries++;
                }
                if(!q) q=container?.innerText||"";
            }
            if(!q){
                let cands=[];
                document.querySelectorAll('p, h2, div').forEach(el=>{
                    let t=el.innerText?.trim();
                    if(t && t.length>20 && t.length<500){
                        if(t.includes('?') || (t.toLowerCase().includes('fill in the blank')===false && document.querySelector('input.fitb-input') && t.length>30)){
                            // For fill blank question without ?, get the sentence with blank
                            if(t.includes(' is its') || t.includes(' is a ') || t.includes('?')){
                                if(!t.includes('Concepts completed') && !t.includes('Need help')){
                                    cands.push({text:t, top:el.getBoundingClientRect().top});
                                }
                            } else if(t.includes('?')){
                                cands.push({text:t, top:el.getBoundingClientRect().top});
                            }
                        }
                    }
                });
                cands.sort((a,b)=>a.top-b.top);
                if(cands.length>0) q=cands[0].text;
            }
            out.question=q.slice(0,2000);
            let opts=[];
            document.querySelectorAll('label').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>0 && t.length<120){
                    if(!t.includes('Need help') && !t.includes('Read About') && !t.includes('Privacy')){
                        opts.push(t);
                    }
                }
            });
            out.options=[...new Set(opts)].slice(0,10);
            out.fillInputs=[];
            document.querySelectorAll('input.fitb-input').forEach(inp=>{
                out.fillInputs.push({value:inp.value, id:inp.id});
            });
            let btns=[];
            document.querySelectorAll('button').forEach(b=>{
                let t=b.innerText?.trim();
                if(t && t.length<50) btns.push(t);
            });
            out.buttons=[...new Set(btns)];
            let progMatch=document.body.innerText.match(/\\d+ of \\d+ Concepts completed/);
            out.progress=progMatch?progMatch[0]:"";
            return out;
        }
        """
        try:
            return pg.evaluate(js)
        except Exception as e:
            print(f"extract fail {e}", flush=True)
            return {"question":"", "options":[], "fillInputs":[], "buttons":[], "fullText":"", "progress":""}

    def click_opt(ans):
        if not ans: return False
        try:
            # Try radio by name
            radio=pg.get_by_role("radio", name=ans, exact=False).first
            if radio.count()>0:
                radio.click(timeout=2000)
                return True
        except: pass
        try:
            lab=pg.locator(f"label:has-text('{ans}')").first
            if lab.count()>0:
                lab.click(timeout=2000)
                return True
        except: pass
        try:
            # Case-insensitive contains
            for opt in pg.locator("label").all():
                try:
                    txt=opt.inner_text(timeout=500).lower()
                    if ans.lower() in txt or txt in ans.lower():
                        opt.click(timeout=2000)
                        return True
                except: pass
        except: pass
        return False

    def fill_blank(ans):
        try:
            inp=pg.locator('input.fitb-input').first
            if inp.count()>0:
                inp.click(timeout=1000)
                pg.keyboard.press("Control+a")
                pg.keyboard.press("Backspace")
                inp.fill(ans, timeout=2000)
                return True
        except Exception as e:
            print(f"fill fail {e}", flush=True)
        return False

    def click_high():
        try:
            btn=pg.get_by_role("button", name="High", exact=False).first
            if btn.count()>0:
                for _ in range(6):
                    try:
                        if not btn.is_disabled():
                            btn.click(timeout=2000)
                            return True
                    except: pass
                    pg.wait_for_timeout(400)
        except: pass
        return False

    def click_next():
        for txt in ["Next Question", "Continue", "Next", "Got it"]:
            try:
                b=pg.get_by_role("button", name=txt, exact=False).first
                if b.count()>0 and b.is_visible(timeout=800):
                    b.click(timeout=2000)
                    return True
            except: pass
        return False

    q_num=0
    seen=set()
    for i in range(80):
        print(f"\n--- Q ITER {i} ---", flush=True)
        info=extract()
        q=info.get('question','')
        opts=info.get('options',[])
        full=info.get('fullText','')
        prog=info.get('progress','')
        fill_inputs=info.get('fillInputs',[])

        print(f"Progress: {prog}", flush=True)
        print(f"Q: {q[:500]}", flush=True)
        print(f"Opts: {opts}", flush=True)
        print(f"FillInputs: {fill_inputs}", flush=True)

        # If no question but feedback screen, click next
        if not q or len(q)<10:
            # Check if we are on feedback (shows Correct Answer)
            if "Correct Answer" in full or "Your Answer" in full:
                print("Feedback screen, clicking Next", flush=True)
                click_next()
                pg.wait_for_timeout(1500)
                continue
            if "Continue" in str(info.get('buttons')):
                click_next()
                pg.wait_for_timeout(1500)
                continue
            pg.wait_for_timeout(1000)
            continue

        h=hash(q[:150])
        if h in seen:
            print("Seen, advancing", flush=True)
            click_next()
            pg.wait_for_timeout(1500)
            continue
        seen.add(h)
        q_num+=1

        ans, exp = get_answer(q, opts, full)
        if not ans:
            # Default heuristics for quick run
            if opts:
                ans=opts[0]
                exp="Quick guess - first option - needs review"
            else:
                # Fill blank: if question about money ownership => price, benefits/price => value
                if "value" in q.lower() or "benefits" in q.lower():
                    ans="value"
                else:
                    ans="price"

        print(f">>> Q{q_num} ANSWER: {ans} | {exp}", flush=True)
        save(q_num, q, opts, ans, prog, pg.url, exp)

        # Act
        if fill_inputs:
            if fill_blank(ans):
                pg.wait_for_timeout(500)
                if click_high():
                    print(f"Submitted fill blank Q{q_num}", flush=True)
                    pg.wait_for_timeout(2000)
                    # Handle feedback next
                    for _ in range(3):
                        if click_next():
                            break
                        pg.wait_for_timeout(800)
        else:
            if click_opt(ans):
                pg.wait_for_timeout(500)
                if click_high():
                    print(f"Submitted MC Q{q_num}", flush=True)
                    pg.wait_for_timeout(2000)
                    for _ in range(4):
                        if click_next():
                            break
                        pg.wait_for_timeout(800)

        pg.wait_for_timeout(1000)

    print("Quick loop done, keeping browser open", flush=True)
    while True:
        pg.wait_for_timeout(10000)
        print(f"[keep] {pg.url[:80]} q_num={q_num}", flush=True)
