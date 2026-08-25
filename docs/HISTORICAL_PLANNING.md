# Historical Planning Documents

## Purpose

The repository retains older root-level planning documents that pre-date the
current ADB Business Platform architecture, including:

- `ADB_SOFTWARE_SOLUTIONS_BUILD_PLAN.md`;
- `DJANGO_ARCHITECTURE.md`.

They contain useful original product ideas and implementation context, but they
are **historical references, not the current specification**.

The platform has moved substantially since those plans were written: multiple
ADB Brands are first-class, the ADB Software Solutions public/admin frontend
has been consolidated, Ticketing/Graph is implemented, work management is now
Asana-style, Infrastructure has a structured resource graph, and the secure
Credential Vault is the active technical feature slice.

---

## Canonical precedence

Use this order when documents disagree:

1. `docs/PLATFORM_MASTER_PLAN.md` — current product/architecture/build plan.
2. `docs/PERMISSIONS_AND_ACCESS_MODEL.md` — authorisation and scope.
3. `docs/DOMAIN_MODEL_AUDIT.md` — current domain/model decisions.
4. `docs/CURRENT_STATE_AND_FOUNDATION_CHECKLIST.md` — implementation snapshot.
5. relevant current domain architecture/runbook documents.
6. historical root-level planning documents.

A later explicit architectural decision may update the canonical set, but an
old root plan must never silently override it.

---

## Superseded assumptions

Do not revive the following older assumptions without a new explicit decision:

- the platform exists only for `adbsoftwaresolutions.co.uk`;
- public content is single-site rather than Brand-aware;
- simple Admin/Staff/Read-only labels are sufficient authorisation;
- Client scope and Ticket Queue scope are unnecessary;
- a separate standalone admin Next.js application should exist;
- Django REST Framework or GraphQL is the undecided/primary current API layer;
- contact forms terminate in a separate enquiry silo;
- email communication is separate from Ticket communication;
- operational Project and public Portfolio/CaseStudy are the same record;
- Project/Task/Time always require a Client/Project;
- internal ADB work should be represented by a fake Client;
- Tasks are basic project-only checklist items;
- Credentials are ordinary plaintext fields;
- technical Infrastructure is a collection of unrelated flat asset tables;
- each Microsoft 365 Ticket mailbox needs its own app/certificate/RBAC setup;
- all historical/inactive/closed records should dominate the default register
  view;
- CRUD tables are the intended primary product experience.

### Important correction to previous historical guidance

The **current** architecture intentionally keeps the ADB Software Solutions
public routes and authenticated `/admin` operations routes in the same Next.js
application/deployment. The superseded architecture was the separate admin
application, not the combined topology.

The authentication/account-security application remains separate.

---

## Major current concepts absent or incomplete in the old plans

The current platform includes architectural decisions that the old plans could
not fully represent:

- three first-class Brands: ADB Software Solutions, ADB Web Designs and ADB
  Technology;
- code-owned marketing pages with Brand-aware editorial CMS content;
- dedicated Next.js authentication/account application with Django identity;
- fine-grained Django capability permissions plus Client/Ticket Queue scope;
- server-backed staff preferences where appropriate;
- append-only AuditEvent foundation;
- current/actionable-first operational UX;
- right-side record/task drawers and context-preserving workspaces;
- Client as the operational Command Centre;
- Client/Internal ownership across work and technical resources;
- My Tasks, Task Lists, Sections, Board/List/Timeline, Subtasks, dependencies,
  recurrence, comments and persistent timers;
- work-first Project views and dependency-aware Project Timeline;
- Time Tracking by Client/Project/Internal and period rather than one global
  history;
- a permission-aware work Calendar foundation;
- unified Ticketing for Graph email/contact forms/future portal communication;
- My Tickets/Unassigned/All Active/Queue focus with resolved/closed history;
- chronological internal Ticket Notes and Ticket live timer;
- one Microsoft 365 tenant/app/certificate connection with many Shared
  Mailboxes;
- Exchange SharedMailbox-scoped RBAC plus database Mailbox operational allow-
  list;
- Lead email sent/tracked through Tickets and Microsoft Graph;
- structured `InfrastructureResource` identity, Providers and typed
  relationships;
- explicit legacy Infrastructure reconciliation instead of guessed ownership;
- encrypted Credential payload/key-ring architecture and the modern Vault
  feature direction;
- planned Monitoring as checks/results/incidents attached to resources;
- redesigned linked Knowledge Base direction;
- later commercial analytics including profitability, Client lifetime value,
  Lead-source revenue/conversion and time-versus-pay/revenue analysis;
- later Client portal with explicit, private-by-default visibility.

---

## How to use the old plans safely

Historical documents may still contain useful:

- feature ideas;
- field examples;
- operational scenarios;
- early workflow thinking;
- deployment context.

Before implementing an extracted idea:

1. check whether the relevant domain already exists differently on `main`;
2. check `PLATFORM_MASTER_PLAN.md` and `CURRENT_STATE_AND_FOUNDATION_CHECKLIST.md`;
3. apply current Client/Internal ownership and access policy;
4. apply the current-first/workspace/drawer UX doctrine;
5. do not duplicate a newer canonical model/service;
6. update canonical documentation if the extracted idea becomes a new explicit
   decision.

Chat history can help explain why a decision changed, but the repository docs
should remain sufficient to implement the current plan without relying on chat
history.
