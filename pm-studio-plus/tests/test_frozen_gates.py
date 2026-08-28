"""Executable truth-table tests for the frozen six-gate Waldron scenario."""

from __future__ import annotations

import unittest
from typing import Any, Callable

from support import (
    GATE_VALIDATOR,
    canonical_exclusions,
    deep_copy,
    failure_codes,
    gate_envelope,
    load_module,
    parse_json_stdout,
    retry_envelope,
    run_json_cli,
)


Mutation = Callable[[dict[str, Any]], None]


class FrozenGateTruthTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_module("frozen_gate_validator", GATE_VALIDATOR)
        if not hasattr(cls.validator, "validate"):
            raise AssertionError(f"{GATE_VALIDATOR} must expose validate(envelope)")

    def evaluate(self, envelope: dict[str, Any]) -> dict[str, Any]:
        result = self.validator.validate(deep_copy(envelope))
        self.assertIsInstance(result, dict)
        self.assertIn(result.get("status"), {"OPEN", "CLOSED"})
        self.assertIsInstance(result.get("failed_checks"), list)
        self.assertIsInstance(result.get("criteria_feedback", []), list)
        return result

    def assert_open(self, envelope: dict[str, Any]) -> dict[str, Any]:
        result = self.evaluate(envelope)
        self.assertEqual(result["status"], "OPEN", result)
        self.assertEqual(failure_codes(result), set(), result)
        return result

    def assert_closed_with(
        self,
        gate_number: int,
        expected_code: str,
        mutation: Mutation,
    ) -> dict[str, Any]:
        envelope = gate_envelope(gate_number)
        mutation(envelope)
        result = self.evaluate(envelope)
        self.assertEqual(result["status"], "CLOSED", result)
        self.assertIn(expected_code, failure_codes(result), result)
        self.assert_withholds_fix(result)
        return result

    def assert_withholds_fix(self, result: dict[str, Any]) -> None:
        serialized = repr(result).lower()
        for prohibited in (
            "corrected_submission",
            "suggested_fix",
            "model_answer",
            "passing_answer",
            "replacement_text",
        ):
            self.assertNotIn(prohibited, serialized)

    def test_exactly_six_ordered_gates_open_on_complete_first_attempts(self) -> None:
        observed: list[int] = []
        for gate in range(1, 7):
            with self.subTest(gate=gate):
                result = self.assert_open(gate_envelope(gate))
                observed.append(result.get("gate_number", gate))
        self.assertEqual(observed, [1, 2, 3, 4, 5, 6])
        with self.assertRaises((KeyError, ValueError)):
            gate_envelope(7)

    def test_gate_cli_uses_zero_one_two_exit_contract(self) -> None:
        opened = run_json_cli(GATE_VALIDATOR, gate_envelope(1))
        self.assertEqual(opened.returncode, 0, opened.stdout + opened.stderr)
        self.assertEqual(parse_json_stdout(opened).get("status"), "OPEN")

        closed_payload = gate_envelope(1)
        closed_payload["submission"]["big5"]["q1_history"] = ""
        closed = run_json_cli(GATE_VALIDATOR, closed_payload)
        self.assertEqual(closed.returncode, 1, closed.stdout + closed.stderr)
        self.assertEqual(parse_json_stdout(closed).get("status"), "CLOSED")

        diagnostic_payload = gate_envelope(1)
        diagnostic_payload["submission"] = {}
        diagnostic = run_json_cli(GATE_VALIDATOR, diagnostic_payload)
        self.assertEqual(diagnostic.returncode, 1, diagnostic.stdout + diagnostic.stderr)
        self.assertEqual(parse_json_stdout(diagnostic).get("status"), "INCOMPLETE")

        malformed = run_json_cli(
            GATE_VALIDATOR,
            {"gate_number": 1, "submission": "not-an-object"},
        )
        self.assertEqual(malformed.returncode, 2, malformed.stdout + malformed.stderr)
        self.assertEqual(parse_json_stdout(malformed).get("status"), "MALFORMED")

    # Gate 1 -----------------------------------------------------------------

    def test_gate_1_each_hard_check_closes(self) -> None:
        cases: list[tuple[str, Mutation]] = [
            (
                "G1_BIG5_COMPLETE",
                lambda e: e["submission"]["big5"].__setitem__("q2_role", ""),
            ),
            (
                "G1_HISTORY_EVIDENCE",
                lambda e: e["submission"]["big5"].__setitem__(
                    "q1_history", "Meridian should plan carefully."
                ),
            ),
            (
                "G1_AUTHORITY_BOUNDARY",
                lambda e: e["submission"]["big5"].__setitem__(
                    "q3_authority", "Marcus controls the final allocation decision and the lease."
                ),
            ),
            (
                "G1_INTERNAL_STUDY",
                lambda e: e["submission"]["research_and_development"].__setitem__(
                    "internal_study", ""
                ),
            ),
            (
                "G1_COMPARISON_EXAMPLE",
                lambda e: e["submission"]["research_and_development"][
                    "outside_precedents"
                ][0].__setitem__("card_id", "REPLACEMENT-EXAMPLE"),
            ),
            (
                "G1_COMPARISON_LESSON",
                lambda e: e["submission"]["research_and_development"][
                    "outside_precedents"
                ][0].__setitem__("adaptation", ""),
            ),
        ]
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(1, code, mutation)

    def test_frozen_demo_gate_1_literal_input_closes_exactly(self) -> None:
        envelope = gate_envelope(1)
        envelope["submission"] = {
            "big5": {
                "q1_history": "Meridian is a well-run organization with strong leadership.",
                "q2_role": "I'm the project manager.",
                "q3_authority": (
                    "As PM I have full authority over this project and will make "
                    "the final call on the allocation."
                ),
                "q4_patron": "My patron is Dana Okoye, the Executive Director.",
                "q5_plan_type": "A space allocation plan.",
            }
        }
        result = self.evaluate(envelope)
        self.assertEqual(result["status"], "CLOSED", result)
        self.assertEqual(
            failure_codes(result),
            {
                "G1_HISTORY_EVIDENCE",
                "G1_AUTHORITY_BOUNDARY",
                "G1_INTERNAL_STUDY",
                "G1_COMPARISON_EXAMPLE",
                "G1_COMPARISON_LESSON",
            },
        )
        self.assertEqual(
            next(
                check["result"]
                for check in result["hard_checks"]
                if check["code"] == "G1_BIG5_COMPLETE"
            ),
            "PASS",
        )

        bounded = gate_envelope(1)
        bounded["submission"]["big5"]["q3_authority"] = (
            "I do not have full authority or the final call on the allocation; "
            "the board decides. I control the planning process and recommendation format."
        )
        self.assertEqual(self.evaluate(bounded)["status"], "OPEN")

    def test_gate_1_criteria_are_feedback_only(self) -> None:
        envelope = gate_envelope(1)
        envelope["submission"]["big5"]["q4_patron"] = "Dana is my patron."
        envelope["submission"]["big5"]["q5_plan_type"] = "One-time allocation."
        result = self.assert_open(envelope)
        self.assertTrue(result["criteria_feedback"])

    # Gate 2 -----------------------------------------------------------------

    def test_gate_2_each_hard_check_closes(self) -> None:
        def omit_access_gap(envelope: dict[str, Any]) -> None:
            envelope["submission"]["requirements"][0]["statement"] = (
                "The City lease requires 900 annual below-market community-access hours."
            )

        def omit_dance(envelope: dict[str, Any]) -> None:
            envelope["submission"]["requirements"] = [
                row
                for row in envelope["submission"]["requirements"]
                if row["id"] != "REQ-02"
            ]

        def omit_gallery(envelope: dict[str, Any]) -> None:
            envelope["submission"]["requirements"] = [
                row
                for row in envelope["submission"]["requirements"]
                if row["id"] != "REQ-03"
            ]

        def presume_capital(envelope: dict[str, Any]) -> None:
            envelope["submission"]["requirements"].append(
                {
                    "id": "REQ-BAD",
                    "statement": "Renovate the Firebay and renegotiate the City lease.",
                    "source_authority": "student preference",
                    "type": "other",
                    "verification_method": "Inspect completed construction.",
                    "status": "CONFIRMED",
                }
            )

        field_cases = [
            ("G2_REQUIREMENT_SOURCE", "source_authority"),
            ("G2_REQUIREMENT_TYPE", "type"),
            ("G2_REQUIREMENT_VERIFICATION", "verification_method"),
            ("G2_REQUIREMENT_STATUS", "status"),
        ]
        cases: list[tuple[str, Mutation]] = [
            ("G2_COMMUNITY_ACCESS_GAP", omit_access_gap),
            ("G2_DANCE_AGREEMENT", omit_dance),
            ("G2_GALLERY_CALENDAR", omit_gallery),
            ("G2_NO_CAPITAL_OR_LEASE_CHANGE", presume_capital),
        ]
        for code, field in field_cases:
            cases.append(
                (
                    code,
                    lambda e, field=field: e["submission"]["requirements"][0].__setitem__(
                        field, ""
                    ),
                )
            )
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(2, code, mutation)

    def test_gate_2_ada_within_no_capital_boundary_does_not_false_fail(self) -> None:
        self.assert_open(gate_envelope(2))

    def test_gate_2_cross_gate_disconnect_is_feedback_only(self) -> None:
        envelope = gate_envelope(2)
        envelope["prior_gate_artifacts"] = {"gate_1": gate_envelope(1)["submission"]}
        result = self.assert_open(envelope)
        self.assertTrue(result["criteria_feedback"])

    # Gate 3 -----------------------------------------------------------------

    def test_gate_3_each_hard_check_closes(self) -> None:
        def empty_wont(envelope: dict[str, Any]) -> None:
            envelope["submission"]["moscow"]["wont"] = []

        def move_exclusion(envelope: dict[str, Any]) -> None:
            item = envelope["submission"]["moscow"]["wont"].pop()
            envelope["submission"]["moscow"]["should"].append(item)

        def alter_exclusion(envelope: dict[str, Any]) -> None:
            envelope["submission"]["moscow"]["wont"][0]["id"] = "EX-01-ALTERED"

        def omit_firebay(envelope: dict[str, Any]) -> None:
            envelope["submission"]["conflicts"] = []

        def omit_source_tag(envelope: dict[str, Any]) -> None:
            envelope["submission"]["moscow"]["must"][0]["source_tag"] = ""

        def duplicate_item(envelope: dict[str, Any]) -> None:
            envelope["submission"]["moscow"]["could"].append(
                deep_copy(envelope["submission"]["moscow"]["must"][0])
            )

        cases = [
            ("G3_WONT_NONEMPTY", empty_wont),
            ("G3_CANONICAL_EXCLUSIONS", move_exclusion),
            ("G3_CANONICAL_EXCLUSIONS", alter_exclusion),
            ("G3_FIREBAY_CONFLICT", omit_firebay),
            ("G3_SOURCE_TAG", omit_source_tag),
            ("G3_NO_DUPLICATES", duplicate_item),
        ]
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(3, code, mutation)

    def test_gate_3_all_five_canonical_wonts_pass_location_check(self) -> None:
        envelope = gate_envelope(3)
        ids = {item["id"] for item in envelope["submission"]["moscow"]["wont"]}
        self.assertEqual(ids, {row["id"] for row in canonical_exclusions()})
        self.assert_open(envelope)

    def test_gate_3_attribution_quality_does_not_block(self) -> None:
        envelope = gate_envelope(3)
        envelope["submission"]["moscow"]["should"][0]["attribution"] = "the organization"
        self.assert_open(envelope)

    # Gate 4 -----------------------------------------------------------------

    def test_gate_4_each_hard_check_closes(self) -> None:
        def two_goals(envelope: dict[str, Any]) -> None:
            envelope["submission"]["goal"] = ["Improve allocation", "Finish Stage 1"]

        def two_objectives(envelope: dict[str, Any]) -> None:
            envelope["submission"]["objectives"].pop()

        def after_june_1(envelope: dict[str, Any]) -> None:
            envelope["submission"]["objectives"][2]["completion_date"] = "2027-06-02"
            envelope["submission"]["objectives"][2]["statement"] = (
                "By June 2, issue 1 post-vote handoff record."
            )

        def omit_may_14(envelope: dict[str, Any]) -> None:
            envelope["submission"]["objectives"][1]["completion_date"] = "2027-05-13"
            envelope["submission"]["objectives"][1]["statement"] = (
                "By May 13, present 1 final allocation recommendation."
            )

        def unmeasured_objective(envelope: dict[str, Any]) -> None:
            envelope["submission"]["objectives"][2]["statement"] = "Improve the handoff."
            envelope["submission"]["objectives"][2]["completion_date"] = ""

        cases = [
            ("G4_EXACTLY_ONE_GOAL", two_goals),
            ("G4_OBJECTIVE_COUNT", two_objectives),
            ("G4_NO_DATE_AFTER_JUNE_1", after_june_1),
            ("G4_MAY_14_FIXED_POINT", omit_may_14),
            ("G4_OBJECTIVE_MEASURABLE_TOKEN", unmeasured_objective),
        ]
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(4, code, mutation)

    def test_gate_4_weak_smart_and_success_criteria_are_feedback_only(self) -> None:
        envelope = gate_envelope(4)
        envelope["submission"]["goal"] = "Complete the assignment."
        for objective in envelope["submission"]["objectives"]:
            objective["success_criterion"] = "Evidence is unclear."
            objective["smart"] = {
                "specific": False,
                "measurable": True,
                "achievable": None,
                "relevant": None,
                "time_bound": True,
            }
        result = self.assert_open(envelope)
        self.assertTrue(result["criteria_feedback"])

    # Gate 5 -----------------------------------------------------------------

    def test_gate_5_each_hard_check_closes(self) -> None:
        def omit_statement_component(envelope: dict[str, Any]) -> None:
            del envelope["submission"]["project_statement"]["trigger"]

        def omit_exclusion(envelope: dict[str, Any]) -> None:
            envelope["submission"]["exclusions"].pop()

        def omit_assumptions(envelope: dict[str, Any]) -> None:
            envelope["submission"]["assumptions"] = []

        def omit_action_verb(envelope: dict[str, Any]) -> None:
            envelope["submission"]["scope_action_plan"][0]["action"] = (
                "Meetings about the 2019 study"
            )

        def activity_as_deliverable(envelope: dict[str, Any]) -> None:
            envelope["submission"]["deliverables"][0]["output"] = (
                "Hold stakeholder meetings"
            )

        def omit_approver(envelope: dict[str, Any]) -> None:
            envelope["submission"]["deliverables"][0]["approver"] = ""

        def one_end_date(envelope: dict[str, Any]) -> None:
            for deliverable in envelope["submission"]["deliverables"]:
                deliverable["due_date"] = "2027-05-14"

        cases = [
            ("G5_PROJECT_STATEMENT_COMPONENTS", omit_statement_component),
            ("G5_CANONICAL_EXCLUSIONS", omit_exclusion),
            ("G5_CONSTRAINTS_ASSUMPTIONS_SEPARATE", omit_assumptions),
            ("G5_ACTION_VERB", omit_action_verb),
            ("G5_DELIVERABLE_OUTPUT", activity_as_deliverable),
            ("G5_NAMED_APPROVER", omit_approver),
            ("G5_PHASED_DATES", one_end_date),
        ]
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(5, code, mutation)

    def test_gate_5_action_owner_and_cross_gate_optional_exclusion_do_not_block(self) -> None:
        envelope = gate_envelope(5)
        for action in envelope["submission"]["scope_action_plan"]:
            action.pop("owner", None)
        envelope["submission"]["exclusions"].append(
            {"id": "STUDENT-WONT-01", "meaning": "Optional preference omitted from formal scope"}
        )
        self.assert_open(envelope)

    # Gate 6 -----------------------------------------------------------------

    def test_gate_6_each_structural_hard_check_closes(self) -> None:
        def omit_deliverable(envelope: dict[str, Any]) -> None:
            for element in envelope["submission"]["wbs"]["elements"]:
                if element["deliverable_id"] == "DEL-02":
                    element["deliverable_id"] = None
                    element["branch"] = "UNLINKED"

        def add_out_of_scope(envelope: dict[str, Any]) -> None:
            bad = deep_copy(envelope["submission"]["wbs"]["elements"][1])
            bad["id"] = "1.2"
            bad["name"] = "Renovate the Firebay and renegotiate the lease"
            envelope["submission"]["wbs"]["elements"].append(bad)

        def omit_preplanning(envelope: dict[str, Any]) -> None:
            envelope["submission"]["wbs"]["elements"] = [
                row
                for row in envelope["submission"]["wbs"]["elements"]
                if row["branch"] != "PRE_PLANNING" and row["id"] != "1"
            ]

        def ownerless(envelope: dict[str, Any]) -> None:
            envelope["submission"]["wbs"]["elements"][1]["owner"] = ""

        def bad_hierarchy(envelope: dict[str, Any]) -> None:
            envelope["submission"]["wbs"]["elements"][1]["parent_id"] = "9.9"

        def missing_time(envelope: dict[str, Any]) -> None:
            envelope["submission"]["wbs"]["elements"][1]["time_window"] = ""

        def missing_summary(envelope: dict[str, Any]) -> None:
            del envelope["submission"]["wbs"]["resource_summary"]["total_facilitator_days"]

        def over_capacity(envelope: dict[str, Any]) -> None:
            envelope["submission"]["wbs"]["elements"][1]["people_hours"] = 526

        cases = [
            ("G6_DELIVERABLE_TRACEABILITY", omit_deliverable),
            ("G6_SCOPE_BOUNDARY", add_out_of_scope),
            ("G6_PREPLANNING_WORK", omit_preplanning),
            ("G6_SINGLE_OWNER", ownerless),
            ("G6_HIERARCHY_AND_LINK", bad_hierarchy),
            ("G6_TIME_AND_HOURS", missing_time),
            ("G6_RESOURCE_SUMMARY", missing_summary),
            ("G6_PREVOTE_EFFORT", over_capacity),
        ]
        for code, mutation in cases:
            with self.subTest(code=code):
                self.assert_closed_with(6, code, mutation)

    def test_gate_6_resource_vector_rejects_every_incomplete_form(self) -> None:
        mutations: list[tuple[str, Mutation]] = [
            (
                "omitted",
                lambda e: e["submission"]["wbs"]["elements"][1]["resources"].pop(
                    "software_tools"
                ),
            ),
            (
                "blank",
                lambda e: e["submission"]["wbs"]["elements"][1]["resources"].__setitem__(
                    "equipment", ""
                ),
            ),
            (
                "N/A",
                lambda e: e["submission"]["wbs"]["elements"][1]["resources"].__setitem__(
                    "materials", "N/A"
                ),
            ),
            (
                "as needed",
                lambda e: e["submission"]["wbs"]["elements"][1]["resources"].__setitem__(
                    "contractors", "as needed"
                ),
            ),
            (
                "negative facilitator days",
                lambda e: e["submission"]["wbs"]["elements"][1]["resources"].__setitem__(
                    "facilitator_days", -1
                ),
            ),
        ]
        for label, mutation in mutations:
            with self.subTest(label=label):
                self.assert_closed_with(6, "G6_RESOURCE_VECTOR", mutation)

    def test_gate_6_zero_and_none_resource_values_pass_structurally(self) -> None:
        self.assert_open(gate_envelope(6))

    def test_gate_6_criteria_do_not_become_hidden_hard_checks(self) -> None:
        envelope = gate_envelope(6)
        envelope["submission"]["wbs"]["reported_depth"] = 4
        envelope["submission"]["wbs"]["hundred_percent_rule_checked"] = False
        envelope["submission"]["wbs"]["elements"][1]["name"] = "Work"
        result = self.assert_open(envelope)
        self.assertTrue(result["criteria_feedback"])

    # Gate 6B ---------------------------------------------------------------

    def test_gate_6b_is_internal_to_gate_6_and_each_hard_check_closes(self) -> None:
        for component in (
            "assumption_audit",
            "scope_creep_comparison",
            "disposition",
            "final_revision_record",
            "why_this_is_defensible",
        ):
            with self.subTest(component=component):
                self.assert_closed_with(
                    6,
                    "G6B_COMPONENTS",
                    lambda e, component=component: e["submission"]["final_audit"].__setitem__(
                        component, [] if component in {"assumption_audit", "scope_creep_comparison", "disposition"} else ""
                    ),
                )

        self.assert_closed_with(
            6,
            "G6B_ASSUMPTION_STATUS",
            lambda e: e["submission"]["final_audit"]["assumption_audit"][0].__setitem__(
                "source_or_status", "CONFIRMED"
            ),
        )
        self.assert_closed_with(
            6,
            "G6B_CHANGE_DISPOSITION",
            lambda e: e["submission"]["final_audit"].__setitem__("disposition", []),
        )

        def unreconciled_acceptance(envelope: dict[str, Any]) -> None:
            disposition = envelope["submission"]["final_audit"]["disposition"][0]
            disposition["decision"] = "ACCEPT WITH IRON TRIANGLE CONSEQUENCE"
            disposition["gate_5_reconciled"] = False
            disposition["wbs_reconciled"] = False

        self.assert_closed_with(6, "G6B_RECONCILIATION", unreconciled_acceptance)
        self.assert_closed_with(
            6,
            "G6B_STUDENT_REVISION_REASON",
            lambda e: e["submission"]["final_audit"].__setitem__(
                "final_revision_record", "NO CHANGE"
            ),
        )

    def test_gate_6b_complete_student_authored_no_change_can_open_gate_6(self) -> None:
        result = self.assert_open(gate_envelope(6))
        self.assertEqual(result.get("gate_number", 6), 6)
        self.assertNotEqual(result.get("gate_number"), 7)

    # Global post-closure revision ------------------------------------------

    def test_two_revision_elements_are_required_only_after_a_closed_attempt(self) -> None:
        self.assert_open(gate_envelope(2))
        self.assert_open(retry_envelope(2))

        field_codes = {
            "revision": "POST_CLOSURE_REVISION",
            "why_this_improves_project": "POST_CLOSURE_IMPROVEMENT_REASON",
        }
        for field, code in field_codes.items():
            with self.subTest(field=field):
                envelope = retry_envelope(2)
                envelope["retry_envelope"][field] = ""
                result = self.validator.validate(deep_copy(envelope))
                if field == "why_this_improves_project":
                    self.assertEqual(result.get("interaction_state"), "PENDING_REFLECTION", result)
                    self.assertFalse(result.get("attempt_recorded"), result)
                    self.assertIn(code, failure_codes(result), result)
                    self.assertNotIn("Ready to move on", result["student_response"])
                    self.assertEqual(
                        result["student_response"]["next"],
                        "Why does this change make the plan stronger?",
                    )
                else:
                    self.assertEqual(result.get("status"), "CLOSED", result)
                    self.assertIn(code, failure_codes(result), result)
                    self.assert_withholds_fix(result)

    def test_multiple_hard_failures_are_all_named(self) -> None:
        envelope = gate_envelope(2)
        envelope["submission"]["requirements"] = [
            {
                "id": "REQ-SYNTHETIC",
                "statement": (
                    "This student submission proposes a generic requirement "
                    "without the required scenario facts."
                ),
                "source_authority": "Student analysis",
                "type": "client",
                "verification_method": "Review the recorded requirement.",
                "status": "CONFIRMED",
            }
        ]
        result = self.evaluate(envelope)
        self.assertEqual(result["status"], "CLOSED")
        self.assertTrue(
            {
                "G2_COMMUNITY_ACCESS_GAP",
                "G2_DANCE_AGREEMENT",
                "G2_GALLERY_CALENDAR",
            }.issubset(failure_codes(result)),
            result,
        )


if __name__ == "__main__":
    unittest.main()
