"""Search the small, bundled set of official genealogy references."""

import json
import re

from langchain_core.tools import tool


REFERENCES = [
    {
        "id": "chinaql-root-seeking",
        "title": "亲情中华·中国寻根之旅",
        "source": "中华全国归国华侨联合会",
        "url": "https://www.chinaql.org/",
        "content": "面向海外华裔青年的中华文化体验与寻根交流项目。",
        "keywords": "官方 寻根 活动 亲情中华 中国寻根之旅 china roots programme",
    },
    {
        "id": "chinaql",
        "title": "中国侨联官网",
        "source": "中华全国归国华侨联合会",
        "url": "https://www.chinaql.org/",
        "content": "提供侨务交流、权益服务和相关活动的官方信息。",
        "keywords": "侨务 政策 官方支持 中国侨联 overseas chinese affairs",
    },
    {
        "id": "malaysia-census-2020",
        "title": "Malaysia Population and Housing Census 2020",
        "source": "Department of Statistics Malaysia",
        "url": "https://www.dosm.gov.my/",
        "content": "Malaysia's official population and housing census source.",
        "keywords": "马来西亚 华人 人口 数据 malaysia chinese population census",
    },
    {
        "id": "us-census-2020",
        "title": "2020 United States Census",
        "source": "United States Census Bureau",
        "url": "https://www.census.gov/",
        "content": "Official United States population and demographic data.",
        "keywords": "美国 华人 人口 数据 united states chinese population census",
    },
    {
        "id": "npc-overseas-chinese-affairs",
        "title": "国务院关于新时代侨务工作情况的报告",
        "source": "全国人民代表大会",
        "url": "http://www.npc.gov.cn/",
        "content": "新时代侨务工作、海外侨胞权益与交流支持的官方报告。",
        "keywords": "侨务 工作 政策 报告 overseas chinese policy support",
    },
]


def _terms(query: str) -> set[str]:
    latin = re.findall(r"[a-z0-9]+", query.lower())
    chinese_blocks = re.findall(r"[\u4e00-\u9fff]{2,}", query)
    chinese = []
    for block in chinese_blocks:
        chinese.append(block)
        chinese.extend(block[index : index + 2] for index in range(len(block) - 1))
    return set(latin + chinese)


@tool
def search_official_reference(query: str) -> str:
    """Search bundled official references and return source URLs."""
    terms = _terms(query)
    ranked = []
    for reference in REFERENCES:
        haystack = " ".join(str(value) for value in reference.values()).lower()
        score = sum(1 for term in terms if term.lower() in haystack)
        if score:
            ranked.append((score, reference))
    ranked.sort(key=lambda item: item[0], reverse=True)
    matches = [reference for _, reference in ranked[:3]]
    return json.dumps(
        {
            "query": query,
            "found": bool(matches),
            "count": len(matches),
            "references": matches,
            "message": "" if matches else "未找到匹配的本地权威资料。",
        },
        ensure_ascii=False,
        indent=2,
    )
