# Unified Operational Polish Architecture

## Purpose

Stage 9 turns the already implemented operational domains into one coherent
staff experience. It does not replace the Client Command Centre, Ticketing,
Infrastructure, Credential Vault, Monitoring, Tasks or Dashboard architecture.
It adds the shared discovery, activity, notification, lifecycle, escalation and
planning layers that let those domains work together.

The Stage 9 implementation covers:

- permission-aware global and Client-context search;
- Infrastructure topology and navigation polish;
- scoped Client/resource/platform Activity;
- audit/security UX;
- persistent operational notifications;
- Credential expiry and rotation health/reminders;
- Ticket SLA and escalation posture;
- first-class Calendar Events/Meetings alongside dated Tasks and Projects.

The general rule remains: **Django decides what exists for the caller and the
Next.js application renders that already-scoped contract.**

## 1. Unified operational search

Search is a bounded read model over existing operational domains. It is not a
new source of authority and it does not introduce a permission capable of
widening access.

The endpoint is:

```text
POST /api/admin/search
Content-Type: application/json
```

The query is deliberately sent in a CSRF-protected JSON body rather than a URL
query string. Operators may accidentally paste a password, token or other
sensitive value into search; keeping the term out of URLs avoids unnecessarily
placing it in browser history, reverse-proxy paths and ordinary access logs.

Search participates only in domains the caller can already view and reuses the
same object-scope policies as the normal workspaces. The first Stage 9 search
covers Clients, Contacts, Leads, Tickets, Projects, Tasks, Knowledge Base,
Infrastructure and Credential metadata.

Ticket message text may locate a visible Ticket, but message bodies are never
projected into the search result. Credential search never indexes or compares
legacy plaintext secret columns, encrypted payloads, decrypted values or
secret field contents.

See `UNIFIED_OPERATIONAL_SEARCH_ARCHITECTURE.md` for the detailed search
contract.

## 2. Scoped Activity and audit/security UX

`AuditEvent` remains append-only. Stage 9 adds explicit Client and structured
Infrastructure-resource context so operational history can be resolved through
current object scope instead of exposing an unscoped global event stream.

The Activity API supports three useful contexts:

- platform-wide Activity for staff with `core.view_auditevent`;
- one authorised Client;
- one authorised Infrastructure resource, optionally within a Client context.

Global Activity is still scope-filtered. A staff user with the global audit
capability does not automatically gain visibility of events belonging to a
Client or resource outside their current access grants.

Sensitive audit metadata is a separate capability. Ordinary Activity rows can
show action, actor, safe target identity and time, while arbitrary metadata,
IP address and user-agent values are omitted unless the caller has the
sensitive-audit permission.

Audit acknowledgement is itself append-only. Acknowledging an event records a
new `audit.acknowledged` AuditEvent referencing the source event rather than
mutating the original history. The source event is looked up through the same
scoped Activity queryset so acknowledgement cannot be used as an object-ID
existence probe.

The `/admin/activity` workspace lets authorised operators move between
platform, Client and resource context without bypassing backend scope.

## 3. Operational notifications

Stage 9 introduces a persistent per-user `Notification` model. Notifications
are a projection of live operational conditions; they are not a second copy of
the source domain state.

Each generated notification has a deterministic `source_key`. Refreshing the
notification feed upserts the current condition and resolves deterministic
notifications whose source condition is no longer active. A dismissed unchanged
condition is not repeatedly reopened merely because the feed is refreshed.

The first notification sources are:

1. overdue Tasks assigned to the current user;
2. assigned Ticket SLA warnings or breaches;
3. Credential expiry/rotation warnings and critical states;
4. visible open/acknowledged Monitoring incidents;
5. upcoming first-class Calendar Events/Meetings relevant to the current user.

Every source applies its normal capability and object-scope rules before a
notification can exist for the caller. The top-bar bell consumes only this
server-generated feed and supports read, dismiss and read-all actions.

Notifications deliberately do not include Credential secret values or Ticket
message-body content.

## 4. Credential expiry and rotation health

The Credential Vault remains the only authority for Credential secret material.
Stage 9 adds lifecycle metadata and a derived health service; it does not add a
parallel secret store.

Lifecycle inputs are:

- `expires_at`;
- `last_rotated_at`;
- optional `rotation_interval_days`.

Existing real secret writes already update `last_rotated_at`. The health service
derives healthy, warning and critical expiry/rotation states from metadata only
and therefore never needs to decrypt a Credential.

The Credential Health workspace provides:

- scoped health counts;
- expiry date/days remaining;
- last rotation and next configured rotation;
- quick rotation-interval configuration;
- an explicit `mark rotated` metadata action for externally rotated secrets.

Lifecycle actions do not reveal, copy or download secret fields. Existing Vault
permissions for reveal/copy/download remain independent and authoritative.

## 5. Ticket SLA and escalation

SLA policy belongs to `TicketQueue`. A Queue may define:

- first-response target minutes;
- resolution target minutes.

A Ticket stores the resulting due timestamps so the operational deadline is
stable and auditable rather than being recomputed from whatever Queue settings
happen to exist later.

New Tickets receive deadlines from their Queue. Moving a Ticket to another
Queue recalculates unmet deadlines from the destination Queue policy. Successful
Microsoft Graph delivery remains the established point at which
`first_response_at` is recorded; queued or failed outbound mail does not satisfy
the first-response target.

The derived Ticket SLA read model exposes healthy, warning, breached and
waiting-customer posture. `Waiting for customer` suppresses active escalation,
but Stage 9 does **not** pretend the elapsed clock stopped. The recorded due
timestamps remain truthful. A future true paused-duration SLA model would need
an explicit pause/resume ledger rather than hidden date manipulation.

The Service Levels workspace gives staff a scoped attention queue and supports
recalculation where the caller has Ticket change capability. Queue SLA policy
changes require the existing Queue configuration capability.

## 6. Infrastructure topology

Stage 9 exposes the existing typed `ResourceRelationship` graph as a bounded
operational topology read model.

Topology is intentionally limited to one or two hops and bounded node/edge
counts. This is enough for operator navigation without turning the current
relational model into a graph-database project.

Every relationship is returned only when **both** source and target resources
are in the caller's normal Infrastructure scope. An inaccessible root returns
not found. The API therefore cannot reveal the existence, name or relationship
of a resource belonging to an unauthorised Client.

The `/admin/infrastructure/topology` workspace lets operators choose a visible
root resource, inspect typed directed relationships and deep-link to neighbouring
resource workspaces.

## 7. Calendar Events and Meetings

Tasks and Projects keep their existing date-span semantics. Stage 9 adds a
first-class `CalendarEvent` rather than forcing meetings/reminders into the Task
model.

A Calendar Event supports:

- Internal or Client ownership;
- optional Project context;
- Event, Meeting, Milestone or Reminder type;
- exact start/end datetimes;
- all-day state;
- location;
- meeting URL;
- attendee email addresses;
- scheduled/completed/cancelled lifecycle;
- normal create/change/delete permissions and AuditEvents.

Client-owned Events use the same Client scope as other Client-owned operational
records. Project context must match the Event's ownership context.

The Calendar feed combines Events, dated Tasks and Projects. The frontend adds
Event filtering, an upcoming Events/Meetings agenda, meeting links and a
permission-aware quick-create flow. The quick-create flow defaults to Internal
because silently attaching a quick Event to a Client would be a worse failure
mode than requiring an explicit Client-context workflow later.

External Microsoft/Google calendar synchronisation remains deferred until its
authority, conflict and invitation semantics are explicitly designed.

## 8. Navigation and operator workflow

Stage 9 promotes the cross-domain workspaces into the main operations
navigation:

- Calendar;
- Service Levels;
- Credential Health;
- Infrastructure Topology;
- Activity & Security.

Navigation visibility is only a convenience. Backend permissions remain the
security boundary. Stage 9 also corrects the Ticket navigation capability to
use the real `ticketing.view_ticket` permission.

Global search and the notification bell stay in the top bar because they are
cross-domain actions rather than domain destinations.

## 9. Security invariants

Stage 9 must preserve all of the following:

- capability + object scope on every cross-domain projection;
- inaccessible scoped objects return not found where existence itself is
  sensitive;
- no Credential secret values in search, Activity, notifications, health,
  topology, SLA or Calendar payloads;
- no search terms in URL query strings;
- no Ticket message bodies projected through search or notifications;
- sensitive AuditEvent metadata requires its own permission;
- acknowledgement adds history rather than rewriting it;
- notification state cannot grant access to a source object;
- topology validates both ends of every relationship;
- Calendar Client/Project ownership is backend-validated;
- cookie-authenticated state changes remain CSRF protected.

Permission-boundary tests are mandatory for the new scoped APIs.

## 10. Deliberate deferrals

Stage 9 does not require:

- Elasticsearch/OpenSearch or another external search service;
- fuzzy/typo ranking beyond the current bounded database-backed search;
- decrypted Credential indexing;
- internal Ticket Note full-text search;
- a graph database or unlimited topology traversal;
- a fictional SLA pause clock without a real pause ledger;
- notification delivery to external channels before a channel policy exists;
- two-way Microsoft/Google Calendar synchronisation;
- generic enterprise workflow/escalation engines.

Those can be introduced only when real ADB usage justifies the added authority,
state and operational complexity.

## 11. Stage completion boundary

Stage 9 is complete when the implementation and exact PR head demonstrate all
of the following together:

- unified search works through existing permissions/scope;
- scoped platform/Client/resource Activity and audit-security UX are usable;
- the persistent notification feed aggregates current operational attention;
- Credential lifecycle health is visible without weakening Vault boundaries;
- Ticket SLA posture and Queue policy are enforceable and auditable;
- resource topology is bounded and scope-safe;
- first-class Events/Meetings coexist with Task/Project Calendar planning;
- the corresponding admin workspaces/navigation are available;
- repository lint, backend tests/security scans/container builds and the ADB
  Software Solutions tests/production build all pass on the same exact head.
