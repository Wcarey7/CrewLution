# CrewLution Architecture

High-level architecture for the CrewLution Django application — a multi-tenant field-service CRM with quotes, jobs, invoices, and scheduling.

> **Interactive version (Cursor Canvas):** Open [crewlution-architecture.canvas.tsx](canvases/crewlution-architecture.canvas.tsx) beside chat. For the live canvas panel, copy or sync this file to `~/.cursor/projects/c-dev-CrewLution/canvases/crewlution-architecture.canvas.tsx` — Cursor only renders canvases from that managed folder.

## Overview

| Aspect | Detail |
|--------|--------|
| Framework | Django 5.x (API + legacy templates) |
| Frontend | Next.js 15 (`frontend/`) — Phase 1: auth + dashboard |
| Database | PostgreSQL |
| Auth | Stock `django.contrib.auth.models.User` |
| Multi-tenancy | Row-level isolation via `company` FK + session `active_company_id` |
| Static files | WhiteNoise (`CompressedManifestStaticFilesStorage` in production) |

### Django apps

| App | Responsibility |
|-----|----------------|
| `accounts` | Companies, memberships, roles, invites, team management, client portal links, settings |
| `crm` | Customers, contacts, locations, notes, activity timeline |
| `commerce` | Quotes, jobs, invoices, line items, schedule view, dashboard metrics |
| `crewlution` | Project package — landing, dashboard, signup, company switching, root URLs |

## Multi-tenancy

1. Every user belongs to one or more companies through `CompanyMembership`.
2. `ActiveCompanyMiddleware` reads `session["active_company_id"]` and attaches `request.company` and `request.membership`.
3. If the session company is invalid, the middleware falls back to the user's first active membership (ordered by company name).
4. All CRM and commerce queries filter by `request.company`.

## Middleware & context

| Component | Purpose |
|-----------|---------|
| `ActiveCompanyMiddleware` | Resolves active company and membership |
| `AdminSuperuserOnlyMiddleware` | Restricts Django admin to superusers |
| `nav_companies` context processor | Company switcher in app shell |
| `crm_permissions` context processor | Template flags for write/delete capabilities |

## Permission model

Roles are stored on `CompanyMembership` — not Django groups.

| Capability | Owner | Admin | Dispatcher | Tech | Viewer |
|------------|:-----:|:-----:|:----------:|:----:|:------:|
| Read CRM & commerce | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write CRM & commerce | ✓ | ✓ | ✓ | | |
| Delete CRM / void invoices | ✓ | ✓ | | | |
| Manage team invites | ✓ | ✓ | | | |
| Edit company settings | ✓ | ✓ | | | |

Enforcement: `crm.access.can_write_crm()` and `can_delete_crm()` in views; `@company_required` decorator on app views.

## Services layer

Only `commerce` uses a dedicated services package:

| Module | Functions |
|--------|-----------|
| `commerce/services/transitions.py` | Quote/job/invoice state transitions with validation |
| `commerce/services/line_items.py` | `recalculate_total`, `copy_line_items` |
| `commerce/services/dashboard.py` | `workflow_counts`, `today_appointments`, `business_performance` |
| `commerce/services/schedule.py` | `month_schedule`, `week_schedule`, `jobs_for_range` for calendar views |

CRM side effects use Django signals (`crm/signals.py`) rather than a service layer.

## URL structure

```
/                           landing
/dashboard/                 dashboard
/accounts/signup/           signup
/join/<token>/              invite accept
/portal/<token>/            client magic link (read-only quotes/jobs/invoices)
/app/settings/company/      company settings
/app/settings/client-hub/   client portal link management
/app/team/                  team members + invites
/app/crm/...                CRM (customers, contacts, locations)
/app/schedule/              month/week calendar (?view=month|week)
/app/quotes/...             quotes CRUD
/app/jobs/...               jobs CRUD + locations JSON API
/app/invoices/...           invoices CRUD
/{ADMIN_PATH}/              Django admin (superuser only)
```

## Human-readable references

Per-company auto-sequenced IDs:

| Model | Format | Example |
|-------|--------|---------|
| Quote | `QT-{sequence:05d}` | QT-00001 |
| Job | `JB-{sequence:05d}` | JB-00001 |
| Invoice | `INV-{sequence:05d}` | INV-00001 |

## Related docs

- [Software design document (SDD)](SDD.md) — formal design spec
- [OpenAPI spec (openapi.yaml)](openapi.yaml) — REST API contract for Next.js client
- [Database schema (DBML)](schema.dbml) — import at dbdiagram.io
- [SQL DDL (PostgreSQL)](schema.sql) — CREATE TABLE statements
- [Database schema](database-schema.md) — models, fields, relationships, constraints
- [Workflows](workflows.md) — user journeys and commerce state machine
