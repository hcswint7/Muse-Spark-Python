# Credential Security Handling

## Stored Credentials (in .env - gitignored)

### Canvas JCCC
- Email: h***@stumail.jcc.edu (masked)
- Password: Stored as CANVAS_USERNAME / CANVAS_PASSWORD in .env
- Used for: canvas.jccc.edu via Microsoft SSO (login.microsoftonline.com)
- MFA: Yes (via Authenticator app) - password alone cannot fully compromise
- Session retention: Debug profile ~/chrome-debug-profile retains login 7-14 days after one manual login

### Gmail (for many logins)
- Email: h***@gmail.com (masked)
- Password: Stored as GMAIL_USERNAME / GMAIL_PASSWORD in .env
- Used for: Google OAuth for many services (Perplexity, etc), direct Gmail access
- Security: Plain password may trigger Google security alerts for automation

## Security Best Practices Implemented

1. **Never log password**: Only masked username shown (first 3 chars + ***)
2. **Only in .env**: File is gitignored, not in code, not in docs
3. **No hardcoding**: Scripts read from env vars via os.environ.get()
4. **MFA aware**: Canvas and Gmail have MFA - automation pauses 60s for user approval via phone
5. **Debug profile retains session**: After one manual login, no password needed for days
6. **CDP method preferred**: Connects to real Chrome via port 9222 - no password needed, uses existing session

## Risks & Recommendations

### Password Reuse Detected
- Canvas: Shapeman1971? 
- Gmail: Shapeman1971! 
- Similar base, different ending - indicates reuse pattern
- **Recommendation:** Use distinct strong passwords per service, use password manager (Bitwarden, 1Password)

### Gmail Plain Password + Automation
- Google may block sign-in from automation as "less secure app"
- If 2FA enabled (recommended), plain password won't work - need App Password:
  1. Go to https://myaccount.google.com/apppasswords
  2. Generate App Password for "Mail" or "Other"
  3. Use that 16-char app password instead of regular password in GMAIL_PASSWORD
- Better: Use OAuth flow, not password

### .env File Security
- Location: ~/muse-spark-python/.env
- Permissions: Should be 600 (only owner read/write)
  ```bash
  chmod 600 ~/muse-spark-python/.env
  ```
- Git status: gitignored (verified via .gitignore)
- Backup: Do not backup to cloud without encryption

### Chat History
- User says will delete chat after done
- Credentials provided in chat are visible in chat history until deleted
- **Recommendation:** 
  - Delete chat after tasks complete (as user plans)
  - Change passwords after if concerned, especially if chat was on shared system
  - Consider using temporary app passwords that can be revoked

### For Future Logins Using Gmail
- Many sites use "Sign in with Google" OAuth - this is better than password
- When agent encounters "Sign in with Google":
  - If CDP connected to real Chrome (logged into Google), it will already be authenticated - no password needed
  - If not, it will show Google OAuth popup - may require manual approval
  - Never enter Gmail password into non-Google domains (phishing check)

### Secure Auto-Login Implementation

```python
import os
from dotenv import load_dotenv
load_dotenv(override=True)

username = os.environ.get("CANVAS_USERNAME") # or GMAIL_USERNAME
password = os.environ.get("CANVAS_PASSWORD") # Masked, never printed

# Only use if exists, never log
if username and password:
    # Fill form
    page.locator("input[type='email']").fill(username)
    # Never: print(password) or log password
```

## What to Do After Tasks Complete

1. **Review .env** - ensure no extra copies
2. **Set permissions**: chmod 600 .env
3. **Consider password rotation** if chat was on shared machine or you want to revoke access
4. **For Gmail**: If you used App Password, you can revoke it at https://myaccount.google.com/apppasswords
5. **Delete chat** as planned

## Current Login Status

- Debug profile ~/chrome-debug-profile: **Logged in** to Canvas (tested 2026-07-13 17:06 CDT) - no password needed for Canvas tasks
- Perplexity: Works without login, but debug profile also logged in
- Gmail: Not yet tested - will need when you request Gmail-based tasks
- Main Chrome Profile 1: Has history, but direct launch flagged - use CDP method instead

## Next Steps

User says: "You will be prompted with gmail creds for many logins that I will request"

Ready to handle:
- Tasks requiring Google OAuth (Sign in with Google)
- Tasks requiring direct Gmail access (reading emails, etc) - will need to handle 2FA/MFA pause
- Will ask for confirmation before performing sensitive actions (sending emails, deleting, etc)
