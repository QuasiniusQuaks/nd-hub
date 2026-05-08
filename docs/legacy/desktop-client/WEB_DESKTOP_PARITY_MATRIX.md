!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Web/Desktop Parity Matrix

This matrix tracks parity of `ndhub-web` features in the **desktop-client** (PySide6) application.

## Legend
- `done`: implemented in desktop
- `partial`: available but missing web-equivalent depth
- `todo`: missing in desktop

## Feature Matrix

| Domain | Web capability | Desktop status | Desktop target |
|---|---|---|---|
| Sync | `/sync/status`, `/sync/pull`, `/sync/push` | partial | extend sync monitoring and ops visibility |
| Sync tokens | `/auth/desktop-sync-token*` create/list/revoke | todo | desktop admin token lifecycle UI |
| Sync ops | `/sync/ops/stats` | todo | desktop sync ops snapshot |
| Audit | `/audit-logs` with filters/paging | partial | dedicated desktop audit tab |
| Users | reset/unlock + permission catalog | partial | unlock action + permissions visibility |
| Onboarding | `/onboarding/status`, `/onboarding/institution-setup` | todo | guided desktop setup assistant |
| Geo/Map | `/geo/geocode`, `/map/institutions` | todo | geocode helper for institutions |
| Email | drafts + optional send-now + delivery status | partial | send-now toggle + status history in desktop |
| Import | preview diagnostics + execute summary/fingerprint | partial | richer diagnostics and import run summary |

## Phase Mapping

1. Sync parity (`core/*`, settings sync tab)
2. Security/admin parity (audit + user unlock/permissions)
3. Onboarding + geocode helper
4. Email/import parity improvements
5. Hardening (tests, migration safety, rollout checks)

## Verification Checklist

- Hybrid sync works with remote backend and local fallback.
- Token lifecycle can be managed directly from desktop.
- Audit data is queryable in desktop without SQL access.
- User unlock/reset flows are available to admins.
- Onboarding assistant can bootstrap a fresh deployment.
- Email/import flows provide operational status feedback.
