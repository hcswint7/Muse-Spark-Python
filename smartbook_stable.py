import os, time, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv("/Users/hswin/muse-spark-python/.env", override=True)

from playwright.sync_api import sync_playwright

URL="https://canvas.jccc.edu/courses/86815/assignments/2329275?module_item_id=5531124"

mem_path=Path("smartbook_memorized.jsonl")
lesson_path=Path("smartbook_lesson.md")

def get_cdp():
    return "http://localhost:9222"

with sync_playwright() as p:
    print("Connecting to stable Chrome on port 9222...", flush=True)
    browser=p.chromium.connect_over_cdp(get_cdp())
    # Get contexts - there's already one
    if browser.contexts:
        ctx=browser.contexts[0]
    else:
        ctx=browser.new_context()
    # Find existing page with canvas or create new
    pages=ctx.pages
    print(f"Found {len(pages)} pages", flush=True)
    for pg in pages:
        print(f"  page: {pg.url[:120]} title={pg.title()[:50]}", flush=True)
    
    # Use first non-extension page or create new
    target_page=None
    for pg in pages:
        if "canvas.jccc.edu" in pg.url or "mheducation" in pg.url or "login.microsoftonline" in pg.url:
            target_page=pg
            break
    if not target_page:
        target_page=ctx.new_page()
    
    target_page.bring_to_front()
    print(f"Using page {target_page.url}", flush=True)

    # Check if at Microsoft login - need to auto-login
    def is_ms_login(pg):
        u=pg.url.lower()
        return "login.microsoftonline.com" in u or "login.windows" in u or "saml" in u

    if is_ms_login(target_page):
        print("Detected MS login, attempting auto-login", flush=True)
        username=os.getenv("CANVAS_USERNAME")
        password=os.getenv("CANVAS_PASSWORD")
        target_page.wait_for_timeout(3000)
        # Email
        for sel in ["input[type='email']","input[name='loginfmt']","#i0116"]:
            try:
                loc=target_page.locator(sel).first
                if loc.count()>0 and loc.is_visible(timeout=2000):
                    print(f"Filling email via {sel}", flush=True)
                    loc.fill(username, timeout=5000)
                    break
            except: pass
        # Next
        for sel in ["input[type='submit']","#idSIButton9"]:
            try:
                b=target_page.locator(sel).first
                if b.count()>0 and b.is_visible(timeout=2000):
                    b.click(timeout=5000)
                    print(f"Clicked Next {sel}", flush=True)
                    break
            except: pass
        target_page.wait_for_timeout(3000)
        # Password
        for sel in ["input[type='password']","input[name='passwd']","#i0118"]:
            try:
                loc=target_page.locator(sel).first
                loc.wait_for(state="visible", timeout=8000)
                print(f"Filling pw len {len(password)} via {sel}", flush=True)
                loc.fill(password, timeout=5000)
                break
            except: pass
        for sel in ["input[type='submit']","#idSIButton9"]:
            try:
                b=target_page.locator(sel).last
                if b.count()>0 and b.is_visible(timeout=2000):
                    b.click(timeout=5000)
                    print(f"Clicked Signin {sel}", flush=True)
                    break
            except: pass
        target_page.wait_for_timeout(5000)
        # Check MFA - try Ente
        print(f"After login attempt url={target_page.url[:100]}", flush=True)

        # Try Ente MFA auto via v3
        try:
            import sys
            sys.path.insert(0, "./examples")
            from ente_auth_ocr_secure_v3 import fill_microsoft_mfa_v3
            print("Trying MFA auto", flush=True)
            if fill_microsoft_mfa_v3(target_page, "Microsoft"):
                print("MFA success", flush=True)
        except Exception as e:
            print(f"MFA attempt fail {e}", flush=True)
            import traceback; traceback.print_exc()

        # Poll for redirect
        for i in range(20):
            time.sleep(3)
            u=target_page.url.lower()
            print(f"[poll {i*3}s] {target_page.url[:100]}", flush=True)
            if "login.microsoftonline" not in u:
                print("Login succeeded", flush=True)
                break

    # Now go to assignment
    print(f"Navigating to {URL}", flush=True)
    target_page.goto(URL, timeout=30000)
    target_page.wait_for_timeout(4000)
    print(f"After goto {target_page.url} title {target_page.title()}", flush=True)

    # Find Begin button in any page of context
    for _ in range(20):
        found=False
        for pg in ctx.pages:
            try:
                b=pg.get_by_role("button", name="Begin", exact=False).first
                if b.count()>0 and b.is_visible(timeout=800):
                    print(f"Found Begin on {pg.url[:80]}", flush=True)
                    pg.bring_to_front()
                    b.click(timeout=5000)
                    found=True
                    target_page=pg
                    break
            except: pass
        if found:
            break
        time.sleep(1.5)
        print(f"Waiting for Begin... pages={len(ctx.pages)}", flush=True)
        for pg in ctx.pages:
            print(f"  {pg.url[:100]}", flush=True)

    time.sleep(5)
    # Find mheducation page
    for pg in ctx.pages:
        print(f"After Begin: page {pg.url[:120]} title {pg.title()[:60]}", flush=True)

    # Switch to latest mheducation
    for pg in reversed(ctx.pages):
        if "mheducation" in pg.url:
            target_page=pg
            target_page.bring_to_front()
            break

    print(f"Switched to {target_page.url}", flush=True)
    target_page.wait_for_timeout(5000)
    target_page.screenshot(path="stable_welcome.png")
    print("screenshot stable_welcome.png")

    # Try Start Questions
    for _ in range(5):
        try:
            b=target_page.get_by_role("button", name="Start Questions", exact=False).first
            if b.count()>0 and b.is_visible(timeout=1000):
                b.click(timeout=5000)
                print("Clicked Start Questions", flush=True)
                break
        except: pass
        time.sleep(1)

    time.sleep(4)
    target_page.screenshot(path="stable_q0.png")
    print(f"After Start Questions {target_page.url} title {target_page.title()}")

    # Extract current question
    def extract(page):
        js="""
        () => {
            let out={};
            out.url=location.href;
            out.title=document.title;
            let q="";
            let candidates=[];
            document.querySelectorAll('p, div, h2, h3').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>30 && t.length<600 && t.includes('?')){
                    if(!t.includes('Concepts completed') && !t.includes('Dashboard')){
                        candidates.push(t);
                    }
                }
            });
            if(candidates.length>0) q=candidates[0];
            out.question=q.slice(0,2000);
            let opts=[];
            document.querySelectorAll('label, [role="radio"], .choice').forEach(el=>{
                let t=el.innerText?.trim();
                if(t && t.length>0 && t.length<100){
                    if(!t.includes('Need help') && !t.includes('Read About')){
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
            out.progress=(document.body.innerText.match(/\\d+ of \\d+ Concepts completed/)||[""])[0];
            out.fullText=document.body.innerText.slice(0,10000);
            return out;
        }
        """
        try:
            return page.evaluate(js)
        except Exception as e:
            print(f"extract fail {e}", flush=True)
            return {}

    for iter in range(50):
        print(f"\n=== ITER {iter} ===", flush=True)
        # Find player page again
        for pg in reversed(ctx.pages):
            if "mheducation" in pg.url and "coversheet" not in pg.url:
                target_page=pg
        try:
            target_page.bring_to_front()
        except: pass

        info=extract(target_page)
        print(f"Progress: {info.get('progress')}", flush=True)
        print(f"Q: {info.get('question','')[:600]}", flush=True)
        print(f"Opts: {info.get('options')}", flush=True)
        print(f"Buttons: {info.get('buttons')}", flush=True)

        # If no question, try to continue
        if not info.get('question'):
            for txt in ["Continue", "Next", "Got it"]:
                try:
                    b=target_page.get_by_role("button", name=txt, exact=False).first
                    if b.count()>0 and b.is_visible(timeout=800):
                        print(f"Clicking {txt} on non-question screen", flush=True)
                        b.click(timeout=3000)
                        time.sleep(2)
                        break
                except: pass
            time.sleep(3)
            continue

        # Save question
        q_text=info.get('question')
        opts=info.get('options',[])
        # Answer logic
        ans=None
        exp=""
        if "unique role" in q_text and "all other business decisions" in q_text:
            ans="price"
            exp="Price is unique: only revenue-generating element of 4Ps. It's where product costs, promotion value, place/distribution costs all converge to capture value. Product/Place/Promotion are costs."
        elif "marketing mix" in q_text.lower():
            # generic
            pass

        # Click option if we know answer
        if ans:
            try:
                # Try radio
                radio=target_page.get_by_role("radio", name=ans, exact=False).first
                if radio.count()>0:
                    radio.click(timeout=3000)
                    print(f"Clicked answer radio {ans}", flush=True)
                else:
                    lab=target_page.locator(f"label:has-text('{ans}')").first
                    if lab.count()>0:
                        lab.click(timeout=3000)
                        print(f"Clicked label {ans}", flush=True)
            except Exception as e:
                print(f"click ans fail {e}", flush=True)

            # Click High confidence
            try:
                high=target_page.get_by_role("button", name="High", exact=False).first
                if high.count()>0:
                    # Wait for enabled
                    for _ in range(5):
                        if not high.is_disabled():
                            break
                        time.sleep(1)
                    high.click(timeout=3000)
                    print("Clicked High confidence - submitted", flush=True)
                    time.sleep(4)
                    target_page.screenshot(path=f"stable_after_q{iter}.png")
                    # Then Continue
                    for _ in range(5):
                        for txt in ["Continue", "Next", "Next Question"]:
                            try:
                                b=target_page.get_by_role("button", name=txt, exact=False).first
                                if b.count()>0 and b.is_visible(timeout=1000):
                                    print(f"Clicking {txt} after submit", flush=True)
                                    b.click(timeout=3000)
                                    time.sleep(2)
                                    break
                            except: pass
                        time.sleep(1)
            except Exception as e:
                print(f"confidence fail {e}", flush=True)

        time.sleep(5)

    print("Teaching loop ended, keeping browser open (browser will stay alive since not tied to python)")
    # Don't close browser, just exit python - chrome remains
    print("Exiting python, Chrome stays open on 9222")
