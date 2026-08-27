# Client Command Centre Architecture

## Purpose

The Client Command Centre is the ADB Business Platform's Client-local operational
workspace. It brings the platform's mature work-management, communication and
technical-operations domains together without creating a second copy of their
business logic or data models.

`Client` is the context anchor. Projects, Tasks, Tickets, Time, Infrastructure,
Credentials, Knowledge Base and Monitoring remain authoritative in their own domains.
The Command Centre projects the parts of those domains that are useful while working
with one Client and provides deep links back to the full workspaces when broader
history or specialist workflows are required.

The canonical platform direction remains `PLATFORM_MASTER_PLAN.md`. Permission and
scope rules remain governed by `PERMISSIONS_AND_ACCESS_MODEL.md`; secret handling
remains governed by `CREDENTIAL_VAULT_ARCHITECTURE.md`.

## Workspace structure

The implemented Client workspace is organised as:

```text
Client
├── Overview
├── Contacts
├── Projects
├── Tasks
├── Tickets
├── Time
├── Infrastructure
├── Credentials
├── Knowledge
└── Activity
```

Sections are URL-addressable through the Client route so refresh/bookmark behaviour
preserves the selected section. Time period selection is also represented in the URL.

Only sections the current user can actually view are shown. If a bookmarked section
is no longer permitted, the workspace falls back to Overview.

## Server-authoritative projection

The Command Centre summary is provided by:

```text
GET /api/admin/clients/{client_id}/command-centre
```

The optional `period_days` value accepts the established operational periods:

- 7 days;
- 30 days;
- 90 days;
- 365 days.

Unsupported values fall back to 30 days.

The endpoint owns the cross-domain summary rather than making the browser load global
registers and reconstruct Client state itself. It returns:

- capability flags for each optional domain;
- current-first counts;
- a bounded list of current Projects;
- a bounded list of open Tasks;
- a bounded list of current Tickets;
- selected-period tracked and billable Time totals;
- current Infrastructure, active Credential and Knowledge counts;
- active Monitoring incident count when Monitoring is visible;
- a bounded safe recent-activity projection.

This projection is intentionally a read model. Normal domain writes still use the
owning domain APIs and services.

## Current-first behaviour

The Command Centre follows the platform-wide current/actionable-first doctrine.

### Contacts

Active Contacts are the normal view. Inactive Contacts remain available explicitly as
history.

### Projects

Planning, Active and Paused Projects are current. Completed/Archived Projects are
shown through the history toggle rather than mixed into everyday delivery work.

### Tasks

Open Client Tasks are current. Completed Tasks remain available through the history
toggle. The Overview surfaces open work with overdue Tasks called out explicitly.

### Tickets

The Client summary shows current conversations and actionable counts. Resolved and
Closed history remains available through the existing Client-scoped full Ticket
workspace.

### Time

The Client workspace shows tracked and billable totals for a selected period rather
than embedding an unbounded entry history. The full Time Tracking workspace is opened
with the Client context preserved through `client_id`.

### Technical operations

Infrastructure, active Credential metadata, Knowledge and Monitoring health are
projected into the Client context using the existing domain workspaces/panels. Retired
or Archived Infrastructure and archived/inactive records do not dominate the summary.

## Contextual actions and deep links

The Client workspace provides permission-gated contextual actions rather than sending
operators back to global registers for normal Client work.

Implemented examples include:

- Edit Client;
- Add Contact;
- create Project with the Client preselected;
- create Task with the Client preselected;
- add Client-owned Knowledge documentation;
- open the Client-scoped Ticket history;
- open Client-scoped Time Tracking;
- open full Project, Task, Ticket and Infrastructure records.

The Command Centre deliberately reuses mature domain workspaces where they already
solve the problem well. It does not duplicate the Credential Vault, Infrastructure
resource editor, Knowledge document reader or Monitoring health implementation.

## Permissions and scope

`clients.view_client` plus normal Client scope is the baseline required to resolve the
Client.

Each optional domain then has an independent capability boundary. The current
projection checks the corresponding Django view permission before querying or
returning that domain's data.

Examples include:

- `clients.view_clientcontact` for Contacts;
- `clients.view_project` for Projects;
- `tasks.view_task` for Tasks;
- `ticketing.view_ticket` for Tickets;
- `clients.view_timeentry` for Time;
- `infrastructure.view_infrastructureresource` for Infrastructure;
- `credentials.view_storedcredential` for Credential metadata;
- `knowledge_base.view_knowledgebasedocument` for Knowledge;
- Infrastructure visibility plus Monitoring permission for Monitoring incident
  summaries.

The existing Client detail endpoint also independently omits nested Contacts and
Projects when those permissions are absent. Hiding a Command Centre section in React
is therefore presentation, not the authorisation boundary.

Client access scope is established before the projection is built. A user cannot
supply another Client ID to widen access.

### Ticket Queue scope

Ticket visibility has an additional boundary: the user's accessible Ticket Queues.
Client Ticket counts, summaries and Ticket activity are calculated only from queues
returned by the existing Ticket Queue scope policy. Client access alone does not grant
access to every Ticket conversation for that Client.

### Infrastructure and Credentials

Infrastructure and Credential projections reuse their existing scope policies rather
than implementing Client-only shortcuts.

Credential information in the Command Centre is metadata only. Decrypted payloads are
never part of this API, the Activity feed or Client summary counts. Secret reveal,
copy and download remain explicit Vault actions with their own capabilities and audit
behaviour.

## Activity foundation

Activity is a bounded operational projection, not a promise of a complete audit log.
It combines recent safe metadata changes from domains the current user can view and
sorts them into one recent Client-context list.

Current activity kinds can include:

- Client;
- Contact;
- Project;
- Task;
- Ticket;
- Infrastructure;
- Knowledge;
- Credential metadata.

Ticket activity retains Ticket Queue scope. Infrastructure/Credential activity retains
normal domain scope. Credential secret values are never included.

This is the Stage 6 Activity/history foundation. A later unified activity/audit pass
may provide richer event semantics, filtering and chronology using safe domain events
and `AuditEvent`; the current implementation must not be described as a full audit
ledger.

## Frontend composition

The Next.js Client route owns local section navigation and composes existing domain
components where useful.

Notable integration behaviour includes:

- Client-scoped Infrastructure can render in embedded mode so it does not produce a
  second page header inside the Command Centre;
- Monitoring health remains a reusable Client-context panel;
- Credential Vault uses its Client filter and compact presentation;
- Knowledge Base uses its Client-context panel;
- Ticket and Time deep links pass `client_id` to their existing server-filtered
  workspaces;
- Project creation accepts a Client query parameter and preselects Client ownership.

The frontend does not load entire global operational datasets merely to filter them to
one Client.

## Boundary tests

The Stage 6 API coverage proves the important cross-domain boundaries, including:

- current-first Project/Task calculations and selected-period Time totals;
- optional domain data disappears when the caller lacks that domain capability;
- hidden domain counts remain zero rather than leaking existence through statistics;
- Ticket summaries and Activity obey Ticket Queue scope.

The wider domain test suites continue to own their specialist permission, scope and
business-rule coverage.

## Deliberately deferred work

Stage 6 does not claim to complete:

- a platform-wide unified search system;
- a complete cross-domain audit/activity ledger;
- Dashboard/My Work personalisation;
- Users & Access administration;
- notifications/escalation/SLA refinement;
- commercial records such as contracts, recurring services or invoices;
- Client portal exposure;
- portal visibility rules for internal operational sections.

Those remain ordered later stages in `PLATFORM_MASTER_PLAN.md`.

## Architectural rule

The Client Command Centre is an integration surface, not a new domain authority.
Future Client-context additions should project and compose existing scoped domain
capabilities wherever possible. New Client-specific copies of Projects, Tickets,
Credentials, Infrastructure or other mature records should not be introduced merely
for presentation convenience.
