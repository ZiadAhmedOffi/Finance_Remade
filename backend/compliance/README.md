# Compliance App

This app is the dedicated home for the KYC/KYB/AML domain.

It intentionally separates:

- platform identity/auth concerns in `users`
- investment operations in `funds` / `real_estate`
- compliance cases, screenings, restrictions, and monitoring in `compliance`

Phase 1 scaffolding introduced here is intentionally structural:

- first-class compliance models
- gating and case-management service boundaries
- applicant and reviewer/admin API scaffolding
- vendor adapter normalization boundary
- queue/worker dispatch boundary with inline fallback mode
- vendor submission, sync, webhook, and rescreen workflow stubs

Implementation should keep policy and workflow decisions here rather than
leaking them into other apps.
