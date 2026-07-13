# Dual-Platform Agent Automation

A browser automation workspace powered by two AI agents:
1. **Spark (OpenCode)**: Terminal-based coding agent for architecture and script refactoring.
2. **Antigravity**: Autonomous browser and system automation agent.

## Recommended Ecosystem
- **macOS Users:** OpenCode + Muse Spark 1.1 + Antigravity is the recommended stack. Use `spark` and `antigrav` commands.
- **Windows Users:** For Windows, you should only run with **Cursor** (as your IDE/Coding agent) or the built-in **Antigravity** agent (`antigrav.ps1`) for browser automation. Do not use Claude or Kimi Web Bridge in this workflow.

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
- `meta-model-cookbook/`: Upstream patterns integrated into this project.
- `legacy/`: Old v1 scripts kept for reference.
