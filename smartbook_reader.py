import os, time, json, re
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

COURSE_ID=86815
ASSIGNMENT_ID=2329275
URL=f"https://canvas.jccc.edu/courses/{COURSE_ID}/assignments/{ASSIGNMENT_ID}?module_item_id=5531124"

questions_mem=[]

def extract_questions(page):
    print("[extract] Getting page content", flush=True)
    try:
        title=page.title()
        print(f"title: {title}", flush=True)
        url=page.url
        print(f"url: {url}", flush=True)
    except Exception as e:
        print(f"extract title fail {e}", flush=True)

    # Get main text
    try:
        body_text=page.locator("body").inner_text(timeout=5000)[:20000]
        print(f"[body] {len(body_text)} chars", flush=True)
        print(body_text[:5000], flush=True)
    except Exception as e:
        print(f"body fail {e}", flush=True)
        body_text=""

    # Check iframes - SmartBook likely in iframe
    try:
        frames=page.frames
        print(f"[frames] {len(frames)} frames", flush=True)
        for i,f in enumerate(frames):
            try:
                print(f"  frame {i}: url={f.url[:200]} name={f.name}", flush=True)
                # try inner text
                ft=f.locator("body").inner_text(timeout=3000)[:5000]
                if len(ft)>100:
                    print(f"    frame {i} body len {len(ft)} preview: {ft[:1000]}", flush=True)
            except Exception as fe:
                print(f"    frame {i} fail {fe}", flush=True)
    except Exception as e:
        print(f"frames fail {e}", flush=True)

    # Try to find question elements via JS
    js="""
    () => {
        let out=[];
        // Find all text that looks like questions
        let els=document.querySelectorAll('div, p, span, h1,h2,h3, li');
        for(let el of els){
            let t=el.innerText?.trim();
            if(!t) continue;
            if(t.length>20 && t.length<2000){
                // Heuristic: contains ? or looks like multiple choice
                if(t.includes('?') || /[A-D]\\s+[A-Z]/.test(t) || el.querySelector('input[type=radio]') || el.querySelector('button')){
                    out.push({tag: el.tagName, cls: el.className, text: t.slice(0,2000), html: el.outerHTML.slice(0,3000)});
                    if(out.length>50) break;
                }
            }
        }
        return out;
    }
    """
    try:
        qs=page.evaluate(js)
        print(f"[js extract] found {len(qs)} potential Q elements", flush=True)
        for q in qs[:10]:
            print(f" - {q['text'][:500]}", flush=True)
        return qs
    except Exception as e:
        print(f"js fail {e}", flush=True)
        return []

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
    page.wait_for_timeout(4000)
    print(f"After goto: {page.url} | {page.title()}", flush=True)
    page.screenshot(path="smartbook_initial.png", full_page=False)
    print("screenshot smartbook_initial.png", flush=True)

    # If redirected to Connect / SmartBook, follow
    time.sleep(2)
    # Try to find Load assignment button etc
    for txt in ["Load", "Launch", "Open in new tab", "Connect", "SmartBook"]:
        try:
            btn=page.get_by_role("button", name=txt, exact=False).first
            if btn.count()>0 and btn.is_visible(timeout=1500):
                print(f"Clicking button {txt}", flush=True)
                btn.click(timeout=5000)
                page.wait_for_timeout(3000)
        except Exception as e:
            pass
        try:
            link=page.get_by_role("link", name=txt, exact=False).first
            if link.count()>0 and link.is_visible(timeout=1500):
                print(f"Clicking link {txt}", flush=True)
                link.click(timeout=5000)
                page.wait_for_timeout(3000)
        except: pass

    print(f"After attempt clicks: {page.url} title {page.title()}", flush=True)
    page.screenshot(path="smartbook_after_clicks.png")
    
    qs=extract_questions(page)

    # Also check if new page/tab opened
    print(f"pages count {len(ctx.pages)}", flush=True)
    for idx, pg in enumerate(ctx.pages):
        print(f" page {idx}: {pg.url} | {pg.title()}", flush=True)
        if idx!=0:
            try:
                pg.bring_to_front()
                time.sleep(1)
                pg.screenshot(path=f"smartbook_page_{idx}.png")
                extract_questions(pg)
            except Exception as e:
                print(f"page {idx} fail {e}", flush=True)

    # Keep alive for teaching - infinite resilient loop
    print("=== SMARTBOOK READER READY - KEEPING BROWSER OPEN ===", flush=True)
    print("Browser is same profile, logged in, at assignment. Ready to teach.", flush=True)
    # Save questions to file for practice test creation
    with open("smartbook_questions_raw.json","w") as f:
        json.dump(qs,f,indent=2)
    print("saved smartbook_questions_raw.json", flush=True)

    for i in range(9999):
        time.sleep(10)
        try:
            u=ctx.pages[0].url if ctx.pages else page.url
            t=ctx.pages[0].title() if ctx.pages else page.title()
            print(f"[keep {i*10}s] {u[:120]} | {t[:80]}", flush=True)
        except Exception as e:
            print(f"[keep] err {e}", flush=True)
