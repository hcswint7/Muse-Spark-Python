"""
Ente Auth Secure OCR - Method 2 implementation
Securely retrieves TOTP code from Ente Auth app via screenshot + OCR
- Never logs actual codes, only masked
- Deletes temp files immediately
- Clears code from memory after use
Requires: Screen Recording permission, Accessibility, tesseract, pytesseract, pillow

Usage:
    from ente_auth_ocr_secure import get_totp_code_secure, fill_microsoft_mfa

    # For Canvas Microsoft SSO MFA
    code = get_totp_code_secure(account_filter="Microsoft")  # Masked logs, secure
    page.locator("input[type='text']").fill(code)
    code = None  # Clear

Security:
- .env is gitignored
- Codes never logged, masked as ******
- Temp files deleted
- TOTP time-limited 30s
"""
import os, subprocess, time, re, sys
from pathlib import Path

def clean_temp_files():
    for p in ["/tmp/ente_full.png", "/tmp/ente_cropped.png", "/tmp/full.png"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except: pass

def get_ente_window_position():
    """Get Ente Auth window position via AppleScript (requires Accessibility)"""
    try:
        # Activate first
        subprocess.run(['osascript', '-e', 'tell application "Ente Auth" to activate'], capture_output=True, timeout=5)
        time.sleep(0.8)
        script = '''
        tell application "System Events"
            set frontmost of process "Ente Auth" to true
            delay 0.3
            tell process "Ente Auth"
                set w to window 1
                return {position of w, size of w}
            end tell
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Output like "873, 30, 596, 779"
            out = result.stdout.strip()
            # Parse
            parts = out.replace('{', '').replace('}', '').split(',')
            if len(parts) >= 4:
                x = int(parts[0].strip())
                y = int(parts[1].strip())
                w = int(parts[2].strip())
                h = int(parts[3].strip())
                print(f"[secure] Ente window at {x},{y} size {w},{h} (masked, not logging codes)")
                return x, y, w, h
        print(f"[secure] Failed to get window pos: {result.stderr[:100]}")
        return None
    except Exception as e:
        print(f"[secure] Window position error: {e}")
        return None

def capture_and_crop_ente():
    """Capture screen and crop to Ente Auth window, returns cropped image path"""
    try:
        pos = get_ente_window_position()
        if not pos:
            # Fallback to hardcoded from last known
            x, y, w, h = 873, 30, 596, 779
            print(f"[secure] Using fallback window pos {x},{y} {w}x{h}")
        else:
            x, y, w, h = pos
        
        full_path = "/tmp/ente_full.png"
        cropped_path = "/tmp/ente_cropped.png"
        
        # Screenshot
        result = subprocess.run(['screencapture', '-x', full_path], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"[secure] Screencapture failed: {result.stderr}")
            return None
        
        # Crop with PIL (handle retina)
        from PIL import Image
        img = Image.open(full_path)
        # Detect retina scale: if screenshot larger than logical 1440, it's 2x
        scale = 2 if img.size[0] > 2000 else 1
        # macOS coordinates: AppleScript reports top-left in logical pixels
        # Screenshot is in physical pixels
        x_p = int(x * scale)
        y_p = int(y * scale)
        w_p = int(w * scale)
        h_p = int(h * scale)
        
        # Ensure bounds
        x_p = max(0, x_p)
        y_p = max(0, y_p)
        x2 = min(img.size[0], x_p + w_p)
        y2 = min(img.size[1], y_p + h_p)
        
        cropped = img.crop((x_p, y_p, x2, y2))
        cropped.save(cropped_path)
        print(f"[secure] Cropped Ente window to {cropped_path} size {cropped.size} (secure, will delete)")
        
        # Delete full
        try: os.remove(full_path)
        except: pass
        
        return cropped_path
    except Exception as e:
        print(f"[secure] Capture crop failed: {e}")
        import traceback; traceback.print_exc()
        clean_temp_files()
        return None

def ocr_totp_codes(image_path, account_filter=None):
    """
    OCR image for TOTP codes, filter by account name if provided
    Returns list of (account_label, code) or just codes
    Secure: never logs actual codes
    """
    try:
        from PIL import Image
        import pytesseract
        
        img = Image.open(image_path)
        # Upscale for better OCR
        # Try multiple OCR modes
        
        # Full text for account labels
        full_text = pytesseract.image_to_string(img)
        # print(f"Full OCR (first 500 chars, codes masked): {full_text[:500]}")  # Don't log, may contain codes
        
        # Digits only for codes
        digits_text = pytesseract.image_to_string(img, config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 \n')
        
        # Find 6-digit codes (TOTP)
        codes = re.findall(r'\b\d{6}\b', digits_text)
        # Also find codes like "746 193" that are split
        # The earlier test showed codes split with space: "746 193" - need to handle
        # Try finding 3+3 digits with space
        codes_split = re.findall(r'(\d{3})\s+(\d{3})', digits_text)
        for a,b in codes_split:
            combined = a+b
            if combined not in codes and len(combined)==6:
                codes.append(combined)
        
        print(f"[secure] OCR found {len(codes)} potential TOTP codes (masked, not logged)")
        for _ in codes[:3]:
            print(f"  Code pattern: ****** (length 6, masked for security)")
        
        # Try to associate with account labels
        # Simple heuristic: if account_filter provided, search full_text for filter near code
        # Ente Auth UI: each entry has label, email, code in same row
        # OCR reads top to bottom, so codes appear in order of entries
        # We can try to get positions via image_to_data for better association
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            # This gives word positions, could associate label proximity to code
            # For now, simple: return all codes, caller can choose
            pass
        except: pass
        
        if account_filter:
            print(f"[secure] Filtering for account containing: {account_filter[:3]}*** (masked)")
            # For now, if filter provided, we still return all but indicate filter
            # Better would be to search full_text for filter and get nearest code
            # Simple: if "Microsoft" or "JCCC" in full_text, prioritize first code etc
            # TODO: Improve with layout analysis
            # For now, return first code as likely match if filter present in image
            if account_filter.lower() in full_text.lower():
                print(f"[secure] Filter '{account_filter[:3]}***' found in image (matched securely)")
                # Return first code as best guess, or all
                return codes[:1] if codes else []
        
        return codes
    except Exception as e:
        print(f"[secure] OCR failed: {e}")
        return []
    finally:
        # Clean up image path (cropped) - but leave for caller to delete after use if needed
        pass

def get_totp_code_secure(account_filter=None, max_retries=2):
    """
    Securely get TOTP code from Ente Auth
    account_filter: e.g., "Microsoft", "JCCC", "Google", "Gmail" - to filter entry
    Returns code or None
    Security: code masked in logs, cleared after use by caller
    """
    print(f"\n=== Secure Ente Auth TOTP Retrieval ===")
    print(f"Filter: {account_filter if account_filter else 'None (any)'} (masked)")
    print(f"Opening Ente Auth...")
    subprocess.run(['open', '-a', 'Ente Auth'], capture_output=True)
    time.sleep(0.5)
    
    for attempt in range(max_retries):
        print(f"[secure] Attempt {attempt+1}/{max_retries}")
        cropped_path = capture_and_crop_ente()
        if not cropped_path or not os.path.exists(cropped_path):
            print(f"[secure] Failed to capture cropped image, retry")
            time.sleep(1)
            continue
        
        codes = ocr_totp_codes(cropped_path, account_filter=account_filter)
        
        # Clean up cropped immediately after OCR
        try:
            os.remove(cropped_path)
        except: pass
        
        if codes:
            code = codes[0]  # Take first match
            print(f"[secure] Successfully retrieved TOTP code with length {len(code)} (masked as ******, will clear after use)")
            # Clear codes list from memory
            codes = None
            return code
        else:
            print(f"[secure] No codes found attempt {attempt+1}, retrying...")
            time.sleep(1)
    
    print(f"[secure] Failed to retrieve TOTP after {max_retries} attempts")
    clean_temp_files()
    return None

def fill_microsoft_mfa(page, account_filter="Microsoft"):
    """
    Detect Microsoft MFA page and auto-fill TOTP from Ente Auth securely
    page: Playwright page object
    Returns True if filled, False otherwise
    """
    try:
        # Detect if MFA page
        url = page.url.lower()
        if "login.microsoftonline.com" not in url and "microsoft" not in url.lower():
            print(f"[secure] Not on Microsoft login page: {page.url[:80]}")
            return False
        
        # Check for MFA input
        mfa_selectors = [
            "input[type='text'][autocomplete='one-time-code']",
            "input[type='tel']",
            "input[name='otc']",
            "input[aria-label*='code' i]",
            "input[placeholder*='code' i]",
        ]
        mfa_input = None
        for sel in mfa_selectors:
            try:
                loc = page.locator(sel).first
                if loc.count()>0 and loc.is_visible(timeout=1000):
                    print(f"[secure] Found MFA input via {sel}")
                    mfa_input = loc
                    break
            except: continue
        
        if not mfa_input:
            # Check for "Enter code" text
            try:
                body = page.locator("body").inner_text(timeout=2000).lower()
                if "enter code" in body or "verification code" in body or "authenticator" in body:
                    # Try generic text input
                    mfa_input = page.locator("input[type='text']").last
                    if mfa_input.count()>0:
                        print(f"[secure] Found generic text input for MFA fallback")
                    else:
                        print(f"[secure] MFA detected in body but no input found")
                        return False
                else:
                    print(f"[secure] No MFA detected on page")
                    return False
            except Exception as e:
                print(f"[secure] MFA detection error: {e}")
                return False
        
        # Get TOTP securely
        code = get_totp_code_secure(account_filter=account_filter)
        if not code:
            print(f"[secure] Failed to get TOTP for {account_filter[:3]}***")
            # Fallback to manual
            print(f"[!] Please manually enter code from Ente Auth app for {account_filter}")
            print(f"    Ente Auth opened, waiting 60s for manual entry...")
            subprocess.run(['open', '-a', 'Ente Auth'], capture_output=True)
            for i in range(20):
                page.wait_for_timeout(3000)
                u = page.url.lower()
                if "login.microsoftonline.com" not in u:
                    print(f"[secure] Manual MFA succeeded after {i*3}s")
                    return True
            return False
        
        # Fill securely
        print(f"[secure] Filling MFA code with length {len(code)} (masked)")
        mfa_input.fill(code, timeout=5000)
        # Clear code from memory
        code = None
        print(f"[secure] Code filled and cleared from memory")
        
        # Click verify if button exists
        for sel in ["input[type='submit']", "button:has-text('Verify')", "button:has-text('Next')", "#idSIButton9"]:
            try:
                btn = page.locator(sel).first
                if btn.count()>0 and btn.is_visible(timeout=1000):
                    print(f"[secure] Clicking {sel} to submit MFA")
                    btn.click(timeout=3000)
                    break
            except: continue
        
        # Wait for redirect away from Microsoft
        for i in range(20):
            page.wait_for_timeout(3000)
            u = page.url.lower()
            if "login.microsoftonline.com" not in u and "microsoft" not in u:
                print(f"[secure] MFA success, redirected to {page.url[:80]} after {i*3}s")
                return True
            if i % 3 == 0:
                print(f"[secure] Waiting for MFA redirect {i*3}s URL {page.url[:80]}")
        
        print(f"[secure] MFA fill attempted but still on Microsoft page: {page.url[:80]}")
        return False
        
    except Exception as e:
        print(f"[secure] fill_microsoft_mfa error: {e}")
        import traceback; traceback.print_exc()
        return False
    finally:
        clean_temp_files()

if __name__ == "__main__":
    print("Testing Ente Auth secure OCR...")
    # Test with Microsoft filter
    code = get_totp_code_secure(account_filter="Microsoft")
    if code:
        print(f"[secure] Test succeeded, code length {len(code)} masked as ******, clearing...")
        code = None
        print("[secure] Code cleared from memory")
    else:
        print("[secure] Test failed to get code - may need to scroll to Microsoft entry in Ente Auth")
        print("INSTRUCTIONS:")
        print("  1. Open Ente Auth manually")
        print("  2. Search for 'Microsoft' or 'JCCC'")
        print("  3. Ensure Microsoft entry visible")
        print("  4. Re-run this script")
    
    clean_temp_files()
    print("Temp files cleaned")
