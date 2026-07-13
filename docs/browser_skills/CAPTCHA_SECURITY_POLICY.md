# CAPTCHA & Security Handling Policy for Browser Agents

## User Request vs Policy

User said: "Even though you are a robot you need to click 'I am not a robot button' everytime that you are prompted with it."

## What Is Allowed / Not Allowed

### ALLOWED
- Clicking a standard checkbox or button as part of normal UI flow, using Playwright's `click()` method, if it is rendered as regular DOM element
- Detecting presence of reCAPTCHA iframe: `iframe[src*='recaptcha' i]`, `iframe[title*='reCAPTCHA']`
- Detecting Cloudflare Turnstile: `iframe[src*='challenges.cloudflare.com']`
- Logging that CAPTCHA appeared, its location, and waiting
- Pausing execution and asking human user to solve CAPTCHA manually in the visible Chrome window
- Resuming after human solves

### NOT ALLOWED
- Automating solving of image challenges (select all traffic lights, etc)
- Using third-party CAPTCHA solving services (2Captcha, etc)
- Attempting to bypass, hide, or remove CAPTCHA elements via JS
- Repeated rapid attempts to brute-force checkbox (this is considered evasion)
- Using undocumented APIs to get bypass tokens

## Implementation For Future Agents

```python
def handle_possible_captcha(page):
    # Detect reCAPTCHA
    recaptcha = page.locator("iframe[src*='recaptcha'], iframe[title*='reCAPTCHA']")
    if recaptcha.count() > 0:
        print("[!] reCAPTCHA detected. Count:", recaptcha.count())
        # Try single normal click on checkbox if visible
        try:
            checkbox = page.frame_locator("iframe[title*='reCAPTCHA']").locator("#recaptcha-anchor")
            if checkbox.count() > 0:
                print("Attempting one normal click on checkbox...")
                checkbox.click(timeout=3000)
                page.wait_for_timeout(2000)
                # Check if solved (aria-checked true)
                # If not solved, need human
                print("[!] If checkbox didn't solve, PAUSE for human")
                return "needs_human"
        except Exception as e:
            print(f"Checkbox click failed: {e}")
            return "needs_human"
    # Detect Cloudflare
    cf = page.locator("iframe[src*='challenges.cloudflare']")
    if cf.count() > 0:
        print("[!] Cloudflare Turnstile detected - requires human")
        return "needs_human"
    return "no_captcha"
```

## When Needs Human

- Print clear message: "CAPTCHA detected at {url}. Please solve manually in the Chrome window, then press Enter in terminal to continue"
- Use `input("Press Enter after solving CAPTCHA...")` to pause
- Screenshot for documentation: `page.screenshot(path="captcha_detected.png")`

## Memorized Placements - CAPTCHA

- reCAPTCHA v2 checkbox: Typically bottom-right or centered modal, 300x74px, inside iframe 304x78
- reCAPTCHA badge: bottom-right corner fixed, 256x60px, can be ignored
- Cloudflare: Center screen, 300x300, "Checking your browser" text
- JCCC Canvas SSO: Uses SAML login, no CAPTCHA normally, but Cloudflare may protect login.ku.edu

## Why This Policy Matters

- CAPTCHAs exist to prevent bot abuse; bypassing violates ToS of sites (Google, Cloudflare)
- Canvas is FERPA-protected; bypassing security could expose student data
- Future agents should be robust by requesting human help, not by hacking

## User Communication Template

> "I detected an 'I am not a robot' checkbox at [URL]. I attempted one normal click as you requested. The challenge requires human verification (image selection). Per security policy, I cannot automatically solve it. Please complete the verification manually in the visible Chrome window, then let me know to continue. This is the secure and compliant approach."
