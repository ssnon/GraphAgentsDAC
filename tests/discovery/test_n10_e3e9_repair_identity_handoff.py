from __future__ import annotations

from pipeline_core.discovery.n10_specification_repair_context import (
    N10SpecificationRepairClaimDiagnostic,
    N10SpecificationRepairContext,
)
from pipeline_core.discovery.novelty_refinement_prompt import (
    _render_specification_repair_diagnosis,
)


def _diagnostic(
    *,
    identity: list[str] | None = None,
) -> N10SpecificationRepairClaimDiagnostic:
    kwargs = {
        "claim_id":
            "external_novelty_claim:test",

        "claim_text":
            "Metal coupling moderates the descriptor relation.",

        "missing_fields":
            ["required_bridge"],

        "reason_codes":
            [
                "atomic_residue_under_specified",
                "missing_required_bridge",
            ],
    }

    if identity is not None:
        kwargs[
            "prior_art_identity_terms"
        ] = identity

    return (
        N10SpecificationRepairClaimDiagnostic(
            **kwargs
        )
    )


def _render(
    diagnostic: N10SpecificationRepairClaimDiagnostic,
) -> str:
    # Renderer consumes only repair_action + diagnostics.
    context = N10SpecificationRepairContext.model_construct(
        repair_action=(
            "REFINE_NOVELTY_BEARING_SPECIFICATION"
        ),
        claim_diagnostics=[
            diagnostic
        ],
    )

    return (
        _render_specification_repair_diagnosis(
            context
        )
    )


def test_historical_diagnostic_without_identity_remains_valid():
    row = _diagnostic()

    assert (
        row.prior_art_identity_terms
        == []
    )


def test_identity_metadata_is_preserved_exactly():
    terms = [
        "metal metal electronic coupling",
        "bonding antibonding distribution",
    ]

    row = _diagnostic(
        identity=terms
    )

    assert (
        row.prior_art_identity_terms
        == terms
    )


def test_prompt_renders_identity_as_diagnostic_reference_only():
    text = _render(
        _diagnostic(
            identity=[
                "metal metal electronic coupling"
            ]
        )
    )

    assert (
        'branch_identity_terms: '
        '["metal metal electronic coupling"]'
        in text
    )

    assert (
        "NOT scientific evidence"
        in text
    )

    assert (
        "NOT a positive premise"
        in text
    )

    assert (
        "do not by themselves justify any missing field"
        in text
    )

    assert (
        "Do not infer a new relation, mechanism, direction, "
        "condition, regime, or bridge from these labels themselves."
        in text
    )


def test_prompt_does_not_expose_broader_atomic_metadata():
    text = _render(
        _diagnostic(
            identity=[
                "metal metal electronic coupling"
            ]
        )
    )

    assert (
        "relation_nucleus_terms"
        not in text
    )

    assert (
        "distinguishing_terms"
        not in text
    )


def test_empty_backward_compatible_identity_is_explicitly_non_authoritative():
    text = _render(
        _diagnostic()
    )

    assert (
        "branch_identity_terms: []"
        in text
    )

    assert (
        "DIAGNOSTIC ONLY"
        in text
    )
