# Dual-Platform Agent Automation

A browser automation workspace powered by two AI agents:
1. **Spark (OpenCode)**: Terminal-based coding agent for architecture and script refactoring.
2. **Antigravity**: Autonomous browser and system automation agent.

## Recommended Ecosystem
This workspace is built to run entirely on **OpenCode** (for autonomous coding) and **Antigravity** (for autonomous browser control) across both macOS and Windows. Do not use Claude or Kimi Web Bridge in this workflow.

### Installing OpenCode
OpenCode is a terminal-native AI coding agent. You must install it before running the `spark` launcher.

**For macOS / Linux:**
The fastest way to install is via the official curl script:
```bash
curl -fsSL https://opencode.ai/install | bash
```

**For Windows (Recommended: WSL):**
For maximum compatibility with terminal utilities, installing via Windows Subsystem for Linux (WSL) is highly recommended.
1. Open PowerShell as Administrator and run `wsl --install`.
2. Restart your computer and open the new Ubuntu/WSL terminal.
3. Install Node and Git: `sudo apt update && sudo apt install -y nodejs npm git`
4. Run the Linux install script: `curl -fsSL https://opencode.ai/install | bash`

**For Windows (Native Alternative):**
If you prefer not to use WSL, you can install OpenCode natively on Windows:
* **Option A:** Download the graphical installer directly from [opencode.ai](https://opencode.ai).
* **Option B:** Install via NPM using PowerShell: `npm install -g opencode-ai`

## Quick Start (macOS)
1. Clone repo: `git clone <repo-url> && cd muse-spark-python`
2. Create virtual environment: `python3 -m venv .venv`
3. Install dependencies: `.venv/bin/pip install -r requirements.txt` (or install manually per guides)
4. Copy environment variables: `cp .env.example .env` and fill in your keys.
5. Launch agents (in separate terminal tabs):
   - `./spark`
   - `./antigrav`

## Quick Start (Windows)
1. Clone repo: `git clone <repo-url>` and open directory in PowerShell.
2. Create virtual environment: `python -m venv .venv`
3. Install dependencies: `.venv\Scripts\pip install -r requirements.txt`
4. Copy environment variables: `copy .env.example .env` and fill in your keys.
5. Launch agents (in separate PowerShell windows):
   - `.\spark.ps1`
   - `.\antigrav.ps1`

## Self-Updating
Run `./sync.sh` (Mac) or `.\sync.ps1` (Windows) to automatically pull and push changes between your machines.

## File Map
- `browser_core_v2.py`: The active core handling retry, stuck detection, and verified fill.
- `antigrav_agent.py`: macOS browser agent.
- `antigrav_agent_win.py`: Windows browser agent (auto-detects Windows Chrome paths).
- `docs/browser_skills/FORM_FILLING_MCQ_GUIDE.md`: Protocol for autonomous MCQ answering and form-filling.
- `meta-model-cookbook/`: Upstream patterns integrated into this project.
- `legacy/`: Old v1 scripts kept for reference.
