"""Run exactly one bounded post-generation N10 specification continuation.

This runner is intentionally separate from the main discovery E2E while the
bounded-continuation path is staged.

For every first-pass Alpha6 H1 candidate that the frozen continuation policy
marks as:

    CONDITIONAL
    + REFINE_NOVELTY_BEARING_SPECIFICATION
    + positive authority False
    + fallback False
    + continuation depth 0

the runner:

1. compiles a deterministic continuation work item;
2. projects frozen H0 discovery lineage onto H1 identity only;
3. rebuilds the H1 role-aware gate for Alpha6 original-fallback scope
   without changing scientific semantics;
4. invokes exactly one diagnostic-aware second Alpha6;
5. rejects any attempt to preserve H1 as kept_original;
6. runs fresh external N9/N10 enforcement over generated H2;
7. evaluates the frozen continuation policy at depth 1 for audit only.

This runner does NOT merge H2 into the final portfolio.  Final portfolio
selection is a separate deterministic integration step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline_core.discovery.discovery_axis_contracts import (
    DiscoveryAxisPlan,
    DiscoveryAxisSynthesisReport,
)
from pipeline_core.discovery.hypothesis_contracts import (
    HypothesisPortfolio,
)
from pipeline_core.discovery.n10_post_generation_continuation_orchestration import (
    PostGenerationContinuationWorkItem,
    compile_post_generation_continuation_work_items,
)
from pipeline_core.discovery.n10_post_generation_continuation_policy import (
    post_generation_continuation_directive_from_gate_row,
)
from pipeline_core.discovery.n10_post_generation_reentry import (
    build_post_generation_reentry_package,
)
from pipeline_core.discovery.nonobviousness_post_generation import (
    _validate_n10_gate,
)
from pipeline_core.discovery.novelty_refinement_contracts import (
    NoveltyRefinementReport,
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
            + str(path)
        )

    return payload


def _jsonable(
    value: object,
) -> object:
    if hasattr(
        value,
        "model_dump",
    ):
        return value.model_dump(
            mode="json"
        )

    if is_dataclass(
        value
    ):
        return asdict(
            value
        )

    return value


def _write_json(
    path: Path,
    value: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            _jsonable(
                value
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
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
            + str(path)
        )

    return path


def _run(
    module: str,
    args: list[str],
) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            module,
            *args,
        ],
        check=True,
    )


def _candidate_artifacts_by_id(
    enforcement_report: Mapping[str, Any],
) -> dict[
    str,
    Mapping[str, Any],
]:
    rows = enforcement_report.get(
        "candidate_artifacts"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ValueError(
            "first post-generation enforcement report "
            "lacks candidate_artifacts"
        )

    result = {}

    for row in rows:
        if not isinstance(
            row,
            Mapping,
        ):
            raise ValueError(
                "candidate artifact row must be an object"
            )

        candidate_id = str(
            row.get(
                "candidate_id"
            )
            or ""
        ).strip()

        if not candidate_id:
            raise ValueError(
                "candidate artifact missing candidate_id"
            )

        if candidate_id in result:
            raise ValueError(
                "duplicate candidate artifact: "
                + candidate_id
            )

        result[
            candidate_id
        ] = row

    return result


def _load_production_gates_from_artifacts(
    enforcement_report: Mapping[str, Any],
) -> dict[
    str,
    dict[str, Any],
]:
    artifacts = (
        _candidate_artifacts_by_id(
            enforcement_report
        )
    )

    result = {}

    for candidate_id, row in artifacts.items():
        path_text = str(
            row.get(
                "production_gate"
            )
            or ""
        ).strip()

        if not path_text:
            raise ValueError(
                "candidate artifact missing production_gate path: "
                + candidate_id
            )

        path = _require_file(
            Path(
                path_text
            ),
            label=(
                "post-generation production gate"
            ),
        )

        result[
            candidate_id
        ] = _load_json(
            path
        )

    return result


def _artifact_for_work_item(
    enforcement_report: Mapping[str, Any],
    work_item: PostGenerationContinuationWorkItem,
) -> Mapping[str, Any]:
    artifacts = (
        _candidate_artifacts_by_id(
            enforcement_report
        )
    )

    candidate_id = (
        work_item
        .continuation_input_candidate_id
    )

    row = artifacts.get(
        candidate_id
    )

    if row is None:
        raise ValueError(
            "missing artifact row for continuation candidate "
            + candidate_id
        )

    return row


def _safe_stem(
    candidate_id: str,
) -> str:
    value = (
        candidate_id
        .replace(
            ":",
            "_",
        )
        .replace(
            "/",
            "_",
        )
    )

    if not value:
        raise ValueError(
            "empty continuation candidate identity"
        )

    return value


def build_second_alpha6_args(
    *,
    work_item:
        PostGenerationContinuationWorkItem,

    lineage_projection_path:
        Path,

    reentry_gate_path:
        Path,

    dual_context:
        Path,

    axis_plan:
        Path,

    provider_plan:
        Path,

    index_dir:
        Path,

    domain_profile:
        str,

    model:
        str,

    critic_model:
        str,

    base_url:
        str | None,

    api_key_env:
        str,

    results_per_query:
        int,

    output_prefix:
        Path,

    question_task_preservation_enforce:
        bool,

) -> list[str]:
    args = [
        "--dual-context",
        str(
            dual_context
        ),

        "--domain-profile",
        domain_profile,

        "--axis-plan",
        str(
            axis_plan
        ),

        "--portfolio",
        work_item.source_portfolio,

        "--lineage",
        str(
            lineage_projection_path
        ),

        "--external-report",
        work_item.external_report,

        "--external-query-plan",
        work_item.query_plan,

        "--external-prior-art",
        work_item.prior_art,

        "--scientific-novelty-gate",
        str(
            reentry_gate_path
        ),

        "--n10-specification-repair-intake-shadow",
        work_item.intake_shadow,

        "--n10-specification-repair-post-generation-gate",
        work_item.production_gate,

        "--model",
        model,

        "--critic-model",
        critic_model,

        "--api-key-env",
        api_key_env,

        "--provider-plan",
        str(
            provider_plan
        ),

        "--results-per-query",
        str(
            results_per_query
        ),

        "--index-dir",
        str(
            index_dir
        ),

        "--output-prefix",
        str(
            output_prefix
        ),
    ]

    if base_url:
        args.extend(
            [
                "--base-url",
                base_url,
            ]
        )

    if (
        question_task_preservation_enforce
    ):
        args.append(
            "--question-task-preservation-enforce"
        )

    return args


def build_fresh_h2_n10_args(
    *,
    second_alpha6_portfolio:
        Path,

    hypothesis_context:
        str,

    second_alpha6_report:
        Path,

    second_alpha6_external_dir:
        Path,

    provider_plan:
        Path,

    domain_profile:
        str,

    model:
        str,

    base_url:
        str | None,

    api_key_env:
        str,

    results_per_query:
        int,

    work_dir:
        Path,

    output_portfolio:
        Path,

    output_report:
        Path,

) -> list[str]:
    args = [
        "--portfolio",
        str(
            second_alpha6_portfolio
        ),

        "--hypothesis-context",
        hypothesis_context,

        "--refinement-report",
        str(
            second_alpha6_report
        ),

        "--external-dir",
        str(
            second_alpha6_external_dir
        ),

        "--provider-plan",
        str(
            provider_plan
        ),

        "--domain-profile",
        domain_profile,

        "--model",
        model,

        "--api-key-env",
        api_key_env,

        "--results-per-query",
        str(
            results_per_query
        ),

        "--work-dir",
        str(
            work_dir
        ),

        "--output-portfolio",
        str(
            output_portfolio
        ),

        "--output-report",
        str(
            output_report
        ),
    ]

    if base_url:
        args.extend(
            [
                "--base-url",
                base_url,
            ]
        )

    return args


def assert_second_alpha6_did_not_keep_h1(
    report: NoveltyRefinementReport,
) -> None:
    invalid = [
        attempt
        for attempt in report.attempts
        if (
            attempt.decision
            == "kept_original"
        )
    ]

    if invalid:
        raise ValueError(
            "bounded continuation may not preserve H1 "
            "through kept_original; H1 was already "
            "CONDITIONAL and fallback-blocked"
        )


def build_depth_one_terminal_audit(
    *,
    enforcement_report:
        Mapping[str, Any],
) -> list[
    dict[str, Any]
]:
    decisions = enforcement_report.get(
        "decisions"
    )

    if not isinstance(
        decisions,
        list,
    ):
        raise ValueError(
            "fresh H2 N10 report lacks decisions"
        )

    artifacts = (
        _candidate_artifacts_by_id(
            enforcement_report
        )
    )

    result = []

    for decision in decisions:
        if not isinstance(
            decision,
            Mapping,
        ):
            raise ValueError(
                "fresh H2 N10 decision must be an object"
            )

        if (
            decision.get(
                "n10_required"
            )
            is not True
        ):
            continue

        candidate_id = str(
            decision.get(
                "candidate_hypothesis_id"
            )
            or ""
        ).strip()

        if not candidate_id:
            raise ValueError(
                "fresh H2 N10 decision missing candidate ID"
            )

        artifact = artifacts.get(
            candidate_id
        )

        if artifact is None:
            raise ValueError(
                "fresh H2 candidate lacks artifact audit: "
                + candidate_id
            )

        production_gate_path = str(
            artifact.get(
                "production_gate"
            )
            or ""
        ).strip()

        if not production_gate_path:
            raise ValueError(
                "fresh H2 candidate lacks production gate path"
            )

        gate = _load_json(
            _require_file(
                Path(
                    production_gate_path
                ),
                label=(
                    "fresh H2 production gate"
                ),
            )
        )

        row = _validate_n10_gate(
            candidate_id=candidate_id,
            gate=gate,
        )

        directive = (
            post_generation_continuation_directive_from_gate_row(
                gate_row=row,
                continuation_depth=1,
            )
        )

        if (
            directive.allow_bounded_continuation
        ):
            raise ValueError(
                "depth-1 H2 unexpectedly received another continuation"
            )

        result.append(
            {
                "candidate_hypothesis_id":
                    candidate_id,

                "selection_class":
                    row.get(
                        "selection_class"
                    ),

                "action":
                    row.get(
                        "action"
                    ),

                "base_aggregation_action":
                    row.get(
                        "base_aggregation_action"
                    ),

                "positive_nonobviousness_authority":
                    row.get(
                        "positive_nonobviousness_authority"
                    ),

                "fallback_allowed":
                    row.get(
                        "fallback_allowed"
                    ),

                "continuation_depth":
                    1,

                "allow_bounded_continuation":
                    directive
                    .allow_bounded_continuation,

                "terminal_due_to_depth_limit":
                    directive
                    .terminal_due_to_depth_limit,

                "fresh_post_generation_n10_required":
                    directive
                    .fresh_post_generation_n10_required,

                "continuation_reason_code":
                    directive.reason_code,
            }
        )

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run one bounded diagnostic continuation from "
            "repair-eligible H1 through fresh H2 N10."
        )
    )

    p.add_argument(
        "--first-post-n10-report",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--source-lineage",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--axis-plan",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--dual-context",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--provider-plan",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--index-dir",
        required=True,
        type=Path,
        help=(
            "Exact mechanism node index. Required so bounded "
            "continuation never falls back to repository-local "
            "historical data paths."
        ),
    )

    p.add_argument(
        "--domain-profile",
        required=True,
    )

    p.add_argument(
        "--model",
        required=True,
    )

    p.add_argument(
        "--critic-model",
        required=True,
    )

    p.add_argument(
        "--base-url",
        default=None,
    )

    p.add_argument(
        "--api-key-env",
        default="OPENROUTER_API_KEY",
    )

    p.add_argument(
        "--results-per-query",
        type=int,
        default=12,
    )

    p.add_argument(
        "--question-task-preservation-enforce",
        action="store_true",
    )

    p.add_argument(
        "--work-dir",
        required=True,
        type=Path,
    )

    p.add_argument(
        "--output-report",
        required=True,
        type=Path,
    )

    return p.parse_args()


def main() -> int:
    args = parse_args()

    for path, label in [
        (
            args.first_post_n10_report,
            "first post-generation N10 report",
        ),
        (
            args.source_lineage,
            "source lineage report",
        ),
        (
            args.axis_plan,
            "axis plan",
        ),
        (
            args.dual_context,
            "dual context",
        ),
        (
            args.provider_plan,
            "provider plan",
        ),
    ]:
        _require_file(
            path,
            label=label,
        )

    if not args.index_dir.is_dir():
        raise ValueError(
            "mechanism index directory does not exist: "
            + str(
                args.index_dir
            )
        )

    if (
        args.work_dir.exists()
        and any(
            args.work_dir.iterdir()
        )
    ):
        raise ValueError(
            "bounded-continuation work directory is not empty: "
            + str(
                args.work_dir
            )
        )

    args.work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_enforcement = _load_json(
        args.first_post_n10_report
    )

    first_gates = (
        _load_production_gates_from_artifacts(
            first_enforcement
        )
    )

    work_items = (
        compile_post_generation_continuation_work_items(
            enforcement_report=(
                first_enforcement
            ),
            gates_by_candidate_id=(
                first_gates
            ),
            continuation_depth=0,
        )
    )

    source_lineage = (
        DiscoveryAxisSynthesisReport
        .model_validate_json(
            args.source_lineage.read_text(
                encoding="utf-8"
            )
        )
    )

    axis_plan = (
        DiscoveryAxisPlan
        .model_validate_json(
            args.axis_plan.read_text(
                encoding="utf-8"
            )
        )
    )

    branches = []

    for index, work_item in enumerate(
        work_items,
        1,
    ):
        candidate_id = (
            work_item
            .continuation_input_candidate_id
        )

        branch_dir = (
            args.work_dir
            / (
                f"{index:02d}_"
                + _safe_stem(
                    candidate_id
                )
            )
        )

        branch_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        source_portfolio_path = (
            _require_file(
                Path(
                    work_item.source_portfolio
                ),
                label=(
                    "H1 continuation source portfolio"
                ),
            )
        )

        candidate_gate_path = (
            _require_file(
                Path(
                    work_item.candidate_gate
                ),
                label=(
                    "H1 candidate v2 gate"
                ),
            )
        )

        post_gate_path = (
            _require_file(
                Path(
                    work_item.production_gate
                ),
                label=(
                    "H1 authoritative post-generation gate"
                ),
            )
        )

        continuation_portfolio = (
            HypothesisPortfolio
            .model_validate_json(
                source_portfolio_path
                .read_text(
                    encoding="utf-8"
                )
            )
        )

        candidate_gate = _load_json(
            candidate_gate_path
        )

        post_gate = _load_json(
            post_gate_path
        )

        package = (
            build_post_generation_reentry_package(
                work_item=(
                    work_item
                ),
                candidate_gate=(
                    candidate_gate
                ),
                post_generation_gate=(
                    post_gate
                ),
                source_lineage_report=(
                    source_lineage
                ),
                axis_plan=(
                    axis_plan
                ),
                continuation_portfolio=(
                    continuation_portfolio
                ),
            )
        )

        work_item_path = (
            branch_dir
            / "continuation_work_item.json"
        )

        lineage_path = (
            branch_dir
            / "lineage_projection.json"
        )

        reentry_gate_path = (
            branch_dir
            / "reentry_gate.production.json"
        )

        _write_json(
            work_item_path,
            work_item,
        )

        _write_json(
            lineage_path,
            package.lineage_projection,
        )

        _write_json(
            reentry_gate_path,
            package.reentry_gate,
        )

        second_prefix = (
            branch_dir
            / "alpha6_second"
        )

        second_args = (
            build_second_alpha6_args(
                work_item=(
                    work_item
                ),
                lineage_projection_path=(
                    lineage_path
                ),
                reentry_gate_path=(
                    reentry_gate_path
                ),
                dual_context=(
                    args.dual_context
                ),
                axis_plan=(
                    args.axis_plan
                ),
                provider_plan=(
                    args.provider_plan
                ),
                index_dir=(
                    args.index_dir
                ),
                domain_profile=(
                    args.domain_profile
                ),
                model=(
                    args.model
                ),
                critic_model=(
                    args.critic_model
                ),
                base_url=(
                    args.base_url
                ),
                api_key_env=(
                    args.api_key_env
                ),
                results_per_query=(
                    args.results_per_query
                ),
                output_prefix=(
                    second_prefix
                ),
                question_task_preservation_enforce=(
                    args
                    .question_task_preservation_enforce
                ),
            )
        )

        _run(
            "scripts.discovery.run_novelty_refinement",
            second_args,
        )

        second_portfolio = (
            Path(
                str(
                    second_prefix
                )
                + ".portfolio.json"
            )
        )

        second_report = (
            Path(
                str(
                    second_prefix
                )
                + ".report.json"
            )
        )

        second_external = (
            Path(
                str(
                    second_prefix
                )
                + ".external"
            )
        )

        _require_file(
            second_portfolio,
            label="second Alpha6 portfolio",
        )

        _require_file(
            second_report,
            label="second Alpha6 report",
        )

        parsed_second_report = (
            NoveltyRefinementReport
            .model_validate_json(
                second_report.read_text(
                    encoding="utf-8"
                )
            )
        )

        assert_second_alpha6_did_not_keep_h1(
            parsed_second_report
        )

        h2_n10_details = (
            branch_dir
            / "h2_n10_details"
        )

        h2_portfolio = (
            branch_dir
            / "h2_n10.portfolio.json"
        )

        h2_report = (
            branch_dir
            / "h2_n10.enforcement.json"
        )

        h2_n10_args = (
            build_fresh_h2_n10_args(
                second_alpha6_portfolio=(
                    second_portfolio
                ),
                hypothesis_context=(
                    work_item
                    .hypothesis_context
                ),
                second_alpha6_report=(
                    second_report
                ),
                second_alpha6_external_dir=(
                    second_external
                ),
                provider_plan=(
                    args.provider_plan
                ),
                domain_profile=(
                    args.domain_profile
                ),
                model=(
                    args.critic_model
                    or args.model
                ),
                base_url=(
                    args.base_url
                ),
                api_key_env=(
                    args.api_key_env
                ),
                results_per_query=(
                    args.results_per_query
                ),
                work_dir=(
                    h2_n10_details
                ),
                output_portfolio=(
                    h2_portfolio
                ),
                output_report=(
                    h2_report
                ),
            )
        )

        _run(
            "scripts.discovery.enforce_alpha6_nonobviousness",
            h2_n10_args,
        )

        _require_file(
            h2_portfolio,
            label="fresh H2 N10 portfolio",
        )

        _require_file(
            h2_report,
            label="fresh H2 N10 report",
        )

        h2_enforcement = _load_json(
            h2_report
        )

        depth_audit = (
            build_depth_one_terminal_audit(
                enforcement_report=(
                    h2_enforcement
                )
            )
        )

        depth_audit_path = (
            branch_dir
            / "depth_one_terminal_audit.json"
        )

        _write_json(
            depth_audit_path,
            {
                "schema_version":
                    "n10-post-generation-depth-one-terminal-audit-v1",

                "continuation_input_candidate_id":
                    candidate_id,

                "continuation_depth":
                    1,

                "rows":
                    depth_audit,

                "production_authority":
                    False,
            },
        )

        h2_filtered = (
            HypothesisPortfolio
            .model_validate_json(
                h2_portfolio.read_text(
                    encoding="utf-8"
                )
            )
        )

        branches.append(
            {
                "source_hypothesis_id":
                    work_item
                    .source_hypothesis_id,

                "h1_candidate_id":
                    candidate_id,

                "continuation_depth":
                    1,

                "work_item":
                    str(
                        work_item_path
                    ),

                "lineage_projection":
                    str(
                        lineage_path
                    ),

                "reentry_gate":
                    str(
                        reentry_gate_path
                    ),

                "second_alpha6_portfolio":
                    str(
                        second_portfolio
                    ),

                "second_alpha6_report":
                    str(
                        second_report
                    ),

                "fresh_h2_n10_portfolio":
                    str(
                        h2_portfolio
                    ),

                "fresh_h2_n10_report":
                    str(
                        h2_report
                    ),

                "depth_one_terminal_audit":
                    str(
                        depth_audit_path
                    ),

                "fresh_h2_n10_survivor_count":
                    len(
                        h2_filtered.hypotheses
                    ),
            }
        )

    output = {
        "schema_version":
            "n10-bounded-post-generation-continuation-run-v1",

        "source_first_post_n10_report":
            str(
                args.first_post_n10_report
            ),

        "source_lineage":
            str(
                args.source_lineage
            ),

        "source_axis_plan":
            str(
                args.axis_plan
            ),

        "continuation_work_item_count":
            len(
                work_items
            ),

        "branches":
            branches,

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

    _write_json(
        args.output_report,
        output,
    )

    print(
        "Bounded post-generation continuation complete"
    )

    print(
        "Continuation work items:",
        len(
            work_items
        ),
    )

    print(
        "H2 survivors after fresh N10:",
        sum(
            int(
                row[
                    "fresh_h2_n10_survivor_count"
                ]
            )
            for row in branches
        ),
    )

    print(
        "Output report:",
        args.output_report,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
