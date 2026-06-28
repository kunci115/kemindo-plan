"""LangGraph ReAct agent over DeepSeek + the deterministic tools.

Exposes:
- run(message): synchronous final answer + tool trace.
- stream(message): yields trace events (for live UI showing the agent's work).
"""
from __future__ import annotations
from typing import Any, Iterator
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from functools import lru_cache
from ..llm import chat_model
from .tools import ALL_TOOLS, EXTERNAL_TOOLS

# how many prior turns to feed back as context (keeps tokens bounded)
HISTORY_TURNS = 12

SYSTEM = """You are the Kemindo Sales Engineer Copilot — an expert industrial
chemical sales engineer assistant for Kemindo Group (chemicals for gold mining,
nickel, paper, agriculture).

Operating rules:
1. ALWAYS ground product, dosage, price, inventory, and compatibility facts in
   tool calls. Never invent numbers, prices, dosages, or stock.
2. Map customer problems to real Kemindo products via search_product, and use
   knowledge_lookup for technical root-cause. CITE the citations you receive.
3. For chemicals, prefer calc_dosage / stoichiometry over estimating.
4. Before recommending products stored/shipped together, call check_compatibility.
5. For quotations: pass the customer's quantity UNIT (e.g. "MT", "kg") to the
   pricing tools — never pre-convert. When you call build_quotation, present its
   `summary_markdown` to the user VERBATIM; never restate, round, or rescale the
   quantity, price, total, or approval — those come only from the tool.
6. Cross-sell: when relevant, suggest complementary products (knowledge base has
   cross-sell logic), but only real catalog items.
7. Be concise, technical, and honest. Always remind that dosages need
   metallurgist + SDS validation. Answer in English.
"""


ADVISOR_SYSTEM = """You are the Kemindo Solution Advisor — the friendly, public,
customer-facing assistant for Kemindo Group ("Your Solution Partner"), an
industrial solution provider (chemicals for gold mining, nickel, paper,
agriculture; plus logistics and energy).

Your job: help customers understand Kemindo's products, solve their operational
problems with technical guidance, answer questions about the company, and capture
their inquiry so a sales specialist can follow up.

Strict rules:
1. NEVER quote prices, margins, costs, or internal stock levels — you don't have
   them and must not invent them. If asked for price/availability/quotation, say a
   Kemindo specialist will prepare a formal quotation, and call capture_lead.
2. Recommend real Kemindo products (search_product) and give technical guidance
   (knowledge_lookup, calc_dosage) with citations. For chemicals, remind that
   dosages must be validated with their engineer + SDS.
3. When the customer shows buying intent or asks for a quote/price/sample, collect
   company + contact + need and call capture_lead, then confirm a specialist will
   reach out.
4. Be warm, professional, concise. Answer in English. Never expose internal
   tooling or that you are an LLM.
"""


@lru_cache
def _agent():
    # langgraph 0.2.x uses `state_modifier` (a system prompt str/SystemMessage)
    return create_react_agent(chat_model(), ALL_TOOLS, state_modifier=SYSTEM)


@lru_cache
def _agent_advisor():
    return create_react_agent(chat_model(), EXTERNAL_TOOLS, state_modifier=ADVISOR_SYSTEM)


def _select(advisor: bool):
    return _agent_advisor() if advisor else _agent()


def _to_lc(messages):
    """Accept a plain string (single turn) or a list of {role, content} history
    and return LangChain messages. Feeding history back gives the agent memory of
    the quote/customer it just produced."""
    if isinstance(messages, str):
        return [HumanMessage(content=messages)]
    out = []
    for m in messages[-HISTORY_TURNS:]:
        c = (m.get("content") or "").strip()
        if not c:
            continue
        out.append(HumanMessage(content=c) if m.get("role") == "user" else AIMessage(content=c))
    return out or [HumanMessage(content="(empty)")]


def _payload(messages) -> dict[str, Any]:
    return {"messages": _to_lc(messages)}


def run(messages, advisor: bool = False) -> dict[str, Any]:
    result = _select(advisor).invoke(_payload(messages))
    msgs = result["messages"]
    return {"answer": msgs[-1].content, "trace": _trace(msgs)}


def stream(messages, advisor: bool = False) -> Iterator[dict[str, Any]]:
    """Yield {type, ...} events as the agent thinks/acts — drives the live UI.
    `messages` is the full conversation history (list) or a single string.
    advisor=True uses the external customer-facing agent (no pricing tools)."""
    for chunk in _select(advisor).stream(_payload(messages), stream_mode="updates"):
        for node, payload in chunk.items():
            for m in payload.get("messages", []):
                tool_calls = getattr(m, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        yield {"type": "tool_call", "tool": tc["name"], "args": tc["args"]}
                elif m.__class__.__name__ == "ToolMessage":
                    yield {"type": "tool_result", "tool": getattr(m, "name", "?"),
                           "content": (m.content or "")[:1500]}
                elif m.content:
                    yield {"type": "assistant", "content": m.content}


def _trace(msgs: list) -> list[dict[str, Any]]:
    trace = []
    for m in msgs:
        tcs = getattr(m, "tool_calls", None)
        if tcs:
            for tc in tcs:
                trace.append({"type": "tool_call", "tool": tc["name"], "args": tc["args"]})
        elif m.__class__.__name__ == "ToolMessage":
            trace.append({"type": "tool_result", "tool": getattr(m, "name", "?"),
                          "content": (m.content or "")[:1500]})
    return trace
