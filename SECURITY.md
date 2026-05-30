# Security Policy

## Reporting Security Issues

Do not open public issues for vulnerabilities, leaked credentials, tokens, exploit details, or sensitive operational data.

Use GitHub private vulnerability reporting if it is enabled for this repository. If private reporting is unavailable, contact the repository owner through GitHub and share only the minimum non-sensitive details needed to start triage.

## Scope

This policy covers source code, configuration, documentation, GitHub Actions, generated-data handling, and deployment guidance for this repository.

## Sensitive Data Rules

- Never commit `.env` files, credentials, database URLs with passwords, API tokens, private keys, certificates, session cookies, or generated production data.
- Do not paste secrets into issues, pull requests, commit messages, logs, screenshots, or documentation.
- Redact secret values before sharing diagnostics.
- Treat generated clinical, partner, QMS, audit, monitoring, and export data as local/runtime artifacts unless explicitly approved for publication.

## Dependency And Supply Chain Expectations

- Review Dependabot pull requests before merging.
- Prefer small dependency updates that can be tested quickly.
- Run available tests, builds, and preflight checks before merging security-sensitive changes.

## Supported Branches

The default branch is the protected development baseline. Security fixes should be proposed through pull requests unless an emergency owner-approved hotfix is required.
