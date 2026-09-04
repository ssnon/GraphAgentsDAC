from __future__ import annotations

from copy import deepcopy

import pytest

from pipeline_core.discovery.n10_post_generation_continuation_orchestration import (
    compile_post_generation_continuation_work_items,
)


CANDIDATE = "hypothesis:candidate"
FINAL = "hypothesis:final"
SOURCE = "hypothesis:source"


def gate(
    *,
    selection="CONDITIONAL",
    action="REFINE_NOVELTY_BEARING_SPECIFICATION",
    positive=False,
    fallback=False,
):
    return {
        "schema_version":
            "scientific-novelty-fallback-gate-v2",

        "production_authority":
            True,

        "authority_scope":
            "alpha6_post_generation_candidate",

        "authority_source":
            "n10_role_aware_nonobviousness_v2",

        "positive_authority_requires":
            "ELIGIBLE_AND_ROLE_AWARE_POSITIVE_NONOBVIOUSNESS",

        "conditional_is_positive":
            False,

        "absence_is_novelty":
            False,

        "candidate_semantics_preserved":
            True,

        "gates": [
            {
                "hypothesis_id":
                    CANDIDATE,

                "selection_class":
                    selection,

                "action":
                    action,

                "base_aggregation_action":
                    action,

                "positive_nonobviousness_authority":
                    positive,

                "fallback_allowed":
                    fallback,

                "reason_codes":
                    [],
            }
        ],
    }


def artifact():
    return {
        "candidate_id":
            CANDIDATE,

        "final_hypothesis_id":
            FINAL,

        "candidate_final_authority_equivalent":
            True,

        "source_portfolio":
            "/tmp/source.portfolio.json",

        "hypothesis_context":
            "/tmp/hypothesis.context.json",

        "query_plan":
            "/tmp/query_plan.json",

        "prior_art":
            "/tmp/prior_art.json",

        "external_report":
            "/tmp/external_report.json",

        "intake_shadow":
            "/tmp/intake.json",

        "full_shadow":
            "/tmp/full.json",

        "candidate_gate":
            "/tmp/production_gate_v2.candidate.json",

        "production_gate":
            "/tmp/production_gate.json",

        "ready_claim_count":
            2,

        "selection_class":
            "CONDITIONAL",

        "fallback_allowed":
            False,
    }


def decision(
    *,
    selection="CONDITIONAL",
    action="REFINE_NOVELTY_BEARING_SPECIFICATION",
    kept=False,
):
    return {
        "original_hypothesis_id":
            SOURCE,

        "candidate_hypothesis_id":
            CANDIDATE,

        "final_hypothesis_id":
            FINAL,

        "alpha6_decision":
            "accepted_refinement",

        "n10_required":
            True,

        "n10_selection_class":
            selection,

        "n10_action":
            action,

        "kept":
            kept,

        "reason_codes":
            [],
    }


def report(
    *,
    selection="CONDITIONAL",
    action="REFINE_NOVELTY_BEARING_SPECIFICATION",
    kept=False,
):
    return {
        "schema_version":
            "alpha6-post-generation-nonobviousness-enforcement-v2",

        "production_authority":
            True,

        "authority_source":
            "n10_role_aware_nonobviousness_v2",

        "authority_scope":
            "alpha6_post_generation_candidate",

        "positive_authority_requires":
            "ELIGIBLE_AND_ROLE_AWARE_POSITIVE_NONOBVIOUSNESS",

        "conditional_is_positive":
            False,

        "absence_is_novelty":
            False,

        "candidate_semantics_preserved":
            True,

        "decisions": [
            decision(
                selection=selection,
                action=action,
                kept=kept,
            )
        ],

        "candidate_artifacts": [
            artifact()
        ],
    }


def compile_one(
    *,
    report_payload=None,
    gate_payload=None,
    depth=0,
):
    return (
        compile_post_generation_continuation_work_items(
            enforcement_report=(
                report_payload
                if report_payload is not None
                else report()
            ),
            gates_by_candidate_id={
                CANDIDATE: (
                    gate_payload
                    if gate_payload is not None
                    else gate()
                )
            },
            continuation_depth=depth,
        )
    )


def test_exact_repairable_conditional_compiles_one_work_item():
    items = compile_one()

    assert len(items) == 1

    row = items[0]

    assert row.source_hypothesis_id == SOURCE
    assert row.continuation_input_candidate_id == CANDIDATE
    assert row.continuation_input_final_hypothesis_id == FINAL

    assert row.selection_class == "CONDITIONAL"

    assert (
        row.action
        == "REFINE_NOVELTY_BEARING_SPECIFICATION"
    )

    assert row.current_depth == 0
    assert row.next_depth == 1

    assert (
        row.continuation_reason_code
        == "allow_one_post_generation_novelty_specification_repair"
    )

    assert row.fresh_post_generation_n10_required is True
    assert row.production_authority is False

    assert (
        row.candidate_gate
        == "/tmp/production_gate_v2.candidate.json"
    )


def test_eligible_candidate_does_not_receive_continuation():
    r = report(
        selection="ELIGIBLE",
        action="NO_ACTION",
        kept=True,
    )

    r["candidate_artifacts"][0][
        "selection_class"
    ] = "ELIGIBLE"

    r["candidate_artifacts"][0][
        "fallback_allowed"
    ] = True

    g = gate(
        selection="ELIGIBLE",
        action="NO_ACTION",
        positive=True,
        fallback=True,
    )

    assert (
        compile_one(
            report_payload=r,
            gate_payload=g,
        )
        == ()
    )


def test_ineligible_candidate_does_not_receive_continuation():
    r = report(
        selection="INELIGIBLE",
        action="EVIDENCE_REQUIRED",
        kept=False,
    )

    r["candidate_artifacts"][0][
        "selection_class"
    ] = "INELIGIBLE"

    g = gate(
        selection="INELIGIBLE",
        action="EVIDENCE_REQUIRED",
        positive=False,
        fallback=False,
    )

    assert (
        compile_one(
            report_payload=r,
            gate_payload=g,
        )
        == ()
    )


def test_conditional_wrong_action_does_not_receive_continuation():
    r = report(
        action="EVIDENCE_REQUIRED",
    )

    g = gate(
        action="EVIDENCE_REQUIRED",
    )

    assert (
        compile_one(
            report_payload=r,
            gate_payload=g,
        )
        == ()
    )


def test_depth_one_does_not_compile_second_continuation():
    assert (
        compile_one(
            depth=1,
        )
        == ()
    )


def test_corrupt_conditional_positive_authority_fails_closed():
    g = gate(
        positive=True,
    )

    with pytest.raises(
        ValueError,
        match="non-ELIGIBLE role-aware candidate",
    ):
        compile_one(
            gate_payload=g,
        )


def test_corrupt_conditional_fallback_authority_fails_closed():
    g = gate(
        fallback=True,
    )

    with pytest.raises(
        ValueError,
        match="non-ELIGIBLE role-aware candidate",
    ):
        compile_one(
            gate_payload=g,
        )


def test_conflicting_gate_actions_are_not_continuation_eligible():
    g = gate()

    g["gates"][0][
        "base_aggregation_action"
    ] = "EVIDENCE_REQUIRED"

    assert (
        compile_one(
            gate_payload=g,
        )
        == ()
    )


def test_missing_candidate_gate_artifact_fails_closed():
    r = report()

    r["candidate_artifacts"][0].pop(
        "candidate_gate"
    )

    with pytest.raises(
        ValueError,
        match="artifact.candidate_gate",
    ):
        compile_one(
            report_payload=r,
        )


def test_candidate_artifact_membership_must_match_decisions():
    r = report()

    r["candidate_artifacts"] = []

    with pytest.raises(
        ValueError,
        match="candidate artifact membership",
    ):
        compile_one(
            report_payload=r,
        )


def test_gate_membership_must_match_generated_decisions():
    with pytest.raises(
        ValueError,
        match="candidate gate membership",
    ):
        compile_post_generation_continuation_work_items(
            enforcement_report=report(),
            gates_by_candidate_id={},
            continuation_depth=0,
        )


def test_enforcement_selection_drift_fails_closed():
    r = report()

    r["decisions"][0][
        "n10_selection_class"
    ] = "INELIGIBLE"

    with pytest.raises(
        ValueError,
        match="selection mismatch",
    ):
        compile_one(
            report_payload=r,
        )


def test_enforcement_action_drift_fails_closed():
    r = report()

    r["decisions"][0][
        "n10_action"
    ] = "EVIDENCE_REQUIRED"

    with pytest.raises(
        ValueError,
        match="action mismatch",
    ):
        compile_one(
            report_payload=r,
        )


def test_candidate_final_equivalence_is_required():
    r = report()

    r["candidate_artifacts"][0][
        "candidate_final_authority_equivalent"
    ] = False

    with pytest.raises(
        ValueError,
        match="candidate/final authority equivalence",
    ):
        compile_one(
            report_payload=r,
        )


def test_role_aware_v2_enforcement_is_required():
    r = report()

    r["schema_version"] = (
        "alpha6-post-generation-nonobviousness-enforcement-v1"
    )

    with pytest.raises(
        ValueError,
        match="requires role-aware",
    ):
        compile_one(
            report_payload=r,
        )


def test_kept_original_decision_does_not_require_candidate_artifact():
    r = report()

    r["decisions"].insert(
        0,
        {
            "original_hypothesis_id":
                "hypothesis:already-eligible",

            "candidate_hypothesis_id":
                "",

            "final_hypothesis_id":
                "hypothesis:already-eligible",

            "alpha6_decision":
                "kept_original",

            "n10_required":
                False,

            "n10_selection_class":
                "PRE_GENERATION_GATE_ALREADY_PASSED",

            "kept":
                True,

            "reason_codes":
                [],
        },
    )

    items = compile_one(
        report_payload=r,
    )

    assert len(items) == 1
    assert (
        items[0].continuation_input_candidate_id
        == CANDIDATE
    )


def test_multiple_generated_candidates_are_independent():
    candidate2 = "hypothesis:candidate2"
    final2 = "hypothesis:final2"

    r = report()

    second_decision = deepcopy(
        decision(
            selection="ELIGIBLE",
            action="NO_ACTION",
            kept=True,
        )
    )

    second_decision[
        "candidate_hypothesis_id"
    ] = candidate2

    second_decision[
        "final_hypothesis_id"
    ] = final2

    r["decisions"].append(
        second_decision
    )

    second_artifact = deepcopy(
        artifact()
    )

    second_artifact[
        "candidate_id"
    ] = candidate2

    second_artifact[
        "final_hypothesis_id"
    ] = final2

    second_artifact[
        "selection_class"
    ] = "ELIGIBLE"

    second_artifact[
        "fallback_allowed"
    ] = True

    r["candidate_artifacts"].append(
        second_artifact
    )

    second_gate = gate(
        selection="ELIGIBLE",
        action="NO_ACTION",
        positive=True,
        fallback=True,
    )

    second_gate[
        "gates"
    ][0][
        "hypothesis_id"
    ] = candidate2

    items = (
        compile_post_generation_continuation_work_items(
            enforcement_report=r,
            gates_by_candidate_id={
                CANDIDATE:
                    gate(),

                candidate2:
                    second_gate,
            },
            continuation_depth=0,
        )
    )

    assert len(items) == 1

    assert (
        items[0].continuation_input_candidate_id
        == CANDIDATE
    )
