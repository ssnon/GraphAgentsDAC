"""Deterministic H1 re-entry preparation for bounded N10 continuation.

This module performs no generation, retrieval, review, N9 adjudication,
scientific aggregation, or final portfolio selection.

It consumes one already-compiled bounded-continuation work item and prepares:

1. a candidate-local lineage projection from the frozen H0 lineage;
2. an Alpha6-original-fallback production envelope rebuilt from the exact
   role-aware candidate gate that produced the authoritative H1
   post-generation gate.

Re-entry is provenance/scope rebinding only.  It does not grant positive
authority to CONDITIONAL candidates and introduces no scientific premise.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pipeline_core.discovery.discovery_axis_contracts import (
    DiscoveryAxisPlan,
    DiscoveryAxisSynthesisReport,
)
from pipeline_core.discovery.hypothesis_contracts import (
    HypothesisPortfolio,
)
from pipeline_core.discovery.n10_post_generation_continuation_orchestration import (
    PostGenerationContinuationWorkItem,
)
from pipeline_core.discovery.n10_post_generation_continuation_policy import (
    REFINE_NOVELTY_BEARING_SPECIFICATION,
)
from pipeline_core.discovery.n10_post_generation_lineage_projection import (
    N10PostGenerationLineageProjection,
    build_n10_post_generation_lineage_projection,
)
from pipeline_core.discovery.nonobviousness_post_generation import (
    _validate_n10_gate,
)
from pipeline_core.discovery.nonobviousness_production_gate_v2 import (
    build_nonobviousness_production_gate_v2,
)


_WORK_ITEM_SCHEMA = (
    "n10-post-generation-continuation-work-item-v1"
)

_CANDIDATE_GATE_SCHEMA = (
    "scientific-novelty-fallback-gate-v2-candidate"
)

_PRODUCTION_GATE_SCHEMA = (
    "scientific-novelty-fallback-gate-v2"
)

_ORIGINAL_SCOPE = (
    "alpha6_original_fallback"
)

_POST_GENERATION_SCOPE = (
    "alpha6_post_generation_candidate"
)


@dataclass(
    frozen=True,
)
class PostGenerationReentryPackage:
    """Non-authoritative deterministic inputs for one second Alpha6 call."""

    schema_version: str

    work_item: PostGenerationContinuationWorkItem

    lineage_projection: N10PostGenerationLineageProjection

    reentry_gate: dict[str, Any]

    production_authority: bool = False
    scientific_evidence_authority: bool = False


def _validate_work_item(
    work_item: PostGenerationContinuationWorkItem,
) -> None:
    if not isinstance(
        work_item,
        PostGenerationContinuationWorkItem,
    ):
        raise ValueError(
            "re-entry requires a compiled continuation work item"
        )

    if (
        work_item.schema_version
        != _WORK_ITEM_SCHEMA
    ):
        raise ValueError(
            "unexpected continuation work-item schema"
        )

    if (
        work_item.production_authority
        is not False
    ):
        raise ValueError(
            "continuation work item must not carry production authority"
        )

    if (
        work_item.selection_class
        != "CONDITIONAL"
    ):
        raise ValueError(
            "re-entry work item must remain CONDITIONAL"
        )

    if (
        work_item.action
        != REFINE_NOVELTY_BEARING_SPECIFICATION
    ):
        raise ValueError(
            "re-entry work item has unsupported action"
        )

    if (
        work_item.current_depth
        != 0
        or work_item.next_depth
        != 1
    ):
        raise ValueError(
            "re-entry work item violates bounded depth contract"
        )

    if (
        work_item.fresh_post_generation_n10_required
        is not True
    ):
        raise ValueError(
            "re-entry work item must require fresh H2 N10"
        )


def _single_portfolio_hypothesis_id(
    portfolio: HypothesisPortfolio,
) -> str:
    if (
        len(
            portfolio.hypotheses
        )
        != 1
    ):
        raise ValueError(
            "continuation input portfolio must contain exactly one H1"
        )

    value = str(
        portfolio.hypotheses[0].hypothesis_id
        or ""
    ).strip()

    if not value:
        raise ValueError(
            "continuation input H1 lacks hypothesis identity"
        )

    return value


def _single_gate_row(
    gate: dict[str, Any],
    *,
    candidate_id: str,
) -> dict[str, Any]:
    rows = gate.get(
        "gates"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ValueError(
            "re-entry gate rows must be a list"
        )

    matches = [
        row
        for row in rows
        if (
            isinstance(
                row,
                dict,
            )
            and str(
                row.get(
                    "hypothesis_id"
                )
                or ""
            ).strip()
            == candidate_id
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "re-entry gate must contain exactly one row "
            "for continuation candidate "
            + candidate_id
        )

    if len(rows) != 1:
        raise ValueError(
            "candidate-local re-entry gate must contain "
            "exactly one hypothesis row"
        )

    return matches[0]


def build_post_generation_reentry_package(
    *,
    work_item:
        PostGenerationContinuationWorkItem,

    candidate_gate:
        dict[str, Any],

    post_generation_gate:
        dict[str, Any],

    source_lineage_report:
        DiscoveryAxisSynthesisReport,

    axis_plan:
        DiscoveryAxisPlan,

    continuation_portfolio:
        HypothesisPortfolio,

) -> PostGenerationReentryPackage:
    """Build one provenance-safe, non-authoritative H1 re-entry package."""

    _validate_work_item(
        work_item
    )

    candidate_id = (
        work_item
        .continuation_input_candidate_id
    )

    portfolio_hypothesis_id = (
        _single_portfolio_hypothesis_id(
            continuation_portfolio
        )
    )

    if (
        portfolio_hypothesis_id
        != candidate_id
    ):
        raise ValueError(
            "continuation source portfolio / work-item "
            "candidate identity mismatch"
        )

    if not isinstance(
        candidate_gate,
        dict,
    ):
        raise ValueError(
            "candidate gate must be an object"
        )

    if (
        candidate_gate.get(
            "schema_version"
        )
        != _CANDIDATE_GATE_SCHEMA
    ):
        raise ValueError(
            "unexpected continuation candidate-gate schema"
        )

    # Validate the already-authoritative H1 post-generation envelope first.
    post_row = _validate_n10_gate(
        candidate_id=candidate_id,
        gate=post_generation_gate,
    )

    if (
        post_generation_gate.get(
            "schema_version"
        )
        != _PRODUCTION_GATE_SCHEMA
    ):
        raise ValueError(
            "bounded re-entry requires role-aware post-generation v2"
        )

    if (
        post_generation_gate.get(
            "authority_scope"
        )
        != _POST_GENERATION_SCOPE
    ):
        raise ValueError(
            "source H1 gate is not post-generation authority"
        )

    if (
        post_row.get(
            "selection_class"
        )
        != work_item.selection_class
    ):
        raise ValueError(
            "work-item / H1 post-generation selection drift"
        )

    resolved_post_action = (
        post_row.get(
            "base_aggregation_action"
        )
        if (
            post_row.get(
                "base_aggregation_action"
            )
            is not None
        )
        else post_row.get(
            "action"
        )
    )

    if (
        resolved_post_action
        != work_item.action
    ):
        raise ValueError(
            "work-item / H1 post-generation action drift"
        )

    if (
        post_row.get(
            "positive_nonobviousness_authority"
        )
        is not False
        or post_row.get(
            "fallback_allowed"
        )
        is not False
    ):
        raise ValueError(
            "CONDITIONAL H1 gained authority before re-entry"
        )

    # Rebuild the original-Alpha6 authority envelope from the SAME frozen
    # candidate semantics.  This compiler performs no re-aggregation.
    reentry_gate = (
        build_nonobviousness_production_gate_v2(
            candidate_gate=deepcopy(
                candidate_gate
            )
        )
    )

    if (
        reentry_gate.get(
            "authority_scope"
        )
        != _ORIGINAL_SCOPE
    ):
        raise ValueError(
            "re-entry gate has unexpected authority scope"
        )

    reentry_row = _single_gate_row(
        reentry_gate,
        candidate_id=candidate_id,
    )

    # The post-generation wrapper is defined as the same production envelope
    # with authority_scope rebound.  Require exact equivalence after undoing
    # that one scope distinction.  This prevents stale/tampered candidate
    # gates from being substituted during continuation.
    expected_post_generation_gate = (
        deepcopy(
            reentry_gate
        )
    )

    expected_post_generation_gate[
        "authority_scope"
    ] = _POST_GENERATION_SCOPE

    if (
        expected_post_generation_gate
        != post_generation_gate
    ):
        raise ValueError(
            "candidate gate does not reproduce the exact authoritative "
            "H1 post-generation semantics"
        )

    if (
        reentry_row
        != post_row
    ):
        raise ValueError(
            "re-entry changed H1 scientific selection semantics"
        )

    if (
        reentry_row.get(
            "selection_class"
        )
        != "CONDITIONAL"
        or reentry_row.get(
            "positive_nonobviousness_authority"
        )
        is not False
        or reentry_row.get(
            "fallback_allowed"
        )
        is not False
    ):
        raise ValueError(
            "scope rebinding promoted CONDITIONAL authority"
        )

    lineage_projection = (
        build_n10_post_generation_lineage_projection(
            source_lineage_report=(
                source_lineage_report
            ),
            axis_plan=(
                axis_plan
            ),
            source_hypothesis_id=(
                work_item
                .source_hypothesis_id
            ),
            projected_portfolio=(
                continuation_portfolio
            ),
        )
    )

    if (
        lineage_projection
        .source_hypothesis_id
        != work_item.source_hypothesis_id
    ):
        raise ValueError(
            "lineage projection source H0 identity mismatch"
        )

    if (
        lineage_projection
        .projected_hypothesis_id
        != candidate_id
    ):
        raise ValueError(
            "lineage projection H1 identity mismatch"
        )

    if (
        lineage_projection
        .production_authority
        is not False
    ):
        raise ValueError(
            "lineage projection unexpectedly gained authority"
        )

    return (
        PostGenerationReentryPackage(
            schema_version=(
                "n10-post-generation-reentry-package-v1"
            ),
            work_item=(
                work_item
            ),
            lineage_projection=(
                lineage_projection
            ),
            reentry_gate=(
                reentry_gate
            ),
        )
    )
