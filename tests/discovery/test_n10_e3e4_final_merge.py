from __future__ import annotations

import json

import pytest

from pipeline_core.discovery.hypothesis_contracts import (
    FalsificationCriterion,
    HypothesisCard,
    HypothesisEvidenceProfile,
    HypothesisPortfolio,
    PredictedObservation,
)
from pipeline_core.discovery.n10_post_generation_final_merge import (
    AuthoritativePostN10Portfolio,
    merge_bounded_continuation_survivors,
    validate_authoritative_post_n10_portfolio,
)
from scripts.discovery.merge_n10_bounded_continuation_portfolio import (
    load_h2_authority_branches,
)


def card(
    hypothesis_id,
    *,
    source_context_id="ctx",
    source_context_sha256="ctxsha",
    source_report_id="report",
    source_report_sha256="reportsha",
):
    return HypothesisCard(
        hypothesis_id=(
            hypothesis_id
        ),

        domain_profile_id="dac_her",

        source_context_id=(
            source_context_id
        ),

        source_context_sha256=(
            source_context_sha256
        ),

        source_report_id=(
            source_report_id
        ),

        source_report_sha256=(
            source_report_sha256
        ),

        title="title",

        hypothesis_statement="statement",

        hypothesis_type="mechanistic_extension",

        premise_statement_ids=[
            "statement:1"
        ],

        inferential_bridge="bridge",

        predicted_observations=[
            PredictedObservation(
                observation_id=(
                    hypothesis_id
                    + ":obs"
                ),
                observable="observable",
                expected_direction="increase",
                rationale="rationale",
            )
        ],

        falsification_criteria=[
            FalsificationCriterion(
                criterion_id=(
                    hypothesis_id
                    + ":false"
                ),
                observable="observable",
                falsifying_outcome="outcome",
            )
        ],

        evidence_profile=(
            HypothesisEvidenceProfile(
                premise_count=1,
                gap_count=0,
                source_paper_count=1,
                candidate_premise_count=0,
                reported_premise_count=1,
                synthesis_premise_count=0,
            )
        ),
    )


def portfolio(
    portfolio_id,
    ids,
    *,
    source_context_id="ctx",
    source_context_sha256="ctxsha",
    source_report_id="report",
    source_report_sha256="reportsha",
):
    cards = [
        card(
            x,
            source_context_id=(
                source_context_id
            ),
            source_context_sha256=(
                source_context_sha256
            ),
            source_report_id=(
                source_report_id
            ),
            source_report_sha256=(
                source_report_sha256
            ),
        )
        for x in ids
    ]

    return HypothesisPortfolio(
        portfolio_id=(
            portfolio_id
        ),

        domain_profile_id="dac_her",

        source_context_id=(
            source_context_id
        ),

        source_context_sha256=(
            source_context_sha256
        ),

        source_report_id=(
            source_report_id
        ),

        source_report_sha256=(
            source_report_sha256
        ),

        hypotheses=(
            cards
        ),

        abstention_reason=(
            None
            if cards
            else "No survivor."
        ),
    )


def enforcement(
    p,
    *,
    generated_only,
):
    decisions = []

    for c in p.hypotheses:
        decisions.append(
            {
                "original_hypothesis_id":
                    "hypothesis:h0",

                "candidate_hypothesis_id":
                    (
                        c.hypothesis_id
                        if generated_only
                        else ""
                    ),

                "final_hypothesis_id":
                    c.hypothesis_id,

                "alpha6_decision":
                    (
                        "accepted_refinement"
                        if generated_only
                        else "kept_original"
                    ),

                "n10_required":
                    generated_only,

                "n10_selection_class":
                    (
                        "ELIGIBLE"
                        if generated_only
                        else "PRE_GENERATION_GATE_ALREADY_PASSED"
                    ),

                "n10_action":
                    (
                        "NO_ACTION"
                        if generated_only
                        else None
                    ),

                "kept":
                    True,

                "reason_codes":
                    [],
            }
        )

    return {
        "schema_version":
            "alpha6-post-generation-nonobviousness-enforcement-v2",

        "source_alpha6_portfolio_id":
            "source",

        "source_alpha6_refinement_report_id":
            "refinement",

        "final_portfolio_id":
            p.portfolio_id,

        "generated_candidate_gate_count":
            (
                len(
                    p.hypotheses
                )
                if generated_only
                else 0
            ),

        "alpha6_survivor_count":
            len(
                p.hypotheses
            ),

        "final_survivor_count":
            len(
                p.hypotheses
            ),

        "removed_by_post_generation_n10_count":
            0,

        "decisions":
            decisions,

        "production_authority":
            True,

        "authority_source":
            "n10_role_aware_nonobviousness_v2",

        "generated_candidate_requires_fresh_n10":
            True,

        "positive_authority_requires":
            "ELIGIBLE_AND_ROLE_AWARE_POSITIVE_NONOBVIOUSNESS",

        "authority_scope":
            "alpha6_post_generation_candidate",

        "conditional_is_positive":
            False,

        "absence_is_novelty":
            False,

        "candidate_semantics_preserved":
            True,
    }


def authoritative(
    p,
    *,
    generated_only,
    source_kind,
):
    return AuthoritativePostN10Portfolio(
        portfolio=p,
        enforcement_report=(
            enforcement(
                p,
                generated_only=(
                    generated_only
                ),
            )
        ),
        source_kind=(
            source_kind
        ),
    )


def test_zero_h2_survivors_preserves_first_portfolio_exactly():
    first = portfolio(
        "portfolio:first",
        [
            "hypothesis:first"
        ],
    )

    empty_h2 = portfolio(
        "portfolio:h2-empty",
        [],
    )

    merged, audit = (
        merge_bounded_continuation_survivors(
            first_pass=(
                authoritative(
                    first,
                    generated_only=False,
                    source_kind="first",
                )
            ),
            h2_branches=[
                authoritative(
                    empty_h2,
                    generated_only=True,
                    source_kind="h2",
                )
            ],
        )
    )

    assert merged is first
    assert (
        merged.portfolio_id
        == "portfolio:first"
    )

    assert (
        audit[
            "first_pass_portfolio_preserved_exactly"
        ]
        is True
    )

    assert (
        audit[
            "bounded_h2_survivor_count"
        ]
        == 0
    )


def test_authorized_h2_survivor_is_merged():
    first = portfolio(
        "portfolio:first",
        [
            "hypothesis:first"
        ],
    )

    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
    )

    merged, audit = (
        merge_bounded_continuation_survivors(
            first_pass=(
                authoritative(
                    first,
                    generated_only=False,
                    source_kind="first",
                )
            ),
            h2_branches=[
                authoritative(
                    h2,
                    generated_only=True,
                    source_kind="h2",
                )
            ],
        )
    )

    assert [
        x.hypothesis_id
        for x in merged.hypotheses
    ] == [
        "hypothesis:first",
        "hypothesis:h2",
    ]

    assert (
        merged.portfolio_id
        != first.portfolio_id
    )

    assert audit[
        "bounded_h2_survivor_ids"
    ] == [
        "hypothesis:h2"
    ]

    assert audit[
        "selection_authority"
    ] is False


def test_h2_report_portfolio_id_mismatch_fails_closed():
    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
    )

    report = enforcement(
        h2,
        generated_only=True,
    )

    report[
        "final_portfolio_id"
    ] = "portfolio:wrong"

    with pytest.raises(
        ValueError,
        match="portfolio ID mismatch",
    ):
        validate_authoritative_post_n10_portfolio(
            portfolio=h2,
            enforcement_report=report,
            require_generated_only=True,
        )


def test_h2_cannot_contain_kept_original_authority():
    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
    )

    report = enforcement(
        h2,
        generated_only=True,
    )

    report["decisions"][0][
        "n10_required"
    ] = False

    report["decisions"][0][
        "alpha6_decision"
    ] = "kept_original"

    with pytest.raises(
        ValueError,
        match="may not contain kept_original",
    ):
        validate_authoritative_post_n10_portfolio(
            portfolio=h2,
            enforcement_report=report,
            require_generated_only=True,
        )


def test_noneligible_generated_survivor_cannot_be_merged():
    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
    )

    report = enforcement(
        h2,
        generated_only=True,
    )

    report["decisions"][0][
        "n10_selection_class"
    ] = "CONDITIONAL"

    with pytest.raises(
        ValueError,
        match="is not ELIGIBLE",
    ):
        validate_authoritative_post_n10_portfolio(
            portfolio=h2,
            enforcement_report=report,
            require_generated_only=True,
        )


def test_different_source_provenance_cannot_be_merged():
    first = portfolio(
        "portfolio:first",
        [
            "hypothesis:first"
        ],
    )

    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
        source_context_sha256="different",
    )

    with pytest.raises(
        ValueError,
        match="different source provenance",
    ):
        merge_bounded_continuation_survivors(
            first_pass=(
                authoritative(
                    first,
                    generated_only=False,
                    source_kind="first",
                )
            ),
            h2_branches=[
                authoritative(
                    h2,
                    generated_only=True,
                    source_kind="h2",
                )
            ],
        )


def test_duplicate_identity_across_first_and_h2_fails_closed():
    first = portfolio(
        "portfolio:first",
        [
            "hypothesis:same"
        ],
    )

    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:same"
        ],
    )

    with pytest.raises(
        ValueError,
        match="duplicate hypothesis identity",
    ):
        merge_bounded_continuation_survivors(
            first_pass=(
                authoritative(
                    first,
                    generated_only=False,
                    source_kind="first",
                )
            ),
            h2_branches=[
                authoritative(
                    h2,
                    generated_only=True,
                    source_kind="h2",
                )
            ],
        )


def test_continuation_report_must_remain_non_authoritative(
    tmp_path,
):
    continuation = {
        "schema_version":
            "n10-bounded-post-generation-continuation-run-v1",

        "continuation_work_item_count":
            0,

        "branches":
            [],

        "production_authority":
            True,

        "final_portfolio_selection_authority":
            False,

        "scientific_evidence_authority":
            False,

        "max_continuation_depth":
            1,

        "fresh_h2_n10_required":
            True,
    }

    with pytest.raises(
        ValueError,
        match="must not carry production authority",
    ):
        load_h2_authority_branches(
            continuation_report=(
                continuation
            )
        )


def test_continuation_branch_declared_survivor_count_is_checked(
    tmp_path,
):
    h2 = portfolio(
        "portfolio:h2",
        [
            "hypothesis:h2"
        ],
    )

    h2_path = (
        tmp_path
        / "h2.json"
    )

    report_path = (
        tmp_path
        / "report.json"
    )

    h2_path.write_text(
        h2.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    report_path.write_text(
        json.dumps(
            enforcement(
                h2,
                generated_only=True,
            )
        ),
        encoding="utf-8",
    )

    continuation = {
        "schema_version":
            "n10-bounded-post-generation-continuation-run-v1",

        "continuation_work_item_count":
            1,

        "branches": [
            {
                "h1_candidate_id":
                    "hypothesis:h1",

                "continuation_depth":
                    1,

                "fresh_h2_n10_portfolio":
                    str(
                        h2_path
                    ),

                "fresh_h2_n10_report":
                    str(
                        report_path
                    ),

                "fresh_h2_n10_survivor_count":
                    0,
            }
        ],

        "production_authority":
            False,

        "final_portfolio_selection_authority":
            False,

        "scientific_evidence_authority":
            False,

        "max_continuation_depth":
            1,

        "fresh_h2_n10_required":
            True,
    }

    with pytest.raises(
        ValueError,
        match="H2 survivor count mismatch",
    ):
        load_h2_authority_branches(
            continuation_report=(
                continuation
            )
        )
