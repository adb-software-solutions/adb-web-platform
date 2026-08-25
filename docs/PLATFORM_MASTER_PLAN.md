# ADB Business Platform Master Plan

## Purpose

This is the canonical product, architecture and build-plan document for the
ADB Business Platform.

The platform is the shared internal operating system for the ADB businesses.
It is intended to replace or substantially reduce reliance on separate CRM,
helpdesk, task-management, time-tracking, technical-documentation,
credential-management, infrastructure-inventory and lightweight commercial
systems.

It takes useful product ideas from HubSpot, Asana, Jira/AutoTask/ServiceNow,
IT Glue and modern helpdesk products, but it must follow ADB's actual workflows
rather than reproduce another product feature-for-feature.

Older plans remain useful historical context, but this document wins when they
conflict with the current architecture.

---

## 1. Product vision

ADB operates three public Brands that share one operational platform:

1. **ADB Software Solutions** — bespoke software, SaaS/application delivery,
   APIs/integrations, automation, mobile applications and consultancy.
2. **ADB Web Designs** — web design/development, WordPress/Next.js delivery,
   rescue/remediation, hosting, maintenance and website support.
3. **ADB Technology** — DevOps, cloud/infrastructure engineering, systems
   administration, IT consultancy and technical support.

The Brands have separate public positioning and visual experiences. They do
not have separate business-data backends.

The internal platform should eventually cover:

- Clients and Contacts;
- CRM/Leads and sales communication;
- Tickets, email and other communication sources;
- Projects, Tasks and work planning;
- Time Tracking;
- Infrastructure and technical-resource relationships;
- encrypted Credentials;
- Knowledge Base/runbooks;
- Monitoring and operational health;
- Calendar and notifications;
- staff Users & Access;
- configurable Dashboard/My Work;
- audit/activity and cross-domain search;
- Brand-scoped CMS/public integrations;
- later products/services, quotes/proposals, contracts, recurring services,
  invoicing, Stripe/payment tracking and commercial analytics;
- later Client portal workflows.

The platform must be useful to ADB first. A future VastDesk/SaaS-style
productisation of reusable platform ideas is a **possibility**, not a current
requirement. Do not introduce premature generic multi-tenancy or abstraction
solely for that possibility.

---

## 2. Product and UX doctrine

### 2.1 Current/actionable-first

The default view of an operational domain should answer: **what needs attention
now?**

History remains available, but it must not dominate normal work.

Examples already established by the product:

- Clients default to **Active**; Inactive/Archived are explicit history views.
- Contacts inside a Client default to active contacts.
- Leads default to **My active/open Leads** with Unassigned and All Active
  alternatives; Won/Lost are history.
- Tickets default to **My actionable Tickets**; Unassigned, All Active and
  Queue views are explicit; Resolved/Closed are history; Waiting on Customer
  is intentionally quieter than work waiting on ADB.
- Projects default to Planning/Active/Paused; Completed/Archived are history.
- Tasks default to **My Tasks**, with Today, Upcoming, Overdue and Completed
  focus views; All Tasks is explicit.
- Infrastructure defaults to current resources; Retired/Archived are history.
- Credentials default to Active; Inactive/Archived are history.

This rule should be applied to new operational domains unless there is a good
reason not to.

### 2.2 Workspaces and drawers, not CRUD as the product

Large CRUD tables are not the primary user experience.

Registers exist for searching, filtering, sorting, pagination and triage.
Normal record interaction should preserve context through:

- focused domain workspaces;
- right-side record drawers;
- contextual panels inside Client/Project/Ticket/Infrastructure workspaces;
- full-page deep links for refresh/bookmark/share and complex work.

The existing shared Task/Record drawer patterns should be reused where they
fit rather than creating unrelated modal behaviour per domain.

### 2.3 Server-authoritative operational UX

For data-heavy screens, the backend should own:

- scope;
- filters;
- sorting;
- pagination;
- counts/statistics;
- business-state transitions.

User preferences that should follow a staff user between browsers/devices
belong server-side. Ticket default queues already follow this rule; Dashboard
layout/configuration should follow it later.

### 2.4 Dark internal console, independent public Brands

The internal operations workspace is intentionally dark-only,
information-dense and workflow-focused. Tailwind CSS is the frontend styling
standard.

Public Brand applications remain independent visual products. Shared packages
are for genuinely shared primitives/contracts/tooling, not for forcing every
Brand into the same design.

---

## 3. Repository and application architecture

The monorepo contains:

```text
backend/
packages/
sites/
    adb-software-solutions/
    adb-web-designs/
    adb-technology/
    auth-adb-software-solutions/
```

There is no separate `admin-adb-software-solutions` application.

### 3.1 Shared Django backend

`backend/` is the single business-data and operations backend. It owns:

- authentication and authorisation;
- staff users, capabilities and scopes;
- Brands;
- Clients/Contacts;
- CRM/Leads;
- Projects/Tasks/Time;
- Tickets/communications;
- Microsoft Graph connections and Shared Mailboxes;
- Knowledge Base;
- Credentials;
- Infrastructure and Monitoring;
- CMS/editorial content;
- audit/activity;
- Celery/background processing;
- future commercial and portal data.

Django remains authoritative for permissions, scope and business rules. The
API layer is Django Ninja.

### 3.2 ADB Software Solutions frontend

`sites/adb-software-solutions/` is one Next.js App Router application serving:

- the ADB Software Solutions public site; and
- authenticated internal operations under `/admin`.

Route/layout boundaries must keep the public and privileged concerns clearly
separated even though they share one deployment.

### 3.3 Other public frontends

`sites/adb-web-designs/` and `sites/adb-technology/` are separate Next.js
public applications.

Main marketing pages are code-owned. CMS-managed public content is limited to
editorial content that benefits from ongoing administration, such as Blog,
Testimonials, FAQs and optional public Case Studies/Portfolio.

Operational `Project` and public CaseStudy/Portfolio remain separate concepts.

### 3.4 Authentication/account frontend

`sites/auth-adb-software-solutions/` is the dedicated Next.js authentication
and account-security application.

Django remains the identity/session/TOTP/WebAuthn authority. Do not introduce
Auth.js/NextAuth, browser-stored JWTs or another identity authority by default.

---

## 4. Core domain rules

### 4.1 Brand is first-class and separate from ownership

Brand identifies the ADB business context for public content, communication
and commercial presentation. It is not a substitute for Client/Internal
ownership.

Example:

```text
Ticket
brand = ADB Web Designs
client = Welcome to Travel
```

### 4.2 Operational ownership is Client or Internal

Operational records deliberately belong to either:

```text
client-owned -> a real Client
internal     -> ADB itself, with no Client
```

Never create a fake ADB Client to represent internal work.

### 4.3 Client is the command-centre context

Client is not merely a company row. The mature Client Command Centre should
converge on:

```text
Client
├── Overview
├── Contacts
├── Projects
├── Tasks
├── Tickets / communications
├── Time
├── Infrastructure
├── Credentials
├── Knowledge Base
├── Activity / history
└── later commercial + portal context
```

Completed/resolved/history records can remain useful in the Client context,
but current information should still be the initial view inside each section.

### 4.4 Contacts bridge people, Clients and communication

ClientContact email identity is a primary key for communication matching.
Contact workspaces should surface Contact-specific Tickets. Future Client
portal identities should link to ClientContact rather than introduce a second
customer-person model.

### 4.5 Permissions are capability + scope

Django Groups/Permissions answer **what** a staff user can do. Access-control
scope answers **where** they can do it.

Scopes include Clients and Ticket Queues and transitively constrain
Client-owned Projects, Tasks, Time, Infrastructure, Credentials, Knowledge and
other domains.

Sensitive actions such as credential reveal/copy/download or access changes
use explicit permissions and audit events.

---

## 5. Implemented operational foundation

The following are established platform architecture, not future-only ideas:

- Django-backed identity/session/TOTP/WebAuthn and dedicated auth frontend;
- Brand-aware CMS/public content isolation;
- capability permissions plus Client/Ticket Queue scope;
- append-only AuditEvent foundation;
- combined ADB Software Solutions public + `/admin` Next.js application;
- Client/Contact CRUD and lifecycle management;
- Lead CRUD, assignment, outcome semantics and Lead -> Client/Contact
  conversion retaining communication history;
- Project CRUD with Client/Internal ownership and current/history views;
- Asana-style Tasks, Lists, Sections, Boards, Timelines, Subtasks,
  Dependencies, recurrence and comments;
- My Tasks/Today/Upcoming/Overdue/Completed focus views and quick capture;
- shared Task drawer and direct-edit Task workspace;
- server-authoritative RunningTimer and manual Time Entries;
- Task and Ticket live timers plus Project/Task/Ticket time context;
- Time Tracking drill-down by Client/Project/Internal and period rather than a
  giant global history table;
- a permission-scoped Task/Project Calendar foundation;
- unified Ticketing with Messages, Notes, Attachments, queues and operational
  focus views;
- Microsoft Graph app-only Shared Mailbox sync and outbound delivery;
- Lead email through the Ticket/Graph layer rather than `mailto:`;
- per-user Ticket Queue defaults stored server-side;
- structured InfrastructureResource identity, Providers, tags and typed
  resource relationships;
- explicit specialist legacy reconciliation and structured Infrastructure
  resource workspaces;
- full typed Credential Vault with encrypted/versioned secrets, independent
  reveal/copy/download permissions, Client/Infrastructure context and atomic
  legacy-secret reconciliation;
- deterministic development data and CI/container foundations.

Knowledge Base, Users & Access, configurable Dashboard and mature Monitoring
remain incomplete.

Credential-specific security and lifecycle rules are authoritative in
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

---

## 6. Work management: Projects, Tasks, Calendar and Time

The Projects/Tasks/Time area is an integrated work-management system, not
separate registers.

### Projects

Opening a Project should be work-first. The established workspace separates:

- Work;
- Timeline;
- Overview;
- Time.

List/Board views support contextual creation and ordering. The Project Timeline
is dependency-aware and supports Day/Week/Month zoom for dated work.

Current Projects are the global default; Completed/Archived remain available
as history.

### Tasks

Tasks do not require Projects. Valid Task contexts include:

- standalone Internal work;
- Client work;
- Project work;
- later explicit Ticket-linked work where useful.

The normal experience includes My Tasks, quick capture, direct editing,
subtasks, blocking dependencies, recurrence, comments, List/Board/Timeline
views, completion controls and the embedded live timer.

### Calendar

A permission-aware Calendar foundation exists for dated Tasks/Projects. The
next Calendar work is refinement rather than a from-scratch build:

- richer day/week planning where useful;
- stronger Project milestone support;
- first-class Event/Meeting design later;
- external calendar integration only after an explicit design decision.

### Time

Time is cross-domain. Timer lifecycle is backend-authoritative with one active
timer per user unless explicitly changed later.

The Time Tracking workspace should remain browse-oriented by:

- Client;
- Project;
- Internal;
- selected period.

Do not regress to one giant undifferentiated history table.

Future commercial work may link billable time to invoices without making
invoicing a dependency of current Time Tracking.

---

## 7. CRM and Client operations

### Clients

Global Client views are current-first and default to Active. Inactive/Archived
Clients are explicit history.

The next major Client pass is the **Client Command Centre**: a coherent single
workspace where authorised staff can move between Contacts, Projects, Tasks,
Tickets, Time, Infrastructure, Credentials, Knowledge and Activity without
repeatedly returning to global registers.

It should include contextual create actions and useful summaries, especially
current work, open communication and time by period.

Active Client-owned Credentials already appear in Client context; the Command
Centre pass should integrate that existing capability into the final navigation
model rather than inventing another password view.

### Leads

Lead operations are sales-pipeline focused:

- My Leads is the primary view;
- Unassigned and All Active are operational alternatives;
- Won/Lost are explicit history/outcomes;
- editing can occur in the record drawer;
- communication is retained through Tickets;
- sending email from a Lead creates/continues an auditable Ticket conversation
  through the selected configured Shared Mailbox and Graph delivery path;
- conversion to Client/primary Contact preserves related Ticket history.

Future CRM work can add useful commercial metadata/deduplication, but should
not recreate a separate communication system.

---

## 8. Ticketing and Microsoft 365

Ticket is the canonical communication thread for:

- Microsoft 365 email;
- public website contact submissions;
- future portal communication;
- future API/integration sources where appropriate.

The main Ticket page is an operational work queue, not a global archive.
Established views include:

- My Tickets;
- Unassigned;
- All Active;
- enabled Queue views;
- Resolved;
- Closed;
- All Tickets.

Waiting on Customer is intentionally lower priority than work waiting on ADB.
Internal Notes appear chronologically in the conversation feed and remain
visually/staff-only distinct.

Per-user default Ticket Queues are server-backed. An empty stored selection
means all accessible enabled queues; an explicit subset narrows default work
views.

### Microsoft Graph model

The normal ADB deployment is:

- one Microsoft Entra application;
- one tenant-level `MicrosoftGraphConnection`;
- certificate-based app-only authentication in production;
- many configured Microsoft 365 Shared Mailboxes;
- Exchange Online RBAC for Applications as the Microsoft-side boundary;
- enabled database Mailbox rows as the narrower operational allow-list;
- certificate/private-key material stored through the Credential Vault rather
  than duplicate plaintext Graph configuration.

For ADB's current tenant model, the preferred Exchange scope is dynamic by
`RecipientTypeDetails -eq 'SharedMailbox'`. This means a new Shared Mailbox
automatically falls inside the Exchange application boundary without creating
another RBAC rule. Licensed `UserMailbox` recipients remain outside it.

Adding a mailbox to the Ticket system should therefore be an application
configuration action: choose/enter the Shared Mailbox, Brand/purpose/default
queue, verify it and enable it. The operator should not re-enter the tenant ID,
client ID, certificate or create a new RBAC assignment for each mailbox.

See `TICKETING_ARCHITECTURE.md`, `MICROSOFT_GRAPH_TICKETING_SETUP.md` and
`CREDENTIAL_VAULT_ARCHITECTURE.md` for details.

---

## 9. Technical operations: Infrastructure, Credentials, Monitoring and KB

The technical-operations goal is IT Glue-style structured documentation for
software development, web delivery, DevOps, Linux/system administration and
support.

It is not a collection of flat asset tables.

### 9.1 Structured Infrastructure

`InfrastructureResource` is the common identity/ownership/lifecycle anchor.
Strongly typed specialist models retain domain-specific fields.

Generic `ResourceRelationship` edges provide cross-resource topology without
replacing normal relational modelling or requiring a graph database.

The merged foundation includes:

- Client/Internal resource ownership;
- lifecycle/environment/criticality;
- tags;
- Service Providers and resource-backed Provider Accounts;
- typed relationships;
- current-first resource views;
- specialist legacy identity bridges;
- explicit operator-driven reconciliation;
- Client-scoped/global structured resource workspaces;
- contextual links to active Credentials.

The next Infrastructure slices should build real specialist operational
structures rather than expanding the legacy flat registers indefinitely.

### 9.2 Credential Vault

The Credential Vault is an implemented technical-operations subsystem, not a
future placeholder. Its authoritative architecture is
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

It provides:

- typed credential templates;
- Client/Internal ownership;
- encrypted versioned secret payloads and key ring/rotation;
- metadata-only ordinary API responses;
- Active-first lifecycle;
- separate reveal, copy and download permissions/actions;
- audit events that record field/context but never secret values;
- links to one or more Infrastructure Resources with ownership validation;
- Client and Infrastructure contextual views;
- atomic reconciliation of legacy plaintext fields into encrypted payloads;
- fail-closed behaviour when encryption configuration is unavailable.

Secret values must never enter normal search, logs, URLs, analytics or audit
metadata.

Infrastructure, Monitoring, Graph, KB and later specialist records reference
Credentials instead of duplicating secret material.

### 9.3 Monitoring

Monitoring is a cross-cutting subsystem attached to structured resources, not
an `is_up` flag on Server/Website.

Planned initial checks include:

- ICMP/ping;
- TCP port;
- HTTP/HTTPS;
- expected/forbidden text/regex;
- TLS validity/expiry;
- DNS record checks;
- domain registration expiry.

Checks produce history and incidents with failure/recovery semantics. Celery
Beat/workers schedule execution through reusable services. Global and
Client-scoped health dashboards should show current problems first.

Checks requiring authentication reference Credentials through the Vault rather
than storing their own plaintext usernames/tokens.

### 9.4 Knowledge Base

The agreed KB direction is a Client/Internal documentation workspace with a
filesystem-like folder/section structure rather than a flat list.

Target behaviour includes:

- Markdown or controlled rich-text editing;
- immutable/versioned history;
- author/editor metadata;
- attachments where appropriate;
- tags/search metadata;
- links to Infrastructure Resources, Credentials, Tickets and Projects;
- resource workspaces surfacing related runbooks/documentation;
- global and Client-context permission-aware search;
- future portal visibility explicit and private by default.

The KB must not become an alternative plaintext credential store. It links to
Vault records when a runbook needs access context.

---

## 10. Users & Access

Users & Access remains a required first-class custom operations area.

It must support authorised administration of:

- staff list/detail;
- create/invite/activate/deactivate according to the identity model;
- Django Group membership;
- capability permissions;
- Client scope;
- Ticket Queue scope;
- effective access display;
- audit of access changes.

Routine staff administration must not require Django superuser access.

The backend permission/scope model already exists; this phase is primarily the
safe operational administration experience plus any missing backend endpoints
and boundary tests.

Credential reveal/copy/download capabilities remain separately grantable and
must be visible clearly in effective-access administration.

---

## 11. Dashboard / My Work

The Dashboard should become a configurable, server-persisted personal
operations surface rather than a fixed stats page.

Target widget categories include:

- My Tickets / selected Ticket Queue / unassigned urgent work;
- My Tasks / overdue / upcoming;
- active timer and recent Time;
- Lead follow-up;
- current Project work/milestones;
- Infrastructure/Monitoring incidents and expiries;
- Calendar agenda;
- authorised audit/security summaries.

Widget visibility and data obey normal backend capability/scope policies.
Layout/configuration should follow the staff user across browsers.

Do not surface Credential secret values in Dashboard widgets; at most show safe
metadata/health indicators when a user has the relevant metadata permission.

---

## 12. Search, activity, notifications and operational polish

Once the underlying workspaces are mature, add a coherent cross-domain layer
rather than independent global search boxes everywhere.

### Search

Permission-aware global and Client-context search should cover useful
non-secret metadata from:

- Contacts;
- Leads/history;
- Tickets/messages where appropriate;
- Projects;
- Tasks;
- KB documents;
- Infrastructure;
- credential metadata only.

Decrypted credential payloads are never indexed.

PostgreSQL-backed search is acceptable initially. Dedicated search
infrastructure is not justified until scale/quality requires it.

### Activity

Client and resource activity should eventually provide a useful chronological
view of operational changes/events. It should build from safe domain events and
audit records rather than dumping every database change.

Commercial events can join the Client activity timeline later.

Credential activity may show safe events such as created/updated/archived or
that a secret action occurred; it must never include the secret value.

### Notifications and SLA refinements

Notifications, escalation/SLA behaviour and richer Calendar/Event integration
remain later operational refinements. They should be designed after the core
work surfaces are stable rather than embedded piecemeal into unrelated PRs.

Credential expiry/rotation reminders can join this layer after the initial
Vault is proven in real use.

---

## 13. Commercial and analytics layer

The commercial layer is deliberately later than the current operational and
technical foundations, but its agreed scope should influence clean extension
points.

Agreed future areas include:

- products/services catalogue;
- recurring services;
- quotes/proposals;
- contracts;
- invoices/billing;
- Stripe/payment tracking;
- billable operational work flowing into commercial reporting where useful;
- Client profitability;
- Client lifetime value;
- time-versus-pay/revenue analysis;
- Lead-source conversion and revenue attribution.

Detailed contract signing, accounting, tax, forecasting, retainer and SLA
models are **not yet agreed**. Do not invent them during unrelated work.

The commercial layer should reuse existing Client, Lead, Project, Ticket and
Time context rather than create duplicate customer/work models.

Commercial-provider API keys/payment secrets use the Credential Vault rather
than new plaintext secret columns.

---

## 14. Public websites and CMS

The three Brand sites remain important but are not the primary development
focus while the internal platform is still being completed.

Public work can continue opportunistically for security, fixes and stable
integration needs.

When public-site work becomes the primary phase:

- each Brand retains its own public experience;
- normal marketing pages remain code-owned;
- editorial CMS content remains Brand-scoped;
- public forms submit to the shared Django backend and identify Brand/source;
- contact forms continue feeding the Lead + Ticket communication pipeline;
- operational Project remains separate from public CaseStudy/Portfolio.

Public applications must never receive Credential secret payloads simply
because they share the backend repository.

---

## 15. Future Client portal

The Client portal comes after internal operations and relevant commercial
contracts are mature.

Portal identities should use the existing authentication system and link to
ClientContact.

Portal visibility must be explicit per domain and private by default.
Client ownership must never automatically expose:

- Internal resources;
- internal Ticket Notes;
- Credentials/secrets;
- private KB documents;
- staff-only audit/security information.

Credential Vault secret actions are staff-only unless a future explicit threat
model and portal design says otherwise.

---

## 16. Current ordered build plan

The Credential Vault foundation is complete in the change set that carries this
document. The next sustained implementation stage is typed Infrastructure.

### Stage 1 — Core typed Infrastructure

Move beyond transitional legacy specialist records into the most useful
strongly typed operational structures:

- Server/compute and networking foundations;
- Database instance/logical database structures;
- logical Application + environment/source/dependency context;
- Provider Account relationships;
- safe resource create/edit/archive lifecycle;
- Credential references rather than duplicate secret fields.

### Stage 2 — Web Infrastructure

- Websites/endpoints;
- Domains;
- DNS zones/records where useful;
- TLS Certificates and expiry relationships;
- registrar/DNS/CDN/WAF/provider context;
- Credential links for administrative/authentication material.

### Stage 3 — Monitoring and technical dashboards

- checks/results/incidents;
- current health views;
- uptime/response history;
- expiring TLS/domain alerts;
- global and Client-scoped technical dashboards;
- Vault-backed authentication for monitored endpoints where required.

### Stage 4 — Knowledge Base

- folder/section tree;
- Markdown/controlled editor;
- attachments;
- immutable versions;
- Client/Internal ownership;
- Infrastructure/resource backlinks;
- Credential links without secret duplication;
- contextual and global search foundations.

### Stage 5 — Specialist technical operations

- Docker/container structures;
- Kubernetes clusters/namespaces/workloads/services/ingresses/Helm/storage at a
  useful operational level;
- storage/backups;
- system services;
- scheduled jobs/cron/systemd timers;
- remaining specialist operations records.

### Stage 6 — Client Command Centre integration pass

Bring the now-mature operational and technical domains together in the Client
workspace:

- Overview/Contacts/Projects/Tasks/Tickets/Time/Infrastructure/Credentials/KB;
- current-first section defaults;
- contextual quick actions;
- period summaries;
- Activity/history foundation.

Parts of this integration already exist and should continue to be added as
individual domains mature rather than waiting for one giant rewrite.

### Stage 7 — Users & Access

Complete safe custom staff administration for Groups, capabilities, Client
scope, Ticket Queue scope, Credential secret-action capabilities and effective
access.

### Stage 8 — Dashboard / My Work

Add the configurable, permission-aware, server-persisted widget system and
make the personal Dashboard a useful cross-domain starting point.

### Stage 9 — Unified operational polish

- global/Client search;
- topology/navigation polish;
- Client/resource Activity;
- audit/security UX;
- notifications;
- Credential expiry/rotation health/reminders;
- SLA/escalation refinements;
- richer Calendar/Event behaviour where justified.

### Stage 10 — Commercial and analytics

Build the agreed products/services, recurring-services, quotes/proposals,
contracts, invoicing, Stripe/payment tracking and profitability/LTV/source
analytics layer.

### Stage 11 — Public websites as primary focus

Complete the three Brand websites against stable platform contracts.

### Stage 12 — Client portal

Add explicit, narrowly scoped Client-facing access only after the internal and
commercial models are mature enough to expose safely.

The order can move by a small slice when dependencies or real usage justify
it, but a change in major direction should update this document rather than
living only in chat history.

---

## 17. Security and reliability principles

- least privilege by default;
- backend-enforced authorisation and object scope;
- no secrets in Git, ordinary logs, URLs, analytics or audit metadata;
- secret fields opt-in through explicit Vault actions only;
- credential storage fails closed if encryption configuration is unavailable;
- CSRF protection for cookie-authenticated state changes;
- secure production cookies/CORS/trusted origins;
- validated return/redirect URLs;
- rate limiting for authentication and abuse-prone public endpoints;
- external ingestion/delivery is idempotent and retry-safe where practical;
- attachment quarantine/policy enforcement remains active even when malware
  scanning is disabled;
- infected/policy-blocked attachments are never downloadable;
- permission-boundary tests are mandatory for restricted APIs;
- Celery orchestrates asynchronous work but reusable domain logic belongs in
  services rather than only in tasks.

Credential-specific rules, including encryption-key rotation and browser secret
handling, are defined in `CREDENTIAL_VAULT_ARCHITECTURE.md`.

---

## 18. Important non-goals and prohibited shortcuts

Do not:

- create separate Django backends per Brand;
- recreate a separate admin frontend/deployment;
- make every public Brand a recoloured copy of one site;
- use Brand as a substitute for Client/Internal ownership;
- create a fake Internal Client;
- force Tasks to belong to Projects;
- merge operational Projects with public Case Studies;
- return credential secrets in normal list/detail/search APIs;
- duplicate plaintext secrets on Infrastructure, Monitoring, Graph, KB or
  commercial models;
- persist revealed credential secrets in browser storage/routes/analytics;
- implement authorisation only in React;
- give all staff superuser access;
- hard-code each Shared Mailbox as bespoke Graph configuration;
- require per-mailbox certificate/RBAC setup in the normal ADB tenant design;
- treat all Vendor/automated mail as spam;
- create separate email/contact-form/portal communication silos;
- rebuild Time Tracking as one giant history page;
- load entire operational datasets client-side merely to filter/sort them;
- implement speculative portal/accounting/SaaS complexity before its phase.

---

## 19. Architectural statement

> **The ADB Business Platform is one shared operational system serving multiple
> ADB Brands. Django is the business-data, authentication, authorisation and
> scope authority; ADB Software Solutions combines public routes and a protected
> `/admin` workspace in one Next.js application; operational resources are
> Client-owned or Internal; current/actionable work is the default; Client is
> the command-centre context; communications unify into Tickets; and technical
> operations converge on structured Infrastructure, an encrypted Credential
> Vault, Monitoring and linked Knowledge rather than disconnected CRUD
> registers.**

Major future architectural decisions should be checked against this statement
and the canonical documentation set.
