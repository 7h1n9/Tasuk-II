# core-a04 internal notes

The application uses a real Jinja2 `Environment` with `StrictUndefined`. Normal help documents three business variables, while the preview renderer also passes an `application.settings` dictionary into the template context. An invalid variable produces an error response listing context roots; the accidental `application` root then permits reading `application.settings.notice_footer`, which contains the dynamic `INSTANCE_FLAG`.

There is no string-search shortcut for the payload. The container has no application write path, no host mounts, no Docker socket, and runs as UID 10001. `VARIANT_SEED` changes template identifiers and the employee alias.
