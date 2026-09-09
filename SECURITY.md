# Security Policy

## Reporting a vulnerability

**Do not file a public issue.** Email security@jacobwu.org with:

- A description of the issue
- Steps to reproduce
- The version/commit affected
- Any known mitigations

We aim to acknowledge within 2 business days and provide a remediation timeline within 7.

## Scope

In scope: this repository, its deployed instances, its first-party dependencies.

Out of scope: third-party services we integrate with (report directly to them), social engineering, physical attacks, denial of service.

## Secrets

This codebase reads secrets only from environment variables, only via the configured config layer (see `CLAUDE.md` §6). If you find a secret committed to git history, treat it as a P0 — rotate the secret first, then file a remediation issue.
