# Unified Operational Search Architecture

## Purpose

Stage 9 introduces one permission-aware discovery surface across the ADB Business
Platform. Search is an operational read model over existing domains; it is not a new
data authority and it does not bypass the owning workspace for normal actions.

The first Stage 9 slice provides global and Client-context search across useful
non-secret metadata from Clients, Contacts, Leads, Tickets and visible Ticket message
text, Projects, Tasks, Knowledge Base documents, Infrastructure Resources and
Credential Vault metadata.

## API

```text
GET /api/admin/search?q=<query>&client_id=<optional>&per_type=<optional>
```

Rules:

- queries are trimmed and must contain 2-160 characters;
- results are capped per domain (default 5, maximum 10);
- `client_id` narrows search to one Client already inside the caller's Client scope;
- an inaccessible Client context returns not-found rather than exposing existence;
- result groups are returned only when the caller has the owning domain capability and
  at least one matching scoped result.

The API returns safe metadata plus deep links. It does not perform domain mutations.

## Capability and object scope

Search has no independent permission that can widen access. Each domain participates
only when the caller has its ordinary view capability and every query begins from the
normal scope boundary for that domain.

Examples:

- Clients and Contacts use staff Client scope;
- Client/Internal Projects and Tasks include Internal records plus authorised Clients
  globally, and only the selected Client in Client-context mode;
- Tickets use Ticket Queue scope and Client scope together;
- unmatched/internal Tickets remain discoverable only through an authorised Queue;
- Infrastructure uses `scope_infrastructure_resources_for_user`;
- Credentials use `scope_credentials_for_user`;
- Knowledge Base follows the same Client/Internal ownership boundary as its normal
  workspace;
- Leads remain capability-scoped because the current Lead model has no separate object
  scope; Client-context search includes converted Leads for that Client.

The frontend is presentation only. Removing a permission or object grant immediately
removes the corresponding search result because the backend resolves live access for
every request.

## Ticket message search

Ticket search may match subject/reference and visible Ticket message subject, sender
or normalised plain-text body. This improves operational recall without returning
message-body snippets through the global result projection.

A Ticket found through message text must still be inside both the caller's Queue and
Client visibility. Internal Ticket Notes are not searched by this first slice.

## Credential Vault boundary

Credential search is metadata-only. Its search predicate is deliberately restricted
to fields already exposed by ordinary Credential metadata views:

- name;
- description;
- username;
- URL;
- Credential Type name.

It never searches or returns:

- legacy plaintext password/API key/secret/private-key/note fields;
- `encrypted_secret_payload`;
- decrypted secret values;
- secret field contents;
- arbitrary secret-bearing audit metadata.

Search results link to the normal Credential workspace where reveal/copy/download
remain separate explicit, audited capabilities.

## Search implementation

The initial implementation uses ordinary database predicates and bounded domain
queries. PostgreSQL-backed full-text/ranking can be introduced later if real usage
shows that quality or scale warrants it. A separate search service is intentionally
not introduced at this stage.

Search does not load whole operational datasets into the browser. The server performs
scope filtering, matching and per-domain limiting before returning results.

## Deliberate boundaries

This first Stage 9 slice does not yet complete:

- typo/fuzzy matching or relevance scoring;
- external search infrastructure;
- indexing decrypted Credential values;
- searching internal Ticket Notes;
- the richer Client/resource Activity model;
- notifications, Credential rotation reminders or SLA escalation;
- topology visualisation/navigation polish;
- richer Calendar/Event behaviour.

Those remain later Stage 9 slices in `PLATFORM_MASTER_PLAN.md`.
