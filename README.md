# ai-phase1-playground

A hands-on playground for **Phase 1 of an applied-AI learning plan**: learning the
Claude API from first principles.

## Goal

Phase 1 is about building a solid mental model of how LLM applications actually work
by writing small, self-contained exercises directly against the
[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) — no
frameworks, no abstractions hiding the request/response cycle.

Topics to cover in this phase:

- The Messages API: roles, content blocks, `stop_reason`, token usage
- Tool use: defining tools, running the tool-use loop by hand, returning results
- Validating model output with Pydantic
- Structured outputs, streaming, and prompt caching
- Error handling and retries

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste your key into .env
set -a; source .env; set +a   # export the variables into your shell
```

## Exercises

| # | File | What it teaches |
|---|------|-----------------|
| 01 | `exercises/01_tool_use_loop.py` | A manual tool-use loop with a fake `get_invoice_status` tool, with Pydantic validation of tool inputs |

Run an exercise:

```bash
python exercises/01_tool_use_loop.py
python exercises/01_tool_use_loop.py "Has invoice INV-1002 been paid?"
```
