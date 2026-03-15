# Contributing to GAIA-Server

Please see the [GAIA-Core Contributing Guide](https://github.com/xxkylesteenxx/GAIA-Core/blob/main/.github/CONTRIBUTING.md)
for full contribution workflow, branch naming, commit message, and code style standards.

Server-specific notes:
- All storage and bootstrap changes must go through GAIA-Core first
- Daemon / service configuration changes live in `gaia_server/services/`
- New features require tests in `tests/`
