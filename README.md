# UTCM Exporter

UTCM Exporter is a Python toolset that snapshots Microsoft 365 tenant configuration through Microsoft Graph UTCM beta APIs and writes deterministic YAML files for Git-based historization and diff tracking.

## Scope

The project currently covers:
- App-only authentication using `msal` client credentials.
- UTCM snapshot creation and async polling.
- Snapshot JSON download.
- Parsing into structured YAML files in `tenant_state/`.
- Docs-driven resource catalog generation (`resources.json`).
- Snapshot job cleanup utilities.

Planned later:
- Step 4 Git automation (auto `git add`/diff/commit) is intentionally deferred.

## Output Structure

Exported state is written to:

`tenant_state/{workload}/{resource_type}/{resource_display_name_or_id}.yaml`

Examples:
- `tenant_state/entra/conditionalaccesspolicy/Require_MFA_For_Admins.yaml`
- `tenant_state/exchange/transportrule/Block_External_Forwarding.yaml`
- `tenant_state/teams/meetingpolicy/Global.yaml`

## Prerequisites

- Python 3.12+
- `uv`
- `.env` with:
  - `AZURE_TENANT_ID`
  - `AZURE_CLIENT_ID`
  - `AZURE_CLIENT_SECRET`
- Required UTCM and workload permissions/roles assigned in tenant

## Install

```bash
uv sync
```

## Script Usage

### 1) Test Graph auth

```bash
uv run scripts/test_graph_connectivity.py
```

Expected: logs your tenant `displayName` and `id`.

### 2) Build resource catalog from official docs

Generates `resources.json` with supported UTCM resource IDs from docs pages.

```bash
uv run scripts/build_resources_catalog.py --output resources.json
```

### 3) Run snapshot job

Default: uses resources from `resources.json`.

```bash
uv run scripts/run_utcm_snapshot.py
```

Test mode with explicit resources:

```bash
uv run scripts/run_utcm_snapshot.py --resources \
  microsoft.entra.conditionalaccesspolicy \
  microsoft.teams.meetingpolicy
```

The command prints a `resourceLocation` URL when the job completes.

### 4) Parse snapshot into YAML files

```bash
uv run scripts/parse_snapshot.py "<resourceLocation>" --output-dir tenant_state --debug
```

Notes:
- Pruning stale files is enabled by default.
- Use `--no-clean` to disable prune.
- `--debug` writes raw snapshot JSON to `tenant_state/_debug/` (or `--debug-file <path>`).

### 5) Cleanup old snapshot jobs

Dry run:

```bash
uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7 --dry-run
```

Delete:

```bash
uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7
```

## Operational Notes

- Snapshot jobs can return `partiallySuccessful`; this is treated as terminal.
- Some resource IDs may be listed in docs but rejected by backend as unsupported at runtime.
- The snapshot client auto-removes unsupported resource types reported by Graph and retries.

## Project Docs

- `PLAN.md`: implementation milestones and validation checks.
- `AGENTS.md`: coding and architecture rules for AI-driven development.
- `RUNBOOK.md`: concise day-2 command reference.
