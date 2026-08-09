# core-a02 internal notes

This challenge is an independent procurement-order application. The intentional flaw is in `GET /api/orders/<order_id>`: authentication is required, but ownership is not checked. The foreign order number is exposed only as a business reference in the cross-department announcement. The foreign response discloses a per-process attachment capability URL; the attachment contains `INSTANCE_FLAG`.

`VARIANT_SEED` derives both order numbers. The attachment token is regenerated when the container starts, so reset invalidates old attachment URLs. The app is in-memory and has no database or host-file access.
