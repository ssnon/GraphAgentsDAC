from __future__ import annotations

from pipeline_core.discovery.nonobviousness_shadow import (
    select_uniquely_discriminated_atomic_claim_id,
)
from pipeline_core.discovery.novelty_residue import (
    NoveltyResidueClaim,
)


def _claim(
    claim_id: str,
    *,
    nucleus: tuple[str, ...],
    distinguishing: tuple[str, ...],
) -> NoveltyResidueClaim:
    return NoveltyResidueClaim(
        hypothesis_id="hypothesis:e3e9-helper",
        claim_id=claim_id,
        claim_text=f"Atomic claim {claim_id}.",
        claim_kind="moderator_interaction",
        prior_art_status="COMPONENTS_ONLY",
        disposition="RESIDUAL",
        is_residue=True,
        distinguishing_terms=distinguishing,
        prior_art_identity_terms=(
            "shared prior art family",
        ),
        relation_nucleus_terms=nucleus,
        required_bridge="",
        predicted_observation="",
        falsification_condition="",
        direct_or_partial_work_ids=(),
        lower_order_work_ids=(),
        component_work_ids=(),
    )


def _select(
    bridge: str,
    *claims: NoveltyResidueClaim,
) -> str | None:
    return (
        select_uniquely_discriminated_atomic_claim_id(
            candidate_bridge=bridge,
            sibling_claims=claims,
        )
    )


# ------------------------------------------------------------------
# Historical positive shape: Q03-1.
#
# Same prior-art family, but canonical candidate contains a
# distinguishing facet unique to exactly one atomic sibling.
# ------------------------------------------------------------------


def test_q03_1_shape_selects_one_distinguishing_claim():
    relation = _claim(
        "q03-1-relation",
        nucleus=(
            "ICOHP based prediction",
            "d band center based prediction",
            "HER activity prediction error",
            "descriptor dependence",
        ),
        distinguishing=(
            "signed difference between HER activity prediction errors",
            "sign change",
        ),
    )

    prediction = _claim(
        "q03-1-prediction",
        nucleus=(
            "ICOHP based prediction",
            "d band center based prediction",
            "HER activity prediction error",
            "descriptor performance dependence",
        ),
        distinguishing=(
            "lower error descriptor identity changes",
        ),
    )

    bridge = (
        "The supplied relation predicts a signed difference between "
        "HER activity prediction errors and a sign change while "
        "comparing the descriptors."
    )

    assert (
        _select(
            bridge,
            relation,
            prediction,
        )
        == "q03-1-relation"
    )


# ------------------------------------------------------------------
# Historical positive shape: Q06-2.
#
# Both nucleus and distinguishing metadata point consistently to
# one sibling.
# ------------------------------------------------------------------


def test_q06_2_shape_selects_one_claim_from_both_fields():
    response = _claim(
        "q06-2-response",
        nucleus=(
            "second hydrogen occupation",
            "HER activity",
            "poisoning response",
            "dependence",
        ),
        distinguishing=(
            "occupation dependent poisoning response",
        ),
    )

    regime = _claim(
        "q06-2-regime",
        nucleus=(
            "second hydrogen occupation",
            "apparent HER regime assignment",
            "poisoning response",
            "dependence",
        ),
        distinguishing=(
            "different apparent HER regime assignments",
        ),
    )

    bridge = (
        "The candidate connects apparent HER regime assignment "
        "with different apparent HER regime assignments under the "
        "shared poisoning response."
    )

    assert (
        _select(
            bridge,
            response,
            regime,
        )
        == "q06-2-regime"
    )


# ------------------------------------------------------------------
# Historical negative shapes.
#
# Each canonical candidate contains unique metadata belonging to
# multiple siblings.  They must remain ambiguous.
# ------------------------------------------------------------------


def test_q02_2_shape_remains_ambiguous():
    first = _claim(
        "q02-2-a",
        nucleus=(
            "hydrogen adsorption relation",
        ),
        distinguishing=(
            "ICOHP linked oxygenated intermediate adsorption relation",
        ),
    )

    second = _claim(
        "q02-2-b",
        nucleus=(
            "oxygenated intermediate adsorption relation",
        ),
        distinguishing=(
            "joint hydrogen oxygenated intermediate descriptor",
        ),
    )

    bridge = (
        "The bridge combines an ICOHP linked oxygenated intermediate "
        "adsorption relation with a joint hydrogen oxygenated "
        "intermediate descriptor."
    )

    assert (
        _select(
            bridge,
            first,
            second,
        )
        is None
    )


def test_q02_4_shape_remains_umbrella_ambiguous():
    moderator = _claim(
        "q02-4-moderator",
        nucleus=(
            "metal metal coupling",
            "metal hydrogen adsorption",
        ),
        distinguishing=(
            "coordination regime",
        ),
    )

    prediction = _claim(
        "q02-4-prediction",
        nucleus=(
            "HER activity maximum",
        ),
        distinguishing=(
            "rather than one common coupling value",
        ),
    )

    composite = _claim(
        "q02-4-composite",
        nucleus=(
            "conditional dependence",
        ),
        distinguishing=(
            "regime specific coupling coordinate",
        ),
    )

    bridge = (
        "The coordination regime changes metal metal coupling and "
        "HER activity maximum through a conditional dependence, "
        "with a regime specific coupling coordinate rather than one "
        "common coupling value."
    )

    assert (
        _select(
            bridge,
            moderator,
            prediction,
            composite,
        )
        is None
    )


def test_q03_2_shape_remains_umbrella_ambiguous():
    local_bonding = _claim(
        "q03-2-local",
        nucleus=(
            "oxygenated intermediate adsorption free energies",
            "local metal oxygen ICOHP",
        ),
        distinguishing=(
            "local metal oxygen ICOHP",
        ),
    )

    concordance = _claim(
        "q03-2-concordance",
        nucleus=(
            "descriptor concordance",
        ),
        distinguishing=(
            "descriptor concordance",
        ),
    )

    bridge = (
        "The bridge relates local metal oxygen ICOHP to oxygenated "
        "intermediate adsorption free energies and descriptor "
        "concordance."
    )

    assert (
        _select(
            bridge,
            local_bonding,
            concordance,
        )
        is None
    )


def test_q06_1_shape_remains_umbrella_ambiguous():
    slope = _claim(
        "q06-1-slope",
        nucleus=(
            "potential dependent slope",
        ),
        distinguishing=(
            "potential dependent slope",
        ),
    )

    ordering = _claim(
        "q06-1-ordering",
        nucleus=(
            "barrier ordering",
        ),
        distinguishing=(
            "barrier ordering",
        ),
    )

    crossover = _claim(
        "q06-1-crossover",
        nucleus=(
            "barrier ordering crossover",
        ),
        distinguishing=(
            "barrier ordering crossover",
        ),
    )

    bridge = (
        "The candidate jointly describes potential dependent slope, "
        "barrier ordering, and a barrier ordering crossover."
    )

    assert (
        _select(
            bridge,
            slope,
            ordering,
            crossover,
        )
        is None
    )


def test_q06_3_shape_remains_chained_ambiguous():
    configuration_a = _claim(
        "q06-3-config-a",
        nucleus=(
            "electronic configuration",
        ),
        distinguishing=(
            "electronic configuration",
        ),
    )

    configuration_b = _claim(
        "q06-3-config-b",
        nucleus=(
            "electronic configuration",
        ),
        distinguishing=(
            "configuration dependent response",
        ),
    )

    shift_a = _claim(
        "q06-3-shift-a",
        nucleus=(
            "second minus first hydrogen adsorption energy shift",
        ),
        distinguishing=(
            "second minus first hydrogen adsorption energy shift",
        ),
    )

    shift_b = _claim(
        "q06-3-shift-b",
        nucleus=(
            "second minus first hydrogen adsorption energy shift",
        ),
        distinguishing=(
            "adsorption energy shift comparison",
        ),
    )

    bridge = (
        "The bridge connects electronic configuration and a "
        "configuration dependent response with the second minus first "
        "hydrogen adsorption energy shift and an adsorption energy "
        "shift comparison."
    )

    assert (
        _select(
            bridge,
            configuration_a,
            configuration_b,
            shift_a,
            shift_b,
        )
        is None
    )


def test_q07_2_shape_remains_chained_ambiguous():
    mismatch = _claim(
        "q07-2-mismatch",
        nucleus=(
            "electronic mismatch",
        ),
        distinguishing=(
            "electronic mismatch",
        ),
    )

    reduction = _claim(
        "q07-2-reduction",
        nucleus=(
            "electronic mismatch reduction",
        ),
        distinguishing=(
            "electronic mismatch reduction",
        ),
    )

    bridge = (
        "The candidate attributes the response to electronic mismatch "
        "and to electronic mismatch reduction."
    )

    assert (
        _select(
            bridge,
            mismatch,
            reduction,
        )
        is None
    )


# ------------------------------------------------------------------
# Generic fail-closed structural controls.
# ------------------------------------------------------------------


def test_empty_candidate_fails_closed():
    claim = _claim(
        "empty",
        nucleus=("unique nucleus",),
        distinguishing=("unique facet",),
    )

    assert (
        _select(
            "",
            claim,
        )
        is None
    )


def test_duplicate_claim_ids_fail_closed():
    first = _claim(
        "duplicate",
        nucleus=("first unique nucleus",),
        distinguishing=(),
    )

    second = _claim(
        "duplicate",
        nucleus=("second unique nucleus",),
        distinguishing=(),
    )

    assert (
        _select(
            "first unique nucleus",
            first,
            second,
        )
        is None
    )


def test_cross_hypothesis_siblings_fail_closed():
    first = _claim(
        "first",
        nucleus=("first unique nucleus",),
        distinguishing=(),
    )

    second = _claim(
        "second",
        nucleus=("second unique nucleus",),
        distinguishing=(),
    )

    second = NoveltyResidueClaim(
        **{
            **second.__dict__,
            "hypothesis_id":
                "hypothesis:other",
        }
    )

    assert (
        _select(
            "first unique nucleus",
            first,
            second,
        )
        is None
    )
