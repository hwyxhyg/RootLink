"""SSE formatting and LangGraph streaming helpers."""

import json
import re
from typing import Any, Generator

from langchain_core.messages import AIMessage, AIMessageChunk


class SSEHandler:
    def format_sse_event(self, event_type: str, content: Any) -> str:
        event = {"type": event_type, "content": content}
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def format_answer_event(self, text: str) -> str:
        return self.format_sse_event("answer", {"answer": text})

    def format_structured_event(self, data: dict) -> str:
        return self.format_sse_event("structured", data)

    def parse_structured_data(self, full_response: str) -> dict:
        candidates = [full_response]
        markdown = re.search(
            r"\x60\x60\x60(?:json)?\s*(\{.*?\})\s*\x60\x60\x60",
            full_response,
            re.DOTALL,
        )
        if markdown:
            candidates.append(markdown.group(1))
        start, end = full_response.find("{"), full_response.rfind("}")
        if start != -1 and end > start:
            candidates.append(full_response[start : end + 1])

        for candidate in candidates:
            try:
                value = json.loads(candidate)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
        return {
            "message": full_response,
            "user_info": {},
            "analysis": "",
            "intermediaries": [],
            "todos": [],
        }

    def sanitize_structured_data(self, data: dict, lang: str = "zh") -> dict:
        missing = "Not provided" if lang == "en" else "未提供"
        data.setdefault("message", "")
        user_info = data.setdefault("user_info", {})
        for field in ["surname", "location", "dialect", "migration_info"]:
            user_info.setdefault(field, missing)
        data.setdefault("analysis", "")
        data.setdefault("intermediaries", [])
        data.setdefault("todos", [])
        return data


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("type") in {"text", "text_delta"}:
            parts.append(str(item.get("text", "")))
    return "".join(parts)


def stream_agent_response_sync(
    agent, messages: list, config: dict, lang: str = "zh"
) -> Generator[str, None, None]:
    """Stream model tokens, followed by one parsed structured result."""
    handler = SSEHandler()
    full_response = ""
    try:
        for message, _metadata in agent.stream(
            {"messages": messages},
            config=config,
            stream_mode="messages",
        ):
            if not isinstance(message, (AIMessageChunk, AIMessage)):
                continue
            text = _text_content(message.content)
            if not text:
                continue
            full_response += text
            yield handler.format_answer_event(text)

        structured = handler.parse_structured_data(full_response)
        yield handler.format_structured_event(
            handler.sanitize_structured_data(structured, lang)
        )
        yield handler.format_sse_event("done", {"ok": True})
    except Exception as exc:
        yield handler.format_sse_event(
            "error",
            {
                "code": "agent_stream_error",
                "message": str(exc),
            },
        )
