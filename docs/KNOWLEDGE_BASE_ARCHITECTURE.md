# Knowledge Base Architecture

## Purpose

The Knowledge Base is the platform's structured operational documentation system. It stores ADB-internal and client-owned runbooks, setup notes, maintenance procedures, troubleshooting guidance and other durable technical knowledge alongside the Client, Infrastructure and Credential Vault systems that give the documentation context.

The Stage 4 implementation deliberately keeps documentation and secrets separate. Knowledge Base content may link to Credential Vault records as metadata, but secret values are never copied into document responses, revisions, attachments, logs or search projections.

## Ownership and scope

Knowledge Base sections and documents use the shared platform ownership model:

- `internal` documentation belongs to ADB and has no client.
- `client` documentation belongs to exactly one client.
- A document and its section must always have the same ownership type and client.
- A document cannot be moved between ownership scopes by a normal edit. Such a move requires an explicit future migration operation.
- Client access is always restricted through the platform's existing client-scope policy.

Sections form an adjacency-list tree through `parent`. Parent and child sections must use the same ownership scope. The UI presents the resulting `path` as a folder-style navigation tree.

## Core models

### `KnowledgeBaseSection`

Represents a scoped folder in the documentation tree. It stores ownership, optional client, parent, name, description and display order.

### `KnowledgeBaseDocument`

Stores the current document projection:

- title and summary
- owning client scope
- section
- Markdown content
- tags
- optional future portal-visibility flag
- archive state
- creator/editor metadata

The current row is the mutable working projection. Historical content is stored separately in immutable versions.

### `DocumentVersion`

Every content-bearing revision is an immutable snapshot containing the title, Markdown content, section path, change summary, editor and revision number. Creation starts at version 1. Title, content or section changes create a new version. Metadata-only updates do not create artificial content revisions.

Revision numbers are allocated while the document row is locked with `SELECT ... FOR UPDATE`, preventing concurrent writers from assigning the same next version.

### Resource and Vault links

`KnowledgeBaseResourceLink` and `KnowledgeBaseCredentialLink` create explicit backlinks to Infrastructure and Credential Vault records. Both links are validated to ensure their target uses the same ownership/client scope as the document.

The API only projects links the caller is independently allowed to see. When an editor lacks Infrastructure or Vault visibility, omitted link arrays preserve the hidden existing links instead of deleting them.

## Lifecycle

Documents use archive/restore rather than destructive deletion in normal operation.

Archived documents:

- are excluded from the default `current` workspace view;
- remain available through archived/all views and immutable revision history;
- cannot be edited until explicitly restored;
- cannot receive new attachments;
- retain their existing links, versions and attachments.

This makes archive state a real read-only lifecycle boundary rather than merely a list filter.

## API and access model

The staff API is mounted below `/api/admin/knowledge-base` and requires Django model permissions in addition to staff status and client scope.

Primary operations include:

- workspace search/filter/pagination;
- options for visible clients, sections, Infrastructure resources and active Vault records;
- document create/detail/update;
- immutable version detail;
- archive/restore;
- section create/update;
- attachment upload/download/delete.

Ownership, client, section and Infrastructure Resource filters always narrow the caller's already-resolved access scope; they never widen it. Resource-filtered requests also require independent Infrastructure Resource visibility before the filter can be applied.

Search currently covers document title, summary, Markdown content and tag names using database `icontains` matching. Stage 4 does not introduce an external search engine.

## Markdown rendering

The admin frontend stores Markdown as the source format and renders it with `react-markdown` plus GitHub-Flavoured Markdown support.

Raw HTML embedded in Markdown is not rendered. This keeps the current reader/editor deliberately constrained and avoids creating an HTML sanitisation boundary merely for the Knowledge Base.

The operator workflow includes:

- global scoped folder navigation;
- search, ownership, client and archive-state filters;
- controlled create/edit forms;
- live Markdown preview;
- reader view;
- immutable revision browser;
- Infrastructure and Vault context;
- secure attachment controls.

Client and Infrastructure Resource pages also expose contextual Knowledge Base panels so operational documentation is reachable from the records it describes.

## Attachments and quarantine

Knowledge Base attachments use the same malware-scanning policy model as ticket attachments rather than a separate upload trust model.

Upload flow:

1. require document change permission plus attachment add permission;
2. confirm the document is visible and not archived;
3. enforce the configured 25 MB Knowledge Base size policy;
4. sanitise the original filename;
5. stream into private quarantine storage while calculating SHA-256;
6. detect content type from the file signature;
7. create the quarantined attachment record;
8. dispatch ClamAV scanning when scanning is enabled.

Download is a protected API operation. The caller must have document and attachment view permission and the document must remain in scope. When malware scanning is enabled, only attachments with a successful safe verdict are downloadable; pending, scanning, infected, blocked and failed attachments remain quarantined. In development environments where malware scanning is explicitly disabled, pending or failed scan states may be downloaded for local workflow testing, while infected, blocked and scanning states remain denied.

API projections expose only safe operator metadata such as original name, size, detected content type and scan status. Storage paths, hashes and raw scanner output are not included in document detail responses.

Legacy attachment rows are migrated into a blocked/untrusted state rather than being silently grandfathered into the new protected download path.

## Development data

`seed_knowledge_base_development` creates deterministic Stage 4 data after the base Client, Vault and Infrastructure development seeds exist. It creates:

- internal and client-owned nested section trees;
- Markdown runbooks;
- multiple immutable revisions;
- tags;
- client-scoped Infrastructure backlinks where matching demo resources exist;
- client-scoped Credential Vault metadata links where matching active demo credentials exist.

`seed_all_development` invokes the dedicated Knowledge Base seed after the earlier platform seeds so cross-domain links can be built against existing demo records.

## Deliberate Stage 4 boundaries

The current implementation does not attempt to deliver later roadmap features that require additional product or security design. Deferred items include:

- client self-service portal publication and approval workflow;
- external/full-text search infrastructure;
- collaborative real-time editing;
- document templates and approval/sign-off flows;
- automatic article generation from tickets/incidents;
- secret reveal or secret injection into Markdown;
- public documentation/status publishing;
- attachment inline rendering of arbitrary active content.

Those should build on the ownership, immutable history, capability-scoped backlinks and quarantine boundaries established here rather than bypassing them.
