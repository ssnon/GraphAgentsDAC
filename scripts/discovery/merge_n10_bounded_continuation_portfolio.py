"""Merge authoritative first-pass and bounded-H2 N10 survivors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core.discovery.hypothesis_contracts import (
    HypothesisPortfolio,
)
from pipeline_core.discovery.n10_post_generation_final_merge import (
    AuthoritativePostN10Portfolio,
    merge_bounded_continuation_survivors,
)


_CONTINUATION_SCHEMA = (
    "n10-bounded-post-generation-continuation-run-v1"
)


def _load_json(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "expected JSON object: "
            + str(
                path
            )
        )

    return payload


def _load_portfolio(
    path: Path,
) -> HypothesisPortfolio:
    return (
        HypothesisPortfolio
        .model_validate_json(
            path.read_text(
                encoding="utf-8"
            )
        )
    )


def _require_file(
    path: Path,
    *,
    label: str,
) -> Path:
    if not path.is_file():
        raise ValueError(
            label
            + " does not exist: "
            + str(
                path
            )
        )

    return path


def load_h2_authority_branches(
    *,
    continuation_report:
        dict[str, Any],
) -> list[
    AuthoritativePostN10Portfolio
]:
    if (
        continuation_report.get(
            "schema_version"
        )
        != _CONTINUATION_SCHEMA
    ):
        raise ValueError(
            "unexpected bounded-continuation report schema"
        )

    if (
        continuation_report.get(
            "production_authority"
        )
        is not False
    ):
        raise ValueError(
            "continuation runner must not carry production authority"
        )

    if (
        continuation_report.get(
            "final_portfolio_selection_authority"
        )
        is not False
    ):
        raise ValueError(
            "continuation runner must not carry final selection authority"
        )

    if (
        continuation_report.get(
            "scientific_evidence_authority"
        )
        is not False
    ):
        raise ValueError(
            "continuation runner must not carry scientific evidence authority"
        )

    if (
        continuation_report.get(
            "max_continuation_depth"
        )
        != 1
    ):
        raise ValueError(
            "unexpected continuation depth contract"
        )

    if (
        continuation_report.get(
            "fresh_h2_n10_required"
        )
        is not True
    ):
        raise ValueError(
            "continuation report does not require fresh H2 N10"
        )

    branches = continuation_report.get(
        "branches"
    )

    if not isinstance(
        branches,
        list,
    ):
        raise ValueError(
            "continuation branches must be a list"
        )

    result = []

    seen_h1 = set()

    for row in branches:
        if not isinstance(
            row,
            dict,
        ):
            raise ValueError(
                "continuation branch must be an object"
            )

        h1_id = str(
            row.get(
                "h1_candidate_id"
            )
            or ""
        ).strip()

        if not h1_id:
            raise ValueError(
                "continuation branch missing H1 candidate identity"
            )

        if h1_id in seen_h1:
            raise ValueError(
                "duplicate continuation H1 branch: "
                + h1_id
            )

        seen_h1.add(
            h1_id
        )

        if (
            row.get(
                "continuation_depth"
            )
            != 1
        ):
            raise ValueError(
                "continuation branch violates depth-1 contract"
            )

        portfolio_path = _require_file(
            Path(
                str(
                    row.get(
                        "fresh_h2_n10_portfolio"
                    )
                    or ""
                )
            ),
            label="fresh H2 N10 portfolio",
        )

        report_path = _require_file(
            Path(
                str(
                    row.get(
                        "fresh_h2_n10_report"
                    )
                    or ""
                )
            ),
            label="fresh H2 N10 report",
        )

        portfolio = _load_portfolio(
            portfolio_path
        )

        declared_survivors = row.get(
            "fresh_h2_n10_survivor_count"
        )

        if (
            not isinstance(
                declared_survivors,
                int,
            )
            or declared_survivors
            != len(
                portfolio.hypotheses
            )
        ):
            raise ValueError(
                "continuation branch H2 survivor count mismatch"
            )

        result.append(
            AuthoritativePostN10Portfolio(
                portfolio=(
                    portfolio
                ),

                enforcement_report=(
                    _load_json(
                        report_path
                    )
                ),

                source_kind=(
                    "bounded_h2"
                ),
            )
        )

    declared_work_items = continuation_report.get(
        "continuation_work_item_count"
    )

    if (
        not isinstance(
            declared_work_items,
            int,
        )
        or declared_work_items
        != len(
            branches
        )
    ):
        raise ValueError(
            "continuation work-item/branch count mismatch"
        )

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Deterministically merge first-pass post-N10 "
            "survivors with independently authorized bounded-H2 survivors."
        )
    )

    p.add_argument(
        "--first-post-n10-portfolio",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--first-post-n10-report",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--continuation-report",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--output-portfolio",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--output-audit",
        required=True,
        type=Path,
    )

    return p.parse_args()


def main() -> int:
    args = parse_args()

    for path, label in [
        (
            args.first_post_n10_portfolio,
            "first post-N10 portfolio",
        ),
        (
            args.first_post_n10_report,
            "first post-N10 report",
        ),
        (
            args.continuation_report,
            "bounded continuation report",
        ),
    ]:
        _require_file(
            path,
            label=label,
        )

    first = (
        AuthoritativePostN10Portfolio(
            portfolio=(
                _load_portfolio(
                    args
                    .first_post_n10_portfolio
                )
            ),

            enforcement_report=(
                _load_json(
                    args
                    .first_post_n10_report
                )
            ),

            source_kind=(
                "first_post_generation"
            ),
        )
    )

    continuation = _load_json(
        args.continuation_report
    )

    h2_branches = (
        load_h2_authority_branches(
            continuation_report=(
                continuation
            )
        )
    )

    merged, audit = (
        merge_bounded_continuation_survivors(
            first_pass=(
                first
            ),
            h2_branches=(
                h2_branches
            ),
        )
    )

    args.output_portfolio.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output_audit.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output_portfolio.write_text(
        merged.model_dump_json(
            indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    args.output_audit.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "Bounded-continuation final merge complete"
    )

    print(
        "First-pass survivors:",
        len(
            first
            .portfolio
            .hypotheses
        ),
    )

    print(
        "Bounded H2 survivors:",
        audit[
            "bounded_h2_survivor_count"
        ],
    )

    print(
        "Final survivors:",
        len(
            merged.hypotheses
        ),
    )

    print(
        "Final portfolio:",
        args.output_portfolio,
    )

    print(
        "Merge audit:",
        args.output_audit,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
