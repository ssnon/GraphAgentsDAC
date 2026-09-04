from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline_core.discovery.n10_post_generation_continuation_orchestration import (
    PostGenerationContinuationWorkItem,
)
from pipeline_core.discovery.nonobviousness_post_generation_production_gate_v2 import (
    build_nonobviousness_post_generation_production_gate_v2,
)
from scripts.discovery.run_n10_bounded_post_generation_continuation import (
    assert_second_alpha6_did_not_keep_h1,
    build_depth_one_terminal_audit,
    build_fresh_h2_n10_args,
    build_second_alpha6_args,
)


CANDIDATE = "hypothesis:h1"
H2 = "hypothesis:h2"


def work_item():
    return PostGenerationContinuationWorkItem(
        schema_version=(
            "n10-post-generation-continuation-work-item-v1"
        ),

        source_hypothesis_id="hypothesis:h0",

        continuation_input_candidate_id=CANDIDATE,

        continuation_input_final_hypothesis_id=(
            "hypothesis:h1-final"
        ),

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
        candidate_gate="/tmp/h1.candidate.json",
        production_gate="/tmp/h1.production.json",

        production_authority=False,
    )


def h2_candidate_gate(
    *,
    selection="CONDITIONAL",
    action="REFINE_NOVELTY_BEARING_SPECIFICATION",
    positive=False,
):
    allowed = bool(
        selection == "ELIGIBLE"
        and positive
    )

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
            "hypothesis_portfolio:h2",

        "source_query_plan_id":
            "literature_query_plan:h2",

        "gate_count":
            1,

        "candidate_fallback_allowed_count":
            int(
                allowed
            ),

        "candidate_fallback_blocked_count":
            int(
                not allowed
            ),

        "selection_counts": {
            "ELIGIBLE":
                int(
                    selection == "ELIGIBLE"
                ),

            "CONDITIONAL":
                int(
                    selection == "CONDITIONAL"
                ),

            "INELIGIBLE":
                int(
                    selection == "INELIGIBLE"
                ),
        },

        "gates": [
            {
                "hypothesis_id":
                    H2,

                "selection_class":
                    selection,

                "candidate_positive_nonobviousness_authority":
                    positive,

                "candidate_fallback_allowed":
                    allowed,

                "production_authority":
                    False,

                "action":
                    action,

                "base_aggregation_action":
                    action,

                "blocking_claim_ids":
                    [],

                "unresolved_claim_ids":
                    [],

                "unresolved_selection_role_claim_ids":
                    [],

                "structurally_unresolved_claim_ids":
                    [],

                "resolution_requirements":
                    [],

                "reason_codes":
                    [],
            }
        ],
    }


def test_second_alpha6_args_include_exact_diagnostic_reentry_inputs():
    args = build_second_alpha6_args(
        work_item=work_item(),

        lineage_projection_path=Path(
            "/tmp/projected_lineage.json"
        ),

        reentry_gate_path=Path(
            "/tmp/reentry_gate.json"
        ),

        dual_context=Path(
            "/tmp/dual.json"
        ),

        axis_plan=Path(
            "/tmp/axis.json"
        ),

        provider_plan=Path(
            "/tmp/provider.json"
        ),

        index_dir=Path(
            "/tmp/node_index"
        ),

        domain_profile="dac_her",

        model="model-a",

        critic_model="model-b",

        base_url="https://example.test/v1",

        api_key_env="OPENROUTER_API_KEY",

        results_per_query=12,

        output_prefix=Path(
            "/tmp/second"
        ),

        question_task_preservation_enforce=True,
    )

    joined = "\n".join(
        args
    )

    assert "--portfolio" in args
    assert "/tmp/h1.portfolio.json" in args

    assert "--lineage" in args
    assert "/tmp/projected_lineage.json" in args

    assert "--scientific-novelty-gate" in args
    assert "/tmp/reentry_gate.json" in args

    assert (
        "--n10-specification-repair-intake-shadow"
        in args
    )

    assert "/tmp/h1.intake.json" in args

    assert (
        "--n10-specification-repair-post-generation-gate"
        in args
    )

    assert "/tmp/h1.production.json" in args

    assert "--index-dir" in args
    assert "/tmp/node_index" in args

    assert (
        "--question-task-preservation-enforce"
        in args
    )

    assert (
        "--post-generation-scientific-novelty-enforce"
        not in joined
    )


def test_fresh_h2_n10_args_require_new_second_alpha6_outputs():
    args = build_fresh_h2_n10_args(
        second_alpha6_portfolio=Path(
            "/tmp/second.portfolio.json"
        ),

        hypothesis_context="/tmp/context.json",

        second_alpha6_report=Path(
            "/tmp/second.report.json"
        ),

        second_alpha6_external_dir=Path(
            "/tmp/second.external"
        ),

        provider_plan=Path(
            "/tmp/provider.json"
        ),

        domain_profile="dac_her",

        model="critic",

        base_url=None,

        api_key_env="OPENROUTER_API_KEY",

        results_per_query=12,

        work_dir=Path(
            "/tmp/h2_details"
        ),

        output_portfolio=Path(
            "/tmp/h2.portfolio.json"
        ),

        output_report=Path(
            "/tmp/h2.report.json"
        ),
    )

    assert "/tmp/second.portfolio.json" in args
    assert "/tmp/second.report.json" in args
    assert "/tmp/second.external" in args

    assert "/tmp/h2.portfolio.json" in args
    assert "/tmp/h2.report.json" in args

    assert args[
        args.index("--model") + 1
    ] == "critic"


def test_second_alpha6_cannot_keep_h1_original():
    report = SimpleNamespace(
        attempts=[
            SimpleNamespace(
                decision="kept_original"
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="may not preserve H1",
    ):
        assert_second_alpha6_did_not_keep_h1(
            report
        )


def test_second_alpha6_generated_repair_is_allowed():
    report = SimpleNamespace(
        attempts=[
            SimpleNamespace(
                decision="accepted_refinement"
            )
        ]
    )

    assert_second_alpha6_did_not_keep_h1(
        report
    )


def write_h2_enforcement(
    tmp_path,
    *,
    selection,
    action,
    positive,
):
    candidate = h2_candidate_gate(
        selection=selection,
        action=action,
        positive=positive,
    )

    production = (
        build_nonobviousness_post_generation_production_gate_v2(
            candidate_gate=candidate
        )
    )

    gate_path = (
        tmp_path
        / "production_gate.json"
    )

    gate_path.write_text(
        json.dumps(
            production
        ),
        encoding="utf-8",
    )

    kept = bool(
        selection == "ELIGIBLE"
        and positive
    )

    return {
        "decisions": [
            {
                "candidate_hypothesis_id":
                    H2,

                "n10_required":
                    True,

                "n10_selection_class":
                    selection,

                "n10_action":
                    action,

                "kept":
                    kept,
            }
        ],

        "candidate_artifacts": [
            {
                "candidate_id":
                    H2,

                "production_gate":
                    str(
                        gate_path
                    ),
            }
        ],
    }


def test_repairable_h2_is_terminal_at_depth_one(
    tmp_path,
):
    report = write_h2_enforcement(
        tmp_path,
        selection="CONDITIONAL",
        action=(
            "REFINE_NOVELTY_BEARING_SPECIFICATION"
        ),
        positive=False,
    )

    rows = build_depth_one_terminal_audit(
        enforcement_report=report
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row["allow_bounded_continuation"]
        is False
    )

    assert (
        row["terminal_due_to_depth_limit"]
        is True
    )

    assert (
        row["continuation_reason_code"]
        == "post_generation_specification_repair_depth_exhausted"
    )


def test_eligible_h2_is_not_continued_and_not_depth_terminal(
    tmp_path,
):
    report = write_h2_enforcement(
        tmp_path,
        selection="ELIGIBLE",
        action="NO_ACTION",
        positive=True,
    )

    rows = build_depth_one_terminal_audit(
        enforcement_report=report
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row["allow_bounded_continuation"]
        is False
    )

    assert (
        row["terminal_due_to_depth_limit"]
        is False
    )

    assert (
        row["positive_nonobviousness_authority"]
        is True
    )

    assert (
        row["fallback_allowed"]
        is True
    )


def test_ineligible_h2_is_not_continued(
    tmp_path,
):
    report = write_h2_enforcement(
        tmp_path,
        selection="INELIGIBLE",
        action="EVIDENCE_REQUIRED",
        positive=False,
    )

    rows = build_depth_one_terminal_audit(
        enforcement_report=report
    )

    assert len(rows) == 1

    assert (
        rows[0][
            "allow_bounded_continuation"
        ]
        is False
    )

    assert (
        rows[0][
            "terminal_due_to_depth_limit"
        ]
        is False
    )


def test_depth_audit_fails_without_exact_candidate_artifact(
    tmp_path,
):
    report = {
        "decisions": [
            {
                "candidate_hypothesis_id":
                    H2,
                "n10_required":
                    True,
            }
        ],
        "candidate_artifacts": [],
    }

    with pytest.raises(
        ValueError,
        match="lacks artifact audit",
    ):
        build_depth_one_terminal_audit(
            enforcement_report=report
        )
