"""RootLink genealogy agents."""

import json
import os
from pathlib import Path
from typing import Annotated

from langchain.agents import create_agent
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from src.storage.memory.memory_saver import get_memory_saver
from src.tools.match_intermediaries import match_intermediaries
from src.tools.search_genealogy_location import search_genealogy_location
from src.tools.search_official_reference import search_official_reference


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_CONFIG = {
    "zh": PROJECT_ROOT / "config" / "agent_llm_config.json",
    "en": PROJECT_ROOT / "config" / "agent_llm_config_en.json",
}
MAX_MESSAGES = 40

PRESET_TODOS = {
    "zh": {
        "collect_surname": "收集家族姓氏",
        "collect_generation": "收集家族字辈（家谱排序）",
        "collect_origin": "收集祖籍具体地址（省/市/县/村）",
        "collect_dialect": "收集家族使用的方言",
        "collect_migration": "收集家族迁徙历史（时间/路线/原因）",
        "collect_relics": "整理家中老物件（族谱、信件、照片）",
        "analyze_location": "分析亲缘地历史背景与移民来源",
        "match_intermediaries": "匹配推送中间人资源",
        "contact_intermediaries": "协助联系中间人进行进一步验证",
    },
    "en": {
        "collect_surname": "Collect the family surname",
        "collect_generation": "Collect the family generation name",
        "collect_origin": "Collect the ancestral hometown address",
        "collect_dialect": "Collect the family dialect",
        "collect_migration": "Collect the family migration history",
        "collect_relics": "Organize old family records and photographs",
        "analyze_location": "Analyze the ancestral area's history and migration",
        "match_intermediaries": "Match relevant intermediary resources",
        "contact_intermediaries": "Contact intermediaries for further verification",
    },
}


def _windowed_messages(old, new):
    """Keep only the most recent messages while retaining LangGraph semantics."""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]
    todos: list[dict]


def _language_policy(lang: str) -> str:
    todo_text = json.dumps(PRESET_TODOS[lang], ensure_ascii=False)
    if lang == "en":
        proper_nouns = (
            "Use English only for familiar countries and regions such as Malaysia, "
            "Singapore, Thailand, Indonesia, Taiwan, Fujian, Guangdong, and Shanghai. "
            "Add Chinese in parentheses only for less recognizable, specific ancestral "
            "places, for example Nan'an (南安), Anxi (安溪), Jiaomei (角美), and "
            "Fushi Village (浮石村). Do not add Chinese parentheses to people's names."
        )
    else:
        proper_nouns = "Respond in Chinese and use natural Chinese place and person names."
    return (
        f"\n\n# Runtime language policy\n{proper_nouns}\n"
        "Todo IDs and output schema must remain unchanged. Use exactly these localized "
        f"todo labels for the selected language: {todo_text}"
    )


def build_agent(ctx=None, lang: str = "zh"):
    """Build the Chinese or English agent for a normal Python environment."""
    del ctx  # Kept in the signature for compatibility with older callers.
    lang = lang if lang in LLM_CONFIG else "zh"

    with LLM_CONFIG[lang].open("r", encoding="utf-8") as config_file:
        cfg = json.load(config_file)

    api_key = os.getenv("VOLCENGINE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "VOLCENGINE_API_KEY is required. Copy .env.example to .env and set the Ark API key."
        )

    model_config = cfg["config"]
    llm = ChatOpenAI(
        model=model_config.get("model"),
        api_key=api_key,
        base_url=os.getenv(
            "VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        ),
        temperature=model_config.get("temperature", 0.7),
        streaming=True,
        timeout=model_config.get("timeout", 600),
        extra_body={
            "thinking": {"type": model_config.get("thinking", "disabled")}
        },
    )

    return create_agent(
        model=llm,
        system_prompt=(cfg.get("sp") or "") + _language_policy(lang),
        tools=[
            search_genealogy_location,
            match_intermediaries,
            search_official_reference,
        ],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
