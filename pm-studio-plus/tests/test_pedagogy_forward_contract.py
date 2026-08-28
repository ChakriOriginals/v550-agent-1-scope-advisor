"""Deterministic policy and forward-case coverage for student-first behavior."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from support import (
    GATE_VALIDATOR,
    RUNTIME,
    SKILL,
    canonical_exclusions,
    failure_codes,
    gate_envelope,
    load_module,
)


FORWARD_CASES = RUNTIME / "tests" / "fixtures" / "forward-cases.json"
ORCHESTRATOR = RUNTIME / "gpt" / "orchestrator-instructions.md"
REVIEW_BOARD = RUNTIME / "gpt" / "review-board.md"
FROZEN_SCENARIO = SKILL / "references" / "frozen-waldron-scenario.md"
FROZEN_GATES = SKILL / "references" / "frozen-six-gates.md"
PRIVACY = SKILL / "references" / "privacy-telemetry-and-reports.md"
PEDAGOGY = SKILL / "references" / "pedagogy-and-session-flow.md"


class PedagogyAndForwardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [
            SKILL / "SKILL.md",
            SKILL / "agents" / "openai.yaml",
            ORCHESTRATOR,
            REVIEW_BOARD,
            FROZEN_SCENARIO,
            FROZEN_GATES,
            PRIVACY,
            PEDAGOGY,
            FORWARD_CASES,
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise AssertionError(f"Required forward-test sources are missing: {missing}")
        cls.skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cls.metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        cls.orchestrator = ORCHESTRATOR.read_text(encoding="utf-8")
        cls.review = REVIEW_BOARD.read_text(encoding="utf-8")
        cls.scenario = FROZEN_SCENARIO.read_text(encoding="utf-8")
        cls.gates = FROZEN_GATES.read_text(encoding="utf-8")
        cls.privacy = PRIVACY.read_text(encoding="utf-8")
        cls.pedagogy = PEDAGOGY.read_text(encoding="utf-8")
        cls.corpus = "\n".join(
            [
                cls.skill,
                cls.orchestrator,
                cls.review,
                cls.gates,
                cls.privacy,
                cls.pedagogy,
            ]
        )
        cls.forward = json.loads(FORWARD_CASES.read_text(encoding="utf-8"))

    def assert_has_any(self, text: str, alternatives: tuple[str, ...]) -> None:
        lowered = text.lower()
        self.assertTrue(
            any(alternative.lower() in lowered for alternative in alternatives),
            f"Expected one of {alternatives!r}",
        )

    def test_skill_metadata_matches_required_interface(self) -> None:
        self.assertIn('display_name: "v550 Scope Advisor"', self.metadata)
        self.assertIn(
            'short_description: "Build and run the frozen six-gate v550 Scope Advisor."',
            self.metadata,
        )
        self.assertIn(
            'default_prompt: "Use $v550-scope-advisor as a patient learning partner: '
            'coach the student through the six-gate sequence, evaluate only when the student says they are ready, '
            'enforce the frozen hard checks, preserve completed work, give one manageable next step, and never '
            'supply the student’s graded judgment or assignment-ready answer."',
            self.metadata,
        )
        frontmatter = self.skill.split("---", 2)[1].lower()
        for trigger in (
            "build",
            "configure",
            "test",
            "update",
            "run",
            "waldron",
            "validate",
            "evaluate",
            "report",
        ):
            self.assertIn(trigger, frontmatter)

    def test_frozen_sequence_contains_exactly_six_numbered_gates(self) -> None:
        block = re.findall(r"```json\s*(\{.*?\})\s*```", self.gates, re.DOTALL)
        self.assertEqual(len(block), 1)
        machine = json.loads(block[0])
        self.assertEqual(
            machine["gate_names"],
            [
                {"number": 1, "name": "Big 5 Pre-Planning"},
                {"number": 2, "name": "Requirements"},
                {"number": 3, "name": "Expectations"},
                {"number": 4, "name": "Goals & Objectives"},
                {"number": 5, "name": "Scope of Work"},
                {"number": 6, "name": "Work Breakdown Structure"},
            ],
        )
        self.assertEqual(machine["gate_count"], 6)
        self.assertFalse(machine["gate_6_internal_phase"]["is_numbered_gate"])
        numbered = re.findall(r"(?m)^#{2,4}\s+Gate\s+([0-9]+)\b", self.gates)
        self.assertEqual(numbered, ["1", "2", "3", "4", "5", "6"])
        self.assertNotRegex(self.gates, r"(?im)^#{1,6}\s+Gate\s+7\b")
        self.assertIn("Gate 6B", self.gates)
        self.assertRegex(self.gates.lower(), r"internal.*gate 6|part of gate 6")

    def test_frozen_scenario_uses_relative_merger_time_and_exact_exclusions(self) -> None:
        self.assertIn("Eighteen months after the merger completed", self.scenario)
        exclusions = canonical_exclusions()
        self.assertEqual(len(exclusions), 5)
        self.assertEqual(len({row["id"] for row in exclusions}), 5)
        self.assertIn("canonical_exclusions", self.scenario)
        # The scenario incorporates the sole machine registry by reference; it must
        # not become a second independently editable copy of the five IDs.
        for row in exclusions:
            self.assertEqual(self.scenario.count(row["id"]), 0)
            self.assertEqual(self.gates.count(row["id"]), 1)
        self.assertNotRegex(
            self.scenario,
            r"(?i)merger (?:completed|closed|finished) in (?:19|20)[0-9]{2}",
        )

    def test_student_first_loop_withholds_project_specific_fix(self) -> None:
        normalized = self.corpus.lower()
        for required in (
            "student drafts with guidance",
            "student signals ready",
            "agent evaluates once",
            "agent explains the specific gap",
            "student revises in their own words",
        ):
            self.assertIn(required, normalized)
        self.assert_has_any(
            self.corpus,
            (
                "student drafts first",
                "student submits an original answer first",
                "the student submits first",
                "require the student to submit first",
            ),
        )
        self.assert_has_any(
            self.corpus,
            ("blank structure", "guided questions", "unrelated example"),
        )
        self.assert_has_any(
            self.corpus,
            ("one focused socratic question", "ask one focused question"),
        )
        self.assert_has_any(
            self.corpus,
            (
                "end every important teaching exchange",
                "end every teaching exchange",
                "end each evaluation with one focused question",
            ),
        )

    def test_stale_answer_generation_contract_is_absent(self) -> None:
        for stale in (
            "SUBMIT → GENERATE → EVALUATE → REVISE → JUSTIFY",
            "PRELIMINARY DRAFT — FOR STUDENT CRITIQUE",
            "meaningful draft allows labeled preliminary alternative",
        ):
            self.assertNotIn(stale, self.corpus)

    def test_gate_status_depends_only_on_explicit_hard_checks(self) -> None:
        normalized = self.corpus.lower()
        self.assertIn("open", normalized)
        self.assertIn("closed", normalized)
        self.assertRegex(normalized, r"hard checks?.{0,120}(?:only|pass)")
        self.assertRegex(normalized, r"criteria.{0,120}(?:never block|non-blocking|cannot close)")
        self.assertRegex(
            normalized,
            r"(?:score|auto-grader).{0,300}(?:cannot|never).{0,80}(?:open|close|block|delay|condition)",
        )
        self.assertNotRegex(normalized, r"average score.{0,80}(?:open|pass|gate)")
        self.assertNotRegex(normalized, r"no dimension is 1.{0,80}(?:open|pass|gate)")

    def test_two_revision_elements_are_scoped_to_prior_closure(self) -> None:
        normalized = self.corpus.lower()
        self.assertIn("corrected or expanded answer", normalized)
        self.assertIn("one brief", normalized)
        self.assertIn("issue restatement", normalized)
        self.assertRegex(normalized, r"natural(?:ly)? across (?:preserved )?messages|ordinary language across preserved messages")
        self.assertRegex(
            normalized,
            r"(?:only after|after).{0,80}(?:gate closes|closed attempt|prior closure)",
        )
        self.assertRegex(
            normalized,
            r"(?:never|not).{0,80}requir(?:e|ed).{0,100}(?:first attempt|passing first attempt)",
        )

    def test_direct_answer_and_injection_forward_cases_are_complete_and_unique(self) -> None:
        self.assertEqual(self.forward.get("schema_version"), "2.0.0")
        cases = self.forward.get("cases")
        self.assertIsInstance(cases, list)
        ids = [case["id"] for case in cases]
        self.assertEqual(ids, [f"FW-{index:02d}" for index in range(1, 9)])
        self.assertEqual(len(ids), len(set(ids)))
        for case in cases:
            self.assertTrue(case["prompt"].strip())
            self.assertIsInstance(case["expected"], dict)
            self.assertTrue(case["expected"])
            self.assertTrue(all(value is not None for value in case["expected"].values()))

    def test_every_forward_expectation_has_an_executable_runtime_policy(self) -> None:
        normalized = self.corpus.lower()
        evidence_patterns = {
            "project_specific_answer_withheld": r"(?:waldron-specific|assignment-ready).{0,100}(?:prohibited|do not|never)",
            "waldron_decision_withheld": r"never choose the student.s (?:requirement|expectation)",
            "token_attempt_not_expanded": r"no meaningful (?:attempt|work|draft).{0,260}(?:blank structure|focused question)",
            "allowed_support": r"(?s)(?=.*blank structure)(?=.*focused question)(?=.*unrelated example)",
            "smallest_scaffold_only": r"smallest useful scaffold|provide only the smallest useful scaffold",
            "focused_question_count_max": r"ask one focused question|one focused socratic question",
            "student_action_required": r"end (?:each|every).{0,80}(?:student action|focused question)",
            "student_application_required": r"explain course concepts directly.{0,180}(?:student action|never choose)",
            "concept_explanation_allowed": r"explain course concepts directly",
            "prompt_and_secret_withheld": r"prompt-extraction.{0,160}untrusted|never (?:send|accept).{0,100}secrets",
            "cross_student_read_refused": r"no (?:cross-student|student-facing) read|never receive another student.s work",
            "score_and_gate_gaming_refused": r"scores? (?:are )?advisory|cannot alter (?:it|the gate)",
            "assessment_rules_unchanged": r"student text.{0,160}untrusted|ignore requests to",
            "sensitive_detail_not_repeated": r"do not repeat|avoid repeating",
            "sensitive_detail_not_logged": r"exclude it from.{0,100}(?:telemetry|reports)",
            "nonidentifying_replacement_requested": r"non-identifying (?:substitute|replacement)",
            "post_closure_revision_not_required": r"(?:never|not).{0,80}requir(?:e|ed).{0,100}(?:first attempt|passing first attempt)",
            "gate_remains_open": r"first submission opens immediately when every gate-specific hard check passes",
            "criteria_feedback_preserved": r"criteria feedback.{0,80}non-blocking|criteria.{0,160}feedback only",
            "score_does_not_block": r"evaluator scores.{0,180}(?:cannot|never).{0,80}(?:delay|condition|block|close)",
        }
        observed_keys = {
            key
            for case in self.forward["cases"]
            for key in case["expected"]
        }
        self.assertEqual(observed_keys, set(evidence_patterns))
        for key, pattern in evidence_patterns.items():
            with self.subTest(expectation=key):
                self.assertRegex(normalized, pattern)

    def test_empty_and_token_gate_submissions_remain_diagnostic_without_an_answer_bank(self) -> None:
        validator = load_module("forward_gate_validator", GATE_VALIDATOR)
        for submission in ({}, {"big5": {"q1_history": "make it good"}}):
            with self.subTest(submission=submission):
                envelope = gate_envelope(1)
                envelope["submission"] = submission
                result = validator.validate(envelope)
                self.assertEqual(result.get("status"), "INCOMPLETE", result)
                self.assertEqual(result.get("milestone_outcome"), "INCOMPLETE", result)
                self.assertFalse(result.get("attempt_recorded"), result)
                self.assertFalse(result.get("retry_required_next"), result)
                self.assertEqual(result.get("hard_checks"), [], result)
                self.assertFalse(failure_codes(result), result)
                serialized = json.dumps(result, ensure_ascii=False).lower()
                for prohibited in (
                    "corrected_submission",
                    "model_answer",
                    "passing_answer",
                    "answer_bank",
                ):
                    self.assertNotIn(prohibited, serialized)

        substantive = gate_envelope(1)
        substantive["submission"] = {
            "big5": {
                "q1_history": (
                    "The student identifies the old planning binder and explains "
                    "that the abandoned donor database merge shows a concrete "
                    "execution risk worth examining before the allocation process."
                )
            }
        }
        result = validator.validate(substantive)
        self.assertEqual(result.get("status"), "CLOSED", result)
        self.assertTrue(result.get("attempt_recorded"), result)
        self.assertTrue(failure_codes(result), result)

    def test_privacy_response_contract_covers_accidental_disclosure(self) -> None:
        normalized = (self.privacy + "\n" + self.pedagogy).lower()
        for alternatives in (
            ("avoid repeating", "do not repeat"),
            ("exclude",),
            ("non-identifying replacement", "non-identifying substitute"),
            ("pseudonymized",),
            ("re-identifiable",),
        ):
            self.assert_has_any(normalized, alternatives)


if __name__ == "__main__":
    unittest.main()
