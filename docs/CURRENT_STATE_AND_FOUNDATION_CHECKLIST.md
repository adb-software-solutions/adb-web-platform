# Current State and Operational Roadmap

## Purpose

This document is the implementation companion to `PLATFORM_MASTER_PLAN.md`.
It records what is implemented by the platform at this point in the build and
what remains in the agreed sequence.

Snapshot for this refresh:

- date: **2026-08-25**;
- base before the Credential Vault slice: `main` at the merged platform-docs
  refresh;
- this document is updated in the same change set as the full Credential Vault,
  so the Vault capabilities below describe the post-merge platform state.

Credential-specific security and operational rules are defined in
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

## 1. Repository/application foundation

### Implemented

- [x] One shared Django backend is the business-data/auth/scope authority.
- [x] Django Ninja is the API layer.
- [x] PostgreSQL/Redis/Celery foundations are established.
- [x] ADB Software Solutions, ADB Web Designs and ADB Technology are
      first-class Brands.
- [x] ADB Software Solutions public + `/admin` routes share one Next.js app.
- [x] Authentication/account security is a separate Next.js application.
- [x] Django session/TOTP/WebAuthn/passkey flows remain authoritative.
- [x] Tailwind CSS is the frontend styling standard.
- [x] The operations workspace is dark-only and workflow-oriented.
- [x] Brand-aware CMS/public content isolation exists.
- [x] append-only AuditEvent foundation exists.
- [x] deterministic development seeding and repository CI/devcontainer tooling
      exist.

## 2. Platform-wide operational UX rules

### Implemented direction

- [x] Active/current/actionable records are the default in the major operational
      areas already refined.
- [x] history is retained behind explicit filters/views rather than deleted.
- [x] shared right-side Task/Record drawer patterns preserve list/workspace
      context.
- [x] full-page deep links remain available for refresh/bookmark/complex work.
- [x] data-heavy operational pages use server-side pagination/filtering/sorting
      and statistics where implemented.
- [x] Client/Internal ownership is a first-class platform rule.
- [x] Django capability + scope remains authoritative regardless of frontend
      visibility.

### Apply consistently to future work

- [ ] keep KB, Monitoring, commercial records and later portal/admin surfaces
      current-first where that domain has meaningful lifecycle/history.
- [ ] persist cross-device user preferences server-side rather than defaulting
      to browser-only storage.

## 3. Clients and Contacts

### Implemented

- [x] Client create/edit lifecycle management.
- [x] Active/Inactive/Archived Client lifecycle.
- [x] global Client overview defaults to Active Clients.
- [x] Client overview statistics, filtering and server-side pagination.
- [x] Client records can open in a right-side record drawer.
- [x] ClientContact create/edit/deactivate.
- [x] Primary/Billing/Technical contact semantics.
- [x] Client workspace shows active contacts by default with explicit inactive
      history.
- [x] Contact routes open a Contact workspace rather than only an edit form.
- [x] Contact workspace exposes Contact-specific Tickets.
- [x] Client workspace exposes current Projects and keeps archived projects out
      of the default view while retaining completed project history.
- [x] Client/Contact email identity participates in Ticket sender resolution.
- [x] Client workspace has foundations for Projects/Tickets, Infrastructure and
      active Client-owned Credentials.

### Next Client Command Centre work

- [ ] consolidate Overview/Contacts/Projects/Tasks/Tickets/Time/Infrastructure/
      Credentials/Knowledge into one coherent Client navigation model.
- [ ] surface current work/open communication/technical state first within each
      section.
- [ ] add Client period summaries, especially tracked/billable Time.
- [ ] add permission-aware contextual create actions.
- [ ] add useful Client Activity/history.
- [ ] add commercial history later without turning Client into a giant
      unstructured page.

## 4. CRM / Leads

### Implemented

- [x] Lead create/edit/detail/workspace.
- [x] Lead ownership/assignment.
- [x] explicit `open` / `won` / `lost` outcome semantics on LeadStatus.
- [x] default Lead view is My active/open Leads.
- [x] Unassigned and All Active operational views.
- [x] Won/Lost/All Leads history views.
- [x] server-side Lead statistics, filtering and pagination.
- [x] Lead records open in a right-side drawer.
- [x] Lead edit can occur inside the drawer.
- [x] website contact submissions create Leads and canonical Tickets.
- [x] matching inbound/outbound Ticket communication appears on the Lead.
- [x] Lead email sends through configured Microsoft 365 Shared Mailboxes using
      the Ticket/Graph layer; there is no parallel `mailto:` workflow.
- [x] Lead -> Client + primary Contact conversion retains related Ticket and
      communication history.

### Remaining/refinement

- [ ] stronger manual contact matching/deduplication where sender matching is
      insufficient.
- [ ] explicit manual conversation linkage only if real usage shows it is
      needed.
- [ ] add commercial value/follow-up metadata in the commercial/analytics phase
      rather than speculatively duplicating future models now.

## 5. Projects

### Implemented

- [x] Client/Internal Project ownership.
- [x] create/edit/status/archive lifecycle.
- [x] current global Project views default to Planning/Active/Paused.
- [x] Completed/Archived/All are explicit history views.
- [x] Project workspace is work-first rather than metadata-first.
- [x] Work, Timeline, Overview and Time tabs.
- [x] Project List/Board work surfaces.
- [x] quick Task creation inside Project workflow columns.
- [x] persistent card ordering and drag/drop.
- [x] `No task list` handling for unorganised Project Tasks.
- [x] inline Task completion/reopen controls.
- [x] dependency-aware Project Timeline with Day/Week/Month zoom.
- [x] dated Subtasks appear in the Project Timeline.
- [x] dependency connector arrows and blocked/completed visual state.
- [x] Project Time ledger with tracked/billable/non-billable totals and related
      work context.

### Remaining/refinement

- [ ] first-class Project milestones where the current Task/date model is not
      sufficient.
- [ ] Project participants/ownership only if real collaboration workflows need
      more than existing assignment/context.
- [ ] richer contextual Tickets/KB/Infrastructure links as those domains
      mature.

## 6. Tasks / ADB work management

### Implemented

- [x] Tasks may be standalone Internal, Client-owned or Project-owned.
- [x] My Tasks is the default global Task experience.
- [x] Today, Upcoming, Overdue, Completed and All Tasks focus views.
- [x] server-authoritative counts for focus views.
- [x] quick capture with Internal/Client/Project context and due-date shortcuts.
- [x] quick-captured Tasks assign to the current user.
- [x] shared Task drawer used across work-management surfaces.
- [x] direct editing of title, description, assignee, priority, start/due dates.
- [x] structural Planning & organisation fields available in the Task workspace.
- [x] Client/Internal/Project Task Lists and ordered Sections.
- [x] List/Board/Timeline Task List workspaces.
- [x] Section rename/reorder.
- [x] quick add inside Board/Sections.
- [x] Task ordering/cross-section drag/drop inside valid ownership context.
- [x] Subtasks with inherited work context.
- [x] blocking dependencies and cycle detection.
- [x] daily/weekly/monthly recurrence.
- [x] completing a recurring occurrence materialises the next occurrence while
      preserving history.
- [x] Task comments/discussion.
- [x] completion/reopen controls in My Tasks, Project and Task List surfaces.
- [x] embedded live timer and Task time history.

### Remaining/refinement

- [ ] agree long-term delete/archive semantics for Tasks if needed beyond
      completion/history.
- [ ] explicit Ticket-linked Tasks only when the workflow is designed; do not
      bolt it on as a loose nullable FK without UX.
- [ ] notification/escalation behaviour later.

## 7. Calendar / planning

### Implemented

- [x] permission-aware Calendar API/workspace foundation.
- [x] dated Task and Project work can be shown on the Calendar.
- [x] Client/Project/source filtering foundations.
- [x] Task links preserve Task-drawer context.

### Remaining/refinement

- [ ] richer day/week operational planning where useful.
- [ ] stronger first-class Project milestone support.
- [ ] design a real Event/Meeting domain later rather than pretending Tasks are
      Events.
- [ ] external calendar integration only after an explicit design decision.

## 8. Time Tracking

### Implemented

- [x] manual Time Entries.
- [x] Client/Internal ownership with Internal time forced non-billable.
- [x] Project/Task/Ticket attribution and valid direct Client context.
- [x] persistent server-side RunningTimer.
- [x] one active timer per staff user.
- [x] backend-calculated Start/Stop/Cancel lifecycle.
- [x] Task live timer.
- [x] Ticket live timer.
- [x] contextual Time panels/history on Task/Ticket/Project surfaces.
- [x] Time Tracking workspace starts with active timer and compact Start/Add
      Manually controls.
- [x] Time browsing is by Client/Project/Internal rather than a giant global
      history table.
- [x] period filters include This Week, Last Week, 30 Days, This Month, Last
      Month and This Year.
- [x] scoped entry/report APIs and tracked/billable/non-billable summaries.
- [x] timer stop falls back to useful contextual descriptions when the user
      leaves the description blank.

### Remaining/refinement

- [ ] edit/delete Time Entries with clear permission/audit policy.
- [ ] richer staff breakdown/reporting where useful.
- [ ] Client Command Centre period summaries.
- [ ] future invoice/commercial linkage without making invoicing a current Time
      dependency.

## 9. Ticketing and communications

### Implemented

- [x] TicketQueue, Ticket, TicketMessage, TicketNote and TicketAttachment.
- [x] Client + Ticket Queue capability/scope enforcement.
- [x] main Ticket page uses a dedicated operational focus API rather than the
      generic history/scoped collection API.
- [x] My Tickets is the default work queue.
- [x] Unassigned and All Active views.
- [x] Resolved/Closed/All Tickets history.
- [x] enabled Queue navigation as a first-class sidebar concern.
- [x] per-user default Ticket Queues stored on StaffAccessProfile.
- [x] empty stored queue preference means all accessible enabled queues.
- [x] Ticket sorting by operational priority, update time, priority, creation
      and subject.
- [x] Ticket records can open in the shared right-side drawer.
- [x] Ticket detail retains full controls and live timer.
- [x] Internal Notes are merged chronologically into the message conversation
      as visibly distinct staff-only cards.
- [x] Graph connection and Shared Mailbox configuration.
- [x] certificate/client-secret app-only Graph support.
- [x] Shared Mailbox verification.
- [x] persisted delta sync/cursors and worker locking.
- [x] inbound normalisation/thread matching/idempotency.
- [x] outbound replies/new Lead email through Graph/Celery.
- [x] website contact forms feed canonical Ticket ingestion.
- [x] deterministic routing/classification.
- [x] database-backed Vendor/service sender routing.
- [x] attachment quarantine/policy plus optional ClamAV scanning.

### Remaining/refinement

- [ ] harden the rare ambiguous-send case where Graph accepts mail but the
      worker loses the provider response before local persistence.
- [ ] notification/SLA/escalation behaviour later.
- [ ] richer cross-links into Tasks/KB/Infrastructure as surrounding domains
      mature.

## 10. Microsoft 365 deployment model

### Established architecture

- [x] one tenant/app-level MicrosoftGraphConnection can serve many Shared
      Mailboxes.
- [x] production prefers certificate-based app-only authentication.
- [x] Exchange Online RBAC for Applications is the Microsoft-side mailbox
      boundary.
- [x] enabled database Mailbox rows are the narrower operational allow-list.
- [x] licensed user mailboxes are not intended Ticket sources.
- [x] Graph private-key/certificate material can be administered through the
      encrypted Credential Vault instead of legacy plaintext secret fields.

### Current ADB default

- [x] the preferred normal ADB Exchange management scope is dynamic across
      `RecipientTypeDetails -eq 'SharedMailbox'` so newly created Shared
      Mailboxes do not need a new RBAC rule/assignment.
- [x] adding a new Ticket mailbox should reuse the existing Graph connection and
      certificate; the operator configures/verifies the mailbox in ADB rather
      than re-entering Microsoft app credentials.

See `MICROSOFT_GRAPH_TICKETING_SETUP.md` and
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

## 11. Infrastructure

### Implemented

- [x] `InfrastructureResource` common identity.
- [x] Client/Internal ownership.
- [x] lifecycle/environment/criticality/current-first filtering.
- [x] resource tags.
- [x] `ServiceProvider`.
- [x] resource-backed `ProviderAccount`.
- [x] typed `ResourceRelationship` topology.
- [x] ownership and cross-Client relationship validation.
- [x] permission-aware global/Client resource collections and details.
- [x] typed one-to-one legacy specialist identity bridges.
- [x] explicit `reconcile_legacy_infrastructure` capability.
- [x] operator-driven reconciliation with no guessed ownership.
- [x] reconciliation workspace with Unlinked/Linked/All history.
- [x] specialist safe metadata projection that excludes secret-bearing legacy
      fields.
- [x] structured resource drawer/full-page workspaces.
- [x] relationship create/delete management with backend validation.
- [x] Client-context Infrastructure workspace.
- [x] Infrastructure Resource workspaces surface linked active Credentials.
- [x] native Server/compute/network specialists with resource-centric create/edit/archive flows.
- [x] native Database Instance and Logical Database specialists.
- [x] native Application and Application Environment specialists.
- [x] native Source Repository specialists plus typed Application/Repository role/path links.
- [x] deterministic safe legacy Server/Database/Application promotion where source data is unambiguous.
- [x] native Website and concrete Website Endpoint specialists.
- [x] native Domain, DNS Zone and structured DNS Record specialists.
- [x] non-secret TLS Certificate metadata plus typed Domain coverage.
- [x] explicit hosting/registrar/DNS/CDN/WAF Provider Account context.
- [x] Website Endpoint links to Application Environment, Domain and TLS Certificate.
- [x] nested Website Endpoint, DNS Record and TLS Domain-coverage operations in the resource workspace.
- [x] deterministic safe legacy Website/Domain/SSL promotion without ownership/provider/alias/nameserver guessing.
- [x] unified resource drawer/workspace create/edit flows for the implemented specialist families.

### Next technical slices

- [ ] Monitoring checks/history/incidents.
- [ ] Docker/Kubernetes and later specialist operations resources.

## 12. Credential Vault

### Implemented

- [x] StoredCredential Client/Internal ownership.
- [x] typed credential templates for passwords, SSH, DB, API/OAuth, service
      accounts, certificates, licences, recovery/encryption/custom secrets.
- [x] encrypted, versioned secret payload service.
- [x] environment-managed ordered MultiFernet key ring.
- [x] Active/Inactive/Archived lifecycle and Active-first operational views.
- [x] searchable non-secret metadata, expiry and rotation metadata.
- [x] permission-aware secure CRUD.
- [x] separate reveal/copy/download operations and audit paths.
- [x] ordinary API responses contain metadata/secret-field presence only, not
      secret values.
- [x] safe browser handling for explicitly revealed secrets without persistence
      to localStorage/sessionStorage/routes/normal caches.
- [x] Infrastructure resource links with Client-boundary validation.
- [x] Client and Infrastructure contextual Credential registers.
- [x] atomic legacy plaintext -> encrypted payload reconciliation.
- [x] migrated legacy secret fields remain usable even where an old credential
      type had no modern field schema.
- [x] encryption fails closed when the key ring is unavailable/invalid.

The authoritative design, key-rotation procedure, permission model, audit
requirements and browser-handling rules are in
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

### Later Vault work

- [ ] remove reconciled legacy plaintext columns when production migration is
      verified.
- [ ] scheduled expiry/rotation reminders and health reporting.
- [ ] bulk key-rotation tooling/reporting.
- [ ] richer template administration only if actually needed.
- [ ] consider step-up/break-glass behaviour only if the threat model justifies
      it.

## 13. Knowledge Base

### Implemented foundation

- [x] existing KB model/register foundation.
- [x] Client/Internal ownership and permission foundations.
- [x] version-history model foundation.

### Agreed redesign / missing

- [ ] filesystem-like folder/section tree.
- [ ] proper document read/workspace experience.
- [ ] Markdown or controlled rich-text editor.
- [ ] immutable version creation through domain services.
- [ ] author/editor context.
- [ ] attachments where appropriate.
- [ ] tags/search metadata.
- [ ] Infrastructure/Project/Ticket/Credential links where operationally useful.
- [ ] Client/resource contextual navigation.
- [ ] global and Client-context permission-aware search.
- [ ] future portal visibility explicit and private by default.

The KB redesign follows the current Infrastructure/Monitoring run. Sensitive
values remain in Credentials and are referenced, not copied into KB content.

## 14. Monitoring

### Current state

There is not yet a mature Monitoring subsystem.

### Agreed target

- [ ] MonitorCheck/domain model attached to structured resources.
- [ ] ICMP, TCP, HTTP/HTTPS, content, TLS, DNS and domain-expiry checks.
- [ ] schedules/timeouts/failure/recovery thresholds/severity.
- [ ] historical results.
- [ ] incidents representing failure -> recovery periods.
- [ ] Celery Beat/worker execution through reusable monitoring services.
- [ ] current-first global and Client technical health views.
- [ ] uptime/response history and expiry dashboards.
- [ ] Credential references for checks that require authentication.

## 15. Users & Access

### Backend foundation implemented

- [x] Django Groups/Permissions capability model.
- [x] StaffAccessProfile.
- [x] all/selected Client scope.
- [x] all/selected Ticket Queue scope.
- [x] default Ticket Queue preference on StaffAccessProfile.
- [x] reusable scope-policy helpers.

### Missing custom operations experience

- [ ] complete the Users & Access workspace/route.
- [ ] staff list/detail.
- [ ] create/invite/activate/deactivate according to identity policy.
- [ ] Group/capability administration.
- [ ] Client scope administration.
- [ ] Ticket Queue scope administration.
- [ ] clear effective-access display.
- [ ] audit access changes.
- [ ] complete permission-boundary tests around administration APIs.

Routine staff administration must not depend on Django superuser access.

## 16. Dashboard / My Work

### Implemented foundation

- [x] initial fixed operational dashboard/API foundation.

### Missing

- [ ] permission-aware widget catalogue.
- [ ] per-user server-persisted layout/configuration.
- [ ] reorder/move/resize where useful.
- [ ] My Tickets / selected Queue widgets.
- [ ] My Tasks/Overdue/Upcoming widgets.
- [ ] active timer/recent Time.
- [ ] Leads needing follow-up.
- [ ] Project work/milestones.
- [ ] Monitoring/Infrastructure incidents/expiry.
- [ ] Calendar agenda.

## 17. Search, Activity, notifications and SLA polish

### Missing / later

- [ ] unified permission-aware global search.
- [ ] Client-context search across mature domains.
- [ ] metadata-only Credential search; decrypted secrets must never be indexed.
- [ ] Client/resource Activity timeline.
- [ ] topology/navigation polish across Infrastructure/KB/Credentials.
- [ ] notification preferences and agent notifications.
- [ ] SLA/escalation behaviour once Ticket workflows are stable in real usage.
- [ ] richer Calendar/Event integration.

PostgreSQL search is acceptable initially; do not add dedicated search
infrastructure without a real need.

## 18. Commercial and analytics layer

### Agreed future scope, not implemented yet

- [ ] products/services catalogue.
- [ ] recurring services.
- [ ] quotes/proposals.
- [ ] contracts.
- [ ] invoices/billing.
- [ ] Stripe/payment tracking.
- [ ] profitability reporting.
- [ ] Client lifetime value.
- [ ] time-versus-pay/revenue analysis.
- [ ] Lead-source conversion and revenue attribution.

Detailed signing/accounting/tax/retainer/forecasting/SLA models are not yet
agreed and should not be invented during unrelated implementation work.

## 19. Public websites

### Foundation implemented

- [x] Brand-aware CMS/public API isolation.
- [x] contact-form Brand/source ingestion into Lead + Ticket pipeline.
- [x] separate public Next.js applications exist.

### Primary build focus deferred

- [ ] complete each Brand's public experience after the internal platform and
      agreed commercial contracts are stable enough not to be repeatedly
      redesigned underneath it.

Security/fix/integration work may still happen opportunistically.

## 20. Client portal

### Deferred

- [ ] design explicit portal identity link to ClientContact.
- [ ] design per-domain portal visibility.
- [ ] expose only deliberately Client-visible Tickets/Projects/Documents/etc.
- [ ] never expose Internal resources, credential secrets, Ticket Notes or
      staff-only audit/security data implicitly.

## 21. Current ordered implementation sequence

1. **Core typed Infrastructure — implemented** — Server/network/Database/Application
   structures and safe specialist CRUD.
2. **Web Infrastructure — implemented** — Website/Endpoint/Domain/DNS/TLS/provider context.
3. **Monitoring + technical dashboards — next.**
4. **Knowledge Base redesign + resource links/search foundations.**
5. **Docker/Kubernetes + storage/backups/services/scheduled jobs.**
6. **Client Command Centre integration pass.**
7. **Users & Access custom operations UI.**
8. **Dashboard / My Work configurable widgets.**
9. **Unified search/topology/activity/audit/notifications/SLA/Calendar polish.**
10. **Commercial + analytics layer.**
11. **Public websites as primary focus.**
12. **Client portal.**

Small dependency-driven slices may move, but major order changes should update
`PLATFORM_MASTER_PLAN.md` and this checklist.

## 22. Internal-platform readiness gate

Before the public websites become the main sustained focus, the platform should
be capable of normal ADB operations without relying on several parallel tools:

- Clients/Contacts managed through the custom UI;
- Leads and tracked communication usable day to day;
- Projects/Tasks/Time usable as ADB's work-management system;
- Ticketing/Graph mail usable as the communication system;
- Infrastructure/Credentials/Knowledge usable as the technical documentation
  system;
- Monitoring surfaces current technical health;
- Client Command Centre exposes the major operational context;
- Users & Access is safe and usable;
- Dashboard/My Work is materially useful;
- cross-domain search/navigation is coherent;
- CI/security/dependency health remains green.

The platform does not need every speculative future feature before that gate.
Commercial functionality is its own later phase and the Client portal follows
only when internal/commercial visibility rules are mature.
