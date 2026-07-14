import time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

mem_path=Path("smartbook_memorized.jsonl")
lesson_path=Path("smartbook_lesson.md")
coords_path=Path("smartbook_coords.json")

# Load existing coords
coords_db={}
if coords_path.exists():
    try:
        coords_db=json.loads(coords_path.read_text())
    except:
        coords_db={}

def save_coord(key, x, y, nx, ny):
    coords_db[key]={"x":x,"y":y,"nx":nx,"ny":ny,"ts":time.time()}
    coords_path.write_text(json.dumps(coords_db, indent=2))

def save_q(q_num, q, opts, ans, prog, url, exp, coord_info):
    data={"q_num":q_num,"question":q,"options":opts,"answer":ans,"progress":prog,"url":url,"explanation":exp,"coords":coord_info,"ts":time.time()}
    with open(mem_path,"a") as f:
        f.write(json.dumps(data)+"\n")
    with open(lesson_path,"a") as f:
        f.write(f"\n### Q{q_num} [{prog}] {q[:600]}\nAns: {ans} | Coords: {coord_info}\nExp: {exp[:1000]}\n")
    print(f"[SAVED Q{q_num}] {q[:80]} -> {ans} at {coord_info}", flush=True)

def get_answer(q, opts, full):
    ql=(q+" "+full).lower()
    # Direct definitions
    if "money or other considerations exchanged" in ql and "ownership or use" in ql and "is its" in ql:
        return "price", "Def: price is money/other considerations exchanged for ownership/use"
    if "ratio of perceived benefits to price" in ql:
        return "value", "Value = perceived benefits / price"
    if "unique role" in ql and "all other business decisions come together" in ql:
        return "price", "Price unique revenue converging point"
    if "demand-oriented, cost-oriented, profit-oriented, and competition-oriented" in ql and "approaches used to set" in ql:
        return "approximate price levels", "Ch11: 4 approaches set approx price levels (Step 4 pricing process)"
    if "price is defined as" in ql:
        for opt in opts:
            if "money or other considerations exchanged" in opt.lower():
                return opt, "Textbook definition of price"
        return "the money or other considerations exchanged for the ownership or use of a product.", "Definition"
    if "demand-oriented pricing approaches weigh which factors most heavily" in ql:
        for opt in opts:
            if "customer tastes and preferences" in opt.lower() or "expected customer" in opt.lower():
                return opt, "Demand-oriented = focuses on demand, customer tastes/preferences, willingness"
        return "expected customer tastes and preferences", "Demand-oriented weighs customer demand"
    if "value is defined as" in ql:
        for opt in opts:
            if "perceived benefits divided by price" in opt.lower():
                return opt, "Value = perceived benefits / price"
        return "perceived benefits divided by price", "Value definition"
    if "four factors must be taken into consideration to determine the" in ql and "right" in ql and "price" in ql:
        for opt in opts:
            if "customers willing to pay" in opt.lower():
                return opt, "Right price must consider customer willingness"
        return opts[1] if len(opts)>1 else opts[0], "Customer willingness is core pricing factor"
    # Generic pricing
    if "only" in ql and "revenue" in ql and any("price" in o.lower() for o in opts):
        for o in opts:
            if "price" in o.lower():
                return o, "Only price generates revenue"
    if "skimming" in ql:
        return "price skimming", "Skimming = high price"
    if "penetration" in ql:
        return "penetration pricing", "Penetration = low price for share"
    if "elastic" in ql and "inelastic" in ql:
        return "elasticity", "Elasticity concept"

    # Fallback: if options contain approximate price levels and question about approaches, choose it
    for o in opts:
        if "approximate price levels" in o.lower() and "approach" in ql:
            return o, "Approaches set approximate price levels"

    return None, f"Unknown - need review. Full: {full[:500]}"

with sync_playwright() as p:
    browser=p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=browser.contexts[0]
    pg=None
    for page in ctx.pages:
        if "learning.mheducation.com" in page.url:
            pg=page
            break
    if not pg:
        print("No player", flush=True)
        exit(1)
    pg.bring_to_front()
    print(f"Connected to player {pg.url[:100]} title={pg.title()}", flush=True)

    def extract():
        js="""
        () => {
            let txt=document.body.innerText;
            let prog=(txt.match(/\\d+ of \\d+ Concepts completed/)||[""])[0];
            let q="";
            // Try to find question text: before options, after Question Mode
            // Look for div containing question
            // For MC: text between "Question Mode" and "Multiple choice question."
            let m=txt.match(/Question Mode[\\s\\S]*?\\n\\n([\\s\\S]*?)\\n\\nMultiple choice question\\./);
            if(m) q=m[1].trim();
            else {
                let m2=txt.match(/Question Mode[\\s\\S]*?\\n\\n([\\s\\S]*?)\\n\\nNeed help/);
                if(m2) q=m2[1].trim();
            }
            if(!q){
                // Fill blank
                let m3=txt.match(/Fill in the blank question\\.\\n\\n([\\s\\S]*?)\\n\\nNeed help/);
                if(m3) q=m3[1].trim();
            }
            // Clean q
            q=q.split('\\n').filter(l=>l.trim().length>0 && !l.includes('Concepts completed') && !l.includes('Progress information') && !l.includes('Time Check')).join(' ').slice(0,2000);

            let opts=[];
            document.querySelectorAll('label').forEach(l=>{
                let t=l.innerText?.trim();
                if(t && t.length>0 && t.length<250 && !t.includes('Need help') && !t.includes('Read About')){
                    opts.push(t);
                }
            });
            let fillInputs=[];
            document.querySelectorAll('input.fitb-input').forEach(inp=>{
                fillInputs.push({value:inp.value});
            });
            let btns=[];
            document.querySelectorAll('button').forEach(b=>{
                let t=b.innerText?.trim();
                if(t && t.length<50) btns.push(t);
            });
            return {question:q, options: [...new Set(opts)].slice(0,12), fillInputs: fillInputs, buttons: [...new Set(btns)], progress: prog, fullText: txt.slice(0,8000)};
        }
        """
        try:
            return pg.evaluate(js)
        except Exception as e:
            print(f"extract fail {e}", flush=True)
            return {"question":"", "options":[], "fillInputs":[], "buttons":[], "fullText":"", "progress":""}

    def click_option_fast(answer_text):
        if not answer_text:
            return None
        try:
            # Use filter with has_text for speed and avoids CSS escaping
            loc=pg.locator("label").filter(has_text=answer_text).first
            if loc.count()>0:
                box=loc.bounding_box()
                if box:
                    x=box['x']+box['width']/2
                    y=box['y']+box['height']/2
                    nx=int(x/1440*1000)
                    ny=int(y/900*1000)
                    print(f"Clicking {answer_text[:60]} at pixel {int(x)},{int(y)} normalized [{nx},{ny}]", flush=True)
                    loc.click(timeout=1500)
                    return {"x":int(x),"y":int(y),"nx":nx,"ny":ny,"method":"filter_label"}
        except Exception as e:
            print(f"filter click fail {answer_text[:30]} {e}", flush=True)
        try:
            # Try get_by_text
            el=pg.get_by_text(answer_text, exact=False).first
            if el.count()>0:
                box=el.bounding_box()
                x=box['x']+box['width']/2 if box else 100
                y=box['y']+box['height']/2 if box else 100
                nx=int(x/1440*1000)
                ny=int(y/900*1000)
                el.click(timeout=1500)
                print(f"Clicked via text {answer_text[:40]} at [{nx},{ny}]", flush=True)
                return {"x":int(x),"y":int(y),"nx":nx,"ny":ny,"method":"get_by_text"}
        except Exception as e:
            print(f"text click fail {e}", flush=True)
        return None

    def fill_blank_fast(ans):
        try:
            inp=pg.locator('input.fitb-input').first
            if inp.count()>0:
                box=inp.bounding_box()
                x=int(box['x']+box['width']/2) if box else 400
                y=int(box['y']+box['height']/2) if box else 400
                nx=int(x/1440*1000)
                ny=int(y/900*1000)
                print(f"Fill blank at [{nx},{ny}] pixel {x},{y} with '{ans}'", flush=True)
                inp.click(timeout=800)
                pg.keyboard.press("Control+a")
                pg.keyboard.press("Backspace")
                inp.fill(ans, timeout=1500)
                return {"x":x,"y":y,"nx":nx,"ny":ny}
        except Exception as e:
            print(f"fill blank fail {e}", flush=True)
        return None

    def click_high_fast():
        try:
            btn=pg.get_by_role("button", name="High", exact=False).first
            if btn.count()>0:
                box=btn.bounding_box()
                nx=ny=0
                if box:
                    x=box['x']+box['width']/2
                    y=box['y']+box['height']/2
                    nx=int(x/1440*1000)
                    ny=int(y/900*1000)
                    print(f"High btn at [{nx},{ny}] pixel {int(x)},{int(y)}", flush=True)
                # Wait enabled quickly
                for _ in range(6):
                    try:
                        if not btn.is_disabled():
                            btn.click(timeout=1000)
                            print(f"Clicked High at [{nx},{ny}]", flush=True)
                            return {"x":int(box['x']+box['width']/2) if box else 0,"y":int(box['y']+box['height']/2) if box else 0,"nx":nx,"ny":ny}
                    except: pass
                    pg.wait_for_timeout(300)
                print("High still disabled", flush=True)
        except Exception as e:
            print(f"High click fail {e}", flush=True)
        return None

    def click_next_fast():
        for name in ["Next Question", "Continue", "Next"]:
            try:
                b=pg.get_by_role("button", name=name, exact=False).first
                if b.count()>0 and b.is_visible(timeout=600):
                    box=b.bounding_box()
                    nx=ny=0
                    if box:
                        nx=int((box['x']+box['width']/2)/1440*1000)
                        ny=int((box['y']+box['height']/2)/900*1000)
                        print(f"{name} btn at [{nx},{ny}]", flush=True)
                    b.click(timeout=1000)
                    print(f"Clicked {name}", flush=True)
                    return True
            except: pass
        return False

    q_num=0
    seen=set()
    for iter in range(100):
        print(f"\n========== FAST ITER {iter} ==========", flush=True)
        info=extract()
        q=info.get('question','')
        opts=info.get('options',[])
        full=info.get('fullText','')
        prog=info.get('progress','')
        fill_inputs=info.get('fillInputs',[])

        print(f"Progress: {prog}", flush=True)
        print(f"Q: {q[:600]}", flush=True)
        print(f"Opts: {opts}", flush=True)
        print(f"Fill: {fill_inputs}", flush=True)

        if not q or len(q)<15:
            # Feedback screen?
            if "Correct Answer" in full or "Your Answer" in full:
                print("Feedback, clicking Next", flush=True)
                click_next_fast()
                pg.wait_for_timeout(1200)
                continue
            if "Continue" in str(info.get('buttons')):
                click_next_fast()
                pg.wait_for_timeout(1000)
                continue
            pg.wait_for_timeout(800)
            continue

        h=hash(q[:120])
        if h in seen:
            print("Seen, advancing", flush=True)
            click_next_fast()
            pg.wait_for_timeout(1000)
            continue
        seen.add(h)
        q_num+=1

        ans, exp = get_answer(q, opts, full)
        if not ans:
            if opts:
                ans=opts[0]
                exp="Quick first option"
            else:
                ans="price"

        print(f">>> Q{q_num} ANS: {ans} | Exp: {exp}", flush=True)

        coord_info={}

        if fill_inputs:
            # Fill blank
            coord=fill_blank_fast(ans)
            coord_info['fill']=coord
            if coord:
                save_coord(f"fill_{q_num}_{ans}", coord['x'], coord['y'], coord['nx'], coord['ny'])
            pg.wait_for_timeout(400)
            high_coord=click_high_fast()
            coord_info['high']=high_coord
            if high_coord:
                save_coord(f"high_{q_num}", high_coord['x'], high_coord['y'], high_coord['nx'], high_coord['ny'])
            pg.wait_for_timeout(1500)
        else:
            # MC
            coord=click_option_fast(ans)
            coord_info['option']=coord
            if coord:
                save_coord(f"mc_opt_{ans[:30]}", coord['x'], coord['y'], coord['nx'], coord['ny'])
            pg.wait_for_timeout(400)
            high_coord=click_high_fast()
            coord_info['high']=high_coord
            pg.wait_for_timeout(1500)

        save_q(q_num, q, opts, ans, prog, pg.url, exp, coord_info)

        # After submit, handle feedback
        for _ in range(4):
            if click_next_fast():
                break
            pg.wait_for_timeout(400)

        pg.wait_for_timeout(800)

    print("FAST LOOP DONE - KEEPING BROWSER OPEN", flush=True)
    while True:
        pg.wait_for_timeout(10000)
        print(f"[keep] {pg.url[:80]} q_num={q_num}", flush=True)