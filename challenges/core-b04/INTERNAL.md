# core-b04 internal notes

This challenge is an audit-query business application. The personal department query filters records by the logged-in actor, but the normal “all departments” selector expands the candidate set and forgets that actor constraint. This is a broken data-filtering issue, not SQL injection and not a direct `user_id` role switch.

The leaked internal event can be exported through the normal report workflow. The per-process report token is dynamic and the report embeds `INSTANCE_FLAG`. `VARIANT_SEED` derives all event identifiers.
