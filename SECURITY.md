# Security Policy

## Supported Versions

`pyfallow` is currently pre-1.0. Security fixes are expected to target the latest released version.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting Vulnerabilities

Do not include sensitive vulnerability details in public issues.

This repository does not yet publish a private security contact. Until one exists:

- use GitHub issues only for non-sensitive security hardening reports
- ask maintainers to establish a private contact before sharing sensitive details
- do not include secrets, tokens, private repository content, or exploit payloads in public reports

## Analyzer Safety Model

`pyfallow` must never execute analyzed project code. It must not:

- import analyzed project modules
- run `setup.py`
- evaluate arbitrary project expressions
- call external AI services
- require network access at runtime

This makes pyfallow safer for untrusted repositories, but it is still a local file analyzer. Run it with normal care when inspecting untrusted code.

