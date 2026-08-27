# Dashboard / My Work Architecture

## Purpose

Stage 8 replaces the fixed administrative statistics page with a personal,
current-first **My Work** surface.

The Dashboard is a projection over existing operational domains. It is not a
new source of truth for Tasks, Tickets, Time, Leads, Projects, Monitoring or
audit events, and it is never an alternative authorisation layer.

## Core model

Each staff account may have one `DashboardPreference` row. The persisted
preference contains only an ordered list of known widget keys and their desktop
column spans.

Widget definitions, titles, required capabilities, data queries and rendering
contracts remain code-owned. Arbitrary queries, URLs, templates, filters or
executable widget configuration are not stored in the database.

This keeps the preference model intentionally small while allowing the layout
to follow a staff user between browsers and devices.

## Layout contract

The Dashboard uses a 12-column desktop grid. Supported widget spans are:

- `4` — one third;
- `6` — one half;
- `8` — two thirds;
- `12` — full width.

A layout may contain at most twelve widgets and a widget key may occur only
once.

When no preference exists, the server returns the recommended layout containing
all widgets the current user is authorised to view. The frontend can restore
that recommended order and width configuration through the customiser.

The browser does not persist Dashboard configuration in `localStorage` or
another browser-side preference store.

## Authorisation model

Dashboard visibility is fail-closed and server-authoritative.

A saved widget key does not grant access to its data. On every read the server:

1. evaluates the staff user's current Django capabilities;
2. removes saved widgets the user may no longer view;
3. applies normal Client/Internal, Ticket Queue and Infrastructure scope inside
   each domain query;
4. only executes data builders for widgets that remain enabled.

A preference update may contain only widget keys currently available to that
user. Forging a hidden widget key in the request is rejected.

Permission changes therefore take effect immediately without requiring the
stored Dashboard preference to be rewritten.

## Widget catalogue

### My Tasks

Requires `tasks.view_task`.

Shows incomplete Tasks assigned to the current staff user inside normal
Client/Internal Task scope, including open, due-today and overdue counts plus a
small current-work list.

### My Tickets

Requires `ticketing.view_ticket`.

Shows actionable Tickets inside the user's normal Client and Ticket Queue
scope. The widget reuses the server-backed default Ticket Queue preference, so
its normal work set is consistent with the Ticket workspace.

It exposes assigned, unassigned and active counts plus recent Tickets assigned
to the current user.

### Time

Requires `clients.view_timeentry`.

Shows the current user's Running Timer and personal tracked hours for the
current week. Time Entries retain normal Client/Internal scope semantics.

### Lead follow-up

Requires `crm.view_lead`.

Shows open Leads assigned to the current staff user. The widget is a follow-up
surface rather than a replacement for the Lead workspace.

### Current Projects

Requires `clients.view_project`.

Shows Planning, Active and Paused Projects inside the current user's normal
Client/Internal ownership scope. Project does not currently have a staff
assignee field, so this is intentionally a scoped current-project view rather
than an invented "assigned projects" concept.

### Technical health

Requires both:

- `monitoring.view_monitorcheck`;
- `monitoring.view_monitorincident`.

This matches the established Monitoring overview boundary. Incidents and
failing checks are additionally constrained through the normal Infrastructure
resource scope.

### Agenda

Requires `tasks.view_task`.

Shows incomplete Tasks assigned to the current user with due dates from today
through the next seven days. It deliberately shares the Task capability with
My Tasks rather than creating an artificial Dashboard-only permission.

### Recent activity

Requires `core.view_auditevent`.

Shows only safe AuditEvent metadata: action, target label and timestamp. Audit
metadata dictionaries are not projected through this widget and Credential
secret values are never surfaced.

Richer Client/resource activity belongs to Stage 9 rather than being invented
inside the Dashboard.

## Preference writes and audit

`PUT /api/admin/dashboard/preferences` validates the complete submitted layout
before storing it.

Successful changes create the safe audit action
`dashboard.preferences_updated`. Audit metadata records widget keys only; it
does not contain widget data, secret values or arbitrary browser-provided
configuration.

## Frontend behaviour

`/admin` is the My Work workspace. The frontend:

- renders the server-provided ordered layout;
- provides enable/disable controls only for the server-provided widget
  catalogue;
- supports move up/down ordering;
- supports the four documented desktop widths;
- offers a Recommended layout reset;
- saves the complete preference to Django and uses the returned workspace as
  the new state;
- provides deep links to the mature domain workspaces rather than duplicating
  full operational workflows inside Dashboard cards.

## Security boundaries

The Dashboard must not:

- treat stored layout as authorisation;
- query data for a widget after the required capability is lost;
- bypass Client/Internal, Ticket Queue or Infrastructure scope;
- surface Credential secret payloads;
- store widget data or secrets in browser persistence;
- expose Monitoring metadata with weaker permissions than the normal
  Monitoring workspace;
- become a generic user-defined query/report engine.

## Deliberate deferrals

Stage 8 provides the personal configurable work surface. It does not absorb
Stage 9 concerns.

The following remain later operational-polish work:

- unified global and Client-context search;
- richer Client/resource Activity timelines;
- notifications and notification preferences;
- SLA/escalation refinements;
- Credential expiry/rotation reminders;
- richer Calendar/Event behaviour;
- speculative user-authored query/report widgets.
