# Iterative Implementation Plan

This plan is the operational source for building, rerunning, and updating the UTCM exporter.

## Step 1: Authentication and Basic Connectivity (Implemented)
Goal:
- Set up project with `uv`.
- Implement app-only Graph auth in `auth.py`.
- Verify tenant connectivity.

Implementation:
- `src/utcm_exporter/auth.py`
- `scripts/test_graph_connectivity.py`

Validation command:
- `uv run scripts/test_graph_connectivity.py`

Expected:
- Logs tenant `displayName` and `id` from `GET /v1.0/organization`.

## Step 2: Snapshot Trigger and Polling (Implemented)
Goal:
- Create UTCM snapshot jobs and poll until completion.

Implementation:
- `src/utcm_exporter/utcm_client.py`
- `scripts/run_utcm_snapshot.py`

Key behaviors:
- Unique valid `displayName` per run.
- Handles `409` conflicts.
- Treats `succeeded` and `partiallySuccessful` as terminal.
- Parses Graph validation errors.
- Auto-removes resource IDs reported as unsupported and retries.

Validation command:
- `uv run scripts/run_utcm_snapshot.py --resources microsoft.entra.conditionalaccesspolicy microsoft.teams.meetingpolicy`

Expected:
- Prints `resourceLocation` URL on success.

## Step 3: Download, Parse, and Persist Files (Implemented)
Goal:
- Download snapshot JSON and unpack to deterministic YAML files.

Implementation:
- `src/utcm_exporter/parser.py`
- `scripts/parse_snapshot.py`

Key behaviors:
- Output path: `tenant_state/{workload}/{resource_type}/{name}.yaml`
- Stable YAML formatting for Git-friendly diffs.
- Filename fallback supports both instance-level and resource-level display names.
- Teams meeting policy display names are normalized from `Prefix-Name` to `Name`.
- Default prune mode removes stale files and empty directories.
- Optional debug raw snapshot dump.

Validation command:
- `uv run scripts/parse_snapshot.py "<resourceLocation>" --output-dir tenant_state --debug`

Expected:
- Fresh YAML tree under `tenant_state/`
- Raw snapshot JSON under `tenant_state/_debug/` when `--debug` is set.

## Step 4: Git Historization Automation (Deferred)
Status:
- Not implemented yet by design.

Target:
- Add orchestrator logic to run `git add`, detect diffs, and commit timestamped changes.

## Step 5: Scale to All Supported Resources (Implemented)
Goal:
- Export all supported UTCM resources using docs-driven catalog.

Implementation:
- `src/utcm_exporter/resources_catalog.py`
- `scripts/build_resources_catalog.py`
- `resources.json`
- `scripts/run_utcm_snapshot.py` (default source: `resources.json`)

Key behaviors:
- Catalog generated from official UTCM docs pages, not schema-only source.
- Missing docs pages are skipped with warnings.
- Runtime fallback removes Graph-rejected resource IDs and retries.

Validation commands:
1. Build catalog  
`uv run scripts/build_resources_catalog.py --output resources.json`
2. Run full snapshot  
`uv run scripts/run_utcm_snapshot.py`

Expected:
- Snapshot job starts with docs-derived resources.
- If Graph rejects some resource IDs as unsupported, job retries with filtered list.

## Day-2 Operations
- Cleanup old snapshot jobs:
`uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7 --dry-run`
- Then apply cleanup:
`uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7`
