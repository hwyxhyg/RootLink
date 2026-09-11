import json

from src.utils.sse_handler import SSEHandler
from src.tools.search_official_reference import search_official_reference


def test_sse_event_is_parseable():
    handler = SSEHandler()
    event = handler.format_sse_event("answer", {"answer": "你好"})
    assert event.endswith("\n\n")
    assert json.loads(event.removeprefix("data: ")) == {
        "type": "answer",
        "content": {"answer": "你好"},
    }


def test_language_specific_missing_values():
    handler = SSEHandler()
    zh = handler.sanitize_structured_data({"message": ""}, "zh")
    en = handler.sanitize_structured_data({"message": ""}, "en")
    assert zh["user_info"]["surname"] == "未提供"
    assert en["user_info"]["surname"] == "Not provided"


def test_official_reference_matches_unspaced_chinese_query():
    result = json.loads(search_official_reference.invoke({"query": "官方寻根活动"}))
    assert result["found"] is True
    assert result["references"][0]["id"] == "chinaql-root-seeking"
