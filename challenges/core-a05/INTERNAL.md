# core-a05 internal notes

This is an independent contract-review application with `draft -> submitted -> reviewing -> approved` business states. The `GET /api/contracts/<contract_id>/review` endpoint checks only that the target contract is `approved`; it does not check that the authenticated user has the reviewer role. A completed contract number is discoverable in the activity record, and the review response yields a per-process final attachment URL containing `INSTANCE_FLAG`.

`VARIANT_SEED` derives the own and approved-contract identifiers. The attachment token changes when the container is recreated, and no database, host mount, or shared challenge implementation is used.
