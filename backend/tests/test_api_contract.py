import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk

import src.api.chat_sse as api


class FakeAgent:
    def __init__(self, lang):
        self.lang = lang
        self.configs = []

    def stream(self, _payload, config, stream_mode):
        self.configs.append(config)
        assert stream_mode == "messages"
        message = "English reply" if self.lang == "en" else "中文回复"
        body = json.dumps(
            {
                "message": message,
                "user_info": {},
                "analysis": "",
                "intermediaries": [],
                "todos": [],
            },
            ensure_ascii=False,
        )
        for part in (body[:15], body[15:]):
            yield AIMessageChunk(content=part), {}

    def invoke(self, _payload, config):
        self.configs.append(config)
        message = "English reply" if self.lang == "en" else "中文回复"
        return {"messages": [AIMessage(content=json.dumps({"message": message}))]}


def test_chat_languages_fallback_and_memory_separation(monkeypatch):
    agents = {}

    def fake_build_agent(ctx=None, lang="zh"):
        del ctx
        agents[lang] = FakeAgent(lang)
        return agents[lang]

    monkeypatch.setattr(api, "build_agent", fake_build_agent)
    with TestClient(api.app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        en = client.post(
            "/api/chat/sse",
            json={"user_id": "same", "message": "Hello", "lang": "en"},
        )
        zh = client.post(
            "/api/chat/sse",
            json={"user_id": "same", "message": "你好", "lang": "zh"},
        )
        fallback = client.post(
            "/api/chat/sse",
            json={"user_id": "other", "message": "test", "lang": "abc"},
        )

    assert en.status_code == zh.status_code == fallback.status_code == 200
    assert en.headers["content-type"].startswith("text/event-stream")
    assert "English reply" in en.text
    assert "中文回复" in zh.text
    assert "中文回复" in fallback.text
    assert agents["en"].configs[0]["configurable"]["thread_id"] == "same_en"
    assert agents["zh"].configs[0]["configurable"]["thread_id"] == "same_zh"
    assert agents["zh"].configs[1]["configurable"]["thread_id"] == "other_zh"


def test_archive_routes_use_authenticated_identity(monkeypatch):
    saved = {}

    async def fake_user(_request):
        return {"id": "uuid", "email": "member@example.com"}

    async def fake_save(user_id, data):
        saved[user_id] = data

    async def fake_load(user_id):
        return saved.get(user_id)

    monkeypatch.setattr(api, "build_agent", lambda ctx=None, lang="zh": FakeAgent(lang))
    monkeypatch.setattr(api, "authenticated_user", fake_user)
    monkeypatch.setattr(api, "save_archive", fake_save)
    monkeypatch.setattr(api, "load_archive", fake_load)

    with TestClient(api.app) as client:
        headers = {"Authorization": "Bearer test"}
        assert client.post(
            "/api/archive/save",
            headers=headers,
            json={"data": {"todos": []}},
        ).json() == {"ok": True}
        assert client.post("/api/archive/load", headers=headers).json() == {
            "data": {"todos": []}
        }
