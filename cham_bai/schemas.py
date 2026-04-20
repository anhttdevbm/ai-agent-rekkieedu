from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GradePayload:
    score: int
    comment: str
    integrity_verdict: str  # pass | suspicious | likely_ai
    integrity_confidence_0_100: int
    integrity_notes: list[str] = field(default_factory=list)
    rubric: dict[str, Any] | None = None
    # Mini project: chỉ điều kiện có/không — không tính vào score/comment.
    mini_project_present: str = "không_rõ"  # có | không | không_rõ

    def to_public_dict(
        self,
        *,
        applied_penalty: bool,
        final_comment: str,
        final_score: int,
    ) -> dict[str, Any]:
        return {
            "final_score": final_score,
            "final_comment": final_comment,
            "model_score": self.score,
            "model_comment": self.comment,
            "mini_project_present": self.mini_project_present,
            "integrity_verdict": self.integrity_verdict,
            "integrity_confidence_0_100": self.integrity_confidence_0_100,
            "integrity_notes": self.integrity_notes,
            "rubric": self.rubric,
            "applied_ai_penalty": applied_penalty,
        }


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def parse_llm_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    m = _JSON_FENCE.search(raw)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Không tìm thấy JSON object trong phản hồi model.")
    raw = raw[start : end + 1]
    return json.loads(raw)


def coalesce_grade(d: dict[str, Any]) -> GradePayload:
    try:
        score = int(d.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    comment = str(d.get("comment", "")).strip() or "(Không có nhận xét.)"

    verdict_raw = str(d.get("integrity_verdict", "pass")).strip().lower()
    if verdict_raw in {"likely_ai", "ai", "fail", "fail_ai"}:
        verdict = "likely_ai"
    elif verdict_raw in {"suspicious", "review", "uncertain"}:
        verdict = "suspicious"
    else:
        verdict = "pass"

    conf = d.get("integrity_confidence_0_100", 0)
    try:
        conf_int = int(conf)
    except (TypeError, ValueError):
        conf_int = 0
    conf_int = max(0, min(100, conf_int))

    notes = d.get("integrity_notes")
    if notes is None:
        notes_list: list[str] = []
    elif isinstance(notes, list):
        notes_list = [str(x).strip() for x in notes if str(x).strip()]
    else:
        notes_list = [str(notes).strip()]

    rubric = d.get("rubric")
    if rubric is not None and not isinstance(rubric, dict):
        rubric = None

    mpp_val = d.get("mini_project_present", "")
    if isinstance(mpp_val, bool):
        mini_project_present = "có" if mpp_val else "không"
    else:
        mpp_raw = str(mpp_val or "").strip().lower()
        if mpp_raw in {"có", "co", "yes", "true", "1", "c"}:
            mini_project_present = "có"
        elif mpp_raw in {"không", "khong", "no", "false", "0", "k"}:
            mini_project_present = "không"
        else:
            mini_project_present = "không_rõ"

    return GradePayload(
        score=score,
        comment=comment,
        integrity_verdict=verdict,
        integrity_confidence_0_100=conf_int,
        integrity_notes=notes_list,
        rubric=rubric,
        mini_project_present=mini_project_present,
    )
