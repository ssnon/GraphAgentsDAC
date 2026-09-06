from __future__ import annotations

from pipeline_core.discovery.hypothesis_contracts import (
    HypothesisCard,
)
from pipeline_core.discovery.nonobviousness_shadow import (
    recover_uniquely_attributed_required_bridge,
)
from pipeline_core.discovery.novelty_residue import (
    NoveltyResidueClaim,
)


def _hypothesis(
    bridge: str,
) -> HypothesisCard:
    # Recovery uses only these canonical fields:
    # hypothesis_id, inferential_bridge, assumptions.
    return HypothesisCard.model_construct(
        hypothesis_id="hypothesis:e3e9-wiring",
        inferential_bridge=bridge,
        assumptions=(),
    )


def _claim(
    claim_id: str,
    *,
    identity: tuple[str, ...],
    nucleus: tuple[str, ...],
    distinguishing: tuple[str, ...],
) -> NoveltyResidueClaim:
    return NoveltyResidueClaim(
        hypothesis_id="hypothesis:e3e9-wiring",
        claim_id=claim_id,
        claim_text=f"Atomic claim {claim_id}.",
        claim_kind="moderator_interaction",
        prior_art_status="COMPONENTS_ONLY",
        disposition="RESIDUAL",
        is_residue=True,
        distinguishing_terms=distinguishing,
        prior_art_identity_terms=identity,
        relation_nucleus_terms=nucleus,
        required_bridge="",
        predicted_observation="",
        falsification_condition="",
        direct_or_partial_work_ids=(),
        lower_order_work_ids=(),
        component_work_ids=(),
    )


def _recover(
    hypothesis: HypothesisCard,
    claim: NoveltyResidueClaim,
    siblings: tuple[
        NoveltyResidueClaim,
        ...,
    ],
) -> str:
    return (
        recover_uniquely_attributed_required_bridge(
            hypothesis=hypothesis,
            claim=claim,
            sibling_claims=siblings,
        )
    )


def test_existing_unique_identity_fast_path_is_preserved():
    bridge = (
        "Laser power changes SERS enhancement through "
        "an interparticle spacing dependence."
    )

    hypothesis = _hypothesis(
        bridge
    )

    target = _claim(
        "target",
        identity=(
            "laser power",
        ),
        nucleus=(
            "SERS enhancement",
            "dependence",
        ),
        distinguishing=(
            "laser power response",
        ),
    )

    other = _claim(
        "other",
        identity=(
            "surface chemistry",
        ),
        nucleus=(
            "chemical enhancement",
        ),
        distinguishing=(
            "surface chemistry response",
        ),
    )

    siblings = (
        target,
        other,
    )

    assert (
        _recover(
            hypothesis,
            target,
            siblings,
        )
        == bridge
    )

    assert (
        _recover(
            hypothesis,
            other,
            siblings,
        )
        == ""
    )


def test_identity_ambiguity_can_resolve_one_atomic_sibling():
    bridge = (
        "Under the shared coordination regime, "
        "the lower error descriptor identity changes."
    )

    hypothesis = _hypothesis(
        bridge
    )

    relation = _claim(
        "relation",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "descriptor dependence",
        ),
        distinguishing=(
            "signed descriptor error difference",
        ),
    )

    prediction = _claim(
        "prediction",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "descriptor performance",
        ),
        distinguishing=(
            "lower error descriptor identity changes",
        ),
    )

    siblings = (
        relation,
        prediction,
    )

    assert (
        _recover(
            hypothesis,
            prediction,
            siblings,
        )
        == bridge
    )

    assert (
        _recover(
            hypothesis,
            relation,
            siblings,
        )
        == ""
    )


def test_umbrella_candidate_remains_fail_closed():
    bridge = (
        "The coordination regime changes metal metal coupling, "
        "HER activity maximum, and conditional dependence through "
        "a regime specific coupling coordinate."
    )

    hypothesis = _hypothesis(
        bridge
    )

    moderator = _claim(
        "moderator",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "metal metal coupling",
        ),
        distinguishing=(
            "coordination regime",
        ),
    )

    prediction = _claim(
        "prediction",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "HER activity maximum",
        ),
        distinguishing=(
            "activity maximum",
        ),
    )

    composite = _claim(
        "composite",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "conditional dependence",
        ),
        distinguishing=(
            "regime specific coupling coordinate",
        ),
    )

    siblings = (
        moderator,
        prediction,
        composite,
    )

    assert all(
        _recover(
            hypothesis,
            claim,
            siblings,
        )
        == ""
        for claim in siblings
    )


def test_non_identity_matching_sibling_cannot_block_secondary_selection():
    bridge = (
        "The coordination regime produces a "
        "unique descriptor crossover."
    )

    hypothesis = _hypothesis(
        bridge
    )

    selected = _claim(
        "selected",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "descriptor response",
        ),
        distinguishing=(
            "unique descriptor crossover",
        ),
    )

    ambiguous_peer = _claim(
        "peer",
        identity=(
            "coordination regime",
        ),
        nucleus=(
            "descriptor response",
        ),
        distinguishing=(
            "different descriptor behavior",
        ),
    )

    # This sibling deliberately shares the same atomic discriminator,
    # but its prior-art-family identity is absent from the bridge.
    # It must therefore never enter the identity-admissible ambiguity set.
    unrelated = _claim(
        "unrelated",
        identity=(
            "surface reconstruction",
        ),
        nucleus=(
            "surface response",
        ),
        distinguishing=(
            "unique descriptor crossover",
        ),
    )

    siblings = (
        selected,
        ambiguous_peer,
        unrelated,
    )

    assert (
        _recover(
            hypothesis,
            selected,
            siblings,
        )
        == bridge
    )

    assert (
        _recover(
            hypothesis,
            ambiguous_peer,
            siblings,
        )
        == ""
    )

    assert (
        _recover(
            hypothesis,
            unrelated,
            siblings,
        )
        == ""
    )
