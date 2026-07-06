# CrewLution — Software Design Document (SDD)

**Version:** 1.1  
**Last updated:** 2026-06-08  
**Status:** Target architecture (planned)

---

## 1. Overview

CrewLution is a multi-tenant field-service CRM for small service businesses. It supports client management, quotes, jobs, invoicing, scheduling, team collaboration, and a read-only client portal. The product goal is to provide a Jobber-style operational workflow (lead → quote → job → invoice) with strong company isolation and role-based access.

The **target system** is a **Next.js presentation tier** talking to a **Django REST API** backed by **PostgreSQL**. Business rules live in Django service modules; the frontend is a thin, typed consumer of JSON (and binary PDF) endpoints.

### 1.1 Goals

| Goal | Description |
|------|-------------|
| **Operational workflow** | Quotes convert to jobs; completed jobs convert to invoices with line-item totals carried forward. |
| **Multi-tenancy** | Every business (company) has isolated data; users may belong to multiple companies. |
| **Role-based access** | Owner, Admin, Dispatcher, Tech, and Viewer roles gate create/edit/delete actions. |
| **Field-service scheduling** | Jobs have schedule times; calendar month/week views surface upcoming work. |
| **Client communication** | Magic-link client portal, PDF download for quotes/invoices; email delivery in a later phase. |
| **Separation of concerns** | Next.js owns UX and routing; Django owns persistence, authorization, and domain logic. |
| **API-first backend** | All staff and portal features exposed through versioned REST endpoints suitable for future mobile clients. |

### 1.2 Scope

**In scope (target release)**

- Next.js App Router staff application (`/app/*`)
- Django REST API (`/api/v1/*`) with OpenAPI schema
- User signup, login, logout, password reset
- Company creation on signup; multi-company membership and switching
- CRM: customers, contacts, locations, notes, activity timeline
- Commerce: quotes, jobs, invoices, line items, state transitions
- Schedule: month/week calendar for scheduled jobs
- Dashboard: workflow counts, today's appointments, business performance cards
- Settings: company profile, business hours, client hub link management
- Team: member list (role, active/inactive), invite links
- Client portal: tokenized read-only view of quotes/jobs/invoices (Next.js public route + API)
- PDF download for quotes and invoices (staff)
- Django admin for superusers (internal tooling, not primary UX)

**Out of scope (target release)**

- Native mobile apps (API designed to support them later)
- Third-party OAuth / SSO
- Email/SMS delivery of quotes and invoices
- Online payments, tax engine, recurring jobs
- Full client self-service (approve quote, pay invoice online)
- GraphQL API (REST chosen for simplicity and DRF ecosystem)

### 1.3 Implementation phases

| Phase | Presentation | Backend | Notes |
|-------|--------------|---------|-------|
| **0 — Current** | Django templates + static CSS/JS | Django function views, forms | Exists in repo today; domain models and service layer are the migration foundation |
| **1 — API shell** | Next.js auth + app shell + dashboard | DRF `/api/v1/auth/*`, `/dashboard/` | Cookie/JWT auth, company header, CORS |
| **2 — Feature parity** | CRM, commerce, schedule, settings, team, portal | Full REST surface per §4 | Deprecate Django HTML routes |
| **3 — Comms & growth** | Email send UI, reminders | Celery + SMTP/API, webhooks | Builds on PDF + status transitions |

### 1.4 Migration path

| Component | Action |
|-----------|--------|
| PostgreSQL schema | **Keep** — no tenancy model change |
| Django models | **Keep** |
| Service layer (`commerce/services/*`, `accounts/*`) | **Keep** — API views delegate here |
| Django templates / form views | **Replace** by Next.js pages calling API |
| Session-only auth | **Extend** with HttpOnly refresh cookie + short-lived access JWT (or equivalent secure cookie pair) |
| `ActiveCompanyMiddleware` | **Adapt** to read `X-Company-Id` header or JWT claim |
| WhiteNoise for app UI | **Remove** for staff UX; Next.js serves static assets |
| Django admin | **Keep** for superuser operations |

---

## 2. Architecture

### 2.1 Target logical stack

```
┌──────────────────────────────────────────────────────────────┐
│  Presentation — Next.js 15+ (App Router)                     │
│  React Server Components + client components for interactivity│
│  Routes: /, /login, /app/*, /portal/[token]                  │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTPS (JSON + binary PDF)
                              │ Authorization: Bearer / cookie
                              │ Tenancy: X-Company-Id header
┌─────────────────────────────▼────────────────────────────────┐
│  API — Django 5.x + Django REST Framework                    │
│  api/v1/  │  accounts │ crm │ commerce │ crewlution          │
│  Thin viewsets → existing service modules                    │
└─────────────────────────────┬────────────────────────────────┘
                              │ psycopg
┌─────────────────────────────▼────────────────────────────────┐
│  PostgreSQL 15+                                              │
└──────────────────────────────────────────────────────────────┘

Optional (Phase 3+): Redis (cache, Celery broker), object storage for logos
```

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Presentation** | Next.js 15+, TypeScript, React | Routing, forms, calendar UI, permission gates, API client |
| **API** | Django 5.x, DRF, Python 3.12 | Auth, authorization, validation, serialization, PDF bytes |
| **Database** | PostgreSQL 15+ | Single DB, row-level tenancy |
| **Admin** | Django admin (secret path) | Superuser-only internal CRUD |
| **PDF** | `xhtml2pdf` (server-side) | HTML template → PDF; API returns `application/pdf` |

### 2.2 Repository layout (planned)

Monorepo at repository root:

```
CrewLution/
├── backend/                 # Django project (migrated from current root layout)
│   ├── accounts/
│   ├── api/                 # DRF routers, serializers, permissions
│   ├── commerce/
│   ├── crm/
│   └── crewlution/
├── frontend/                # Next.js application
│   ├── app/
│   │   ├── (auth)/          # login, signup, password reset
│   │   ├── (app)/           # staff shell — dashboard, crm, commerce, settings
│   │   └── portal/[token]/  # public client hub
│   ├── components/
│   ├── lib/api-client.ts
│   └── hooks/
├── docs/
│   ├── SDD.md
│   ├── schema.dbml
│   └── openapi.yaml         # Generated or hand-maintained API spec (planned)
└── docker-compose.yml       # web (Django), frontend (Next), db, redis (optional)
```

Phase 0 code currently lives at repo root without `backend/` / `frontend/` split; the migration restructures without changing domain behavior.

### 2.3 Presentation tier (Next.js)

| Area | Design |
|------|--------|
| **Routing** | App Router with route groups: `(auth)` public, `(app)` protected staff shell, `portal/[token]` public |
| **Data fetching** | Server Components fetch via internal API URL where appropriate; client components use SWR/React Query for mutations and live views (schedule) |
| **Auth guard** | Next.js middleware checks session cookie / token; redirects unauthenticated users to `/login` |
| **Active company** | Stored in HttpOnly cookie or client-readable preference synced with `POST /api/v1/companies/active/`; all API calls send `X-Company-Id` |
| **Permissions** | `GET /api/v1/auth/me/` returns role flags; UI hides destructive actions; API enforces regardless |
| **Forms** | React Hook Form (or equivalent) posting JSON to REST endpoints |
| **Schedule** | Client component; fetches `GET /api/v1/schedule/` with `view=month\|week` |
| **Line items** | Nested arrays in quote/job/invoice PATCH payloads |
| **PDF** | Link or fetch blob from `GET .../pdf/` endpoints |
| **Styling** | CSS modules or Tailwind; responsive grid for mobile field use |

### 2.4 API tier (Django + DRF)

| App | Responsibility |
|-----|----------------|
| `api` | Versioned routers, serializers, pagination, OpenAPI schema, global exception handler |
| `accounts` | Companies, memberships, invites, settings, portal token validation |
| `crm` | Customers, contacts, locations, notes, activity events |
| `commerce` | Quotes, jobs, invoices, line items, schedule, PDFs, dashboard metrics |
| `crewlution` | Project settings, middleware, landing redirect (optional) |

**Design rule:** API viewsets perform authz checks and call existing service functions (`accept_quote()`, `month_schedule()`, etc.). No duplicated transition logic in serializers beyond field validation.

### 2.5 Authentication flow

```
[Next.js login form]
    → POST /api/v1/auth/login/ { email, password }
    ← Set-Cookie: refresh (HttpOnly, Secure, SameSite=Lax)
    ← Body: { access_token, expires_in, user, memberships, active_company_id }

[Subsequent API calls]
    → Authorization: Bearer <access_token>
    → X-Company-Id: <company_id>

[Token refresh]
    → POST /api/v1/auth/refresh/ (refresh cookie)
    ← New access_token

[Logout]
    → POST /api/v1/auth/logout/
    ← Clears cookies; invalidates refresh server-side (allowlist in Redis or DB)
```

Signup creates `User` + `Company` + `CompanyMembership(OWNER)` and returns the same token shape as login.

Team invite accept: `POST /api/v1/invites/{token}/accept/` (authenticated or creates account in one step).

Client portal: **no JWT** — opaque URL token validated server-side on `GET /api/v1/portal/{token}/`.

### 2.6 Request lifecycle — Next.js (staff)

1. **Edge middleware** — verify auth cookie / token presence for `(app)` routes  
2. **Layout** — fetch `/api/v1/auth/me/` for user, companies, permissions  
3. **Page** — Server Component prefetch or client hook loads domain data  
4. **Mutation** — API client POST/PATCH/DELETE; handle 401 → refresh → retry once  
5. **Error boundary** — map API `{ detail, code }` to user-visible messages  

### 2.7 Request lifecycle — Django API

1. **SecurityMiddleware** — HTTPS headers  
2. **CorsMiddleware** — allowlisted Next.js origin (`CORS_ALLOWED_ORIGINS`)  
3. **Authentication** — JWT validation or session (admin only)  
4. **ActiveCompanyMiddleware** — resolve `request.company`, `request.membership` from `X-Company-Id` + user memberships  
5. **DRF view** — permission classes (`IsAuthenticated`, `IsCompanyMember`, `CanWriteCRM`, …)  
6. **Service call** — domain logic in `commerce/services/*`, etc.  
7. **Response** — JSON serializer or `HttpResponse` (PDF)  

### 2.8 Deployment topology

```
[Browser]
    → [CDN / Vercel / Node] — Next.js (frontend)
    → [Reverse proxy / TLS] — Django API (Gunicorn)
         ↓                              ↓
    Static assets                   PostgreSQL
                                    Redis (optional)
```

| Service | Env vars (examples) |
|---------|---------------------|
| **Next.js** | `NEXT_PUBLIC_API_URL`, `NEXTAUTH_SECRET` (if used) |
| **Django** | `DJANGO_SECRET_KEY`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `JWT_*`, `DJANGO_ADMIN_URL` |
| **Postgres** | Managed or Docker volume |

Django **does not** serve the staff UI in production. WhiteNoise remains for Django admin static files only.

### 2.9 Key integration points

| Integration | Phase | Notes |
|-------------|-------|-------|
| OpenAPI / Swagger | 1 | `/api/schema/` + `/api/docs/` via drf-spectacular |
| PDF generation | 2 | `xhtml2pdf`; binary responses from API |
| Email (SMTP/API) | 3 | Celery tasks triggered from API actions |
| Redis | 2–3 | Token denylist, cache, Celery broker |
| External auth (OAuth) | Future | Not in target release |

### 2.10 Architecture decision: REST over GraphQL

REST with DRF is chosen because:

- Existing Django service layer maps naturally to resource-oriented endpoints  
- OpenAPI gives Next.js typed client generation  
- Simpler caching, auth, and versioning for a CRUD-heavy CRM  
- GraphQL can be revisited if mobile clients need highly nested fetches  

---

## 3. Modules and services

### 3.1 Backend — `accounts`

| Module | Purpose |
|--------|---------|
| `models.py` | `Company`, `CompanyMembership`, `CompanyInvite`, `CustomerPortalLink` |
| `middleware.py` | `ActiveCompanyMiddleware` (header/JWT-aware) |
| `team_members.py` | Member role change, deactivate/reactivate |
| `business_hours.py` | JSON business hours normalization |
| `invite_tokens.py` | Token generation and SHA-256 hashing |
| `api/serializers.py` | Company, membership, invite, portal link serializers |
| `api/views.py` | Settings, team, invite accept, portal data |

### 3.2 Backend — `crm`

| Module | Purpose |
|--------|---------|
| `models.py` | Customer, Location, Contact, CustomerNote, ActivityEvent |
| `access.py` | `company_required`, `can_write_crm`, `can_delete_crm` |
| `signals.py` | Activity timeline on save events |
| `api/views.py` | Customer CRUD, nested contacts/locations/notes |

### 3.3 Backend — `commerce`

| Module | Purpose |
|--------|---------|
| `models/` | Quote, Job, Invoice, LineItem |
| `services/transitions.py` | Quote/job/invoice state machine |
| `services/line_items.py` | Total recalculation, copy on transition |
| `services/dashboard.py` | Workflow counts, appointments, performance metrics |
| `services/schedule.py` | Month/week calendar data |
| `services/documents.py` | PDF rendering |
| `api/views.py` | Commerce CRUD, actions, schedule, dashboard, PDF |

### 3.4 Backend — `api` (new)

| Module | Purpose |
|--------|---------|
| `urls.py` | `/api/v1/` router includes |
| `permissions.py` | DRF classes mirroring `CompanyMembership` methods |
| `pagination.py` | Cursor or page/limit for list endpoints |
| `exceptions.py` | Consistent `{ detail, code }` error bodies |
| `authentication.py` | JWT + refresh cookie handling |

### 3.5 Backend — `crewlution`

| Module | Purpose |
|--------|---------|
| `settings.py` | CORS, DRF, JWT, database |
| `middleware.py` | Admin lockdown |
| `wsgi.py` / `asgi.py` | Deployment entrypoints |

### 3.6 Frontend — `frontend/`

| Module | Purpose |
|--------|---------|
| `lib/api-client.ts` | Typed fetch wrapper, auth refresh, `X-Company-Id` injection |
| `lib/types.ts` | Generated from OpenAPI or hand-maintained DTOs |
| `middleware.ts` | Route protection for `(app)` group |
| `app/(auth)/` | Login, signup, password reset pages |
| `app/(app)/dashboard/` | Workflow + appointment + performance cards |
| `app/(app)/crm/` | Customer list, detail, unified create/edit |
| `app/(app)/quotes|jobs|invoices/` | List, detail, edit, line items, actions |
| `app/(app)/schedule/` | Month/week calendar (client component) |
| `app/(app)/settings/` | Company profile, business hours, client hub |
| `app/(app)/team/` | Members, invites |
| `app/portal/[token]/` | Public read-only client hub |
| `components/PermissionGate.tsx` | Conditional render from role flags |
| `hooks/useActiveCompany.ts` | Company switcher state |
| `hooks/usePermissions.ts` | Write/delete/manage flags |

**Rule:** The frontend never implements commerce state transitions locally except by calling the documented action endpoints.

---

## 4. API contracts

Base URL: **`/api/v1/`**  
Format: **`application/json`** unless noted  
Tenancy: **`X-Company-Id: <integer>`** on all authenticated staff endpoints  
Auth: **`Authorization: Bearer <access_token>`**  
Pagination: **`?page=1&page_size=25`** (default page size 25; max 100)  
Errors: **`{ "detail": "Human message", "code": "machine_code" }`** with appropriate HTTP status  
OpenAPI: **`GET /api/schema/`** (planned; source of truth for frontend types)

### 4.1 Authentication and session

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/auth/login/` | Public | `{ "email", "password" }` | `{ "access_token", "expires_in", "user", "memberships", "active_company_id" }` + refresh cookie |
| POST | `/auth/logout/` | Refresh cookie | — | `204` |
| POST | `/auth/refresh/` | Refresh cookie | — | `{ "access_token", "expires_in" }` |
| POST | `/auth/signup/` | Public | `{ "email", "password", "company_name" }` | Same as login |
| GET | `/auth/me/` | Bearer | — | `{ "user", "memberships", "active_company_id", "permissions": { "can_write_crm", "can_delete_crm", "can_manage_team" } }` |
| POST | `/auth/password-reset/` | Public | `{ "email" }` | `202` (always, anti-enumeration) |
| POST | `/auth/password-reset/confirm/` | Public | `{ "uid", "token", "password" }` | `204` |

### 4.2 Company context

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/companies/active/` | Bearer | `{ "company_id" }` | `{ "active_company_id", "membership" }` |
| GET | `/companies/` | Bearer | — | `{ "results": [ Company ] }` (via memberships) |

### 4.3 Dashboard

| Method | Path | Permission | Response |
|--------|------|------------|----------|
| GET | `/dashboard/` | Read | `{ "workflow": { quotes, jobs, invoices counts by status }, "appointments": { total, active, completed, overdue, remaining, items[] }, "performance": { receivables, upcoming_jobs, revenue_mtd } }` |

### 4.4 CRM

| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/customers/` | Read | Query: `search`, pagination |
| POST | `/customers/` | Write | Unified Jobber-style create (customer + optional contact + location) |
| GET | `/customers/{id}/` | Read | Includes notes summary, activity preview |
| PATCH | `/customers/{id}/` | Write | Partial update |
| DELETE | `/customers/{id}/` | Delete | Owner/Admin; `204` |
| GET | `/customers/{id}/activity/` | Read | Activity timeline events |
| GET/POST | `/customers/{id}/contacts/` | Read / Write | List / create |
| PATCH/DELETE | `/contacts/{id}/` | Write / Delete | |
| GET/POST | `/customers/{id}/locations/` | Read / Write | List / create |
| PATCH/DELETE | `/locations/{id}/` | Write / Delete | |
| GET/POST | `/customers/{id}/notes/` | Read / Write | |
| DELETE | `/notes/{id}/` | Write | |
| GET | `/contacts/` | Read | Company-wide contact list |
| GET | `/locations/` | Read | Company-wide location list |

**Customer object (abbreviated):** `{ id, name, email, phone, status, primary_contact, primary_location, created_at, updated_at }`

### 4.5 Commerce — quotes, jobs, invoices

| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/quotes/` | Read | Filter: `status`, `customer`, pagination |
| POST | `/quotes/` | Write | Body includes `line_items[]` |
| GET | `/quotes/{id}/` | Read | Includes nested line items |
| PATCH | `/quotes/{id}/` | Write | Line items upsert via nested array |
| POST | `/quotes/{id}/accept/` | Write | → `accepted` |
| POST | `/quotes/{id}/create-job/` | Write | Creates job; copies line items |
| GET | `/quotes/{id}/pdf/` | Read | `application/pdf` |
| GET | `/jobs/` | Read | Filter: `status`, `customer`, date range |
| POST | `/jobs/` | Write | |
| GET | `/jobs/{id}/` | Read | |
| PATCH | `/jobs/{id}/` | Write | Schedule fields: `scheduled_start`, `scheduled_end` |
| POST | `/jobs/{id}/complete/` | Write | → `completed` |
| POST | `/jobs/{id}/cancel/` | Delete | Owner/Admin → `cancelled` |
| POST | `/jobs/{id}/create-invoice/` | Write | Creates invoice; copies line items |
| GET | `/jobs/locations/` | Read | Query: `customer=<id>` → `{ locations[], primary_id }` |
| GET | `/invoices/` | Read | |
| POST | `/invoices/` | Write | |
| GET | `/invoices/{id}/` | Read | |
| PATCH | `/invoices/{id}/` | Write | |
| POST | `/invoices/{id}/send/` | Write | → `sent` |
| POST | `/invoices/{id}/paid/` | Write | → `paid` |
| POST | `/invoices/{id}/void/` | Delete | Owner/Admin → `void` |
| GET | `/invoices/{id}/pdf/` | Read | `application/pdf` |

**Line item shape:** `{ id?, description, quantity, unit_price, amount }` — `amount` computed server-side as `quantity * unit_price`.

### 4.6 Schedule

| Method | Path | Permission | Query | Response |
|--------|------|------------|-------|----------|
| GET | `/schedule/` | Read | `view=month\|week`, `month=YYYY-MM`, `week=YYYY-MM-DD` | `{ "view", "range_start", "range_end", "events": [{ id, title, start, end, status, customer_name, reference }] }` |

### 4.7 Settings and team

| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/settings/company/` | Read | Company profile + business hours |
| PATCH | `/settings/company/` | Manage | Owner/Admin |
| GET | `/settings/client-hub/links/` | Read | Portal links for customers |
| POST | `/settings/client-hub/links/` | Manage | Returns `{ link, raw_token }` once |
| DELETE | `/settings/client-hub/links/{id}/` | Manage | Revoke |
| GET | `/team/members/` | Manage | Active and inactive members |
| PATCH | `/team/members/{id}/` | Manage | `{ role }` or `{ is_active: false }` |
| GET | `/team/invites/` | Manage | Pending invites |
| POST | `/team/invites/` | Manage | `{ role, expires_in_days }` → `{ invite_url, raw_token }` once |
| DELETE | `/team/invites/{id}/` | Manage | Revoke |
| POST | `/invites/{token}/accept/` | Public / Bearer | Join company from invite link |

### 4.8 Client portal (public)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/portal/{token}/` | URL token | `{ company, customer, quotes[], jobs[], invoices[] }` read-only DTOs |

No Bearer token. Invalid or revoked token → `404`. Rate-limited per IP.

**Token rules:** SHA-256 hash stored; raw token shown once on creation; revocable via settings API.

### 4.9 Commerce state transitions

All actions are idempotent where sensible; invalid transitions return `409` with `code: "invalid_transition"`.

| Entity | From | Action | To | Service |
|--------|------|--------|-----|---------|
| Quote | draft, sent | `POST .../accept/` | accepted | `accept_quote()` |
| Quote | accepted | `POST .../create-job/` | — | `create_job_from_quote()` |
| Job | * | `POST .../complete/` | completed | `mark_job_completed()` |
| Job | draft, scheduled, in_progress | `POST .../cancel/` | cancelled | `cancel_job()` |
| Job | completed | `POST .../create-invoice/` | — | `create_invoice_from_job()` |
| Invoice | draft | `POST .../send/` | sent | `mark_invoice_sent()` |
| Invoice | sent | `POST .../paid/` | paid | `mark_invoice_paid()` |
| Invoice | * | `POST .../void/` | void | `void_invoice()` |

Line items are copied quote → job → invoice on creation transitions; totals recalculate from line items.

### 4.10 Human-readable references

| Model | Format | Example |
|-------|--------|---------|
| Quote | `QT-{sequence:05d}` | QT-00001 |
| Job | `JB-{sequence:05d}` | JB-00001 |
| Invoice | `INV-{sequence:05d}` | INV-00001 |

Sequences are unique per company (`UniqueConstraint(company, sequence)`).

### 4.11 Example sequences

**Login and load dashboard**

```
Browser → POST /api/v1/auth/login/
       ← tokens + memberships
Browser → GET /api/v1/dashboard/
          Headers: Authorization, X-Company-Id
       ← workflow + appointments + performance JSON
Next.js → render dashboard page
```

**Accept quote and create job**

```
Browser → POST /api/v1/quotes/42/accept/
       ← Quote { status: "accepted" }
Browser → POST /api/v1/quotes/42/create-job/
       ← Job { id, reference: "JB-00007", ... }
```

### 4.12 Future endpoints (Phase 3+)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/quotes/{id}/send-email/` | Email PDF to customer |
| POST | `/invoices/{id}/send-email/` | Email PDF to customer |
| POST | `/webhooks/stripe/` | Payment status (future) |

---

## 5. Security and tenancy

### 5.1 Multi-tenancy model

- **Isolation:** Row-level — all domain models include `company_id` FK.
- **Active tenant:** Client sends `X-Company-Id`; middleware verifies user has active membership for that company.
- **Query rule:** All API querysets filter by `request.company`; cross-tenant ID access returns `404` (not `403`, to avoid leaking existence).

### 5.2 Authentication

| Concern | Design |
|---------|--------|
| Staff sessions | Short-lived JWT access token (~15 min) + HttpOnly refresh cookie (~7 days) |
| Token storage | Access token in memory (or secure sessionStorage); refresh never exposed to JS |
| Password policy | Django validators (defaults) |
| Signup | Creates `Company` + `CompanyMembership(OWNER)` atomically |
| Logout | Refresh token invalidated server-side |

### 5.3 Authorization (roles)

| Capability | Owner | Admin | Dispatcher | Tech | Viewer |
|------------|:-----:|:-----:|:----------:|:----:|:------:|
| Read CRM/commerce | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write CRM/commerce | ✓ | ✓ | ✓ | | |
| Delete CRM / void / cancel | ✓ | ✓ | | | |
| Manage team / settings | ✓ | ✓ | | | |
| Django admin | Superuser only | | | | |

Enforcement: DRF permission classes call the same methods as today — `CompanyMembership.can_write_crm()`, `can_delete_crm()`, `can_manage_invites()`. Next.js mirrors flags for UX only.

### 5.4 Cross-origin and CSRF

| Concern | Design |
|---------|--------|
| CORS | Allowlist Next.js origin; credentials allowed for cookie auth |
| CSRF | Not required for Bearer JWT requests; refresh cookie endpoints use `SameSite=Lax` + double-submit or restricted to same-site |
| HTTPS | Required in production for both tiers |

### 5.5 Token-based public access

| Token type | Storage | Use |
|------------|---------|-----|
| Team invite | `CompanyInvite.token_hash` | Single-use join; expires |
| Client portal | `CustomerPortalLink.token_hash` | Multi-use until revoked |

Raw tokens are never persisted; only SHA-256 hashes.

### 5.6 Rate limiting

| Endpoint class | Limit (planned) |
|----------------|-----------------|
| `/auth/login/` | 10/min per IP |
| `/auth/signup/` | 5/min per IP |
| `/portal/{token}/` | 60/min per IP |
| PDF downloads | 30/min per user |

Implemented via DRF throttling or reverse-proxy rules.

### 5.7 Admin hardening

- Admin mounted at configurable secret path (`DJANGO_ADMIN_URL`)
- `AdminSuperuserOnlyMiddleware` redirects non-superusers
- Admin uses Django session auth (separate from staff JWT)

### 5.8 Data protection

| Area | Requirement |
|------|-------------|
| Secrets | Environment variables only; never committed |
| PII | Customer email/phone in CRM; audit logging planned Phase 3 |
| PDF/portal | Scoped to customer via portal token; staff PDFs require company membership |
| Correlation IDs | `X-Request-Id` propagated Next → Django for log tracing |

---

## 6. Non-functional requirements

### 6.1 Performance

| Requirement | Target | Approach |
|-------------|--------|----------|
| First contentful paint (staff app) | < 1.5s on broadband | Next.js RSC + edge caching for static shell |
| API list endpoints p95 | < 300ms | Indexed `(company, status)` queries; pagination mandatory |
| Dashboard | Single API call | Aggregated in `dashboard.py` service |
| Schedule month view | Single API call | `(company, scheduled_start)` index |
| PDF generation | < 3s per document | Synchronous in API worker; async queue if volume grows |
| Client navigation | < 200ms perceived | Client-side routing in Next.js |

### 6.2 Scalability

| Aspect | Approach |
|--------|----------|
| Frontend | Stateless Next.js instances behind CDN |
| API | Horizontal Gunicorn/uvicorn workers |
| Database | Single PostgreSQL; row-level tenancy (no schema-per-tenant) |
| Sessions/tokens | Redis for refresh denylist and cache (Phase 2) |
| File storage | PDFs generated in memory; logos → S3-compatible storage (future) |

### 6.3 Availability and reliability

| Requirement | Notes |
|-------------|-------|
| Database backups | Operator responsibility (Postgres dumps / managed DB) |
| Migrations | Django migrations; run on API deploy before traffic shift |
| Zero-downtime deploy | Rolling restarts; API versioning prevents breaking Next.js mid-deploy |
| Frontend deploy | Independent of API; backward-compatible API changes only within v1 |

### 6.4 Maintainability

| Practice | Target |
|----------|--------|
| Backend tests | Django `manage.py test` on models, services, API (contract tests against OpenAPI) |
| Frontend tests | Playwright or Cypress for critical flows; component tests for forms |
| Service layer | Single source of truth for transitions, totals, schedule |
| API schema | OpenAPI generated in CI; diff reviewed on PR |
| Docs | This SDD, `schema.dbml`, `workflows.md`, `openapi.yaml` |

### 6.5 Observability

| Area | Target |
|------|--------|
| Logging | Structured JSON logs with `request_id`, `company_id`, `user_id` |
| APM | Optional Datadog/Sentry on both tiers |
| Error tracking | Sentry recommended for Next.js + Django |
| Metrics | Request rate, error rate, p95 latency per endpoint |

### 6.6 Compatibility

| Client | Support |
|--------|---------|
| Modern browsers (Chrome, Firefox, Safari, Edge) | Primary |
| Mobile responsive | Next.js responsive layouts; field-tech usable |
| API consumers | HTTPS required; JSON UTF-8 |
| IE11 | Not supported |

### 6.7 Localization

- Default `en-us`, `America/Los_Angeles` (company timezone setting planned)
- Currency on quotes (default USD); display formatting in Next.js
- i18n: next-intl or equivalent when needed; not required for Phase 2

---

## 7. Related documents

| Document | Path |
|----------|------|
| Architecture overview (as-built reference) | [architecture.md](architecture.md) |
| Workflows | [workflows.md](workflows.md) |
| Database schema (Markdown) | [database-schema.md](database-schema.md) |
| Database diagram (DBML) | [schema.dbml](schema.dbml) |
| SQL DDL (PostgreSQL) | [schema.sql](schema.sql) |
| OpenAPI spec | [openapi.yaml](openapi.yaml) |

---

## Appendix A — Phase 0 legacy routes (deprecated)

These Django server-rendered routes exist in the repository today and will be removed after Phase 2 parity. They map to §4 API endpoints above.

| Legacy path | Replacement |
|-------------|-------------|
| `/accounts/login/`, `/accounts/signup/` | Next.js `(auth)` + `/api/v1/auth/*` |
| `/dashboard/` | `/app/dashboard` + `GET /api/v1/dashboard/` |
| `/switch-company/<id>/` | `POST /api/v1/companies/active/` |
| `/app/crm/*` | `/app/crm/*` (Next) + `/api/v1/customers/*` |
| `/app/quotes|jobs|invoices/*` | Next commerce routes + `/api/v1/quotes|jobs|invoices/*` |
| `/app/schedule/` | `/app/schedule` + `GET /api/v1/schedule/` |
| `/app/settings/*`, `/app/team/` | Next settings/team + §4.7 API |
| `/portal/<token>/` | `/portal/[token]` + `GET /api/v1/portal/{token}/` |
| `/join/<token>/` | `/join/[token]` + `POST /api/v1/invites/{token}/accept/` |

---

## 8. Revision history

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-08 | Initial SDD from as-built Django codebase |
| 1.1 | 2026-06-08 | Reframed as target Next.js + Django REST architecture; full API contracts, migration phases, legacy appendix |
