# core-b03 internal notes

This challenge is an enterprise knowledge-base application. The document list correctly shows only `published` records, but the search endpoint queries a stale index without applying that visibility filter. A search for a normal business term can therefore reveal the archived annual security audit document. Its detail page exposes a dynamic attachment capability URL; the downloaded report contains `INSTANCE_FLAG`.

`VARIANT_SEED` derives three document identifiers. Public and archived attachments use per-process tokens. The issue is sensitive information disclosure through the search index, not SQL injection or authorization-role manipulation.
