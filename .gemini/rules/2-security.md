# Security Guardrails

- **Zero Credentials:** Never commit, display, or generate passwords, real session tokens, private API keys, or cookies.
- **Zero Private Identifiers:** Use RFC 5737 placeholders (e.g., `192.168.1.100`, `admin`, `camera1`). Never use production or site-specific IPs, domains, or hostnames.
- **Local Settings Isolation:** Keep sensitive settings in local `.env` (git-ignored). Expose template fields solely through `.env.example`.
- **Safe I/O Operations:** Always use temporary `.part` files during downloads and verify complete transfer before renaming to final media names.