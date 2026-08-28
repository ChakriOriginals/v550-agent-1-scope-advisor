#!/usr/bin/env python3
"""Load and validate instructor-provided V550 canonical course materials."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_PRECEDENT_CARDS = Path(__file__).resolve().parents[1] / "references/gate-1-precedent-cards.md"


class InstructorMaterialError(ValueError):
    """Required instructor-provided material is absent or malformed."""


def load_precedent_cards(path: Path = DEFAULT_PRECEDENT_CARDS) -> list[dict[str, Any]]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: cannot read the Gate 1 comparison example: {exc}") from exc
    matches = re.findall(
        r"<!-- GATE_1_PRECEDENT_CARDS_JSON_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- GATE_1_PRECEDENT_CARDS_JSON_END -->",
        source,
        flags=re.DOTALL,
    )
    if len(matches) != 1:
        raise InstructorMaterialError("INSTRUCTOR MATERIAL NEEDED: the Gate 1 comparison example requires one canonical JSON registry.")
    try:
        registry = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise InstructorMaterialError("INSTRUCTOR MATERIAL NEEDED: the Gate 1 comparison-example registry is invalid JSON.") from exc
    cards = registry.get("cards") if isinstance(registry, dict) else None
    if not isinstance(cards, list) or len(cards) != 1:
        raise InstructorMaterialError("INSTRUCTOR MATERIAL NEEDED: exactly one approved Gate 1 comparison example is required.")
    identifiers: set[str] = set()
    required_text = (
        "card_id",
        "title",
        "case_description",
        "comparability",
        "source_locator",
        "adaptation_label",
    )
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} must be an object.")
        if any(not isinstance(card.get(key), str) or not card[key].strip() for key in required_text):
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} is missing required text.")
        if card.get("approval_status") != "INSTRUCTOR_APPROVED":
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} lacks instructor approval.")
        if card["card_id"] in identifiers:
            raise InstructorMaterialError("INSTRUCTOR MATERIAL NEEDED: Gate 1 comparison-example IDs must be unique.")
        identifiers.add(card["card_id"])
        features = card.get("neutral_features")
        if (
            not isinstance(features, list)
            or not 2 <= len(features) <= 3
            or any(not isinstance(item, str) or not item.strip() for item in features)
        ):
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} needs two or three neutral features.")
        if len(card["source_locator"].strip()) < 30:
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} needs a locatable verified source.")
        if card.get("adapted_for_teaching") is True and "ADAPTED" not in card["adaptation_label"].upper():
            raise InstructorMaterialError(f"INSTRUCTOR MATERIAL NEEDED: comparison example {index + 1} needs an accurate adapted label.")
    return cards


def card_ids(path: Path = DEFAULT_PRECEDENT_CARDS) -> tuple[str]:
    cards = load_precedent_cards(path)
    return (cards[0]["card_id"],)
