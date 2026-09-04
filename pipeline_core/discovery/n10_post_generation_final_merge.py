"""Deterministic final merge for bounded post-generation N10 continuation.

This module performs no generation, retrieval, review, N9/N10 adjudication,
semantic comparison, or scientific inference.

It combines only portfolios that have already been filtered by authoritative
role-aware post-generation N10 enforcement.

The merge itself grants no scientific or selection authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pipeline_core.discovery.hypothesis_contracts import (
    HypothesisPortfolio,
)


_ENFORCEMENT_SCHEMA = (
    "alpha6-post-generation-nonobviousness-enforcement-v2"
)

_AUTHORITY_SOURCE = (
    "n10_role_aware_nonobviousness_v2"
)

_AUTHORITY_SCOPE = (
    "alpha6_post_generation_candidate"
)

_POSITIVE_REQUIREMENT = (
    "ELIGIBLE_AND_ROLE_AWARE_POSITIVE_NONOBVIOUSNESS"
)


@dataclass(
    frozen=True,
)
class AuthoritativePostN10Portfolio:
    portfolio: HypothesisPortfolio
    enforcement_report: Mapping[str, Any]
    source_kind: str


def _stable_id(
    prefix: str,
    *parts: object,
    length: int = 20,
) -> str:
    raw = "|".join(
        str(part)
        for part in parts
    ).encode(
        "utf-8"
    )

    return (
        f"{prefix}:"
        f"{hashlib.sha256(raw).hexdigest()[:length]}"
    )


def _validate_enforcement_envelope(
    report: Mapping[str, Any],
) -> None:
    if not isinstance(
        report,
        Mapping,
    ):
        raise ValueError(
            "post-N10 enforcement report must be a mapping"
        )

    if (
        report.get(
            "schema_version"
        )
        != _ENFORCEMENT_SCHEMA
    ):
        raise ValueError(
            "final merge requires role-aware "
            "post-generation enforcement v2"
        )

    if (
        report.get(
            "production_authority"
        )
        is not True
    ):
        raise ValueError(
            "post-N10 enforcement lacks production authority"
        )

    if (
        report.get(
            "authority_source"
        )
        != _AUTHORITY_SOURCE
    ):
        raise ValueError(
            "unexpected post-N10 authority source"
        )

    if (
        report.get(
            "authority_scope"
        )
        != _AUTHORITY_SCOPE
    ):
        raise ValueError(
            "unexpected post-N10 authority scope"
        )

    if (
        report.get(
            "positive_authority_requires"
        )
        != _POSITIVE_REQUIREMENT
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
            "CONDITIONAL must not be positive authority"
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


def validate_authoritative_post_n10_portfolio(
    *,
    portfolio: HypothesisPortfolio,
    enforcement_report: Mapping[str, Any],
    require_generated_only: bool,
) -> dict[str, Any]:
    """Validate exact portfolio membership against one N10 authority report."""

    _validate_enforcement_envelope(
        enforcement_report
    )

    if (
        enforcement_report.get(
            "final_portfolio_id"
        )
        != portfolio.portfolio_id
    ):
        raise ValueError(
            "post-N10 enforcement / portfolio ID mismatch"
        )

    decisions = enforcement_report.get(
        "decisions"
    )

    if not isinstance(
        decisions,
        list,
    ):
        raise ValueError(
            "post-N10 enforcement decisions must be a list"
        )

    kept_rows = []

    for row in decisions:
        if not isinstance(
            row,
            Mapping,
        ):
            raise ValueError(
                "post-N10 enforcement decision must be an object"
            )

        kept = row.get(
            "kept"
        )

        if not isinstance(
            kept,
            bool,
        ):
            raise ValueError(
                "post-N10 enforcement kept must be boolean"
            )

        if (
            require_generated_only
            and row.get(
                "n10_required"
            )
            is not True
        ):
            raise ValueError(
                "bounded H2 authority report may not contain "
                "kept_original/non-generated survivor decisions"
            )

        if not kept:
            continue

        final_id = str(
            row.get(
                "final_hypothesis_id"
            )
            or ""
        ).strip()

        if not final_id:
            raise ValueError(
                "kept post-N10 decision missing final_hypothesis_id"
            )

        if (
            row.get(
                "n10_required"
            )
            is True
        ):
            if (
                row.get(
                    "n10_selection_class"
                )
                != "ELIGIBLE"
            ):
                raise ValueError(
                    "kept generated candidate is not ELIGIBLE"
                )

        elif require_generated_only:
            raise ValueError(
                "H2 survivor bypassed fresh N10"
            )

        kept_rows.append(
            row
        )

    kept_ids = [
        str(
            row[
                "final_hypothesis_id"
            ]
        )
        for row in kept_rows
    ]

    if (
        len(
            kept_ids
        )
        != len(
            set(
                kept_ids
            )
        )
    ):
        raise ValueError(
            "duplicate kept final hypothesis identity "
            "in post-N10 enforcement report"
        )

    portfolio_ids = [
        card.hypothesis_id
        for card in portfolio.hypotheses
    ]

    if (
        len(
            portfolio_ids
        )
        != len(
            set(
                portfolio_ids
            )
        )
    ):
        raise ValueError(
            "duplicate hypothesis identity in post-N10 portfolio"
        )

    if set(
        portfolio_ids
    ) != set(
        kept_ids
    ):
        raise ValueError(
            "post-N10 authoritative kept membership "
            "does not match portfolio membership"
        )

    declared_count = enforcement_report.get(
        "final_survivor_count"
    )

    if (
        not isinstance(
            declared_count,
            int,
        )
        or declared_count
        != len(
            portfolio.hypotheses
        )
    ):
        raise ValueError(
            "post-N10 final survivor count mismatch"
        )

    return {
        "portfolio_id":
            portfolio.portfolio_id,

        "survivor_count":
            len(
                portfolio.hypotheses
            ),

        "survivor_ids":
            portfolio_ids,

        "require_generated_only":
            require_generated_only,

        "production_authority_validated":
            True,
    }


def _provenance_projection(
    portfolio: HypothesisPortfolio,
) -> tuple[
    str,
    str,
    str,
    str,
    str,
]:
    return (
        portfolio.domain_profile_id,
        portfolio.source_context_id,
        portfolio.source_context_sha256,
        portfolio.source_report_id,
        portfolio.source_report_sha256,
    )


def merge_bounded_continuation_survivors(
    *,
    first_pass:
        AuthoritativePostN10Portfolio,

    h2_branches:
        Sequence[
            AuthoritativePostN10Portfolio
        ],

) -> tuple[
    HypothesisPortfolio,
    dict[str, Any],
]:
    """Merge first-pass and independently fresh-N10-authorized H2 survivors."""

    first_audit = (
        validate_authoritative_post_n10_portfolio(
            portfolio=(
                first_pass.portfolio
            ),
            enforcement_report=(
                first_pass.enforcement_report
            ),
            require_generated_only=False,
        )
    )

    h2_audits = []

    for branch in h2_branches:
        h2_audits.append(
            validate_authoritative_post_n10_portfolio(
                portfolio=(
                    branch.portfolio
                ),
                enforcement_report=(
                    branch.enforcement_report
                ),
                require_generated_only=True,
            )
        )

    reference_provenance = (
        _provenance_projection(
            first_pass.portfolio
        )
    )

    for branch in h2_branches:
        if (
            _provenance_projection(
                branch.portfolio
            )
            != reference_provenance
        ):
            raise ValueError(
                "cannot merge post-N10 portfolios "
                "from different source provenance"
            )

    h2_cards = [
        card
        for branch in h2_branches
        for card in branch.portfolio.hypotheses
    ]

    # No bounded continuation survivor means absolutely no change to the
    # already-authoritative first-pass portfolio, including portfolio ID and
    # abstention reason.
    if not h2_cards:
        audit = {
            "schema_version":
                "n10-bounded-continuation-final-merge-audit-v1",

            "first_pass":
                first_audit,

            "h2_branches":
                h2_audits,

            "bounded_h2_survivor_count":
                0,

            "final_survivor_count":
                len(
                    first_pass
                    .portfolio
                    .hypotheses
                ),

            "final_portfolio_id":
                first_pass
                .portfolio
                .portfolio_id,

            "first_pass_portfolio_preserved_exactly":
                True,

            "production_authority":
                False,

            "scientific_evidence_authority":
                False,

            "selection_authority":
                False,

            "source_authority_validated":
                True,
        }

        return (
            first_pass.portfolio,
            audit,
        )

    cards = [
        *first_pass.portfolio.hypotheses,
        *h2_cards,
    ]

    ids = [
        card.hypothesis_id
        for card in cards
    ]

    if (
        len(
            ids
        )
        != len(
            set(
                ids
            )
        )
    ):
        raise ValueError(
            "duplicate hypothesis identity across "
            "first-pass and bounded H2 survivors"
        )

    portfolio_id = _stable_id(
        "hypothesis_portfolio",
        first_pass.portfolio.domain_profile_id,
        first_pass.portfolio.source_context_sha256,
        *ids,
        "",
    )

    merged = HypothesisPortfolio(
        portfolio_id=(
            portfolio_id
        ),

        domain_profile_id=(
            first_pass
            .portfolio
            .domain_profile_id
        ),

        source_context_id=(
            first_pass
            .portfolio
            .source_context_id
        ),

        source_context_sha256=(
            first_pass
            .portfolio
            .source_context_sha256
        ),

        source_report_id=(
            first_pass
            .portfolio
            .source_report_id
        ),

        source_report_sha256=(
            first_pass
            .portfolio
            .source_report_sha256
        ),

        hypotheses=(
            cards
        ),

        abstention_reason=None,
    )

    audit = {
        "schema_version":
            "n10-bounded-continuation-final-merge-audit-v1",

        "first_pass":
            first_audit,

        "h2_branches":
            h2_audits,

        "bounded_h2_survivor_count":
            len(
                h2_cards
            ),

        "bounded_h2_survivor_ids":
            [
                card.hypothesis_id
                for card in h2_cards
            ],

        "final_survivor_count":
            len(
                merged.hypotheses
            ),

        "final_portfolio_id":
            merged.portfolio_id,

        "first_pass_portfolio_preserved_exactly":
            False,

        "production_authority":
            False,

        "scientific_evidence_authority":
            False,

        "selection_authority":
            False,

        "source_authority_validated":
            True,

        "merge_rule":
            (
                "first_pass_authorized_survivors_union_"
                "fresh_h2_n10_authorized_survivors"
            ),
    }

    return (
        merged,
        audit,
    )
