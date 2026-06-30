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
1. ALWAYS ground facts in tool calls. Never invent numbers, prices, dosages,
   stock, OR product codes. Every product you name MUST come from a
   search_product result, and every price/margin/floor you state MUST come from
   price_quote_line or build_quotation for that exact product + quantity. Never
   recall a code or quote a price from memory or from an earlier turn's prose.
2. Map customer problems to real Kemindo products via search_product, and use
   knowledge_lookup for technical root-cause. CITE the citations you receive.
3. For chemicals, prefer calc_dosage / stoichiometry over estimating.
4. Before recommending products stored/shipped together, call check_compatibility.
5. QUOTATIONS & PDF: build_quotation is the ONLY way to create OR update a
   quotation and its downloadable PDF. Whenever the user wants a quote created,
   changed (substitute a product, add/remove a line, apply a discount), or asks
   you to "make/build the PDF", CALL build_quotation with the FULL current
   line-up (pass each line's unit; never pre-convert). Present the returned
   `summary_markdown` VERBATIM. The app renders the PDF + a download button from
   that result — NEVER say you cannot create or send a PDF, and never paste an
   ASCII/text quote instead of calling the tool.
6. Cross-sell: suggest complementary products, but FIRST obtain them from
   search_product so the names and codes are real — never name a product or code
   from memory.
7b. LEADS: if the user references a Lead ID (e.g. "L-6cac0bf0"), call get_lead
   first to load the customer + their products of interest, then search_product
   and build the quotation. Use list_new_leads to browse captured leads.
7. Be concise, technical, and honest. Always remind that dosages need
   metallurgist + SDS validation.
8. LANGUAGE: reply in the SAME language the user writes in (Indonesian or
   English). But ALWAYS call retrieval tools (search_product, knowledge_lookup)
   with ENGLISH keywords — the catalog and knowledge base are in English — even
   when the user writes in Indonesian. Keep product codes/units unchanged.
9. CONTEXT / MIXED THREADS: a conversation may cover several customers, RFQs, or
   quotations. Act on the MOST RECENT customer/quotation in focus. If a request
   ("this quote", "apply a discount", "make the PDF") is ambiguous about which
   customer/quotation/product it applies to, ASK one short clarifying question —
   never blend details from different customers or guess.
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
4. Be warm, professional, concise. Never expose internal tooling or that you
   are an LLM.
5. LANGUAGE: reply in the SAME language the customer writes in (Indonesian or
   English). But ALWAYS call retrieval tools with ENGLISH keywords (the catalog
   and knowledge base are in English), even when the customer writes Indonesian.
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


_LANG_DIRECTIVE = {"id": "\n\n[Respond in Indonesian.]", "en": "\n\n[Respond in English.]"}


def _to_lc(messages, lang: str | None = None):
    """Accept a plain string (single turn) or a list of {role, content} history
    and return LangChain messages. Feeding history back gives the agent memory of
    the quote/customer it just produced. `lang` ('id'/'en') appends a one-off
    language directive to the current turn WITHOUT polluting stored history."""
    if isinstance(messages, str):
        out = [HumanMessage(content=messages)]
    else:
        out = []
        for m in messages[-HISTORY_TURNS:]:
            c = (m.get("content") or "").strip()
            if not c:
                continue
            out.append(HumanMessage(content=c) if m.get("role") == "user" else AIMessage(content=c))
        out = out or [HumanMessage(content="(empty)")]
    if lang in _LANG_DIRECTIVE and isinstance(out[-1], HumanMessage):
        out[-1] = HumanMessage(content=out[-1].content + _LANG_DIRECTIVE[lang])
    return out


def _payload(messages, lang: str | None = None) -> dict[str, Any]:
    return {"messages": _to_lc(messages, lang)}


def run(messages, advisor: bool = False, lang: str | None = None) -> dict[str, Any]:
    result = _select(advisor).invoke(_payload(messages, lang))
    msgs = result["messages"]
    return {"answer": msgs[-1].content, "trace": _trace(msgs)}


def stream(messages, advisor: bool = False, lang: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield {type, ...} events as the agent thinks/acts — drives the live UI.
    `messages` is the full conversation history (list) or a single string.
    advisor=True uses the external customer-facing agent (no pricing tools).
    lang ('id'/'en') forces the reply language; None = match the user."""
    for chunk in _select(advisor).stream(_payload(messages, lang), stream_mode="updates"):
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
