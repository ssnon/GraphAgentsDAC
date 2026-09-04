"""Pure compilation of bounded post-generation N10 continuation work.

This module performs no generation, retrieval, review, lineage projection,
scope promotion, or portfolio mutation.

It consumes an already-authoritative role-aware post-generation N10
enforcement report plus the exact candidate gate payloads that produced that
report.  Eligibility is delegated to the frozen continuation policy.

The resulting work items are instructions only.  They grant no scientific or
production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pipeline_core.discovery.n10_post_generation_continuation_policy import (
    REFINE_NOVELTY_BEARING_SPECIFICATION,
    post_generation_continuation_directive_from_gate_row,
)
from pipeline_core.discovery.nonobviousness_post_generation import (
    _validate_n10_gate,
)


_ROLE_AWARE_ENFORCEMENT_SCHEMA = (
    "alpha6-post-generation-nonobviousness-enforcement-v2"
)

_ROLE_AWARE_GATE_SCHEMA = (
    "scientific-novelty-fallback-gate-v2"
)

_ROLE_AWARE_AUTHORITY_SOURCE = (
    "n10_role_aware_nonobviousness_v2"
)

_POST_GENERATION_SCOPE = (
    "alpha6_post_generation_candidate"
)

_ROLE_AWARE_POSITIVE_REQUIREMENT = (
    "ELIGIBLE_AND_ROLE_AWARE_POSITIVE_NONOBVIOUSNESS"
)

_GENERATED_ALPHA6_DECISIONS = {
    "accepted_refinement",
    "accepted_reaxis",
}


@dataclass(
    frozen=True,
)
class PostGenerationContinuationWorkItem:
    """One non-authoritative instruction for exactly one bounded H1 repair."""

    schema_version: str

    source_hypothesis_id: str
    continuation_input_candidate_id: str
    continuation_input_final_hypothesis_id: str

    alpha6_decision: str

    selection_class: str
    action: str

    current_depth: int
    next_depth: int

    continuation_reason_code: str
    fresh_post_generation_n10_required: bool

    source_portfolio: str
    hypothesis_context: str
    query_plan: str
    prior_art: str
    external_report: str

    intake_shadow: str
    full_shadow: str

    candidate_gate: str
    production_gate: str

    production_authority: bool = False


def _require_role_aware_enforcement_envelope(
    report: Mapping[str, Any],
) -> None:
    if not isinstance(
        report,
        Mapping,
    ):
        raise ValueError(
            "post-generation enforcement report must be a mapping"
        )

    if (
        report.get(
            "schema_version"
        )
        != _ROLE_AWARE_ENFORCEMENT_SCHEMA
    ):
        raise ValueError(
            "bounded continuation requires role-aware "
            "post-generation enforcement v2"
        )

    if (
        report.get(
            "production_authority"
        )
        is not True
    ):
        raise ValueError(
            "post-generation enforcement report lacks "
            "production authority"
        )

    if (
        report.get(
            "authority_source"
        )
        != _ROLE_AWARE_AUTHORITY_SOURCE
    ):
        raise ValueError(
            "unexpected post-generation N10 authority source"
        )

    if (
        report.get(
            "authority_scope"
        )
        != _POST_GENERATION_SCOPE
    ):
        raise ValueError(
            "unexpected post-generation N10 authority scope"
        )

    if (
        report.get(
            "positive_authority_requires"
        )
        != _ROLE_AWARE_POSITIVE_REQUIREMENT
    ):
        raise ValueError(
            "unexpected role-aware positive-authority contract"
        )

    if (
        report.get(
            "conditional_is_positive"
        )
        is not False
    ):
        raise ValueError(
            "CONDITIONAL must remain non-positive"
        )

    if (
        report.get(
            "absence_is_novelty"
        )
        is not False
    ):
        raise ValueError(
            "search-bounded absence must not become novelty"
        )

    if (
        report.get(
            "candidate_semantics_preserved"
        )
        is not True
    ):
        raise ValueError(
            "candidate semantics must remain preserved"
        )


def _nonempty_text(
    value: object,
    *,
    field: str,
) -> str:
    text = str(
        value
        or ""
    ).strip()

    if not text:
        raise ValueError(
            "continuation artifact missing "
            + field
        )

    return text


def _index_unique(
    rows: object,
    *,
    key: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(
        rows,
        list,
    ):
        raise ValueError(
            label
            + " must be a list"
        )

    result: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for row in rows:
        if not isinstance(
            row,
            Mapping,
        ):
            raise ValueError(
                label
                + " rows must be mappings"
            )

        value = _nonempty_text(
            row.get(
                key
            ),
            field=(
                label
                + "."
                + key
            ),
        )

        if value in result:
            raise ValueError(
                "duplicate "
                + label
                + " "
                + key
                + ": "
                + value
            )

        result[
            value
        ] = row

    return result


def compile_post_generation_continuation_work_items(
    *,
    enforcement_report: Mapping[str, Any],
    gates_by_candidate_id: Mapping[
        str,
        Mapping[str, Any],
    ],
    continuation_depth: int = 0,
) -> tuple[
    PostGenerationContinuationWorkItem,
    ...,
]:
    """Compile exact repair-eligible H1 work items.

    This function does not decide continuation eligibility itself.
    It validates authoritative provenance, then delegates eligibility to
    ``post_generation_continuation_directive_from_gate_row``.

    Every generated candidate represented by the enforcement report must have
    exactly one artifact row and exactly one supplied authoritative gate.
    Extra/missing candidates fail closed.
    """

    _require_role_aware_enforcement_envelope(
        enforcement_report
    )

    if not isinstance(
        gates_by_candidate_id,
        Mapping,
    ):
        raise ValueError(
            "gates_by_candidate_id must be a mapping"
        )

    # kept_original records have no generated candidate gate and may carry
    # an empty candidate_hypothesis_id.  Continuation compilation therefore
    # indexes only N10-required generated rows.  Those rows are validated
    # independently and must carry unique, non-empty candidate identities.
    generated_decisions: dict[
        str,
        Mapping[str, Any],
    ] = {}

    raw_decisions = enforcement_report.get(
        "decisions"
    )

    if not isinstance(
        raw_decisions,
        list,
    ):
        raise ValueError(
            "post-generation decisions must be a list"
        )

    for row in raw_decisions:
        if not isinstance(
            row,
            Mapping,
        ):
            raise ValueError(
                "post-generation decision row must be a mapping"
            )

        if (
            row.get(
                "n10_required"
            )
            is not True
        ):
            continue

        candidate_id = _nonempty_text(
            row.get(
                "candidate_hypothesis_id"
            ),
            field="decision.candidate_hypothesis_id",
        )

        if candidate_id in generated_decisions:
            raise ValueError(
                "duplicate generated post-generation decision: "
                + candidate_id
            )

        generated_decisions[
            candidate_id
        ] = row

    artifacts = _index_unique(
        enforcement_report.get(
            "candidate_artifacts"
        ),
        key="candidate_id",
        label="candidate artifact",
    )

    expected_ids = set(
        generated_decisions
    )

    if (
        set(
            artifacts
        )
        != expected_ids
    ):
        raise ValueError(
            "candidate artifact membership does not match "
            "generated N10-required decisions"
        )

    if (
        set(
            gates_by_candidate_id
        )
        != expected_ids
    ):
        raise ValueError(
            "candidate gate membership does not match "
            "generated N10-required decisions"
        )

    work_items = []

    for candidate_id, decision in generated_decisions.items():
        gate = gates_by_candidate_id[
            candidate_id
        ]

        if (
            gate.get(
                "schema_version"
            )
            != _ROLE_AWARE_GATE_SCHEMA
        ):
            raise ValueError(
                "bounded continuation requires role-aware "
                "candidate gate v2"
            )

        # Reuse the frozen authoritative post-generation validator rather
        # than copying gate validity semantics into this orchestrator.
        gate_row = _validate_n10_gate(
            candidate_id=candidate_id,
            gate=dict(
                gate
            ),
        )

        selection_class = _nonempty_text(
            gate_row.get(
                "selection_class"
            ),
            field="gate.selection_class",
        )

        if (
            decision.get(
                "n10_selection_class"
            )
            != selection_class
        ):
            raise ValueError(
                "enforcement decision / authoritative gate "
                "selection mismatch for "
                + candidate_id
            )

        if (
            decision.get(
                "n10_action"
            )
            != gate_row.get(
                "action"
            )
        ):
            raise ValueError(
                "enforcement decision / authoritative gate "
                "action mismatch for "
                + candidate_id
            )

        expected_kept = (
            selection_class
            == "ELIGIBLE"
        )

        if (
            decision.get(
                "kept"
            )
            is not expected_kept
        ):
            raise ValueError(
                "enforcement kept-state mismatch for "
                + candidate_id
            )

        artifact = artifacts[
            candidate_id
        ]

        final_id = _nonempty_text(
            decision.get(
                "final_hypothesis_id"
            ),
            field="decision.final_hypothesis_id",
        )

        if (
            _nonempty_text(
                artifact.get(
                    "final_hypothesis_id"
                ),
                field="artifact.final_hypothesis_id",
            )
            != final_id
        ):
            raise ValueError(
                "candidate artifact / enforcement final ID mismatch"
            )

        if (
            artifact.get(
                "candidate_final_authority_equivalent"
            )
            is not True
        ):
            raise ValueError(
                "candidate/final authority equivalence is not established"
            )

        if (
            artifact.get(
                "selection_class"
            )
            != selection_class
        ):
            raise ValueError(
                "candidate artifact selection drift"
            )

        if (
            artifact.get(
                "fallback_allowed"
            )
            is not gate_row.get(
                "fallback_allowed"
            )
        ):
            raise ValueError(
                "candidate artifact fallback drift"
            )

        directive = (
            post_generation_continuation_directive_from_gate_row(
                gate_row=gate_row,
                continuation_depth=continuation_depth,
            )
        )

        if not directive.allow_bounded_continuation:
            continue

        if (
            directive.next_depth
            is None
        ):
            raise ValueError(
                "allowed continuation lacks next depth"
            )

        if (
            directive.fresh_post_generation_n10_required
            is not True
        ):
            raise ValueError(
                "allowed continuation must require fresh post-generation N10"
            )

        resolved_action = (
            gate_row.get(
                "base_aggregation_action"
            )
            if (
                gate_row.get(
                    "base_aggregation_action"
                )
                is not None
            )
            else gate_row.get(
                "action"
            )
        )

        if (
            resolved_action
            != REFINE_NOVELTY_BEARING_SPECIFICATION
        ):
            raise ValueError(
                "continuation policy allowed unexpected action"
            )

        source_hypothesis_id = _nonempty_text(
            decision.get(
                "original_hypothesis_id"
            ),
            field="decision.original_hypothesis_id",
        )

        alpha6_decision = _nonempty_text(
            decision.get(
                "alpha6_decision"
            ),
            field="decision.alpha6_decision",
        )

        if (
            alpha6_decision
            not in _GENERATED_ALPHA6_DECISIONS
        ):
            raise ValueError(
                "continuation source is not an accepted "
                "Alpha6 generated candidate"
            )

        required_artifact_fields = {
            "source_portfolio":
                "source_portfolio",
            "hypothesis_context":
                "hypothesis_context",
            "query_plan":
                "query_plan",
            "prior_art":
                "prior_art",
            "external_report":
                "external_report",
            "intake_shadow":
                "intake_shadow",
            "full_shadow":
                "full_shadow",
            "candidate_gate":
                "candidate_gate",
            "production_gate":
                "production_gate",
        }

        paths = {
            target:
                _nonempty_text(
                    artifact.get(
                        source
                    ),
                    field=(
                        "artifact."
                        + source
                    ),
                )
            for (
                target,
                source,
            )
            in required_artifact_fields.items()
        }

        work_items.append(
            PostGenerationContinuationWorkItem(
                schema_version=(
                    "n10-post-generation-continuation-work-item-v1"
                ),

                source_hypothesis_id=(
                    source_hypothesis_id
                ),

                continuation_input_candidate_id=(
                    candidate_id
                ),

                continuation_input_final_hypothesis_id=(
                    final_id
                ),

                alpha6_decision=(
                    alpha6_decision
                ),

                selection_class=(
                    selection_class
                ),

                action=(
                    resolved_action
                ),

                current_depth=(
                    directive.current_depth
                ),

                next_depth=(
                    directive.next_depth
                ),

                continuation_reason_code=(
                    directive.reason_code
                ),

                fresh_post_generation_n10_required=(
                    directive
                    .fresh_post_generation_n10_required
                ),

                source_portfolio=(
                    paths[
                        "source_portfolio"
                    ]
                ),

                hypothesis_context=(
                    paths[
                        "hypothesis_context"
                    ]
                ),

                query_plan=(
                    paths[
                        "query_plan"
                    ]
                ),

                prior_art=(
                    paths[
                        "prior_art"
                    ]
                ),

                external_report=(
                    paths[
                        "external_report"
                    ]
                ),

                intake_shadow=(
                    paths[
                        "intake_shadow"
                    ]
                ),

                full_shadow=(
                    paths[
                        "full_shadow"
                    ]
                ),

                candidate_gate=(
                    paths[
                        "candidate_gate"
                    ]
                ),

                production_gate=(
                    paths[
                        "production_gate"
                    ]
                ),
            )
        )

    return tuple(
        work_items
    )
