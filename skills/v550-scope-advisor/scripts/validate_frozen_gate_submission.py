#!/usr/bin/env python3
"""Coach or evaluate one frozen Waldron gate without supplying the student's fix.

CLI exit codes: 0 OPEN, 1 non-open interaction/result, 2 malformed input or canonical source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from canonical_course_materials import InstructorMaterialError, load_precedent_cards


GATE_NAMES = {
    1: "Big 5 Pre-Planning",
    2: "Requirements",
    3: "Expectations",
    4: "Goals & Objectives",
    5: "Scope of Work",
    6: "Work Breakdown Structure",
}
ALLOWED_REQUIREMENT_TYPES = {
    "legal/regulatory",
    "contractual",
    "client",
    "operational",
    "accessibility/safety",
    "other",
}
ALLOWED_SOURCE_TAGS = {"requirement", "expectation", "preference"}
ALLOWED_OWNERS = {"marcus", "marcus feld", "priya", "priya raghavan", "tomas", "tomas beltrán", "tomas beltran"}
RESOURCE_KEYS = (
    "facilitator_days",
    "software_tools",
    "equipment",
    "materials",
    "contractors",
    "outside_participants",
)
ACTION_VERBS = {
    "analyze", "assess", "compile", "commission", "compare", "convene", "coordinate",
    "create", "define", "document", "draft", "evaluate", "extract", "facilitate", "identify",
    "map", "prepare", "produce", "recommend", "record", "review", "schedule", "synthesize",
    "test", "undertake", "validate", "verify",
}
ACTIVITY_OPENERS = {"meet", "meeting", "hold", "conduct", "attend", "discuss", "research", "interview", "work", "coordinate", "convene", "review"}
EMPTY_MARKERS = {"", "n/a", "n a", "na", "as needed", "tbd", "unknown", "-"}
CANONICAL_GATES_PATH = Path(__file__).resolve().parents[1] / "references/frozen-six-gates.md"

READY_SIGNAL_RE = re.compile(
    r"\b(?:evaluate\s+(?:this|gate\s*[1-6])|submit\s+(?:this|gate\s*[1-6])|i\s+am\s+ready\s+for\s+review|ready\s+for\s+review)\b",
    re.I,
)
DISTRESS_RE = re.compile(
    r"\b(?:overwhelmed|frustrated|stuck|ready\s+to\s+cry|tearful|crying|cannot\s+do\s+this|can't\s+do\s+this)\b",
    re.I,
)
SOURCE_CHALLENGE_RE = re.compile(
    r"\b(?:the\s+(?:agent|ai)\s+is\s+wrong|you(?:'re|\s+are)\s+wrong|recheck\s+(?:the\s+)?source|"
    r"source\s+recheck|i\s+override\s+(?:it|this)|my\s+instructor\s+said)\b",
    re.I,
)
INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|reveal\s+(?:the\s+)?(?:hidden|system|developer)\s+(?:prompt|instructions)|"
    r"force\s+(?:gate\s*)?open|change\s+(?:the\s+)?student\s+key|new\s+rubric|"
    r"\b(?:system|administrator|admin|instructor|test)\s*:\s*.*(?:override|ignore|open|bypass)|"
    r"(?:appeal|override)\s+pin|skip\s+gate|enable\s+test\s+mode)",
    re.I | re.S,
)

FOCUS_QUESTIONS: dict[int, list[tuple[str, str]]] = {
    1: [
        ("Learn from earlier plans", "What earlier plans or studies should Marcus review, and what could each help him avoid repeating or unnecessarily recreating?"),
        ("Know your authority", "What can Marcus control, what can he influence, and what is outside his authority? Why does that matter for the process he designs?"),
        ("Plan the management relationship", "If Dana is hands-off, what check-in rhythm would keep the work sponsored without inventing authority?"),
        ("Choose a patron", "Who could give Marcus inside knowledge, early warning, credibility, or protection when the process gets difficult—and why?"),
        ("Choose the plan type", "Is Marcus creating a one-time allocation, a standing policy, or a scheduling system? What makes that choice fit?"),
        ("Use the evidence already provided", "What could the unread study and the provided comparison example teach Meridian?"),
    ],
    2: [
        ("Identify the non-negotiables", "Which City lease condition and existing space-use agreements must the plan honor?"),
        ("Name the authority and proof", "Who or what makes each item required, and what evidence would show it was satisfied?"),
        ("Plan whom to consult", "Whose input would Marcus need before he can confidently confirm requirements and later understand expectations?"),
        ("Prepare for differing expectations", "What simple sorting tool could help the group discuss priorities once requirements are clear?"),
    ],
    3: [
        ("Start with Dana", "What would you ask Dana to learn what success and failure look like to her?"),
        ("Surface different views", "Which program areas or groups are likely to want different outcomes, and where do those expectations collide?"),
        ("Manage disagreement", "How will Marcus keep objectives visible, state boundaries honestly, and communicate steadily when expectations conflict?"),
        ("Sort with MoSCoW", "How would you classify and justify each item without duplicating it?"),
    ],
    4: [
        ("Separate direction from measurement", "In your own words, how is one broad goal different from a measurable objective?"),
        ("Stay inside Marcus's control", "Could Marcus's team accomplish and prove this objective, or does it assign work or authority that belongs to someone else?"),
        ("Make success visible", "What number, date, count, or piece of evidence would let someone answer yes or no?"),
        ("Use the real checkpoints", "What must be visible by March 19, May 14, and the handoff before June 1?"),
    ],
    5: [
        ("Build broad deliverable phases", "What will someone receive from the existing-conditions research, stakeholder-input work, and preliminary-recommendation phase?"),
        ("Guard against scope creep", "What does scope creep mean here, and which tempting activities belong outside this Facilities Plan?"),
        ("Work within constraints", "Which constraint most shapes the plan, and what can Marcus do within his authority to manage it?"),
        ("Anticipate pushback", "Which action-plan line is most likely to draw resistance, from whom, and how will Marcus explain the process without promising the outcome?"),
        ("Plan the handoff", "What must the board receive, and what must programming receive before June 1?"),
    ],
    6: [
        ("Break down every deliverable", "What specific work packages are needed to produce each Gate 5 deliverable with no gaps or overlap?"),
        ("Assign convening and ownership", "Who schedules the legacy-lead conversation, who facilitates it, and on what authority?"),
        ("Use resources deliberately", "How many facilitator days does the plan carry forward, and what must those days accomplish?"),
        ("Separate fixed from untested", "Which constraints are truly fixed, and which are assumptions or practices nobody has tested?"),
        ("Find unassigned work", "What important responsibility has no owner yet?"),
        ("Run the final audit", "Where does the WBS differ from Gate 5, and what assumption or scope decision follows?"),
    ],
}

STUDENT_CHECK_LABELS = {
    "G1_BIG5_COMPLETE": "Q1–Q5 completion",
    "G1_HISTORY_EVIDENCE": "Q1 — planning history",
    "G1_AUTHORITY_BOUNDARY": "Q3 — practical authority",
    "G1_INTERNAL_STUDY": "Evidence check — internal study",
    "G1_COMPARISON_EXAMPLE": "Evidence check — provided comparison example",
    "G1_COMPARISON_LESSON": "Evidence check — your lesson from the example",
    "G2_COMMUNITY_ACCESS_GAP": "Community-access requirement",
    "G2_DANCE_AGREEMENT": "Dance-school agreement",
    "G2_GALLERY_CALENDAR": "Gallery calendar",
    "G2_NO_CAPITAL_OR_LEASE_CHANGE": "No-capital and lease boundary",
    "G2_REQUIREMENT_SOURCE": "Requirement source or authority",
    "G2_REQUIREMENT_TYPE": "Requirement type",
    "G2_REQUIREMENT_VERIFICATION": "Verification or acceptance evidence",
    "G2_REQUIREMENT_STATUS": "Requirement evidence status",
    "POST_CLOSURE_REVISION": "Your revised section",
    "POST_CLOSURE_IMPROVEMENT_REASON": "Why your revision helps",
}


class InputError(ValueError):
    """The request cannot be evaluated deterministically."""


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if value is not None else ""


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text(value).lower()).strip()


def field(mapping: Any, *names: str, default: Any = None) -> Any:
    if not isinstance(mapping, dict):
        return default
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def all_nonempty(items: Iterable[Any]) -> bool:
    return all(nonempty(item) for item in items)


def meaningful_student_content(value: Any) -> bool:
    leaves: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, dict):
            for child in item.values():
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
        elif isinstance(item, str) and item.strip():
            leaves.append(item.strip())

    collect(value)
    word_count = sum(len(re.findall(r"\b\w+\b", item)) for item in leaves)
    return word_count >= 10 and (len(leaves) >= 2 or word_count >= 25)


def meaningful_section(value: Any, *, minimum_words: int = 6) -> bool:
    """Require an actual student claim, not a lone matching keyword."""

    return len(re.findall(r"\b\w+\b", text(value))) >= minimum_words


def ready_signal_present(value: Any) -> bool:
    if value is True:
        return True
    return isinstance(value, str) and bool(READY_SIGNAL_RE.search(value))


def merge_student_draft(base: Any, update: Any) -> Any:
    """Merge student fragments without rewriting their text."""

    if isinstance(base, dict) and isinstance(update, dict):
        merged = {key: value for key, value in base.items()}
        for key, value in update.items():
            merged[key] = merge_student_draft(merged[key], value) if key in merged else value
        return merged
    if isinstance(base, list) and isinstance(update, list):
        merged = list(base)
        for incoming in update:
            identity = None
            if isinstance(incoming, dict):
                identity = field(incoming, "card_id", "id", "question_id", default=None)
            if identity is not None:
                for index, existing in enumerate(merged):
                    if isinstance(existing, dict) and field(existing, "card_id", "id", "question_id", default=None) == identity:
                        merged[index] = merge_student_draft(existing, incoming)
                        break
                else:
                    merged.append(incoming)
            elif incoming not in merged:
                merged.append(incoming)
        return merged
    return update


def assembled_submission(envelope: dict[str, Any]) -> dict[str, Any]:
    submission = field(envelope, "submission", default={})
    if not isinstance(submission, dict):
        raise InputError("submission must be an object")
    assembled: Any = submission
    updates = field(envelope, "draft_updates", "draftUpdates", default=[])
    if updates is not None and not isinstance(updates, list):
        raise InputError("draft_updates must be an array when supplied")
    for update in updates or []:
        if not isinstance(update, dict):
            raise InputError("every draft update must be an object")
        assembled = merge_student_draft(assembled, update)
    return assembled


def gate1_components(submission: dict[str, Any], cards: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    big5 = field(submission, "big5", default={})
    components = [
        ("Q1", field(big5, "q1_history", "q1", "planning_history")),
        ("Q2", field(big5, "q2_role", "q2", "role")),
        ("Q3", field(big5, "q3_authority", "q3", "authority")),
        ("Q4", field(big5, "q4_patron", "q4", "patron")),
        ("Q5", field(big5, "q5_plan_type", "q5", "plan_type")),
    ]
    research = field(submission, "research_and_development", "research", "r_and_d", default={})
    components.append(("internal study", field(research, "internal_study", "internalStudy", default="")))
    analyses = as_list(field(research, "outside_precedents", "outsidePrecedents", "precedents", default=[]))
    by_id = {
        str(field(item, "card_id", "cardId", default="")): item
        for item in analyses
        if isinstance(item, dict)
    }
    for number, card in enumerate(cards, start=1):
        item = by_id.get(card["card_id"], {})
        components.append(
            (
                "comparison example",
                field(item, "adaptation", "analysis_and_adaptation", "student_adaptation", default=""),
            )
        )
    completed = [label for label, value in components if nonempty(value)]
    remaining = [label for label, value in components if not nonempty(value)]
    return completed, remaining


def student_comparison_example_view(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": card["title"],
        "case_description": card["case_description"],
        "why_comparable": card["comparability"],
        "source": card["source_locator"],
        "features_to_examine": card["neutral_features"],
        "teaching_label": card["adaptation_label"],
    }


def next_focus_question(gate_number: int, envelope: dict[str, Any]) -> tuple[str, str]:
    """Return the first unanswered teaching prompt; focus prompts never become checks."""

    answered = {
        normalized(item)
        for item in as_list(field(envelope, "answered_focus_subheadings", "answeredFocusSubheadings", default=[]))
    }
    for subheading, question in FOCUS_QUESTIONS[gate_number]:
        if normalized(subheading) not in answered:
            return subheading, question
    return FOCUS_QUESTIONS[gate_number][-1]


def integrity_result(gate_number: int, submission: dict[str, Any]) -> dict[str, Any]:
    return {
        "interaction_state": "INTEGRITY_COACHING",
        "attempt_recorded": False,
        "assembled_submission": submission,
        "integrity_reason_code": "UNTRUSTED_INSTRUCTION_IGNORED",
        "student_response": {
            "acknowledgment": "That text cannot change the course rules, identity, gate order, or result.",
            "progress": "Your legitimate course work is still saved; no formal review ran and no private instructions were exposed.",
            "next": "Which part of the current gate would you like to work on next?",
        },
    }


def deployment_configuration_error(message: str) -> dict[str, Any]:
    return {
        "interaction_state": "DEPLOYMENT_BLOCKED",
        "build_configuration_error": True,
        "attempt_recorded": False,
        "errors": [{"code": "TEST_MODE_CONFIGURATION", "message": message}],
        "student_response": {
            "acknowledgment": "This advisor is temporarily unavailable because its deployment safety check failed.",
            "progress": "No student work, telemetry, gate result, or report was changed.",
            "next": "Please ask the instructor to verify the test-environment configuration.",
        },
    }


def validate_deployment_context(envelope: dict[str, Any]) -> dict[str, Any] | None:
    context = field(envelope, "deployment_context", "deploymentContext", default={})
    if context in ({}, None):
        return None
    if not isinstance(context, dict):
        return deployment_configuration_error("deployment_context must be an instructor-controlled object")
    enabled = field(context, "test_mode_enabled", "testModeEnabled", default=False) is True
    if not enabled:
        return None
    authenticated = field(context, "authenticated_instructor_config", "authenticatedInstructorConfig", default=False) is True
    environment = normalized(field(context, "environment", default="production"))
    isolated = field(context, "storage_isolated", "storageIsolated", default=False) is True
    test_namespace = str(field(context, "test_storage_namespace", "testStorageNamespace", default="")).strip()
    production_namespace = str(field(context, "production_storage_namespace", "productionStorageNamespace", default="production")).strip()
    if not authenticated:
        return deployment_configuration_error("test mode requires authenticated instructor deployment configuration")
    if environment != "test":
        return deployment_configuration_error("production deployment must fail closed when test mode is enabled")
    if not isolated or not test_namespace or test_namespace == production_namespace:
        return deployment_configuration_error("test storage must be nonempty and isolated from production storage")
    return None


def evaluate_numeric_item(item: Any) -> dict[str, Any]:
    """Evaluate one instructor-declared numeric item with a private deterministic trace."""

    if not isinstance(item, dict):
        raise InputError("numeric_check must be an object")
    numeric_type = normalized(field(item, "numeric_type", "numericType", default=""))
    if numeric_type not in {"fixed fact", "derived boundary", "estimate", "judgment illustration"}:
        raise InputError("numeric_type must be fixed_fact, derived_boundary, estimate, or judgment_illustration")
    try:
        observed = float(field(item, "observed_value", "observedValue"))
        reference = float(field(item, "reference_value", "referenceValue", "boundary_value", "boundaryValue"))
    except (TypeError, ValueError) as exc:
        raise InputError("numeric_check requires numeric observed and reference/boundary values") from exc
    tolerance_percent = float(field(item, "tolerance_percent", "tolerancePercent", default=5))
    declared_interval = float(field(item, "declared_rounding_interval", "declaredRoundingInterval", default=0))
    units_present = nonempty(field(item, "units", default=""))
    method_sound = field(item, "method_sound", "methodSound", default=False) is True
    assumptions_stated = field(item, "assumptions_stated", "assumptionsStated", default=False) is True
    decision_unchanged = field(item, "decision_unchanged", "decisionUnchanged", default=False) is True
    tolerance = max(abs(reference) * tolerance_percent / 100.0, declared_interval)
    difference = abs(observed - reference)
    if numeric_type == "fixed fact":
        passed = observed == reference
        reason = "Fixed course facts must match exactly."
    elif numeric_type == "derived boundary":
        comparator = str(field(item, "comparator", default="lte")).lower()
        passed = observed <= reference if comparator == "lte" else observed >= reference
        reason = "A hard boundary is recomputed exactly from the underlying entries."
    elif numeric_type == "estimate":
        passed = difference <= tolerance and units_present and method_sound and assumptions_stated and decision_unchanged
        reason = "The estimate must be within tolerance with units, a sound method, stated assumptions, and the same decision."
    else:
        passed = units_present and method_sound and assumptions_stated and decision_unchanged
        reason = "A quantitative illustration is judged by feasibility, transparency, assumptions, and decision relevance."
    trace = {
        "numeric_type": numeric_type.replace(" ", "_"),
        "reference_or_boundary_value": reference,
        "configured_tolerance": tolerance if numeric_type == "estimate" else 0,
        "observed_value": observed,
        "units_present": units_present,
        "method_sound": method_sound,
        "assumptions_stated": assumptions_stated,
        "decision_unchanged": decision_unchanged,
        "result": "PASS" if passed else "FAIL",
    }
    if passed:
        feedback = "This estimate is close enough for the project decision, and your method, units, and assumptions support it."
        next_move = "Move to the next unfinished item; no replacement calculation is required."
    elif numeric_type == "derived boundary":
        feedback = f"The recomputed total is {observed:g}, so it does not satisfy the exact {reference:g} boundary."
        next_move = "Revise only the capacity-driving entries, then recheck the total."
    else:
        feedback = reason
        next_move = "Recheck this one calculation with units, method, assumptions, and its effect on the decision."
    return {
        "interaction_state": "NUMERIC_FEEDBACK",
        "attempt_recorded": False,
        "numeric_item_satisfied": passed,
        "private_numeric_trace": trace,
        "student_response": {
            "acknowledgment": feedback,
            "progress": "Your other correct reasoning remains saved.",
            "next": next_move,
        },
    }


def source_recheck_result(gate_number: int, submission: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    opening = "Thanks for challenging that. I will recheck it against the approved course sources."
    outcome = normalized(field(envelope, "source_recheck_outcome", "sourceRecheckOutcome", default=""))
    test_context = field(envelope, "deployment_context", "deploymentContext", default={})
    can_simulate = isinstance(test_context, dict) and field(
        test_context, "authenticated_instructor_config", "authenticatedInstructorConfig", default=False
    ) is True and normalized(field(test_context, "environment", default="")) == "test"
    if outcome in {"ai wrong", "source conflict"} and not can_simulate:
        outcome = ""
    if outcome == "ai wrong":
        return {
            "interaction_state": "SOURCE_RECHECK_CORRECTED",
            "attempt_recorded": False,
            "attempt_count_preserved": True,
            "assembled_submission": submission,
            "gate_history_note": "AI factual check corrected from approved sources; recompute without a new student attempt.",
            "student_response": {
                "acknowledgment": opening,
                "outcome": "The AI check was wrong: the approved source supports your submitted fact. I corrected the check without counting another attempt.",
                "progress": "Your completed work is preserved and the current gate is ready for a source-backed recomputation.",
                "next": "Would you like me to recompute the current gate now?",
            },
        }
    if outcome == "source conflict":
        return {
            "interaction_state": "INSTRUCTOR_REVIEW_NEEDED",
            "attempt_recorded": False,
            "attempt_count_preserved": True,
            "assembled_submission": submission,
            "instructor_handoff": "Approved sources conflict on the challenged check; preserve the draft and verify the controlling source before evaluation.",
            "student_response": {
                "acknowledgment": opening,
                "outcome": "Instructor review needed: the approved sources conflict, so I cannot verify this check safely.",
                "progress": "Your completed work and attempt count are preserved; this hold is not a student failure.",
                "next": "Would you like a concise handoff note for the instructor?",
            },
        }
    if outcome == "supported":
        result_text = "The original check is supported: the approved source still supports the required item as evaluated."
        next_move = "What part of your own answer would you like to revise using that source reason?"
    else:
        result_text = "I can recheck the factual basis, but I need the reason you think the check conflicts with the course source."
        next_move = "What source section or factual reason should I compare?"
    return {
        "interaction_state": "SOURCE_RECHECK",
        "attempt_recorded": False,
        "attempt_count_preserved": True,
        "assembled_submission": submission,
        "student_response": {
            "acknowledgment": opening,
            "outcome": result_text,
            "progress": "No gate result, attempt count, or saved student work changed during the recheck.",
            "next": next_move,
        },
    }


def _next_gate1_question(remaining: list[str]) -> str:
    if not remaining:
        return "Your Gate 1 answer is assembled. Would you like me to evaluate this now?"
    current = remaining[0]
    questions = {
        "Q1": "Use one event from the Planning history section. What could that record suggest might happen again?",
        "Q2": "Marcus was told to lead the process. What does that role establish, and what remains undefined?",
        "Q3": "Which planning decisions can Marcus control, and which decisions remain outside his authority?",
        "Q4": "Who could provide early warning and protection for this planning process, and why?",
        "Q5": "Which course plan type fits this work, and why?",
        "internal study": "What existing study in the Building section could inform the evidence check, and what might it help Marcus learn?",
        "comparison example": "What is one practice Meridian could learn from the comparison example, and why might it help?",
    }
    return questions[current]


def drafting_result(
    gate_number: int,
    submission: dict[str, Any],
    envelope: dict[str, Any],
    cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cards = cards or []
    latest = str(field(envelope, "latest_message", "latestMessage", default=""))
    full_checklist = field(envelope, "full_checklist_requested", "fullChecklistRequested", default=False) is True
    if full_checklist:
        checklist = {
            1: [
                "Answer Q1 through Q5 in your own words.",
                "Use at least one event from Meridian's planning history in Q1.",
                "Keep Q3 within Marcus's stated authority.",
                "Identify the unread 2019 study.",
                "Explain one lesson from the provided comparison example.",
            ],
            2: [
                "Record the three supplied binding conditions.",
                "Include source, type, verification evidence, and status for every requirement.",
                "Stay inside the no-capital and no-lease-change boundary.",
            ],
        }.get(gate_number, ["Use the gate's blank structure and complete each student-authored section."])
        return {
            "interaction_state": "DRAFTING",
            "attempt_recorded": False,
            "assembled_submission": submission,
            "student_response": {
                "acknowledgment": "Here is the complete planning checklist you requested.",
                "checklist": checklist,
                "progress": "This is a planning aid; no formal review has run.",
                "next": "Choose the first unfinished section and answer it in your own words.",
            },
        }
    if gate_number == 1:
        if re.search(r"\bwhat\s+is\s+r\s*(?:&|and)\s*d\b|\bwhat\s+does\s+r\s*(?:&|and)\s*d\s+mean\b", latest, re.I):
            return {
                "interaction_state": "DRAFTING",
                "attempt_recorded": False,
                "assembled_submission": submission,
                "student_response": {
                    "acknowledgment": "You are asking about a course term before using it.",
                    "explanation": "For this assignment, it means a short evidence check. It has two parts: the internal study and one comparison example.",
                    "progress": "The evidence check has two parts: the 2019 study and one comparison example.",
                    "next": "Start with the internal source: what existing study could inform this planning process?",
                },
            }
        completed, remaining = gate1_components(submission, cards)
        current_part = normalized(field(envelope, "current_part", "currentPart", default=""))
        response: dict[str, Any] = {
            "acknowledgment": "I saved the student-authored pieces you provided; you will not need to enter them again.",
            "progress": (
                "Completed: " + (", ".join(completed) if completed else "none yet") + ". "
                "Still working on: " + (", ".join(remaining) if remaining else "nothing before review") + "."
            ),
            "next": _next_gate1_question(remaining),
        }
        focus_by_component = {
            "Q1": "Learn from earlier plans",
            "Q2": "Know your authority",
            "Q3": "Know your authority",
            "Q4": "Choose a patron",
            "Q5": "Choose the plan type",
            "internal study": "Use the evidence already provided",
            "comparison example": "Use the evidence already provided",
        }
        if remaining:
            response["focus_subheading"] = focus_by_component[remaining[0]]
        if current_part in {"part c", "evidence scan", "evidence", "research and development", "r and d"}:
            response["comparison_example"] = student_comparison_example_view(cards[0])
        elif remaining and remaining[0] == "comparison example":
            response["comparison_example"] = student_comparison_example_view(cards[0])
        return {
            "interaction_state": "DRAFTING",
            "attempt_recorded": False,
            "assembled_submission": submission,
            "student_response": response,
        }
    subheading, question = next_focus_question(gate_number, envelope)
    return {
        "interaction_state": "DRAFTING",
        "attempt_recorded": False,
        "assembled_submission": submission,
        "student_response": {
            "acknowledgment": "I saved this student-authored draft update.",
            "progress": "Your current gate answer remains in progress; no formal review has run.",
            "focus_subheading": subheading,
            "next": question,
        },
    }


def help_ladder_result(gate_number: int, submission: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any] | None:
    attempts = field(envelope, "same_component_attempts", "sameComponentAttempts", default=0)
    component = normalized(field(envelope, "stuck_component", "stuckComponent", default=""))
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts <= 0 or not component:
        return None
    if "study" in component:
        responses = {
            1: ("An internal source is evidence Meridian already has.", "Which part of the scenario describes records already available inside the organization?"),
            2: ("Look under the Building heading for a study and booking information.", "What kind of space-use evidence would you notice there?"),
            3: ("The Building section says an unread 2019 space-utilization study is in the admin-suite filing cabinet. That resolves where to find it.", "What could that study help Marcus learn before recommending an allocation?"),
            4: ("In an unrelated library case, a manager might compare room-booking records before changing shared-room rules.", "Complete this starter in your own words: The study could help Marcus ___ because ___."),
        }
    else:
        responses = {
            1: ("Let's define the current course concept before applying it.", "What decision is this section asking the project manager to make?"),
            2: ("Return to the exact scenario heading tied to this section and notice the authority or evidence it supplies.", "Which supplied detail matters most?"),
            3: ("Choose between two possibilities: a missing fact or a project-judgment decision.", "Which of those two is blocking you?"),
            4: ("Use a short unrelated example to separate the concept from the Waldron decision.", "Complete this starter in your own words: The reasoning I would transfer is ___ because ___."),
        }
    if attempts >= 5:
        explanation = "You have preserved work on the other sections. This item now needs instructor clarification."
        next_move = "Would you like a short handoff note that lists the completed work and this one unresolved question?"
        label = "NEEDS INSTRUCTOR CLARIFICATION"
    else:
        explanation, next_move = responses[min(attempts, 4)]
        label = None
    response: dict[str, Any] = {
        "acknowledgment": "I kept the work you have already completed.",
        "explanation": explanation,
        "progress": "Only this component is being handled now; no formal review has run.",
        "next": next_move,
    }
    if label:
        response["handoff_status"] = label
    return {
        "interaction_state": "COACHING",
        "attempt_recorded": False,
        "assembled_submission": submission,
        "student_response": response,
    }


def saved_progress_labels(gate_number: int, submission: dict[str, Any]) -> list[str]:
    if gate_number == 1:
        big5 = field(submission, "big5", default={})
        labels: list[str] = []
        for label, names in (
            ("Q1", ("q1_history", "q1", "planning_history")),
            ("Q2", ("q2_role", "q2", "role")),
            ("Q3", ("q3_authority", "q3", "authority")),
            ("Q4", ("q4_patron", "q4", "patron")),
            ("Q5", ("q5_plan_type", "q5", "plan_type")),
        ):
            if nonempty(field(big5, *names)):
                labels.append(label)
        research = field(submission, "research_and_development", "research", "r_and_d", default={})
        if nonempty(field(research, "internal_study", "internalStudy", default="")):
            labels.append("the internal study")
        for index, item in enumerate(
            as_list(field(research, "outside_precedents", "outsidePrecedents", "precedents", default=[])),
            start=1,
        ):
            if isinstance(item, dict) and nonempty(
                field(item, "adaptation", "analysis_and_adaptation", "student_adaptation", default="")
            ):
                labels.append("the comparison example")
        return labels
    return [str(key).replace("_", " ") for key, value in submission.items() if nonempty(value)][:5]


def interrupted_result(kind: str, gate_number: int, submission: dict[str, Any]) -> dict[str, Any]:
    completed = saved_progress_labels(gate_number, submission)
    progress = (
        "Saved progress: " + ", ".join(completed) + "; no review is running."
        if completed
        else "Your current draft is saved; no review is running."
    )
    if kind.startswith("DISTRESS"):
        response = {
            "acknowledgment": "I’m sorry this is feeling like a lot right now.",
            "progress": progress,
            "next": "Would you prefer one small question, a brief pause, or a short instructor handoff note?",
        }
        note = "student requested slower pacing"
    else:
        response = {
            "acknowledgment": "That interaction did not work as expected, but the content you provided is saved.",
            "progress": progress + " This did not count as a formal review.",
            "next": "Use plain text to send the next fragment or type the ready-for-review phrase when you choose.",
        }
        note = ""
    return {
        "interaction_state": kind,
        "attempt_recorded": False,
        "assembled_submission": submission,
        "telemetry_note": note,
        "student_response": response,
    }


def canonical_exclusions(path: Path = CANONICAL_GATES_PATH) -> list[dict[str, str]]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read canonical gate source: {exc}") from exc
    for match in re.finditer(r"```json\s*(\{.*?\})\s*```", source, re.S):
        try:
            candidate = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        records = candidate.get("canonical_exclusions") if isinstance(candidate, dict) else None
        if isinstance(records, list) and len(records) == 5:
            parsed: list[dict[str, str]] = []
            for record in records:
                if not isinstance(record, dict) or not nonempty(record.get("id")) or not nonempty(record.get("meaning")):
                    raise InputError("canonical_exclusions contains an invalid record")
                parsed.append({"id": str(record["id"]), "meaning": str(record["meaning"])})
            if len({record["id"] for record in parsed}) != 5:
                raise InputError("canonical_exclusions IDs are not unique")
            return parsed
    raise InputError("frozen-six-gates.md has no canonical_exclusions JSON block")


def check(code: str, passed: bool, label: str, failure: str) -> dict[str, Any]:
    return {
        "code": code,
        "result": "PASS" if passed else "FAIL",
        "label": label,
        "message": label if passed else failure,
    }


def _contains_any(value: Any, patterns: Iterable[str]) -> bool:
    candidate = normalized(value)
    return any(re.search(pattern, candidate) for pattern in patterns)


def _asserts_forbidden_authority(value: Any) -> bool:
    candidate = normalized(value)
    actor = r"(?:i|marcus|he|pm|project manager)"
    positive_claims = (
        rf"\b{actor}\b.{{0,45}}\b(?:have|has|hold|holds|claim|claims)\b.{{0,20}}"
        r"\b(?:full|complete|sole|ultimate) authority\b",
        rf"\b{actor}\b.{{0,70}}\b(?:make|makes|have|has|take|takes)\b.{{0,20}}"
        r"\b(?:the )?final (?:call|decision)\b.{{0,45}}\ballocation\b",
    )
    for pattern in positive_claims:
        for match in re.finditer(pattern, candidate):
            if not re.search(
                r"\b(?:do not|does not|did not|don t|doesn t|didn t|cannot|can t|lack|lacks|without)\b",
                match.group(0),
            ):
                return True
    concepts = (
        "final allocation", "final call on the allocation", "board final", "legacy leads participate", "legacy lead participation",
        "season calendar", "2027 28 season", "lease",
    )
    for concept in concepts:
        for match in re.finditer(re.escape(concept), candidate):
            window = candidate[max(0, match.start() - 90):match.end() + 35]
            if re.search(r"\b(does not|doesn t|cannot|can t|not authorized|no authority|board decides|outside .* authority)\b", window):
                continue
            if re.search(r"\b(marcus|he)\b.*\b(control|controls|decide|decides|authority|approve|approves|choose|chooses)\b", window):
                return True
    return False


def gate1(submission: dict[str, Any], _: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    cards = load_precedent_cards()
    allowed_card_ids = {card["card_id"] for card in cards}
    big5 = field(submission, "big5", default={})
    answers = [
        field(big5, "q1_history", "q1", "planning_history"),
        field(big5, "q2_role", "q2", "role"),
        field(big5, "q3_authority", "q3", "authority"),
        field(big5, "q4_patron", "q4", "patron"),
        field(big5, "q5_plan_type", "q5", "plan_type"),
    ]
    q1, _, q3, q4, q5 = answers
    research = field(submission, "research_and_development", "research", "r_and_d", default={})
    study = field(research, "internal_study", "internalStudy", default="")
    precedents = as_list(field(research, "outside_precedents", "outsidePrecedents", "precedents", default=[]))
    history_evidence = meaningful_section(q1) and _contains_any(
        q1,
        (r"\bbinder\b", r"integration plan", r"website consolidation", r"donor database", r"donor database merge"),
    )
    history_contradiction = _contains_any(q1, (r"\bno (prior |previous )?planning\b", r"\bnever (planned|had a plan)\b"))
    submitted_card_ids = [
        str(field(item, "card_id", "cardId", default=""))
        for item in precedents
        if isinstance(item, dict)
    ]
    exact_example = (
        len(precedents) == 1
        and len(submitted_card_ids) == 1
        and len(set(submitted_card_ids)) == 1
        and set(submitted_card_ids) == allowed_card_ids
    )
    lesson_ok = (
        len(precedents) == 1
        and all(isinstance(item, dict) for item in precedents)
        and all(
            meaningful_section(
                field(item, "adaptation", "analysis_and_adaptation", "student_adaptation"),
                minimum_words=6,
            )
            for item in precedents
        )
    )
    checks = [
        check("G1_BIG5_COMPLETE", all_nonempty(answers), "All five Big 5 answers are present.", "One or more Big 5 answers are missing."),
        check("G1_HISTORY_EVIDENCE", history_evidence and not history_contradiction, "The planning-history answer uses the scenario record.", "The planning-history answer does not accurately engage the project’s actual planning record."),
        check("G1_AUTHORITY_BOUNDARY", nonempty(q3) and not _asserts_forbidden_authority(q3), "The authority answer stays within the project manager’s stated control.", "The authority answer is missing or exceeds the project manager’s stated boundary."),
        check("G1_INTERNAL_STUDY", _contains_any(study, (r"\b2019\b.*\bstudy\b", r"\bstudy\b.*\b2019\b")) and "unread" in normalized(study), "The internal study is identified.", "The required internal study is not identified accurately."),
        check("G1_COMPARISON_EXAMPLE", exact_example, "The evidence check uses the single instructor-provided comparison example.", "The evidence check must use exactly the one instructor-provided comparison example."),
        check("G1_COMPARISON_LESSON", lesson_ok, "The student explains one lesson Meridian could use.", "The provided comparison example still needs one meaningful student-written lesson for Meridian."),
    ]
    criteria: list[str] = []
    if not _contains_any(q1, (r"execut", r"repeat", r"follow through", r"implementation")):
        criteria.append("Non-blocking: explain what the planning history suggests could recur during execution.")
    if not _contains_any(q4, (r"lay of the land", r"early warning", r"protect", r"approval", r"inside knowledge")):
        criteria.append("Non-blocking: strengthen the patron rationale against the functions a patron supplies.")
    if not _contains_any(q5, (r"one time allocation", r"standing policy", r"scheduling system")):
        criteria.append("Non-blocking: make the chosen plan type and its rationale more explicit.")
    return checks, criteria, []


def _requirement_texts(requirements: list[Any]) -> str:
    return " ".join(text(item) for item in requirements if isinstance(item, dict))


def _capital_or_lease_presumption(statement: str) -> bool:
    candidate = normalized(statement)
    prohibited = r"(renovat|construction|construct |capital purchase|buy equipment|purchase equipment|lease change|change the lease|renegotiat)"
    if not re.search(prohibited, candidate):
        return False
    if re.search(r"\b(no|without|cannot|can t|must not|does not|not permitted|out of scope|prohibit)\b.{0,45}" + prohibited, candidate):
        return False
    if re.search(r"\b(ada|accessibility|fire code|occupancy)\b", candidate) and not re.search(r"\b(must|shall|required|need to|will)\b.{0,35}" + prohibited, candidate):
        return False
    return bool(re.search(r"\b(must|shall|required|need to|will|plan to|solution)\b.{0,60}" + prohibited, candidate) or re.search(prohibited, candidate))


def gate2(submission: dict[str, Any], prior: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    requirements = as_list(field(submission, "requirements", default=[]))
    statements = _requirement_texts(requirements)
    norm = normalized(statements)
    community = "900" in norm and "515" in norm and bool(re.search(r"\b(gap|shortfall|difference|385|currently documented|current baseline)\b", norm))
    dance = bool(re.search(r"dance.{0,80}(august|aug).{0,20}2028|(august|aug).{0,20}2028.{0,80}dance", norm))
    gallery = bool(re.search(r"gallery.{0,80}(fourteen|14)[ -]?month|(fourteen|14)[ -]?month.{0,80}gallery", norm))
    capital_ok = all(not _capital_or_lease_presumption(str(field(item, "statement", "text", default=""))) for item in requirements if isinstance(item, dict))
    sources_ok = bool(requirements) and all(nonempty(field(item, "source_authority", "source/authority", "source", "authority")) for item in requirements if isinstance(item, dict))
    allowed_type_tokens = {normalized(item_type) for item_type in ALLOWED_REQUIREMENT_TYPES}
    types_ok = bool(requirements) and all(
        isinstance(item, dict)
        and (
            normalized(field(item, "type")) in allowed_type_tokens
            or normalized(field(item, "type")).startswith("other ")
        )
        and (
            normalized(field(item, "type")) != "other"
            or nonempty(field(item, "type_explanation", "typeExplanation", "other_explanation"))
        )
        for item in requirements
    )
    verification_ok = bool(requirements) and all(nonempty(field(item, "verification_method", "verification_evidence", "acceptance_evidence")) for item in requirements if isinstance(item, dict))
    status_ok = bool(requirements) and all(str(field(item, "status", default="")).strip().upper() in {"CONFIRMED", "VERIFY WITH THE APPROPRIATE AUTHORITY"} for item in requirements if isinstance(item, dict))
    checks = [
        check("G2_COMMUNITY_ACCESS_GAP", community, "The community-access requirement includes its current-state comparison.", "The community-access requirement lacks an accurate current-state/shortfall comparison."),
        check("G2_DANCE_AGREEMENT", dance, "The binding dance agreement is represented.", "The binding dance agreement is missing or misstated."),
        check("G2_GALLERY_CALENDAR", gallery, "The contracted gallery horizon is represented.", "The contracted gallery-calendar horizon is missing or misstated."),
        check("G2_NO_CAPITAL_OR_LEASE_CHANGE", capital_ok, "No listed requirement presumes capital work or a lease change.", "At least one requirement presumes work outside the no-capital/lease boundary."),
        check("G2_REQUIREMENT_SOURCE", sources_ok, "Every requirement names its source or authority.", "At least one requirement lacks its source or authority."),
        check("G2_REQUIREMENT_TYPE", types_ok, "Every requirement uses an allowed type label.", "At least one requirement lacks an allowed type or an explanation for `other`."),
        check("G2_REQUIREMENT_VERIFICATION", verification_ok, "Every requirement states verification or acceptance evidence.", "At least one requirement lacks a verification method or acceptance evidence."),
        check("G2_REQUIREMENT_STATUS", status_ok, "Every requirement uses an allowed evidence status.", "At least one requirement lacks an allowed confirmation/verification status."),
    ]
    criteria: list[str] = []
    if any(re.search(r"\bmust (use|receive|have) (the )?(firebay|ruth|studio|gallery)\b", normalized(field(item, "statement", default=""))) for item in requirements if isinstance(item, dict)):
        criteria.append("Non-blocking: distinguish a necessity from a preferred allocation solution.")
    if not criteria:
        criteria.append("Non-blocking: check that each authority could actually verify the evidence named.")
    cross: list[str] = []
    gate1_prior = field(prior, "gate_1", "gate1", default={})
    prior_patron = field(field(gate1_prior, "big5", default={}), "q4_patron", "q4", default="")
    if "ruth" in normalized(prior_patron) and "lease" not in norm and "ruth" not in norm:
        cross.append("Non-blocking: the current requirements discussion does not reconnect to the earlier patron/lease rationale.")
    return checks, criteria, cross


def _moscow_lists(submission: dict[str, Any]) -> dict[str, list[Any]]:
    moscow = field(submission, "moscow", default={})
    return {
        "must": as_list(field(moscow, "must", "MUST", default=[])),
        "should": as_list(field(moscow, "should", "SHOULD", default=[])),
        "could": as_list(field(moscow, "could", "COULD", default=[])),
        "wont": as_list(field(moscow, "wont", "won't", "WONT", "WONT_THIS_TIME", default=[])),
    }


def _meaning_matches(item_text: Any, meaning: str) -> bool:
    item_words = set(normalized(item_text).split())
    meaning_words = {word for word in normalized(meaning).split() if len(word) > 3 and word not in {"three", "legacy", "city"}}
    return len(item_words & meaning_words) >= min(2, max(1, len(meaning_words)))


def gate3(submission: dict[str, Any], _: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    groups = _moscow_lists(submission)
    exclusions = canonical_exclusions()
    wont_by_id: dict[str, list[dict[str, Any]]] = {}
    misplaced: set[str] = set()
    all_items: list[tuple[str, dict[str, Any]]] = []
    for category, items in groups.items():
        for item in items:
            if not isinstance(item, dict):
                continue
            all_items.append((category, item))
            item_id = str(field(item, "id", default=""))
            if category == "wont":
                wont_by_id.setdefault(item_id, []).append(item)
            elif any(item_id == exclusion["id"] for exclusion in exclusions):
                misplaced.add(item_id)
    canonical_ok = True
    for exclusion in exclusions:
        records = wont_by_id.get(exclusion["id"], [])
        if len(records) != 1 or not _meaning_matches(field(records[0], "text", "statement", "meaning", default=""), exclusion["meaning"]):
            canonical_ok = False
    canonical_ok = canonical_ok and not misplaced and sum(len(wont_by_id.get(item["id"], [])) for item in exclusions) == 5
    conflicts = as_list(field(submission, "conflicts", default=[]))
    firebay = False
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        areas = {normalized(value) for value in as_list(field(conflict, "program_areas", "programAreas", default=[]))}
        resource = normalized(field(conflict, "resource", default=""))
        has_new_play = any("new play" in area for area in areas)
        has_mainstage = any("mainstage" in area for area in areas)
        if len(areas) >= 2 and has_new_play and has_mainstage and "firebay" in resource:
            firebay = True
    tags_ok = bool(all_items) and all(normalized(field(item, "source_tag", "tag", default="")) in ALLOWED_SOURCE_TAGS for _, item in all_items)
    canonical_tags = all(normalized(field(item, "source_tag", "tag", default="")) == "requirement" for _, item in all_items if str(field(item, "id", default="")) in {record["id"] for record in exclusions})
    seen: dict[str, str] = {}
    duplicate = False
    for category, item in all_items:
        item_norm = normalized(field(item, "text", "statement", default=""))
        item_id = str(field(item, "id", default=""))
        for token in (f"id:{item_id}" if item_id else "", f"text:{item_norm}" if item_norm else ""):
            if token and token in seen and seen[token] != category:
                duplicate = True
            elif token:
                seen[token] = category
    checks = [
        check("G3_WONT_NONEMPTY", bool(groups["wont"]), "The Won’t category is present and non-empty.", "The Won’t category is missing or empty."),
        check("G3_CANONICAL_EXCLUSIONS", canonical_ok, "All canonical exclusions appear as distinct Won’t entries with stable IDs and meanings.", "One or more canonical exclusions has the wrong identity, meaning, location, or row structure."),
        check("G3_FIREBAY_CONFLICT", firebay, "The named program-area conflict over the shared resource is visible.", "The required program-area conflict is not represented accurately."),
        check("G3_SOURCE_TAG", tags_ok and canonical_tags, "Every MoSCoW item has an allowed source tag and canonical exclusions are requirements.", "At least one MoSCoW item has a missing/invalid source tag or a canonical exclusion is mistagged."),
        check("G3_NO_DUPLICATES", not duplicate, "No materially identical item is repeated across categories.", "A materially identical item appears in more than one MoSCoW category."),
    ]
    criteria = ["Non-blocking: preserve attribution, unresolved conflict, and justification when refining MoSCoW placement."]
    return checks, criteria, []


def _date_after_june_first(value: Any) -> bool:
    candidate = str(value).strip()
    if not candidate:
        return False
    try:
        parsed = dt.date.fromisoformat(candidate[:10])
        return (parsed.month, parsed.day) > (6, 1)
    except ValueError:
        pass
    lower = candidate.lower()
    month_numbers = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
    match = re.search(r"\b(" + "|".join(month_numbers) + r")\s+(\d{1,2})\b", lower)
    return bool(match and (month_numbers[match.group(1)], int(match.group(2))) > (6, 1))


def gate4(submission: dict[str, Any], _: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    goal_value = field(submission, "goal", "goals", default=None)
    if isinstance(goal_value, list):
        goals = [item for item in goal_value if nonempty(item)]
    else:
        goals = [goal_value] if nonempty(goal_value) else []
    objectives = as_list(field(submission, "objectives", default=[]))
    date_ok = all(not _date_after_june_first(field(item, "completion_date", "completionDate", "due_date", default="")) for item in objectives if isinstance(item, dict))
    serialized = normalized(submission)
    may14 = bool(re.search(r"\bmay\s+14\b|\b05[/-]14\b|\b\d{4}-05-14\b", serialized))
    measurable = bool(objectives) and all(bool(re.search(r"\d", text(field(item, "statement", "text", default="")) + " " + text(field(item, "completion_date", "completionDate", "due_date", default="")))) for item in objectives if isinstance(item, dict))
    checks = [
        check("G4_EXACTLY_ONE_GOAL", len(goals) == 1, "Exactly one goal is present.", "The submission does not contain exactly one goal."),
        check("G4_OBJECTIVE_COUNT", 3 <= len(objectives) <= 5, "The objective count is between three and five.", "The submission must contain three to five objectives."),
        check("G4_NO_DATE_AFTER_JUNE_1", date_ok, "No objective completes after the frozen deadline.", "At least one objective completes after the frozen deadline."),
        check("G4_MAY_14_FIXED_POINT", may14, "The fixed decision point is represented.", "The required fixed decision point is absent."),
        check("G4_OBJECTIVE_MEASURABLE_TOKEN", measurable, "Every objective contains a number, date, or count.", "At least one objective lacks a number, date, or count."),
    ]
    criteria: list[str] = []
    if any(not nonempty(field(item, "success_criterion", "successCriterion")) for item in objectives if isinstance(item, dict)):
        criteria.append("Non-blocking: strengthen the one-to-one tangible success criterion for each objective.")
    criteria.append("Non-blocking: test goal direction, objective SMART quality, and real-world timing without adding a gate condition.")
    return checks, criteria, []


def _canonical_exclusions_in(items: list[Any], exclusions: list[dict[str, str]]) -> bool:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if isinstance(item, dict):
            by_id.setdefault(str(field(item, "id", default="")), []).append(item)
    for exclusion in exclusions:
        records = by_id.get(exclusion["id"], [])
        if len(records) != 1 or not _meaning_matches(field(records[0], "text", "statement", "meaning", default=""), exclusion["meaning"]):
            return False
    return len([item for item in items if isinstance(item, dict) and str(field(item, "id", default="")) in {record["id"] for record in exclusions}]) == 5


def _starts_action_verb(value: Any) -> bool:
    first = normalized(value).split()[:1]
    return bool(first and first[0] in ACTION_VERBS)


def _is_output(value: Any) -> bool:
    words = normalized(value).split()
    return bool(words) and words[0] not in ACTIVITY_OPENERS and normalized(value) not in EMPTY_MARKERS


def gate5(submission: dict[str, Any], _: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    statement = field(submission, "project_statement", "projectStatement", default={})
    labels = (
        ("trigger",),
        ("action",),
        ("frequency_and_timing", "frequency and timing", "timing"),
        ("scope", "scope_breadth_and_complexity"),
        ("constraints_and_uncertainty", "constraints and uncertainty", "constraints_uncertainty"),
    )
    statement_ok = isinstance(statement, dict) and all(nonempty(field(statement, *aliases)) for aliases in labels)
    exclusions = as_list(field(submission, "exclusions", default=[]))
    canonical_ok = _canonical_exclusions_in(exclusions, canonical_exclusions())
    constraints = field(submission, "constraints", default=None)
    assumptions = field(submission, "assumptions", default=None)
    separate = nonempty(constraints) and nonempty(assumptions) and constraints is not assumptions and normalized(constraints) != normalized(assumptions)
    action_plan = as_list(field(submission, "scope_action_plan", "action_plan", "actionPlan", default=[]))
    actions_ok = bool(action_plan) and all(_starts_action_verb(field(item, "action", "text", default=item if isinstance(item, str) else "")) for item in action_plan)
    deliverables = as_list(field(submission, "deliverables", default=[]))
    outputs_ok = bool(deliverables) and all(_is_output(field(item, "output", "name", default="")) for item in deliverables if isinstance(item, dict))
    approvers_ok = bool(deliverables) and all(normalized(field(item, "approver", "named_approver", default="")) not in EMPTY_MARKERS for item in deliverables if isinstance(item, dict))
    dates = {str(field(item, "due_date", "date", "delivery_date", default="")).strip() for item in deliverables if isinstance(item, dict) and nonempty(field(item, "due_date", "date", "delivery_date", default=""))}
    checks = [
        check("G5_PROJECT_STATEMENT_COMPONENTS", statement_ok, "The project statement contains all five labeled components.", "The project statement is missing one or more frozen labeled components."),
        check("G5_CANONICAL_EXCLUSIONS", canonical_ok, "The exclusions section preserves all five canonical IDs and meanings.", "The exclusions section changes, omits, duplicates, or misidentifies a canonical exclusion."),
        check("G5_CONSTRAINTS_ASSUMPTIONS_SEPARATE", separate, "Constraints and assumptions are separately labeled and populated.", "Constraints and assumptions are missing, combined, or indistinguishable."),
        check("G5_ACTION_VERB", actions_ok, "Every Scope Action Plan line begins with an action verb.", "At least one Scope Action Plan line does not begin with an action verb."),
        check("G5_DELIVERABLE_OUTPUT", outputs_ok, "Every deliverable is an output rather than an activity.", "At least one deliverable is an activity rather than a handed-over output."),
        check("G5_NAMED_APPROVER", approvers_ok, "Every deliverable has a named approver.", "At least one deliverable lacks a named approver."),
        check("G5_PHASED_DATES", len(dates) >= 2, "Deliverables land on at least two distinct dates.", "The deliverable dates are missing or collapse onto fewer than two dates."),
    ]
    criteria = ["Non-blocking: check action-plan coverage, consequential assumptions, phased handoff, and Waldron-specific scope language."]
    return checks, criteria, []


def _work_packages(elements: list[Any]) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        item_type = normalized(field(item, "type", default="work_package"))
        if item_type in {"work package", "workpackage", "package", "task", "leaf"} or field(item, "is_work_package", "isWorkPackage") is True:
            packages.append(item)
    return packages


def _resource_value_ok(key: str, value: Any) -> bool:
    if key == "facilitator_days":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value >= 0
    return isinstance(value, str) and normalized(value) not in EMPTY_MARKERS


def _hierarchy_ok(elements: list[Any], deliverable_ids: set[str]) -> bool:
    records = [item for item in elements if isinstance(item, dict)]
    ids = [str(field(item, "id", default="")).strip() for item in records]
    if not ids or any(not item_id for item_id in ids) or len(ids) != len(set(ids)):
        return False
    id_set = set(ids)
    for item, item_id in zip(records, ids):
        parent = field(item, "parent_id", "parentId", default=None)
        if nonempty(parent):
            parent_id = str(parent)
            if parent_id not in id_set or not (item_id.startswith(parent_id + ".") or item_id.startswith(parent_id + "-")):
                return False
        elif "." in item_id or "-" in item_id:
            return False
        deliverable_id = str(field(item, "deliverable_id", "deliverableId", default="")).strip()
        branch = normalized(field(item, "branch", "link", default=""))
        if deliverable_id not in deliverable_ids and not any(token in branch for token in ("project management", "management", "preplanning", "pre planning", "big 5", "research", "requirements", "expectations")):
            return False
    return True


def _summary_ok(summary: Any, elements: list[Any]) -> bool:
    if not isinstance(summary, dict):
        return False
    records = [item for item in elements if isinstance(item, dict)]
    total_hours = sum(float(field(item, "people_hours", "peopleHours", default=0)) for item in records if isinstance(field(item, "people_hours", "peopleHours", default=None), (int, float)) and not isinstance(field(item, "people_hours", "peopleHours", default=None), bool))
    total_days = sum(float(field(field(item, "resources", default={}), "facilitator_days", "facilitatorDays", default=0)) for item in records if isinstance(field(field(item, "resources", default={}), "facilitator_days", "facilitatorDays", default=None), (int, float)) and not isinstance(field(field(item, "resources", default={}), "facilitator_days", "facilitatorDays", default=None), bool))
    summary_hours = field(summary, "total_people_hours", "people_hours", "peopleHours")
    summary_days = field(summary, "total_facilitator_days", "facilitator_days", "facilitatorDays")
    if not isinstance(summary_hours, (int, float)) or isinstance(summary_hours, bool) or abs(float(summary_hours) - total_hours) > 0.01:
        return False
    if not isinstance(summary_days, (int, float)) or isinstance(summary_days, bool) or abs(float(summary_days) - total_days) > 0.01:
        return False
    for key in RESOURCE_KEYS[1:]:
        if not nonempty(field(summary, key, "summary_" + key)):
            return False
    budget = field(summary, "planning_budget_categories", "budget_implications", "non_staff_budget_categories")
    return nonempty(budget)


def _audit_checks(audit: Any) -> list[dict[str, Any]]:
    if not isinstance(audit, dict):
        audit = {}
    assumption_audit = field(audit, "assumption_audit", "Assumption audit", default=None)
    comparison = field(audit, "scope_creep_comparison", "Scope-creep comparison", default=None)
    disposition = field(audit, "disposition", "Disposition", default=None)
    revision = field(audit, "final_revision_record", "Final revision record", default=None)
    defensible = field(audit, "why_this_is_defensible", "Why this is defensible", default=None)
    components_ok = all_nonempty((assumption_audit, comparison, disposition, revision, defensible))

    assumptions = as_list(assumption_audit)
    assumption_status_ok = True
    if assumptions:
        for item in assumptions:
            if not isinstance(item, dict):
                assumption_status_ok = False
                continue
            status = normalized(field(item, "status", "source_or_status", default=""))
            source = field(item, "source", "authority", "scenario_evidence", default="")
            consequence = field(item, "consequence_if_false", "consequence", default="")
            owner_check = field(item, "validation_owner_next_check", "validation_owner", "next_check", default="")
            if not all_nonempty((status, consequence, owner_check)):
                assumption_status_ok = False
            if "confirm" in status and not nonempty(source):
                assumption_status_ok = False
            if "confirm" not in status and "verify with the appropriate authority" not in status and not nonempty(source):
                assumption_status_ok = False
    elif nonempty(assumption_audit):
        norm = normalized(assumption_audit)
        assumption_status_ok = "confirm" not in norm or any(token in norm for token in ("source", "authority", "scenario", "verify with the appropriate authority"))
    else:
        assumption_status_ok = False

    changes = []
    if isinstance(comparison, dict):
        changes = as_list(field(comparison, "changes", default=[]))
    dispositions = as_list(disposition)
    allowed_dispositions = {"reject", "defer", "exchange", "accept with iron triangle consequence"}
    disposition_ok = nonempty(disposition)
    if changes:
        disposition_ok = all(normalized(field(item, "disposition", default="")) in allowed_dispositions for item in changes if isinstance(item, dict)) and all(isinstance(item, dict) for item in changes)
    elif dispositions:
        disposition_ok = all(normalized(field(item, "decision", "disposition", default="")) in allowed_dispositions for item in dispositions if isinstance(item, dict)) and all(isinstance(item, dict) for item in dispositions)
    comparison_norm = normalized(comparison)
    no_change = "no scope change detected" in comparison_norm
    if not changes and not no_change:
        disposition_ok = disposition_ok and any(token in normalized(disposition) for token in allowed_dispositions)

    reconciliation_ok = True
    for item in changes:
        if not isinstance(item, dict):
            reconciliation_ok = False
            continue
        item_disposition = normalized(field(item, "disposition", default=""))
        if item_disposition in {"exchange", "accept with iron triangle consequence"}:
            reconciliation_ok = reconciliation_ok and field(item, "gate5_reconciled", "gate_5_reconciled") is True and field(item, "wbs_reconciled") is True
        if item_disposition in {"reject", "defer"}:
            reconciliation_ok = reconciliation_ok and field(item, "kept_outside_wbs", "outside_current_wbs", default=True) is True
    if not changes and not no_change and any(token in normalized(disposition) for token in ("exchange", "accept with iron triangle consequence")):
        accepted_records = [item for item in dispositions if isinstance(item, dict) and normalized(field(item, "decision", "disposition", default="")) in {"exchange", "accept with iron triangle consequence"}]
        if accepted_records:
            reconciliation_ok = all(field(item, "gate_5_reconciled", "gate5_reconciled") is True and field(item, "wbs_reconciled") is True for item in accepted_records)
        else:
            reconciliation_ok = "gate 5" in comparison_norm and "wbs" in comparison_norm

    if isinstance(revision, dict):
        decision = field(revision, "changes", "decision", "revision", default="")
        reason = field(revision, "reason", "why", "justification", default="")
        origin = normalized(field(revision, "origin", default="student"))
        authored = field(revision, "student_authored", "studentAuthored", default=origin == "student") is True
        revision_reason_ok = nonempty(decision) and nonempty(reason) and authored and origin in {"student", "student originated", "student authored"}
    else:
        revision_norm = normalized(revision)
        revision_reason_ok = nonempty(revision) and len(revision_norm.split()) > 4 and any(token in revision_norm for token in ("because", "reason", "therefore", "so that"))

    return [
        check("G6B_COMPONENTS", components_ok, "All five internal final-audit components are present.", "One or more required final-audit components is missing."),
        check("G6B_ASSUMPTION_STATUS", assumption_status_ok, "Material assumptions include defensible source/status, consequence, and validation follow-up.", "At least one material assumption lacks a defensible status, consequence, or validation follow-up."),
        check("G6B_CHANGE_DISPOSITION", disposition_ok, "Every detected change has an allowed disposition, or the comparison justifies no change.", "A detected scope change lacks an allowed disposition or the no-change comparison is incomplete."),
        check("G6B_RECONCILIATION", reconciliation_ok, "Accepted/exchanged changes are reconciled and rejected/deferred work stays outside the WBS.", "A scope-change disposition is not reconciled with the existing Gate 5 work and WBS."),
        check("G6B_STUDENT_REVISION_REASON", revision_reason_ok, "The student-authored final revision/no-change record includes a reason.", "The final revision/no-change record lacks a student-authored decision and reason."),
    ]


def gate6(submission: dict[str, Any], prior: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    wbs = field(submission, "wbs", default={})
    elements = as_list(field(wbs, "elements", default=[]))
    packages = _work_packages(elements)
    gate5_prior = field(prior, "gate_5", "gate5", default={})
    prior_deliverables = as_list(field(gate5_prior, "deliverables", default=[]))
    deliverable_ids = {str(field(item, "id", default="")).strip() for item in prior_deliverables if isinstance(item, dict) and nonempty(field(item, "id", default=""))}
    linked_ids = {str(field(item, "deliverable_id", "deliverableId", default="")).strip() for item in elements if isinstance(item, dict)}
    trace_ok = bool(deliverable_ids) and deliverable_ids.issubset(linked_ids)
    outside_words = r"renovat|construction|capital campaign|staff restructuring|layoff|ticketing merge|lease renegoti|season selection|choose .*shows"
    boundary_ok = bool(packages) and all(field(item, "outside_scope", "outsideScope", default=False) is not True and not re.search(outside_words, normalized(field(item, "name", "output", default=""))) for item in packages)
    preplanning = any(_contains_any(field(item, "name", "branch", default=""), (r"pre[ -]?planning", r"big 5", r"research", r"requirements", r"expectation")) for item in elements if isinstance(item, dict))
    owner_ok = bool(packages) and all(normalized(field(item, "owner", default="")) in ALLOWED_OWNERS and not isinstance(field(item, "owner", default=""), list) for item in packages)
    hierarchy = _hierarchy_ok(elements, deliverable_ids)
    time_hours = bool(packages) and all(str(field(item, "time_window", "timeWindow", default="")).upper() in {"PRE_VOTE", "POST_VOTE"} and isinstance(field(item, "people_hours", "peopleHours", default=None), (int, float)) and not isinstance(field(item, "people_hours", "peopleHours", default=None), bool) and float(field(item, "people_hours", "peopleHours")) > 0 for item in packages)
    vector_ok = bool(packages)
    for item in packages:
        resources = field(item, "resources", default={})
        if not isinstance(resources, dict):
            vector_ok = False
            continue
        for key in RESOURCE_KEYS:
            value = field(resources, key, "facilitatorDays" if key == "facilitator_days" else key)
            if key not in resources and not (key == "facilitator_days" and "facilitatorDays" in resources):
                vector_ok = False
            elif not _resource_value_ok(key, value):
                vector_ok = False
    summary_ok = _summary_ok(field(wbs, "resource_summary", "resourceSummary", default={}), elements)
    prevote = sum(float(field(item, "people_hours", "peopleHours", default=0)) for item in elements if isinstance(item, dict) and str(field(item, "time_window", "timeWindow", default="")).upper() == "PRE_VOTE" and isinstance(field(item, "people_hours", "peopleHours", default=None), (int, float)) and not isinstance(field(item, "people_hours", "peopleHours", default=None), bool))
    checks = [
        check("G6_DELIVERABLE_TRACEABILITY", trace_ok, "Every approved Gate 5 deliverable is represented in the WBS.", "One or more approved Gate 5 deliverables is absent from the WBS."),
        check("G6_SCOPE_BOUNDARY", boundary_ok, "Work packages stay inside the approved scope.", "At least one work package produces work outside the approved scope."),
        check("G6_PREPLANNING_WORK", preplanning, "The WBS contains explicit pre-planning work.", "The WBS lacks an explicit pre-planning work item."),
        check("G6_SINGLE_OWNER", owner_ok, "Every work package has exactly one allowed named owner.", "At least one work package lacks exactly one allowed named owner."),
        check("G6_HIERARCHY_AND_LINK", hierarchy, "WBS IDs, parent-child relationships, and deliverable/management links are valid.", "The WBS contains an invalid/duplicate ID, parent relationship, or deliverable/management link."),
        check("G6_TIME_AND_HOURS", time_hours, "Every work package has an allowed time window and positive people-hours.", "At least one work package lacks an allowed time window or positive numeric people-hours."),
        check("G6_RESOURCE_VECTOR", vector_ok, "Every work package has a complete, well-formed resource vector.", "At least one work package has a missing, blank, placeholder, or invalid resource-vector value."),
        check("G6_RESOURCE_SUMMARY", summary_ok, "The project resource summary reconciles hours/days and covers all categories.", "The project resource summary is missing, incomplete, or does not reconcile with the work packages."),
        check("G6_PREVOTE_EFFORT", prevote <= 525, "Pre-vote planning-team effort stays within the frozen ceiling.", "Pre-vote planning-team effort exceeds the available ceiling."),
    ]
    audit = field(submission, "final_audit", "gate_6b", "gate6b", default={})
    checks.extend(_audit_checks(audit))
    criteria = ["Non-blocking: review the 100% rule, work-package specificity/depth, mundane work, dependencies, package size, and resource plausibility."]
    return checks, criteria, []


GATE_VALIDATORS: dict[int, Callable[[dict[str, Any], dict[str, Any]], tuple[list[dict[str, Any]], list[str], list[str]]]] = {
    1: gate1,
    2: gate2,
    3: gate3,
    4: gate4,
    5: gate5,
    6: gate6,
}


def retry_checks(envelope: dict[str, Any], submission: dict[str, Any]) -> list[dict[str, Any]]:
    prior_closed = field(envelope, "prior_attempt_closed", "priorAttemptClosed", default=False)
    if prior_closed is not True:
        return []
    retry = field(
        envelope,
        "retry_envelope",
        "retryEnvelope",
        default=field(submission, "retry_envelope", "retryEnvelope", default={}),
    )
    if not isinstance(retry, dict):
        retry = {}
    messages = field(envelope, "post_closure_messages", "postClosureMessages", "retry_messages", "retryMessages", default=[])
    if isinstance(messages, str):
        messages = [messages]
    if not isinstance(messages, list):
        raise InputError("post_closure_messages must be text or an array of text")
    natural = " ".join(str(item) for item in messages if isinstance(item, str)).strip()
    natural_norm = normalized(natural)
    revision_present = nonempty(field(retry, "revision", "Revision")) or (
        len(natural_norm.split()) >= 5
        and bool(re.search(r"\b(?:revis|chang|add|remove|correct|expand|replace|rewrit)\w*\b", natural_norm))
    )
    rationale_present = nonempty(
        field(retry, "why_this_improves_the_project", "why_this_improves_project", "Why this improves the project")
    ) or (
        len(natural_norm.split()) >= 7
        and bool(re.search(r"\b(?:because|so that|therefore|which makes|this helps|in order to|to keep|to align)\b", natural_norm))
    )
    return [
        check("POST_CLOSURE_REVISION", revision_present, "The student's revised section is present.", "The student has not yet supplied a recognizable correction or expansion to the failed section."),
        check("POST_CLOSURE_IMPROVEMENT_REASON", rationale_present, "The student explains why the revision improves the project.", "The student has not yet explained why the change makes the plan stronger."),
    ]


def _student_label(item: dict[str, Any]) -> str:
    return STUDENT_CHECK_LABELS.get(item["code"], item.get("label", "Required section"))


def _next_formal_move(gate_number: int, failed: list[dict[str, Any]], status: str) -> str:
    if not failed:
        return (
            "Carry the preserved answer into the next gate when you are ready."
            if gate_number < 6
            else "Use the course submission process when the authorized report becomes available."
        )
    first = failed[0]["code"]
    questions = {
        "G1_BIG5_COMPLETE": "Which unanswered Big 5 question will you complete first?",
        "G1_HISTORY_EVIDENCE": "Which event from the Planning history section will you use, and what could it suggest might happen again?",
        "G1_AUTHORITY_BOUNDARY": "Which decisions can Marcus control, and which decision remains with the board?",
        "G1_INTERNAL_STUDY": "Look in the Building section: what existing study could inform the planning process?",
        "G1_COMPARISON_EXAMPLE": "Use the provided comparison example. What is one practice Meridian could learn from it?",
        "G1_COMPARISON_LESSON": "What is one practice Meridian could learn from the comparison example, and why might it help?",
        "G2_COMMUNITY_ACCESS_GAP": "You have the annual obligation. What is Meridian documenting now?",
        "POST_CLOSURE_REVISION": "Revise only the failed section in your own words; the rest is preserved.",
        "POST_CLOSURE_IMPROVEMENT_REASON": "Why does this change make the plan stronger?",
    }
    return questions.get(first, "Revise only the first unfinished section in your own words; the rest is preserved.")


def _formal_student_response(
    gate_number: int,
    hard_checks: list[dict[str, Any]],
    criteria: list[str],
    cross: list[str],
    status: str,
) -> dict[str, Any]:
    passed = [item for item in hard_checks if item["result"] == "PASS"]
    failed = [item for item in hard_checks if item["result"] == "FAIL"]
    working_sections: list[str] = []
    for item in passed:
        label = _student_label(item)
        if label not in working_sections:
            working_sections.append(label)
    attention = [
        {"section": _student_label(item), "what_is_missing": item["message"]}
        for item in failed
    ]
    response: dict[str, Any] = {
        "Gate": f"{gate_number} — {GATE_NAMES[gate_number]}",
        "Progress": (
            f"{len(passed)} of {len(hard_checks)} applicable required items are working. "
            + ("Preserved sections: " + "; ".join(working_sections) + "." if working_sections else "The submitted work is preserved.")
        ),
        "What still needs attention": attention if attention else "Nothing blocking.",
        "Ready to move on": (
            "YES — Gate OPEN"
            if status == "OPEN"
            else f"NOT YET — Gate CLOSED — {len(failed)} specific item{'s' if len(failed) != 1 else ''} remain."
        ),
        "Optional advice": {
            "notice": "This advice does not block you.",
            "items": criteria[:1] if status == "CLOSED" else criteria,
        },
    }
    if gate_number >= 2:
        response["Connection to your earlier work"] = cross or ["Your answers connect"]
    response["Your next move"] = _next_formal_move(gate_number, failed, status)
    return response


def pending_reflection_result(
    gate_number: int,
    hard_checks: list[dict[str, Any]],
    submission: dict[str, Any],
) -> dict[str, Any]:
    return {
        "interaction_state": "PENDING_REFLECTION",
        "gate": {"number": gate_number, "name": GATE_NAMES[gate_number]},
        "private_hard_checks": hard_checks,
        "failed_checks": [
            {"code": "POST_CLOSURE_IMPROVEMENT_REASON", "message": "The improvement reason is still needed."}
        ],
        "attempt_recorded": False,
        "assembled_submission": submission,
        "student_response": {
            "acknowledgment": "Your revised section now meets the gate-specific checks, and the rest of the answer remains preserved.",
            "progress": "Only one reflection idea is still needed before this review can be completed.",
            "next": "Why does this change make the plan stronger?",
        },
    }


def validate(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise InputError("input root must be an object")
    deployment_error = validate_deployment_context(envelope)
    if deployment_error is not None:
        return deployment_error
    gate_raw = field(envelope, "gate_number", "gateNumber", "gate")
    if isinstance(gate_raw, str) and gate_raw.isdigit():
        gate_raw = int(gate_raw)
    if gate_raw not in GATE_NAMES:
        raise InputError("gate_number must be an integer from 1 through 6")
    attempt = field(envelope, "gate_attempt", "gateAttempt", "attemptNumber", default=1)
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        raise InputError("gate_attempt must be an integer of at least 1")
    submission = assembled_submission(envelope)
    prior = field(envelope, "prior_gate_artifacts", "priorGateArtifacts", default={})
    if not isinstance(prior, dict):
        raise InputError("prior_gate_artifacts must be an object when supplied")

    latest_message = str(field(envelope, "latest_message", "latestMessage", default=""))
    if DISTRESS_RE.search(latest_message):
        return interrupted_result("DISTRESS_PAUSE", gate_raw, submission)
    if field(envelope, "product_error", "productError", default=False) is True:
        return interrupted_result("PRODUCT_RECOVERY", gate_raw, submission)
    if field(envelope, "source_recheck_requested", "sourceRecheckRequested", default=False) is True or SOURCE_CHALLENGE_RE.search(latest_message):
        return source_recheck_result(gate_raw, submission, envelope)
    uploaded_content = text(field(envelope, "uploaded_content", "uploadedContent", default=""))
    if INJECTION_RE.search(latest_message) or INJECTION_RE.search(uploaded_content):
        return integrity_result(gate_raw, submission)
    numeric_check = field(envelope, "numeric_check", "numericCheck", default=None)
    if numeric_check is not None:
        result = evaluate_numeric_item(numeric_check)
        result["assembled_submission"] = submission
        return result

    cards: list[dict[str, Any]] = []
    if gate_raw == 1:
        try:
            cards = load_precedent_cards()
        except InstructorMaterialError as exc:
            return {
                "interaction_state": "INSTRUCTOR_MATERIAL_NEEDED",
                "build_configuration_error": True,
                "attempt_recorded": False,
                "assembled_submission": submission,
                "errors": [{"code": "INSTRUCTOR_MATERIAL_NEEDED", "message": str(exc)}],
                "student_response": {
                    "acknowledgment": "Your completed work is saved.",
                    "progress": "The required comparison example is unavailable, so this part cannot continue yet.",
                    "next": "Please use this handoff note to ask the instructor to restore the one approved Gate 1 comparison example.",
                },
            }

    ladder = help_ladder_result(gate_raw, submission, envelope)
    if ladder is not None:
        return ladder

    ready_value = field(envelope, "ready_signal", "readySignal", default=latest_message)
    if not ready_signal_present(ready_value):
        return drafting_result(gate_raw, submission, envelope, cards)

    meaningful = meaningful_student_content(submission)
    if not meaningful:
        return {
            "interaction_state": "FORMAL_NO_ATTEMPT",
            "gate": {"number": gate_raw, "name": GATE_NAMES[gate_raw]},
            "hard_checks": [],
            "status": "INCOMPLETE",
            "criteria_feedback": ["Non-blocking: no gate evaluation ran because the student has not submitted meaningful work."],
            "cross_gate_consistency": [],
            "next_move": "Use the blank gate structure to make your own first attempt; start by answering one field in your own words.",
            "failed_checks": [],
            "gate_attempt": attempt,
            "attempt_recorded": False,
            "milestone_outcome": "INCOMPLETE",
            "retry_required_next": False,
            "assembled_submission": submission,
            "student_response": {
                "Gate": f"{gate_raw} — {GATE_NAMES[gate_raw]}",
                "Progress": "No meaningful student-authored section was present for formal review.",
                "What still needs attention": ["A first student-authored attempt."],
                "Ready to move on": "NOT YET — no Gate result was recorded because there is not enough student work to evaluate.",
                "Your next move": "Start with one field in the blank structure and answer it in your own words.",
            },
        }

    try:
        gate_specific_checks, criteria, cross = GATE_VALIDATORS[gate_raw](submission, prior)
    except InstructorMaterialError as exc:
        return {
            "interaction_state": "INSTRUCTOR_MATERIAL_NEEDED",
            "build_configuration_error": True,
            "attempt_recorded": False,
            "assembled_submission": submission,
            "errors": [{"code": "INSTRUCTOR_MATERIAL_NEEDED", "message": str(exc)}],
            "student_response": {
                "acknowledgment": "Your completed work is saved.",
                "progress": "The required comparison example is unavailable, so this review cannot continue.",
                "next": "Please ask the instructor to restore the approved Gate 1 comparison example.",
            },
        }
    retry = retry_checks(envelope, submission)
    hard_checks = gate_specific_checks + retry
    gate_specific_failed = [item for item in gate_specific_checks if item["result"] == "FAIL"]
    retry_failed = [item for item in retry if item["result"] == "FAIL"]
    if (
        not gate_specific_failed
        and len(retry_failed) == 1
        and retry_failed[0]["code"] == "POST_CLOSURE_IMPROVEMENT_REASON"
    ):
        return pending_reflection_result(gate_raw, hard_checks, submission)
    failed = [
        {"code": item["code"], "message": item["message"]}
        for item in hard_checks
        if item["result"] == "FAIL"
    ]
    status = "CLOSED" if failed else "OPEN"
    if not criteria:
        criteria = ["Non-blocking: no additional criteria coaching is required for this attempt."]
    if status == "CLOSED":
        next_move = "Review the required item(s) that need attention and revise only your own answer."
    else:
        next_move = "Carry your approved work forward and submit your own attempt at the next gate." if gate_raw < 6 else "Submit the issued Stage 1 report through the course process when the backend makes it available."
    student_response = _formal_student_response(gate_raw, hard_checks, criteria, cross, status)
    if gate_raw == 1 and status == "CLOSED" and any(
        item["code"] in {"G1_COMPARISON_EXAMPLE", "G1_COMPARISON_LESSON"}
        for item in hard_checks
        if item["result"] == "FAIL"
    ):
        _, remaining = gate1_components(submission, cards)
        if "comparison example" in remaining:
            student_response["Comparison example for the next step"] = student_comparison_example_view(cards[0])
    return {
        "interaction_state": "FORMAL_RESULT",
        "gate": {"number": gate_raw, "name": GATE_NAMES[gate_raw]},
        "gate_number": gate_raw,
        "hard_checks": hard_checks,
        "private_hard_checks": hard_checks,
        "status": status,
        "criteria_feedback": criteria,
        "cross_gate_consistency": cross,
        "next_move": next_move,
        "failed_checks": failed,
        "gate_attempt": attempt,
        "attempt_recorded": True,
        "milestone_outcome": "PASS" if status == "OPEN" else "REVISE",
        "retry_required_next": status == "CLOSED",
        "assembled_submission": submission,
        "student_response": student_response,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        envelope = json.loads(args.input.read_text(encoding="utf-8"))
        result = validate(envelope)
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(json.dumps({"valid": False, "status": "MALFORMED", "errors": [{"code": "INPUT", "message": str(exc)}]}, indent=2 if args.pretty else None, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    if result.get("build_configuration_error"):
        return 2
    return 0 if result.get("status") == "OPEN" else 1


if __name__ == "__main__":
    sys.exit(main())
