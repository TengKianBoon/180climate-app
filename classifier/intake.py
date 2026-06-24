"""classifier/intake.py — Intake classifier for 'describe your own' project type.

This is the ONE additional permitted runtime LLM call (intake boundary only).
NEVER imported by engines/carbon/engine.py — number path remains deterministic.

Maps free-text project description to: REDD | IFM | PEAT | out_of_scope.
Default to out_of_scope when not clearly mappable.
Never accepts user self-assessed eligibility.
"""
from __future__ import annotations
import json
import os
from typing import Any
from pydantic import BaseModel
from typing import Literal


class ClassifierResult(BaseModel):
    category: Literal["REDD", "IFM", "PEAT", "out_of_scope"]
    confidence: Literal["high", "medium", "low"] = "low"
    structured_facts: dict[str, Any] = {}
    rationale: str = ""
    out_of_scope_reason: str = ""


_SYSTEM = """\
You are an expert carbon project classifier for Indonesian forest concessions.
Classify the user's free-text project description into exactly one category:
- REDD: Avoided Planned Deforestation (HTI-type clear-fell on mineral soil forest)
- IFM: Improved Forest Management (HA-type selective logging on mineral soil forest)
- PEAT: Peatland project (concession on peat/swamp soil, any permit type)
- out_of_scope: Does not clearly fit REDD/IFM/PEAT for an Indonesian forest concession

Rules:
1. Default to out_of_scope when uncertain — never guess.
2. NEVER accept user self-assessed eligibility or carbon potential claims.
3. Extract only factual hints: permit type, soil type, forest type, location.
4. Peat soil → PEAT regardless of what the user calls it.
5. If both peat AND mineral forest are mentioned, set structured_facts.mixed=true and classify as REDD (mineral pathway is primary; peat stratum handled by engine).
6. HTI permit + mineral forest → REDD.
7. HA permit + mineral forest → IFM.
8. Respond with JSON only. No prose."""

_USER_TEMPLATE = """\
Project description: {description}
Permit type hint (from form): {permit_type}

Respond with JSON only:
{{
  "category": "REDD" | "IFM" | "PEAT" | "out_of_scope",
  "confidence": "high" | "medium" | "low",
  "structured_facts": {{"permit_type_hint": "...", "soil_type_hint": "...", "forest_type_hint": "...", "mixed": false}},
  "rationale": "one-sentence reason for this classification",
  "out_of_scope_reason": "brief reason if out_of_scope, else empty string"
}}"""


def classify_project(
    description: str,
    permit_type: str = "unknown",
    model: str = "claude-haiku-4-5-20251001",
) -> ClassifierResult:
    """Classify a free-text project description.

    Returns ClassifierResult with category. Falls back to out_of_scope
    if the Anthropic SDK is unavailable or ANTHROPIC_API_KEY is not set.
    """
    if not description.strip():
        return ClassifierResult(
            category="out_of_scope",
            confidence="low",
            rationale="No project description provided — defaulting to out_of_scope.",
        )

    try:
        import anthropic as _anthropic
    except ImportError:
        return ClassifierResult(
            category="out_of_scope",
            confidence="low",
            rationale="Anthropic SDK not available — defaulting to out_of_scope.",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ClassifierResult(
            category="out_of_scope",
            confidence="low",
            rationale="ANTHROPIC_API_KEY not configured — defaulting to out_of_scope.",
        )

    client = _anthropic.Anthropic(api_key=api_key)
    user_msg = _USER_TEMPLATE.format(
        description=description[:2000],
        permit_type=permit_type,
    )

    try:
        message = client.messages.create(
            model=model,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else parts[0]
            if raw.startswith("json\n") or raw.startswith("json\r"):
                raw = raw[5:]
        data = json.loads(raw)
        return ClassifierResult(**data)
    except Exception:
        return ClassifierResult(
            category="out_of_scope",
            confidence="low",
            rationale="Classification failed — defaulting to out_of_scope.",
        )
