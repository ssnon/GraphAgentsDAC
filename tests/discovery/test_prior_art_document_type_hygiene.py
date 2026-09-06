from __future__ import annotations

import numpy as np

from domains.registry import get_domain_profile
from pipeline_core.discovery.external_novelty_contracts import (
    LiteratureQuery,
    LiteratureQueryPlan,
    NoveltyClaim,
    PriorArtPacket,
    PriorArtWork,
)
from pipeline_core.discovery.prior_art_matching import PriorArtRanker
from pipeline_core.discovery.prior_art_retrieval import (
    CrossrefProvider,
    canonicalize_prior_art_works,
)
import pipeline_core.discovery.prior_art_retrieval as retrieval


class FlatEncoder:
    def encode_query(self, text: str):
        return np.array(
            [1.0, 0.0],
            dtype=np.float32,
        )

    def encode_documents(
        self,
        texts,
        *,
        batch_size=32,
    ):
        return np.array(
            [
                [1.0, 0.0]
                for _ in texts
            ],
            dtype=np.float32,
        )


def _claim_and_plan():
    claim = NoveltyClaim(
        claim_id="c1",
        hypothesis_id="h1",
        claim_rank=1,
        kind="composite",
        importance="core",
        text=(
            "metal coupling changes the hydrogen "
            "adsorption descriptor"
        ),
        rationale="fixture",
        search_concepts=[
            "metal coupling",
            "hydrogen adsorption descriptor",
        ],
        search_queries=[
            "metal coupling hydrogen adsorption descriptor",
        ],
    )

    query = LiteratureQuery(
        query_id="q1",
        hypothesis_id="h1",
        claim_id="c1",
        query_kind="claim_primary",
        query_text="fixture query",
    )

    plan = LiteratureQueryPlan(
        plan_id="p1",
        plan_sha256="fixture",
        source_portfolio_id="portfolio",
        queries=[query],
    )

    return claim, query, plan


def _packet(*works: PriorArtWork) -> PriorArtPacket:
    return PriorArtPacket(
        packet_id="packet",
        packet_sha256="fixture",
        source_portfolio_id="portfolio",
        source_query_plan_id="p1",
        searched_at_utc="2026-09-06T00:00:00+00:00",
        works=list(works),
    )


def _work(
    work_id: str,
    *,
    provider_document_types=None,
) -> PriorArtWork:
    return PriorArtWork(
        work_id=work_id,
        title=(
            "Metal coupling changes the hydrogen "
            "adsorption descriptor"
        ),
        abstract=(
            "Metal coupling modifies hydrogen adsorption "
            "and catalytic activity."
        ),
        providers=["crossref"],
        provider_ids={
            "crossref":
                f"10.0000/{work_id}"
        },
        provider_document_types=(
            provider_document_types
            if provider_document_types is not None
            else {}
        ),
        retrieval_query_ids=["q1"],
        retrieval_claim_ids=["c1"],
    )


def test_legacy_prior_art_work_without_type_metadata_remains_valid() -> None:
    work = PriorArtWork(
        work_id="legacy",
        title="Legacy prior-art record",
    )

    assert (
        work.provider_document_types
        == {}
    )


def test_crossref_preserves_structured_peer_review_type(
    monkeypatch,
) -> None:
    _, query, _ = _claim_and_plan()

    payload = {
        "message": {
            "items": [
                {
                    "title": [
                        "Public peer review of a catalyst article"
                    ],
                    "DOI":
                        "10.0000/review-record",
                    "URL":
                        "https://example.test/review",
                    "type":
                        "peer-review",
                    "published-online": {
                        "date-parts": [
                            [2025, 1, 2]
                        ]
                    },
                    "author": [
                        {
                            "given": "A",
                            "family": "Reviewer",
                        }
                    ],
                    "container-title": [
                        "Example Journal"
                    ],
                    "is-referenced-by-count":
                        0,
                }
            ]
        }
    }

    monkeypatch.setattr(
        retrieval,
        "_request_json",
        lambda *args, **kwargs:
            payload,
    )

    rows = CrossrefProvider(
        delay_seconds=0.0,
    ).search(
        query,
        limit=5,
    )

    assert len(rows) == 1

    assert (
        rows[0].provider_document_types
        == {
            "crossref":
                "peer-review"
        }
    )


def test_canonical_merge_preserves_provider_document_type() -> None:
    generic = PriorArtWork(
        work_id="generic",
        title="Shared DOI work",
        doi="10.0000/shared",
        providers=["semanticscholar"],
        provider_ids={
            "semanticscholar":
                "S2-1"
        },
    )

    typed = PriorArtWork(
        work_id="crossref",
        title="Shared DOI work",
        doi="10.0000/shared",
        providers=["crossref"],
        provider_ids={
            "crossref":
                "10.0000/shared"
        },
        provider_document_types={
            "crossref":
                "peer-review"
        },
    )

    works, _ = canonicalize_prior_art_works(
        [
            generic,
            typed,
        ]
    )

    assert len(works) == 1

    assert (
        works[0].provider_document_types
        == {
            "crossref":
                "peer-review"
        }
    )


def test_peer_review_record_is_preserved_in_packet_but_not_ranked() -> None:
    claim, _, plan = _claim_and_plan()

    review = _work(
        "a-review",
        provider_document_types={
            "crossref":
                "peer-review"
        },
    )

    article = _work(
        "z-article",
        provider_document_types={
            "crossref":
                "journal-article"
        },
    )

    packet = _packet(
        review,
        article,
    )

    assert {
        row.work_id
        for row in packet.works
    } == {
        "a-review",
        "z-article",
    }

    ranked = PriorArtRanker(
        FlatEncoder(),
        max_ranked_works_per_claim=1,
        domain_profile=get_domain_profile(
            "dac_her"
        ),
    ).rank(
        claim,
        packet,
        plan,
    )

    assert [
        row.work_id
        for row in ranked.ranked_works
    ] == [
        "z-article"
    ]


def test_missing_document_type_remains_rank_eligible() -> None:
    claim, _, plan = _claim_and_plan()

    legacy = _work(
        "legacy",
    )

    ranked = PriorArtRanker(
        FlatEncoder(),
        max_ranked_works_per_claim=1,
        domain_profile=get_domain_profile(
            "dac_her"
        ),
    ).rank(
        claim,
        _packet(legacy),
        plan,
    )

    assert [
        row.work_id
        for row in ranked.ranked_works
    ] == [
        "legacy"
    ]


def test_mixed_provider_types_do_not_fail_closed_as_peer_review() -> None:
    claim, _, plan = _claim_and_plan()

    mixed = PriorArtWork(
        work_id="mixed",
        title=(
            "Metal coupling changes the hydrogen "
            "adsorption descriptor"
        ),
        abstract=(
            "Metal coupling modifies hydrogen adsorption."
        ),
        providers=[
            "crossref",
            "openalex",
        ],
        provider_ids={
            "crossref":
                "10.0000/mixed",
            "openalex":
                "W1",
        },
        provider_document_types={
            "crossref":
                "peer-review",
            "openalex":
                "journal-article",
        },
        retrieval_query_ids=["q1"],
        retrieval_claim_ids=["c1"],
    )

    ranked = PriorArtRanker(
        FlatEncoder(),
        max_ranked_works_per_claim=1,
        domain_profile=get_domain_profile(
            "dac_her"
        ),
    ).rank(
        claim,
        _packet(mixed),
        plan,
    )

    assert [
        row.work_id
        for row in ranked.ranked_works
    ] == [
        "mixed"
    ]
