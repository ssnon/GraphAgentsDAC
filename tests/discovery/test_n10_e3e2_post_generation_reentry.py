from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

import pipeline_core.discovery.n10_post_generation_reentry as reentry_module

from pipeline_core.discovery.n10_post_generation_continuation_orchestration import (
    PostGenerationContinuationWorkItem,
)
from pipeline_core.discovery.nonobviousness_post_generation_production_gate_v2 import (
    build_nonobviousness_post_generation_production_gate_v2,
)


SOURCE = "hypothesis:h0"
CANDIDATE = "hypothesis:h1"
FINAL = "hypothesis:h1-final"


def work_item():
    return PostGenerationContinuationWorkItem(
        schema_version=(
            "n10-post-generation-continuation-work-item-v1"
        ),

        source_hypothesis_id=SOURCE,
        continuation_input_candidate_id=CANDIDATE,
        continuation_input_final_hypothesis_id=FINAL,

        alpha6_decision="accepted_refinement",

        selection_class="CONDITIONAL",
        action="REFINE_NOVELTY_BEARING_SPECIFICATION",

        current_depth=0,
        next_depth=1,

        continuation_reason_code=(
            "allow_one_post_generation_"
            "novelty_specification_repair"
        ),

        fresh_post_generation_n10_required=True,

        source_portfolio="/tmp/h1.portfolio.json",
        hypothesis_context="/tmp/context.json",
        query_plan="/tmp/h1.plan.json",
        prior_art="/tmp/h1.prior.json",
        external_report="/tmp/h1.report.json",

        intake_shadow="/tmp/h1.intake.json",
        full_shadow="/tmp/h1.full.json",

        candidate_gate="/tmp/h1.candidate_gate.json",
        production_gate="/tmp/h1.production_gate.json",

        production_authority=False,
    )


def candidate_gate():
    return {
        "schema_version":
            "scientific-novelty-fallback-gate-v2-candidate",

        "candidate_only":
            True,

        "production_authority":
            False,

        "alpha6_original_fallback_authority":
            False,

        "authority_policy":
            "none_candidate_only",

        "source_portfolio_id":
            "hypothesis_portfolio:h1",

        "source_query_plan_id":
            "literature_query_plan:h1",

        "gate_count":
            1,

        "candidate_fallback_allowed_count":
            0,

        "candidate_fallback_blocked_count":
            1,

        "selection_counts": {
            "ELIGIBLE": 0,
            "CONDITIONAL": 1,
            "INELIGIBLE": 0,
        },

        "gates": [
            {
                "hypothesis_id":
                    CANDIDATE,

                "selection_class":
                    "CONDITIONAL",

                "candidate_positive_nonobviousness_authority":
                    False,

                "candidate_fallback_allowed":
                    False,

                "production_authority":
                    False,

                "action":
                    "REFINE_NOVELTY_BEARING_SPECIFICATION",

                "base_aggregation_action":
                    "REFINE_NOVELTY_BEARING_SPECIFICATION",

                "blocking_claim_ids":
                    [],

                "unresolved_claim_ids":
                    ["claim:1"],

                "unresolved_selection_role_claim_ids":
                    ["claim:1"],

                "structurally_unresolved_claim_ids":
                    [],

                "resolution_requirements":
                    ["required_bridge"],

                "reason_codes":
                    ["novelty_bearing_specification_incomplete"],
            }
        ],
    }


def post_gate(candidate=None):
    return (
        build_nonobviousness_post_generation_production_gate_v2(
            candidate_gate=(
                deepcopy(
                    candidate
                    if candidate is not None
                    else candidate_gate()
                )
            )
        )
    )


def portfolio(candidate_id=CANDIDATE):
    return SimpleNamespace(
        hypotheses=[
            SimpleNamespace(
                hypothesis_id=candidate_id
            )
        ]
    )


def install_lineage_stub(
    monkeypatch,
):
    calls = []

    def fake_builder(
        *,
        source_lineage_report,
        axis_plan,
        source_hypothesis_id,
        projected_portfolio,
    ):
        calls.append(
            {
                "source_lineage_report":
                    source_lineage_report,

                "axis_plan":
                    axis_plan,

                "source_hypothesis_id":
                    source_hypothesis_id,

                "projected_portfolio":
                    projected_portfolio,
            }
        )

        return SimpleNamespace(
            source_hypothesis_id=(
                source_hypothesis_id
            ),
            projected_hypothesis_id=(
                projected_portfolio
                .hypotheses[0]
                .hypothesis_id
            ),
            production_authority=False,
        )

    monkeypatch.setattr(
        reentry_module,
        "build_n10_post_generation_lineage_projection",
        fake_builder,
    )

    return calls


def build(
    monkeypatch,
    *,
    item=None,
    candidate=None,
    post=None,
    candidate_portfolio=None,
):
    calls = install_lineage_stub(
        monkeypatch
    )

    candidate = (
        candidate
        if candidate is not None
        else candidate_gate()
    )

    post = (
        post
        if post is not None
        else post_gate(candidate)
    )

    result = (
        reentry_module
        .build_post_generation_reentry_package(
            work_item=(
                item
                if item is not None
                else work_item()
            ),
            candidate_gate=candidate,
            post_generation_gate=post,
            source_lineage_report=(
                SimpleNamespace()
            ),
            axis_plan=(
                SimpleNamespace()
            ),
            continuation_portfolio=(
                candidate_portfolio
                if candidate_portfolio is not None
                else portfolio()
            ),
        )
    )

    return (
        result,
        calls,
    )


def test_reentry_rebinds_scope_only_and_preserves_conditional(
    monkeypatch,
):
    package, calls = build(
        monkeypatch
    )

    gate = package.reentry_gate

    assert (
        gate["authority_scope"]
        == "alpha6_original_fallback"
    )

    assert gate["production_authority"] is True

    assert len(gate["gates"]) == 1

    row = gate["gates"][0]

    assert row["hypothesis_id"] == CANDIDATE

    assert row["selection_class"] == "CONDITIONAL"

    assert (
        row["positive_nonobviousness_authority"]
        is False
    )

    assert row["fallback_allowed"] is False

    assert (
        row["action"]
        == "REFINE_NOVELTY_BEARING_SPECIFICATION"
    )

    assert (
        row["unresolved_claim_ids"]
        == ["claim:1"]
    )

    assert package.production_authority is False
    assert package.scientific_evidence_authority is False

    assert len(calls) == 1
    assert calls[0]["source_hypothesis_id"] == SOURCE


def test_reentry_gate_exactly_reconstructs_post_gate_except_scope(
    monkeypatch,
):
    candidate = candidate_gate()
    original_post = post_gate(candidate)

    package, _ = build(
        monkeypatch,
        candidate=candidate,
        post=original_post,
    )

    reconstructed = deepcopy(
        package.reentry_gate
    )

    reconstructed[
        "authority_scope"
    ] = "alpha6_post_generation_candidate"

    assert reconstructed == original_post


def test_candidate_source_portfolio_must_bind_exact_h1(
    monkeypatch,
):
    install_lineage_stub(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="candidate identity mismatch",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=work_item(),
            candidate_gate=candidate_gate(),
            post_generation_gate=post_gate(),
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(
                "hypothesis:wrong"
            ),
        )


def test_tampered_candidate_gate_cannot_replace_authoritative_h1_semantics(
    monkeypatch,
):
    install_lineage_stub(
        monkeypatch
    )

    original = candidate_gate()
    authoritative_post = post_gate(
        original
    )

    tampered = deepcopy(
        original
    )

    tampered[
        "gates"
    ][0][
        "resolution_requirements"
    ] = [
        "falsification_condition"
    ]

    with pytest.raises(
        ValueError,
        match="does not reproduce the exact authoritative",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=work_item(),
            candidate_gate=tampered,
            post_generation_gate=authoritative_post,
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )


def test_post_generation_gate_selection_drift_fails_closed(
    monkeypatch,
):
    install_lineage_stub(
        monkeypatch
    )

    p = post_gate()

    p[
        "gates"
    ][0][
        "selection_class"
    ] = "INELIGIBLE"

    with pytest.raises(
        ValueError,
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=work_item(),
            candidate_gate=candidate_gate(),
            post_generation_gate=p,
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )


def test_work_item_cannot_carry_production_authority(
    monkeypatch,
):
    install_lineage_stub(
        monkeypatch
    )

    item = work_item()

    item = PostGenerationContinuationWorkItem(
        **{
            **item.__dict__,
            "production_authority": True,
        }
    )

    with pytest.raises(
        ValueError,
        match="must not carry production authority",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=item,
            candidate_gate=candidate_gate(),
            post_generation_gate=post_gate(),
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )


def test_only_depth_zero_to_one_work_item_can_reenter(
    monkeypatch,
):
    install_lineage_stub(
        monkeypatch
    )

    item = work_item()

    item = PostGenerationContinuationWorkItem(
        **{
            **item.__dict__,
            "current_depth": 1,
            "next_depth": 2,
        }
    )

    with pytest.raises(
        ValueError,
        match="bounded depth contract",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=item,
            candidate_gate=candidate_gate(),
            post_generation_gate=post_gate(),
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )


def test_lineage_projection_source_and_target_are_checked(
    monkeypatch,
):
    def bad_builder(**kwargs):
        return SimpleNamespace(
            source_hypothesis_id="hypothesis:wrong-source",
            projected_hypothesis_id=CANDIDATE,
            production_authority=False,
        )

    monkeypatch.setattr(
        reentry_module,
        "build_n10_post_generation_lineage_projection",
        bad_builder,
    )

    with pytest.raises(
        ValueError,
        match="source H0 identity mismatch",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=work_item(),
            candidate_gate=candidate_gate(),
            post_generation_gate=post_gate(),
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )


def test_lineage_projection_must_remain_non_authoritative(
    monkeypatch,
):
    def bad_builder(**kwargs):
        return SimpleNamespace(
            source_hypothesis_id=SOURCE,
            projected_hypothesis_id=CANDIDATE,
            production_authority=True,
        )

    monkeypatch.setattr(
        reentry_module,
        "build_n10_post_generation_lineage_projection",
        bad_builder,
    )

    with pytest.raises(
        ValueError,
        match="unexpectedly gained authority",
    ):
        reentry_module.build_post_generation_reentry_package(
            work_item=work_item(),
            candidate_gate=candidate_gate(),
            post_generation_gate=post_gate(),
            source_lineage_report=SimpleNamespace(),
            axis_plan=SimpleNamespace(),
            continuation_portfolio=portfolio(),
        )
