# UTCM Exporter

This project uses AI coding tools (for example, Claude Code or similar) to generate and evolve a Python application that exports Microsoft 365 tenant configuration resources into a Git-friendly folder structure.

The goal is to:
- Trigger a UTCM snapshot from Microsoft Graph beta.
- Download the snapshot JSON once the async job succeeds.
- Split resources into deterministic files for historization and diff tracking in Git.

## What The Export Should Produce

All exported state is written under:

`tenant_state/{workload}/{resource_type}/{resource_display_name_or_id}.json`

This supports both single-instance and multi-instance resource types:
- Category/workload becomes a subfolder (for example `entra`, `exchange`, `teams`).
- Resource type becomes a nested subfolder (for example `conditionalaccesspolicy`, `transportrule`).
- Each resource instance becomes one JSON file.

Examples:
- `tenant_state/entra/conditionalaccesspolicy/Require_MFA_For_Admins.json`
- `tenant_state/exchange/transportrule/Block_External_Forwarding.json`

## Technical Requirements

- Authentication: `msal` client credentials flow with values from `.env`.
- HTTP: `requests`.
- Dependency management: `uv` (not `requirements.txt`).
- Logging: Python `logging` (no basic `print` for progress).
- File naming: sanitize invalid characters (`\ / : * ? " < > |`).
- JSON formatting: `indent=2` and `sort_keys=True` for stable diffs.
- Filename fallback: use `displayName`, then `name`, then `id`.

## Microsoft Graph UTCM Flow (Beta)

1. Start snapshot job  
   `POST /beta/admin/configurationManagement/configurationSnapshots/createSnapshot`
2. Poll snapshot job  
   `GET /beta/admin/configurationManagement/configurationSnapshotJobs/{jobId}` every 10-15 seconds until `succeeded`
3. Download snapshot result  
   Use `resourceLocation` URL returned by the completed job

## AI-Assisted Implementation Plan

Build the project iteratively to reduce risk:

1. Authentication and basic connectivity.
2. UTCM snapshot creation and async polling.
3. Snapshot download and resource-to-file unpacking.
4. Git historization automation (`git add`, diff check, timestamped commit when changed).
5. Scale resource coverage via `resources.json`.

See `PLAN.md` for the full milestone prompts and validation checks.
