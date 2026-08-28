"""Shared fixtures and subprocess helpers for the frozen V550 acceptance suite."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


TESTS = Path(__file__).resolve().parent
RUNTIME = TESTS.parent
REPO = RUNTIME.parent
SKILL = REPO / "skills" / "v550-scope-advisor"
SCRIPTS = SKILL / "scripts"

GATE_VALIDATOR = SCRIPTS / "validate_frozen_gate_submission.py"
TELEMETRY_VALIDATOR = SCRIPTS / "validate_telemetry_payload.py"
CANONICAL_VERIFIER = SCRIPTS / "verify_canonical_knowledge.py"
REPORT_VALIDATOR = SCRIPTS / "validate_report_integrity.py"
FROZEN_GATES = SKILL / "references" / "frozen-six-gates.md"
PRECEDENT_CARDS = SKILL / "references" / "gate-1-precedent-cards.md"

RESOURCE_VECTOR = {
    "facilitator_days": 0,
    "software_tools": "NONE",
    "equipment": "NONE",
    "materials": "NONE",
    "contractors": "NONE",
    "outside_participants": "NONE",
}


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def canonical_exclusions() -> list[dict[str, str]]:
    """Load exclusions from the single machine registry in frozen-six-gates.md."""

    if not FROZEN_GATES.is_file():
        raise AssertionError(f"Missing frozen gate contract: {FROZEN_GATES}")
    text = FROZEN_GATES.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError("Frozen gate contract must contain exactly one JSON registry")
    try:
        registry = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        raise AssertionError("Frozen gate registry must be valid JSON") from exc
    rows = registry.get("canonical_exclusions")
    if not isinstance(rows, list):
        raise AssertionError("Frozen gate registry must declare canonical_exclusions")
    if len(rows) != 5 or len({row["id"] for row in rows}) != 5:
        raise AssertionError("Canonical scenario must declare five distinct exclusion IDs")
    return rows


def load_module(name: str, path: Path) -> Any:
    if not path.is_file():
        raise AssertionError(f"Required implementation is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise AssertionError(f"Could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_json_cli(
    script: Path,
    payload: dict[str, Any] | None = None,
    *,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a JSON-file CLI without writing inside the repository."""

    if not script.is_file():
        raise AssertionError(f"Required CLI is missing: {script}")
    command = [sys.executable, str(script)]
    merged_env = os.environ.copy()
    merged_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged_env.update(env)

    if payload is None:
        command.extend(args or [])
        return subprocess.run(command, capture_output=True, text=True, env=merged_env)

    with tempfile.TemporaryDirectory() as directory:
        input_path = Path(directory) / "input.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        command.append(str(input_path))
        command.extend(args or [])
        return subprocess.run(command, capture_output=True, text=True, env=merged_env)


def parse_json_stdout(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI did not return JSON. exit={process.returncode}\n"
            f"stdout={process.stdout!r}\nstderr={process.stderr!r}"
        ) from exc
    if not isinstance(value, dict):
        raise AssertionError(f"CLI JSON root must be an object, got {type(value).__name__}")
    return value


def failure_codes(result: dict[str, Any]) -> set[str]:
    failures = result.get("failed_checks", [])
    if not isinstance(failures, list):
        raise AssertionError("failed_checks must be a list")
    codes: set[str] = set()
    for failure in failures:
        if isinstance(failure, str):
            codes.add(failure)
        elif isinstance(failure, dict) and isinstance(failure.get("code"), str):
            codes.add(failure["code"])
        else:
            raise AssertionError(f"Invalid failed check: {failure!r}")
    return codes


def valid_gate_1() -> dict[str, Any]:
    return {
        "big5": {
            "q1_history": (
                "The binder left facilities unresolved, and the abandoned donor-database "
                "merge left no written explanation, so this process needs an execution record."
            ),
            "q2_role": (
                "Marcus leads the planning process; the role was not defined in writing or "
                "announced to staff."
            ),
            "q3_authority": (
                "Marcus controls the meeting schedule, consultation, recommendation format, "
                "and $35,000 planning budget. The board controls the final allocation; Marcus "
                "does not control legacy-lead participation, the season calendar, or the lease."
            ),
            "q4_patron": (
                "Ruth Adeyemi is my patron because her 2016 lease experience can provide early "
                "warning and help protect the process when allocation conflicts surface."
            ),
            "q5_plan_type": (
                "I will treat this as a standing allocation policy because Meridian needs a "
                "repeatable basis for resolving collisions after the first decision."
            ),
        },
        "research_and_development": {
            "internal_study": (
                "Read the unread 2019 space-utilization study in the admin-suite filing cabinet."
            ),
            "outside_precedents": [
                {
                    "card_id": "CARD-01_SMART_TRANSIT_SCOPE",
                    "adaptation": (
                        "I would examine where the broad service promise hides access rules, "
                        "then adapt a clearer decision record for Meridian’s shared rooms."
                    ),
                },
            ],
        },
    }


def requirement(
    identifier: str,
    statement: str,
    source: str,
    requirement_type: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "statement": statement,
        "source_authority": source,
        "type": requirement_type,
        "verification_method": "Compare the submitted allocation record with the named source.",
        "status": "CONFIRMED",
    }


def valid_gate_2() -> dict[str, Any]:
    return {
        "requirements": [
            requirement(
                "REQ-01",
                "The City lease requires 900 annual below-market community-access hours; "
                "Meridian currently documents 515, a shortfall of 385 hours.",
                "Course scenario: City lease and current documented-hours record",
                "contractual",
            ),
            requirement(
                "REQ-02",
                "The dance school keeps Studios C and D Tuesday and Thursday, 4–8 p.m., through August 2028.",
                "Course scenario: dance-school agreement",
                "contractual",
            ),
            requirement(
                "REQ-03",
                "The Main Gallery calendar already contracted fourteen months ahead must be honored.",
                "Course scenario: contracted Main Gallery calendar",
                "contractual",
            ),
            requirement(
                "REQ-04",
                "The process must satisfy fire-code occupancy and ADA access within the no-capital boundary.",
                "Course scenario: supplied fire-code and accessibility constraints",
                "accessibility/safety",
            ),
        ]
    }


def valid_gate_3() -> dict[str, Any]:
    wont = [
        {"id": row["id"], "text": row["meaning"], "source_tag": "requirement"}
        for row in canonical_exclusions()
    ]
    return {
        "moscow": {
            "must": [
                {
                    "id": "MOS-01",
                    "text": "Preserve the 900-hour community-access obligation.",
                    "source_tag": "requirement",
                }
            ],
            "should": [
                {
                    "id": "MOS-02",
                    "text": "Give Learning & Media a predictable weekly booking pattern.",
                    "source_tag": "expectation",
                }
            ],
            "could": [
                {
                    "id": "MOS-03",
                    "text": "Pilot room-scheduling software during consultation.",
                    "source_tag": "preference",
                }
            ],
            "wont": wont,
        },
        "conflicts": [
            {
                "program_areas": ["New Play Development", "Mainstage"],
                "resource": "Firebay",
                "description": (
                    "New Play Development wants year-round workshop access while Mainstage "
                    "wants the Firebay for rehearsal during tech weeks."
                ),
            }
        ],
    }


def valid_gate_4() -> dict[str, Any]:
    return {
        "goal": "Create a defensible Waldron allocation framework that Meridian can implement.",
        "objectives": [
            {
                "id": "OBJ-01",
                "statement": "By March 19, deliver 1 progress packet to the Board Facilities Committee.",
                "completion_date": "2027-03-19",
                "success_criterion": "Committee receipt is recorded; quality review remains advisory.",
            },
            {
                "id": "OBJ-02",
                "statement": "By May 14, present 1 final allocation recommendation for the board vote.",
                "completion_date": "2027-05-14",
                "success_criterion": "The recommendation is on the board agenda.",
            },
            {
                "id": "OBJ-03",
                "statement": "By May 20, issue 1 post-vote handoff record to programming.",
                "completion_date": "2027-05-20",
                "success_criterion": "Programming acknowledges the handoff.",
            },
        ],
    }


def valid_gate_5() -> dict[str, Any]:
    return {
        "project_statement": {
            "trigger": "Unresolved Waldron space allocation now blocks 2027–28 season planning.",
            "action": "Lead consultation and produce a documented allocation recommendation.",
            "frequency_and_timing": "Kick off January 12, update March 19, vote May 14, hand off before June 1.",
            "scope": "Allocate existing Waldron rooms among Meridian programs within current agreements.",
            "constraints_and_uncertainty": (
                "Work within $35,000, 0.75 FTE, no capital funds, fixed agreements, and uncertainty "
                "about City auditing and legacy-lead participation."
            ),
        },
        "exclusions": canonical_exclusions(),
        "constraints": [
            "The board votes May 14.",
            "The planning budget is $35,000 and excludes staff time.",
        ],
        "assumptions": [
            {
                "statement": "The City will continue its present community-access audit practice.",
                "status": "VERIFY WITH THE APPROPRIATE AUTHORITY",
            }
        ],
        "deliverables": [
            {
                "id": "DEL-01",
                "output": "Board Facilities Committee progress packet",
                "approver": "Ruth Adeyemi",
                "due_date": "2027-03-19",
            },
            {
                "id": "DEL-02",
                "output": "Final allocation recommendation and programming handoff record",
                "approver": "Full board",
                "due_date": "2027-05-20",
            },
        ],
        "scope_action_plan": [
            {"id": "ACT-01", "action": "Undertake review of the 2019 utilization study."},
            {"id": "ACT-02", "action": "Convene program-area consultation sessions."},
            {"id": "ACT-03", "action": "Produce the progress packet and final recommendation."},
            {"id": "ACT-04", "action": "Document the post-vote programming handoff."},
        ],
    }


def wbs_element(
    identifier: str,
    parent_id: str | None,
    name: str,
    element_type: str,
    owner: str,
    deliverable_id: str | None,
    branch: str | None,
    time_window: str,
    people_hours: float,
    *,
    facilitator_days: float = 0,
) -> dict[str, Any]:
    resources = deep_copy(RESOURCE_VECTOR)
    resources["facilitator_days"] = facilitator_days
    return {
        "id": identifier,
        "parent_id": parent_id,
        "name": name,
        "type": element_type,
        "owner": owner,
        "deliverable_id": deliverable_id,
        "branch": branch,
        "time_window": time_window,
        "people_hours": people_hours,
        "resources": resources,
    }


def valid_gate_6() -> dict[str, Any]:
    elements = [
        wbs_element(
            "1",
            None,
            "Pre-planning and requirements",
            "branch",
            "Marcus",
            None,
            "PRE_PLANNING",
            "PRE_VOTE",
            1,
        ),
        wbs_element(
            "1.1",
            "1",
            "Review planning history and the 2019 study",
            "work_package",
            "Marcus",
            None,
            "PRE_PLANNING",
            "PRE_VOTE",
            60,
        ),
        wbs_element(
            "2",
            None,
            "Progress packet",
            "deliverable",
            "Priya",
            "DEL-01",
            None,
            "PRE_VOTE",
            1,
        ),
        wbs_element(
            "2.1",
            "2",
            "Compile consultation and room-use findings",
            "work_package",
            "Priya",
            "DEL-01",
            None,
            "PRE_VOTE",
            120,
            facilitator_days=2,
        ),
        wbs_element(
            "3",
            None,
            "Final recommendation and handoff",
            "deliverable",
            "Tomas",
            "DEL-02",
            None,
            "PRE_VOTE",
            1,
        ),
        wbs_element(
            "3.1",
            "3",
            "Prepare final allocation recommendation",
            "work_package",
            "Tomas",
            "DEL-02",
            None,
            "PRE_VOTE",
            160,
        ),
        wbs_element(
            "3.2",
            "3",
            "Document post-vote programming handoff",
            "work_package",
            "Marcus",
            "DEL-02",
            None,
            "POST_VOTE",
            40,
        ),
    ]
    return {
        "wbs": {
            "elements": elements,
            "resource_summary": {
                "total_people_hours": 383,
                "pre_vote_people_hours": 343,
                "post_vote_people_hours": 40,
                "total_facilitator_days": 2,
                "software_tools": ["NONE"],
                "equipment": ["NONE"],
                "materials": ["NONE"],
                "contractors": ["NONE"],
                "outside_participants": ["NONE"],
                "planning_budget_categories": ["facilitator_days"],
                "staff_time_priced_in_dollars": False,
            },
        },
        "final_audit": {
            "assumption_audit": [
                {
                    "assumption": "The City will continue its current access-audit practice.",
                    "source_or_status": "VERIFY WITH THE APPROPRIATE AUTHORITY",
                    "consequence_if_false": "The allocation criteria may not satisfy the lease audit.",
                    "validation_owner": "Marcus",
                    "next_check": "Ask Gwen Tsai before the March 19 update.",
                }
            ],
            "scope_creep_comparison": [
                {
                    "change_id": "CH-01",
                    "change": "A renovation option appeared during decomposition.",
                    "comparison": "It is outside EX-01_CAPITAL_WORK and absent from Gate 5 scope.",
                }
            ],
            "disposition": [
                {
                    "change_id": "CH-01",
                    "decision": "REJECT",
                    "reason": "Capital work is outside the approved Stage 1 boundary.",
                }
            ],
            "final_revision_record": (
                "NO CHANGE: I removed no approved work because the rejected renovation never entered "
                "the WBS; Gate 5 and the WBS remain aligned."
            ),
            "why_this_is_defensible": (
                "The decision preserves the requirements and objectives while respecting the no-capital "
                "constraint and the team’s 525-hour pre-vote capacity."
            ),
        },
    }


def gate_envelope(gate_number: int) -> dict[str, Any]:
    builders = {
        1: valid_gate_1,
        2: valid_gate_2,
        3: valid_gate_3,
        4: valid_gate_4,
        5: valid_gate_5,
        6: valid_gate_6,
    }
    envelope: dict[str, Any] = {
        "scenario_id": "allocating_the_waldron",
        "gate_number": gate_number,
        "gate_attempt": 1,
        "ready_signal": f"Evaluate Gate {gate_number}",
        "submission": builders[gate_number](),
        "prior_attempt_closed": False,
    }
    if gate_number == 6:
        envelope["prior_gate_artifacts"] = {"gate_5": valid_gate_5()}
    return envelope


def retry_envelope(gate_number: int = 2) -> dict[str, Any]:
    envelope = gate_envelope(gate_number)
    envelope["gate_attempt"] = 2
    envelope["prior_attempt_closed"] = True
    envelope["retry_envelope"] = {
        "revision": "I added the missing constraint and its verification fields.",
        "why_this_improves_project": (
            "The revision makes the requirement traceable to the scenario and testable at review."
        ),
    }
    return envelope


def valid_start_session() -> dict[str, Any]:
    return {
        "operation": "startSession",
        "classToken": "synthetic-class-token-32-characters",
        "studentKey": "V550-TEST-K7M4Q2",
        "requestId": "req_start_0001",
        "schemaVersion": "2.0.0",
        "consent": {
            "asserted": True,
            "version": "v550-consent-v1",
            "clientObservedAt": "2026-08-07T14:00:00-04:00",
        },
    }


def valid_log_event() -> dict[str, Any]:
    return {
        "operation": "logEvent",
        "classToken": "synthetic-class-token-32-characters",
        "studentKey": "V550-TEST-K7M4Q2",
        "requestId": "req_event_0001",
        "schemaVersion": "2.0.0",
        "sessionId": "ses_server_0001",
        "eventId": "evt_gate_0001",
        "eventType": "gate_attempt",
        "stage": "stage_1_scope",
        "role": "scope_review_board",
        "reasonCodes": ["GATE_1_ATTEMPT_RECORDED"],
    }
