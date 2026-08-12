# B Group Build Report

Date: 2026-08-09

Scope: `core-b03`, `core-b04`, and `core-b05`. The completed `core-a01` through
`core-a05` implementations were preserved.

## Summary

| Check | Result |
|---|---|
| Build | PASS |
| Health | PASS |
| Solver | PASS |
| Reset | PASS |
| Variant | PASS |

## Build

Built each challenge from its directory-local context:

```text
docker build -t ctf-agent-range/core-b03:latest challenges/core-b03
docker build -t ctf-agent-range/core-b04:latest challenges/core-b04
docker build -t ctf-agent-range/core-b05:latest challenges/core-b05
```

All three images use an independent `app/app.py`, expose port 5000, and set
`USER 10001`. Static checks found no `advanced_app.py`, challenge-ID simulation,
privileged mode, Docker socket, or host-volume reference in the B group.

## Health and normal flow

- B03 `/health` returned `{"status":"ok","challenge":"core-b03"}`. The
  published document list excluded the archived report; authenticated search
  discovered it through the stale index.
- B04 `/health` returned the exact challenge ID. A normal engineering query
  returned the two personal records, and a personal-record export did not
  contain a Flag.
- B05 `/health` returned the exact challenge ID. Login, profile, normal upload,
  file listing, processing details, preview, and owner-only download paths were
  exercised.

## Solver and reset

Each B solver dynamically discovered document/event/file identifiers and runtime
attachment, report, or preview tokens. Backend instance tests used the real
`/api/v1/instances` lifecycle:

- B03: solver submission passed; after reset with a regenerated variant, the old
  Flag was rejected and the new solver result was accepted.
- B04: solver submission passed; after reset, stale submission returned
  `correct=false`, and the new result was accepted.
- B05: solver submission passed; after reset, stale submission returned
  `correct=false`, and the new result was accepted.

## Variant

Separate containers with different `VARIANT_SEED` values produced different
business identifiers for all three challenges:

- B03 knowledge-base document IDs changed.
- B04 audit event IDs changed.
- B05 review file IDs changed.

The B03, B04, and B05 solvers continued to discover the current data rather than
relying on hard-coded IDs or tokens.

## Regression checks

- B03-B05 metadata boundary tests: `3 passed`.
- Python compilation passed for `backend/app` and A/B challenge applications.
- A02-A05 real backend instance solver smoke passed.
- A01 real backend solver passed through the existing
  `backend/tests/challenge_solvers/solve_core_a01.py` entry point.
- The repository's A01 pytest files require external `base_url` and
  `reset_instance` fixtures that are not present in this checkout; running them
  directly produced four fixture-setup errors. No A files were changed.

## Operational note

The current backend `build_if_needed` path reuses an existing image tag. During
validation, the three `:latest` images were explicitly rebuilt from the new
directory contexts before backend instance tests, so stale pre-refactor images
were not used.
