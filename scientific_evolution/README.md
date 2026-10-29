# Scientific Evolution — V4 active runtime snapshot

This folder is a **source-preserving checkpoint**, not a refactored or experimentally validated new AI Scientist. It records the code that implements the V2 Claim–Problem Delta → V3 Closed Loop → V4 Research Readiness path, using `e2core` from the live WSL runtime. The Clean Baseline entrypoint is included without changing its model prompts, source pins, or journal contracts.

## Scope

- `runtime/e2core/`: journal, provider, engine, tools, long campaign and package-local support modules, copied without modification.
- `runtime/scientific_problem_evolution.py`, `scientific_problem_autorun.py`, `science_frontier_campaign.py`: V2 + opportunity evaluation.
- `runtime/scientific_closed_loop_v3.py`: scientific-event and reuse extension.
- `runtime/scientific_research_readiness_v4.py`: theory/computation/empirical readiness extension.
- `runtime/scientific_v4_clean_baseline.py`: checkpointed command entrypoint.
- `checks/`: original per-version no-paid tests; `background/`: contemporaneous docs.
- `SOURCE_MANIFEST.json`: SHA256 of all captured source files.

**Excluded:** V5 arbitration and its recovery patches, historical research evaluation ROOTs, model requests/responses, provider billing data, API keys, journals, datasets, notebooks, archives and logs.

This snapshot has *not* been substituted into an ongoing paid process. An existing run should continue using its original version-pinned source paths. Use this snapshot for source review, local regression tests and later consolidation; if starting a new run from the snapshot, run preflight on a newly forked research ROOT and check source pins first.

## No-paid checks (requires the existing graphAgent311 environment)

```bash
conda activate graphAgent311
unset FAKG_RESEARCH_ALLOW_PAID
cd scientific_evolution
export PYTHONPATH="$PWD/runtime"
python -m compileall -q runtime
python -m unittest discover -s checks/v3 -p 'test_*.py' -q
python -m unittest discover -s checks/v4 -p 'test_*.py' -q
python -m unittest discover -s checks/clean -p 'test_*.py' -q
```

Note that tests validate internal contracts using controlled fixtures/mocks; they cannot replace a real WSL integration preflight and do not demonstrate Level II attainment.

## Provenance & code drift

The initial six core files and the V4 wrapper are SHA256-pinned by the running research software. Copies here retain the same bytes, verified by `SOURCE_MANIFEST.json`. When consolidation/refactoring is planned, create a **new execution branch and new root** rather than modifying the code used by an existing journal.

## Security

Never commit `$HOME/GraphAgentsDAC/evaluation`, `.env`, API keys or any file from the research ROOT. Use a separate Git worktree and inspect `git status`, `git diff --cached` before pushing.
