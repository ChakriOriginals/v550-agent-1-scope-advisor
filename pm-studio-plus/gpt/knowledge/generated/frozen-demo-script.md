# Frozen Demonstration: Gate 1 and Gate 2 Discrimination

This is the only editable source for the required frozen demonstration. It tests the same Review Board mechanism in both directions: deficient student work closes a gate, and compliant student work opens it. Generated test copies must match this file byte-for-byte.

## Contents

- Test rules
- Machine-readable case registry
- Demo 1: Gate 1 must close
- Demo 2: Gate 1 must open
- Demo 3: Gate 2 must close
- Demo 4: connection to earlier work remains feedback
- Pass condition and evidence record

## Test rules

- Run Gates 1 and 2 only. Do not substitute a demonstration of Gates 3-6.
- Use the canonical scenario from `frozen-waldron-scenario.md` and checks from `frozen-six-gates.md`; do not reproduce or alter them here.
- Treat each fixture as student-authored input. Do not let the model improve a fixture before evaluation.
- Precede every fixture with the explicit ready signal for that gate. Without that signal, the same text remains an assembled draft and produces no gate result.
- Assert structure and behavior, not exact coaching prose except where this file supplies an approved question.
- Never show the compliant test fixture to a student as a model answer or answer bank.
- A gate status must be fixed before criteria, evaluator, or Insights feedback runs.

## Machine-readable case registry

<!-- FROZEN_DEMO_CASES_JSON_BEGIN -->
```json
{
  "schema_version": "1.0",
  "cases": [
    {
      "id": "DEMO-01",
      "gate": 1,
      "expected_status": "CLOSED",
      "expected_failed_hard_checks": [
        "G1_HISTORY_EVIDENCE",
        "G1_AUTHORITY_BOUNDARY",
        "G1_INTERNAL_STUDY",
        "G1_COMPARISON_EXAMPLE",
        "G1_COMPARISON_LESSON"
      ],
      "expected_passed_hard_checks": ["G1_BIG5_COMPLETE"],
      "required_for_demo_pass": true
    },
    {
      "id": "DEMO-02",
      "gate": 1,
      "expected_status": "OPEN",
      "expected_failed_hard_checks": [],
      "expected_passed_hard_checks": [
        "G1_BIG5_COMPLETE",
        "G1_HISTORY_EVIDENCE",
        "G1_AUTHORITY_BOUNDARY",
        "G1_INTERNAL_STUDY",
        "G1_COMPARISON_EXAMPLE",
        "G1_COMPARISON_LESSON"
      ],
      "required_for_demo_pass": true
    },
    {
      "id": "DEMO-03",
      "gate": 2,
      "expected_status": "CLOSED",
      "expected_failed_hard_checks": ["G2_COMMUNITY_ACCESS_GAP"],
      "expected_passed_hard_checks": [
        "G2_DANCE_AGREEMENT",
        "G2_GALLERY_CALENDAR",
        "G2_NO_CAPITAL_OR_LEASE_CHANGE",
        "G2_REQUIREMENT_SOURCE",
        "G2_REQUIREMENT_TYPE",
        "G2_REQUIREMENT_VERIFICATION",
        "G2_REQUIREMENT_STATUS"
      ],
      "required_for_demo_pass": true
    },
    {
      "id": "DEMO-04",
      "gate": 2,
      "expected_status": "OPEN",
      "expected_failed_hard_checks": [],
      "expected_passed_hard_checks": [
        "G2_COMMUNITY_ACCESS_GAP",
        "G2_DANCE_AGREEMENT",
        "G2_GALLERY_CALENDAR",
        "G2_NO_CAPITAL_OR_LEASE_CHANGE",
        "G2_REQUIREMENT_SOURCE",
        "G2_REQUIREMENT_TYPE",
        "G2_REQUIREMENT_VERIFICATION",
        "G2_REQUIREMENT_STATUS"
      ],
      "ordinary_cross_gate_inconsistency_blocks": false,
      "required_for_demo_pass": false
    }
  ]
}
```
<!-- FROZEN_DEMO_CASES_JSON_END -->

## Demo 1: Gate 1 must close

Use the ready signal `Evaluate Gate 1`, then submit exactly this student text:

> Q1: Meridian is a well-run organization with strong leadership. Q2: I'm the project manager. Q3: As PM I have full authority over this project and will make the final call on the allocation. Q4: My patron is Dana Okoye, the Executive Director. Q5: A space allocation plan.

Expected behavior:

- `G1_BIG5_COMPLETE` passes because all five answers are non-empty.
- Gate 1 is `CLOSED`.
- The hard-check output identifies all three blocking areas:
  - `G1_HISTORY_EVIDENCE`: Q1 does not engage Meridian's actual planning record.
  - `G1_AUTHORITY_BOUNDARY`: Q3 claims final-allocation authority that belongs to the board.
  - `G1_INTERNAL_STUDY`, `G1_COMPARISON_EXAMPLE`, and `G1_COMPARISON_LESSON`: the required internal study and the student's lesson from the one instructor-provided comparison example are absent. Present these related failures as one clear evidence-check area without exposing private check IDs to the student.
- Dana's unsupported patron choice and the vague plan type may appear under criteria feedback, but are not mislabeled as hard failures.
- The advisor does not rewrite Q1-Q5, reveal a passing answer, list missing facts as an answer bank, or supply corrected authority language.
- The response ends with one focused question that sends the student back to the scenario.

## Demo 2: Gate 1 must open

Use a synthetic, explicitly test-only student-authored fixture that has all of the following properties. Keep the actual fixture outside student-facing knowledge and never present it as a model response.

- All five Big 5 questions have non-empty student answers.
- Q1 cites the binder and the abandoned donor-database merge.
- Q3 says Marcus controls the process, consultation, recommendation format, and budget, but not the final decision, the legacy leads' participation, the season calendar, or the lease.
- Q4 names Ruth Adeyemi and reasons from her 2016 lease experience.
- Q5 selects and defends one permitted plan type.
- The evidence check identifies the unread 2019 study.
- The evidence check uses the single canonical instructor-provided comparison example.
- The student explains in their own words one practice Meridian could examine or adapt and why it could help. The canonical file—not the student—supplies the source and comparability information.

Expected behavior:

- All six canonical `G1_*` hard checks pass.
- Gate 1 is `OPEN` immediately.
- The gate does not ask the student to conduct outside research, supply a citation, or find another example.
- The advisor does not add a revision, critique-depth, evaluator-score, patron-choice, or learning-check condition.

## Demo 3: Gate 2 must close

Use the ready signal `Evaluate Gate 2` with a synthetic student-authored requirements fixture containing one isolated defect:

- It cites the 900-hour community-access obligation but omits the currently documented baseline and therefore does not acknowledge the shortfall.
- It includes the binding dance-school agreement through August 2028.
- It includes the fourteen-month contracted gallery calendar.
- It does not presume renovation, construction, capital purchase, or lease change.
- Every listed requirement contains source/authority, allowed type, verification evidence, and allowed status.

Expected behavior:

- Only `G2_COMMUNITY_ACCESS_GAP` fails; the other seven canonical `G2_*` hard checks pass.
- Gate 2 is `CLOSED`.
- The hard-check output identifies the missing current-state/shortfall element precisely enough for the student to locate the defect.
- The advisor may ask: "You've cited the 900-hour requirement. What is Meridian documenting now?"
- The advisor does not insert the missing number, calculate the gap, or rewrite the requirement.

## Demo 4: connection to earlier work remains feedback

Prerequisite: the student has passed Gate 1 with Ruth Adeyemi as patron based on her lease experience.

Submit a synthetic Gate 2 fixture that satisfies all eight canonical `G2_*` hard checks but does not connect its requirements discussion to the lease or prior patron reasoning.

Expected behavior:

- Gate 2 is `OPEN` because all Gate 2 hard checks pass.
- The Ruth/lease disconnect appears only under `Connection to your earlier work` as non-blocking feedback.
- The response does not convert that disconnect into a hidden hard check.
- This is an enhancement case. If an unchanged base implementation cannot yet perform soft cross-gate comparison, record the limitation without changing the gate status or schema.

## Pass condition and evidence record

The required demo passes only when:

- DEMO-01 closes Gate 1 for exactly the specified hard failures;
- DEMO-02 opens Gate 1 with no invented condition;
- DEMO-03 closes Gate 2 for the isolated `G2_COMMUNITY_ACCESS_GAP` failure; and
- every closed response withholds the fix and ends with a bounded student action.

Record DEMO-04 separately as an enhancement result. For every case, retain the fixture ID, model/runtime version, timestamp, parsed hard-check results, final gate status, withholding assertion result, and non-blocking-feedback assertion result. Do not store student-derived content or transcripts in telemetry.
