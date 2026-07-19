"""Tool-using agent loop over the OpenAI-compatible API (LM Studio).

Template pattern: send message + tool schemas, execute requested tools, feed results
back, stop at a final text answer or max_agent_steps. Note: tool calling depends on
the loaded model supporting it; Gemma 3 does in recent LM Studio builds. If the
model never calls tools, the loop degrades to a plain chat answer.
"""
from __future__ import annotations

import json
import logging

from app.agents.client import lmstudio_client
from app.agents.tools import TOOLS
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM = """You are the assistant for a personal knowledge pipeline over an Obsidian vault.
Use the tools to search, answer from, and extend the vault rather than answering from
your own knowledge. Prefer ask_notes for questions, search_notes for exploration.
Use remember for durable facts the user tells you about themselves or their projects."""


async def run_agent(message: str, history: list[dict] | None = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM}, *(history or []),
                {"role": "user", "content": message}]
    schemas = [t["schema"] for t in TOOLS.values()]
    steps: list[dict] = []
    client = lmstudio_client()

    for _ in range(settings.max_agent_steps):
        resp = await client.chat.completions.create(
            model=settings.chat_model, messages=messages, tools=schemas
        )
        choice = resp.choices[0].message
        if not choice.tool_calls:
            return {"answer": choice.content or "", "steps": steps}

        messages.append({"role": "assistant", "content": choice.content,
                         "tool_calls": [tc.model_dump() for tc in choice.tool_calls]})
        for tc in choice.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
                result = await TOOLS[name]["handler"](**args)
            except Exception as exc:  # tool errors go back to the model, not up the stack
                logger.exception("tool %s failed", name)
                result = {"error": str(exc)}
            steps.append({"tool": name, "args": tc.function.arguments})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)[:8000]})

    return {"answer": "(stopped: max tool steps reached)", "steps": steps}
