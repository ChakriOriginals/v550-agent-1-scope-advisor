# Scope Course Requirements

## Contents

- Stage 1 boundary
- Protocol roles
- Scope concepts
- Gate-to-artifact mapping
- WBS and resource treatment
- Assumptions and scope creep
- Accessibility and alternate projects

## Stage 1 boundary

Build only the Scope Advisor stage. One orchestrating GPT wears these existing protocol-role hats:

1. Main Scope Advisor
2. Insights
3. Auto-Grader/Evaluator
4. Summarizer
5. WBS Decomposer & Action Plan
6. Assumption Auditor
7. Scope Review Board

These are protocols, not separate autonomous agents. Do not add another role. Do not build stakeholder-persona simulation, scheduling, critical path, resource leveling, detailed cost estimating, or the other PM Studio+ advisors.

V450 Big 5 Pre-Questions concern the project manager’s own situation. They are not stakeholders and have no relationship to the hidden OCEAN personality tag reserved for a future Stakeholder Advisor.

## Scope concepts

- A requirement is a necessity or condition that must meet a standard.
- An expectation is an assumed, hoped-for, or unstated outcome.
- A goal is directional; an objective is measurable.
- A deliverable is an output handed over, not an activity.
- A Scope Action Plan is milestone-level activity and uses action verbs.
- A WBS decomposes the total approved scope hierarchically; it is not a chronological schedule.
- A constraint is a binding limit; an assumption is treated as true for planning but requires consequence/status; an uncertainty is unresolved.
- An exclusion is an explicit boundary that prevents foreseeable scope creep.

Explain these concepts, but make the student apply them.

## Gate-to-artifact mapping

Use exactly six gates. See `frozen-six-gates.md` for authoritative checks.

| Gate | Student artifact | Existing storage area |
|---|---|---|
| 1 | Five Big 5 answers and the evidence check | Big 5 role-framing versions/notes |
| 2 | Requirements with source, type, evidence, status | Requirements versions |
| 3 | MoSCoW expectations and conflicts | Expectations/MoSCoW versions |
| 4 | One goal, objectives, success criteria | Goals and objectives/success-criteria versions |
| 5 | Project statement, boundaries, exclusions, deliverables, action plan | Existing Scope artifact versions |
| 6 | WBS, resources, final audit/revision | WBS, assumption log, ledger, Gate 6 history |

Do not alter the existing student artifact schemas. Encode required Gate 2 labels in existing text/notes or metadata. Encode Gate 6 `time_window`, `people_hours`, and fixed resource-vector labels in existing WBS dictionary notes/metadata. Student-facing `OPEN` and `CLOSED` serialize through the existing outcome vocabulary without repurposing its meaning.

## WBS and resource treatment

Every work package needs one owner, hierarchy/linkage, a time window, positive people-hours, and a complete resource vector. `NONE` or numeric zero is the valid explicit unused value; blank, `N/A`, and `as needed` fail structural validation.

For Waldron, work-package owners are Marcus, Priya, or Tomas. Pre-vote planning capacity is:

`0.75 FTE × 40 hours/week × approximately 17.5 weeks = 525 person-hours`

Count only `PRE_VOTE` work packages toward the ceiling. Keep post-vote work visible with positive hours. Do not convert staff hours to dollars or charge them to the $35,000 planning budget. Facilitator days and other non-staff resources are counts/descriptions for later costing.

The WBS 100% rule, two-to-three-level guidance, intern test, approximate package size, resource plausibility, and most gap/overlap judgments are criteria feedback. The explicit Gate 5 deliverable trace, hierarchy, owner, resource-field, project-summary, no-outside-scope, pre-planning, and 525-hour checks are hard.

## Assumptions and scope creep

The Assumption Auditor may identify facts presented without authority, distinguish categories, ask what-if questions, compare revisions with approved boundaries, and ask whether a change is `REJECT`, `DEFER`, `EXCHANGE`, or `ACCEPT WITH IRON TRIANGLE CONSEQUENCE`.

Gate 6B is mandatory inside Gate 6. It uses the existing assumption log, Gate 5 artifacts, WBS, and revision ledger. It never creates a seventh gate, schema, role, or event.

## Accessibility and alternate projects

Offer text-first alternatives to visual material and do not require disability disclosure. Never require sensitive organizational, personal, political, budget, medical, legal, employment, or security details. Allow course-approved fictional/anonymized projects and evidence alternatives when real sources or access are unavailable.

For a solo project outside Waldron, require justified ownership and realistic reviewers; do not fabricate team consensus. The frozen Waldron owner restriction remains unchanged.
