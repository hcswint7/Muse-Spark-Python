# Meta Model Cookbook: Agent Integration Guide

This guide dictates how AI agents in this workspace (specifically **Spark / OpenCode** and the **Antigravity SDK Agent**) should leverage the local `meta-model-cookbook/` repository to enhance their capabilities.

---

## 1. For Spark (OpenCode) Developer Agent
Spark is the primary architect and developer in this workspace. You should treat the cookbook as your definitive reference manual for building and scaling the Antigravity SDK and any related infrastructure.

**When to read the cookbook:**
* **Before building Multi-Agent Systems:** If the user asks for a Supervisor or Subagent architecture, immediately read `meta-model-cookbook/02_agent_patterns/08_multi_agent_orchestration/`.
* **When dealing with context limits:** If the Antigravity agent is crashing due to massive HTML DOMs, read `meta-model-cookbook/01_api_fundamentals/08_long_context.ipynb` for caching and truncation strategies.
* **When implementing tool retry logic:** If agents are getting stuck in infinite loops trying the same failed tool, reference `meta-model-cookbook/02_agent_patterns/01_agent_loop_basics/` for interleaved reasoning patterns.

**How to leverage:**
Use your local file reading capabilities (`cat` or `view_file`) to inspect these directories, absorb the best practices, and implement them directly into `antigrav_agent.py` or new scripts.

---

## 2. For Antigravity SDK Agent
Antigravity is a specialized, autonomous browser and system automation agent. Its goal is to navigate interfaces, extract information, and complete workflows reliably. 

**CRITICAL DIRECTIVE - STRICT BOUNDARIES:** 
Do **NOT** leverage the Antigravity agent for non-beneficial uses. Do not attempt to force Antigravity to become a general-purpose coding agent, a conversational chatbot, or a system architect. Its focus must remain strictly on **automation and task execution**.

**When to read the cookbook:**
Antigravity should only read the cookbook to enhance its specific domain (Browser & OS Automation). 
* **macOS Automation:** If the user requests that Antigravity interact with desktop apps outside the browser, read `meta-model-cookbook/03_use_cases/13_macos_cua/` to learn how to use AppleScript and macOS Accessibility APIs.
* **Computer Use API (CUA):** For generic OS-level control (mouse clicking, keyboard events), reference `meta-model-cookbook/03_use_cases/12_computer_use/`.

**How to leverage:**
Use your `read_local_file` tool to read these documents when you need to understand how to construct a payload or execute a command to control the local operating system natively.
