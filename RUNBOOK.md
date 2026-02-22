# UTCM Exporter Runbook

## Prerequisites
- Python 3.12+
- `uv`
- Azure app registration credentials in `.env`
- UTCM service principal permissions/roles granted in tenant

## 1) Install/Sync Dependencies
```bash
uv sync
```

## 2) Verify Graph Connectivity
```bash
uv run scripts/test_graph_connectivity.py
```

## 3) Build/Refresh Full Resource Catalog
```bash
uv run scripts/build_resources_catalog.py --output resources.json
```

## 4) Run Snapshot
Default full run from `resources.json`:
```bash
uv run scripts/run_utcm_snapshot.py
```

Quick test with explicit resources:
```bash
uv run scripts/run_utcm_snapshot.py --resources \
  microsoft.entra.conditionalaccesspolicy \
  microsoft.teams.meetingpolicy
```

## 5) Parse Snapshot to YAML
```bash
uv run scripts/parse_snapshot.py "<resourceLocation>" --output-dir tenant_state --debug
```

Notes:
- Prune mode is enabled by default.
- Use `--no-clean` to keep old files.
- Use `--debug-file <path>` to control raw JSON dump location.

## 6) Cleanup Old Snapshot Jobs
Preview:
```bash
uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7 --dry-run
```

Delete:
```bash
uv run scripts/cleanup_snapshot_jobs.py --older-than-days 7
```

## 7) Refresh Cycle
When docs or APIs change:
1. Rebuild catalog (`build_resources_catalog.py`)
2. Re-run snapshot
3. Parse with debug dump
4. Review missing resources from requested vs exported set
