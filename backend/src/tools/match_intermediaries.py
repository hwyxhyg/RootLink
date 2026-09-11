"""Match genealogy intermediaries from the bundled data file."""

import json
from pathlib import Path

from langchain_core.tools import tool


INTERMEDIARIES_FILE = Path(__file__).resolve().parents[2] / "assets" / "intermediaries.json"


@tool
def match_intermediaries(
    surname: str = "",
    location: str = "",
    dialect: str = "",
    migration_info: str = "",
) -> str:
    """Match guides using surname, location, dialect, and migration clues."""
    try:
        with INTERMEDIARIES_FILE.open("r", encoding="utf-8") as data_file:
            intermediaries = json.load(data_file)

        matches = []
        for intermediary in intermediaries:
            score = intermediary.get("match_score_base", 50)
            reasons = []

            if surname and any(
                surname in specialty
                for specialty in intermediary.get("specialties", [])
            ):
                score += 15
                reasons.append(f"姓氏匹配（{surname}）")
            if location:
                if location in intermediary.get("location", ""):
                    score += 20
                    reasons.append(f"地区精准匹配（{location}）")
                elif any(
                    location in area
                    for area in intermediary.get("expertise_areas", [])
                ):
                    score += 10
                    reasons.append(f"熟悉地区（{location}）")
            if dialect and any(
                dialect in area for area in intermediary.get("expertise_areas", [])
            ):
                score += 15
                reasons.append(f"方言匹配（{dialect}）")
            if migration_info and any(
                keyword in expertise
                for expertise in intermediary.get("expertise_areas", [])
                for keyword in migration_info.split()
            ):
                score += 10
                reasons.append(f"熟悉迁移历史（{migration_info}）")

            score = min(100, max(0, score))
            if score >= 60:
                matches.append(
                    {
                        "id": intermediary.get("id"),
                        "name": intermediary.get("name"),
                        "location": intermediary.get("location"),
                        "match_score": score,
                        "match_reasons": reasons or ["基本匹配"],
                        "success_cases_count": len(
                            intermediary.get("success_cases", [])
                        ),
                        "success_cases": intermediary.get("success_cases", [])[:2],
                        "contact_info": intermediary.get("contact_info"),
                        "notes": intermediary.get("notes", ""),
                    }
                )

        matches.sort(key=lambda item: item["match_score"], reverse=True)
        result = {
            "user_info": {
                "surname": surname or "未提供",
                "location": location or "未提供",
                "dialect": dialect or "未提供",
                "migration_info": migration_info or "未提供",
            },
            "matched_count": len(matches[:5]),
            "intermediaries": matches[:5],
        }
        if not matches:
            result["message"] = (
                "暂未找到完全匹配的中间人，建议补充具体祖籍地或方言信息。"
            )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps(
            {"error": f"匹配中间人时出错: {exc}", "intermediaries": []},
            ensure_ascii=False,
        )
