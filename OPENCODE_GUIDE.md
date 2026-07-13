# OpenCode Quick-Launch Guide
> Using OpenCode as a fast, repeatable terminal AI coding agent for any project

---

## What is OpenCode?

[OpenCode](https://opencode.ai) is an open-source AI coding agent that runs inside your terminal. It supports any AI provider (OpenAI, Anthropic, Meta, custom APIs) and gives you a beautiful TUI where you can chat, write/edit files, run commands, and build projects — without leaving your terminal.

**The key value:** One command opens a fully powered AI coding session in any project.

---

## Your Current Setup (Reference)

| File | Purpose |
|---|---|
| `~/muse-spark-python/.env` | Stores your MODEL_API_KEY and secrets |
| `~/muse-spark-python/opencode.json` | Configures Spark Muse as the AI provider |
| `~/muse-spark-python/spark` | Loads .env and launches OpenCode |
| `~/.zshrc` alias `spark` | Global terminal shortcut |

**To open Spark Muse:** Just type `spark` in any terminal.

---

## How Config Works

OpenCode has two levels of configuration:

### 1. Global Config (~/.config/opencode/opencode.json)
- Applies to every OpenCode session on your machine
- Good for: default model preferences, keybinds, providers you use everywhere

### 2. Per-Project Config (./opencode.json in your project folder)
- Only applies when OpenCode is launched from that directory
- Overrides global config
- Good for: project-specific models, custom API providers

---

## Setting Up a New Project (Quick-Start Checklist)

### Step 1 - Create your project folder
```bash
mkdir my-new-project && cd my-new-project
```

### Step 2 - Create .env for secrets
```env
MODEL_API_KEY=your_api_key_here
```

### Step 3 - Create .gitignore
```
.env
.venv/
__pycache__/
```

### Step 4 - Create opencode.json
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "meta": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Meta Spark Muse",
      "options": {
        "baseURL": "https://api.meta.ai/v1",
        "apiKey": "{env:MODEL_API_KEY}"
      },
      "models": {
        "muse-spark-1.1": {
          "name": "Muse Spark 1.1"
        }
      }
    }
  }
}
```

> IMPORTANT: The correct env var syntax in opencode.json is {env:VARIABLE_NAME} with curly braces.

### Step 5 - Create a spark launcher script
```bash
#!/bin/zsh
SCRIPT_DIR="$HOME/my-new-project"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi
cd "$SCRIPT_DIR"
/Users/hswin/.opencode/bin/opencode "$@"
```

Make it executable and add a global alias:
```bash
chmod +x ./spark
echo 'alias myproject="$HOME/my-new-project/spark"' >> ~/.zshrc
source ~/.zshrc
```

---

## Prompting Best Practices

OpenCode is an agentic coding assistant - give it context and it can read/write files and run commands.

### Effective Prompts

| Instead of...            | Try...                                                                                          |
|--------------------------|-------------------------------------------------------------------------------------------------|
| "Fix the bug"            | "In agent_step.py, the click action times out. The element exists in the page text but Playwright can't find it. Fix it." |
| "Add a feature"          | "Add a function to agent_step.py that screenshots after every action and saves to /screenshots." |
| "Help me with Python"    | "Read agent_step.py, explain what it does, then suggest 3 improvements."                        |

### Prompt Starters

Starting a new feature:
> "Read [filename]. I want to add [feature]. Outline a plan first, then implement step by step."

Debugging:
> "Here is the error: [paste error]. The relevant code is in [filename]. Diagnose and fix it."

Code review:
> "Review [filename] for: 1) bugs 2) performance issues 3) security concerns. Be specific about line numbers."

Learning:
> "Explain how [filename] works in plain English. What should I learn to understand it better?"

---

## OpenCode Key Bindings

| Key         | Action                    |
|-------------|---------------------------|
| Enter       | Send message              |
| Shift+Enter | New line in message       |
| ctrl+x n    | New session               |
| ctrl+x m    | Switch model              |
| ctrl+x u    | Undo last change (needs git) |
| ctrl+x r    | Redo                      |
| ctrl+x e    | Open in external editor   |
| ctrl+x x    | Export conversation to Markdown |
| ctrl+p      | Command palette           |
| tab         | Cycle agents              |
| ctrl+t      | Toggle reasoning mode     |

### Slash Commands
| Command    | Action                              |
|------------|-------------------------------------|
| /connect   | Add API credentials securely        |
| /models    | List and change active model        |
| /new       | Start a fresh session               |
| /export    | Export conversation to Markdown     |
| /undo      | Undo last AI action                 |
| /compact   | Compact session context (save tokens)|
| /thinking  | Toggle reasoning block visibility   |

---

## Adding References (Point AI at docs or other repos)

In opencode.json, give the AI access to folders outside your project:

```json
{
  "references": {
    "docs": {
      "path": "../my-docs-folder",
      "description": "Use for product documentation and API references"
    }
  }
}
```

In your prompt, type @docs to attach those docs to your message.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| opencode: command not found | Run: source ~/.zshrc |
| invalid_api_key in OpenCode | Use the spark launcher — it exports env vars before starting OpenCode |
| Chrome profile locked | Fully quit Chrome (Cmd+Q) before running browser agent |
| Config not loading | Make sure opencode.json is in the directory you launch from |
