"""Exercise 01: a manual tool-use loop.

Claude is given one tool, `get_invoice_status`, backed by a fake in-memory
"database". The loop below is the core pattern behind every tool-using agent:

    1. Send the conversation + tool definitions to Claude.
    2. If Claude answers with `stop_reason == "tool_use"`, run each requested tool.
    3. Send the results back as `tool_result` blocks in a single user message.
    4. Repeat until Claude stops asking for tools.

Usage:
    python exercises/01_tool_use_loop.py ["your question"]
"""

import json
import sys

import anthropic
from pydantic import BaseModel, Field, ValidationError

MODEL = "claude-opus-5-5"
MAX_TURNS = 10  # safety valve so a confused loop can't run forever

# --- Fake backend -------------------------------------------------------------

FAKE_INVOICES = {
    "INV-1001": {"status": "paid", "amount": 1250.00, "currency": "USD", "paid_on": "2026-10-02"},
    "INV-1002": {"status": "overdue", "amount": 480.50, "currency": "USD", "due_on": "2026-10-15"},
    "INV-1003": {"status": "pending", "amount": 9900.00, "currency": "EUR", "due_on": "2026-12-01"},
}


class GetInvoiceStatusInput(BaseModel):
    """Pydantic model for the tool's input: validates what Claude sends us."""

    invoice_id: str = Field(
        description="Invoice identifier, e.g. INV-1001",
        pattern=r"^INV-\d{4}$",
    )


def get_invoice_status(args: GetInvoiceStatusInput) -> dict:
    invoice = FAKE_INVOICES.get(args.invoice_id)
    if invoice is None:
        raise LookupError(f"No invoice found with id {args.invoice_id}")
    return {"invoice_id": args.invoice_id, **invoice}


# Map tool name -> (input model, implementation)
TOOL_REGISTRY = {
    "get_invoice_status": (GetInvoiceStatusInput, get_invoice_status),
}

# The tool definition Claude sees. The JSON schema is generated from Pydantic.
TOOLS = [
    {
        "name": "get_invoice_status",
        "description": (
            "Look up the current status of a customer invoice by its ID. "
            "Returns status (paid, pending, or overdue), amount, currency, and "
            "the relevant date. Use this whenever the user asks about an invoice."
        ),
        "input_schema": GetInvoiceStatusInput.model_json_schema(),
    }
]


# --- Tool dispatch ------------------------------------------------------------


def run_tool(name: str, raw_input: dict) -> dict:
    """Execute one tool call and return a `tool_result` content block."""
    entry = TOOL_REGISTRY.get(name)
    if entry is None:
        return {"content": f"Unknown tool: {name}", "is_error": True}

    input_model, fn = entry
    try:
        args = input_model.model_validate(raw_input)
        result = fn(args)
        return {"content": json.dumps(result)}
    except ValidationError as e:
        return {"content": f"Invalid input: {e}", "is_error": True}
    except Exception as e:  # tool failures go back to Claude, not up the stack
        return {"content": f"Tool error: {e}", "is_error": True}


# --- The loop -----------------------------------------------------------------


def main(question: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": question}]

    print(f"User: {question}\n")

    for turn in range(1, MAX_TURNS + 1):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            tools=TOOLS,
            messages=messages,
            # If a safety classifier declines, retry server-side on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        print(f"[turn {turn}] stop_reason={response.stop_reason} "
              f"(in={response.usage.input_tokens}, out={response.usage.output_tokens})")

        # Always append the full content (not just text) so tool_use ids line up.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            print("\nClaude declined this request.")
            return

        if response.stop_reason != "tool_use":
            final = "".join(b.text for b in response.content if b.type == "text")
            print(f"\nClaude: {final}")
            return

        # Run every tool Claude asked for; return ALL results in ONE user message.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            outcome = run_tool(block.name, block.input)
            print(f"  -> {block.name}({json.dumps(block.input)}) = {outcome['content']}")
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, **outcome})

        messages.append({"role": "user", "content": tool_results})

    print(f"\nStopped after {MAX_TURNS} turns without a final answer.")


if __name__ == "__main__":
    default_q = "Can you check invoices INV-1001, INV-1002 and INV-9999 and summarize what I still owe?"
    main(" ".join(sys.argv[1:]) or default_q)
