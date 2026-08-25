# Infrastructure, Credentials, Knowledge and Monitoring Architecture

## Purpose

This document defines the technical-operations architecture for the ADB
Business Platform. Read it with:

- `PLATFORM_MASTER_PLAN.md`;
- `PERMISSIONS_AND_ACCESS_MODEL.md`;
- `DOMAIN_MODEL_AUDIT.md`;
- `CURRENT_STATE_AND_FOUNDATION_CHECKLIST.md`;
- `CREDENTIAL_VAULT_ARCHITECTURE.md`.

The target is an IT Glue-style workspace for software development, web
delivery, DevOps, Linux/system administration and technical support.

It is **not** a generic asset table and it is not a set of disconnected CRUD
registers. The product goal is contextual technical navigation: from a resource,
an authorised operator should be able to understand what it is, who owns it,
what it depends on, what depends on it, how it is accessed, how it is monitored
and where its documentation lives.

---

## 1. Structured resource architecture

Technical records use a shared `InfrastructureResource` identity plus strongly
typed specialist records.

Conceptually:

```text
InfrastructureResource
├── Server / compute
├── Network resource
├── Database instance / logical database
├── Application / Application Environment
├── Website / endpoint
├── Domain / DNS / TLS
├── Kubernetes / container resources
├── Provider Account
├── storage / backup / service / scheduled job
└── other useful specialist families
```

`InfrastructureResource` owns cross-cutting identity/ownership/lifecycle. It
does not replace specialist relational models with EAV, arbitrary JSON or a
graph database.

Specialist models keep fields/invariants that belong to their technical domain.
The shared resource identity exists so cross-cutting systems can attach
consistently:

- Credentials;
- Knowledge Base documents;
- Monitoring checks/incidents;
- tags;
- Activity/audit context;
- generic technical relationships;
- search/topology/navigation.

---

## 2. Ownership

Every structured resource is deliberately:

```text
client-owned -> a real Client
internal     -> ADB itself, Client is null
```

Never create a fake ADB/Internal Client.

Validation must enforce:

- client-owned resources require a Client;
- Internal resources do not reference a Client;
- two resources owned by different Clients cannot have a direct generic
  relationship;
- Internal ADB resources may relate to Client resources where a genuine shared
  dependency exists.

Valid examples:

```text
Client Website -> hosted_on -> Internal ADB Server
Client Domain  -> managed_by -> Internal Cloudflare Provider Account
```

A future Client portal must not expose Internal resource details merely because
an Internal resource relates to a Client resource.

---

## 3. Capability and scope

Infrastructure follows the platform rule:

```text
Django capability + ownership scope
```

Authorised staff may access Internal resources according to Infrastructure
capability. Client-owned resources additionally require access to the owning
Client.

This applies to:

- collections;
- details/drawers;
- Client-context Infrastructure views;
- relationship selectors and mutations;
- reconciliation;
- specialist projections;
- Credentials/KB/Monitoring panels;
- search/topology.

Denied records are removed at service/queryset level. Frontend filtering is not
an access-control mechanism.

Credential metadata and secret actions add their own independent capability
boundary on top of Infrastructure visibility; seeing a Server does not grant
permission to reveal its linked password or SSH key. See
`CREDENTIAL_VAULT_ARCHITECTURE.md`.

---

## 4. `InfrastructureResource`

The shared resource record carries cross-cutting fields such as:

- Client/Internal ownership;
- name;
- resource type;
- lifecycle;
- environment;
- criticality;
- safe description;
- tags;
- creator/updater metadata;
- archive/create/update timestamps;
- future explicit portal-visibility metadata, private by default.

Normal operational views are **current-first**. Retired/Archived resources are
history and should not dominate the default register or Client context.

---

## 5. Strongly typed specialists

Prefer explicit relational fields for known semantics.

Examples:

- a logical Database belongs to/uses a Database Instance through a real
  relation;
- a self-hosted Database Instance may run on a Server;
- an Application Environment belongs to an Application;
- a Website endpoint may reference an Application Environment;
- a Kubernetes Namespace belongs to a Cluster;
- a repository/source relationship should carry an explicit role when useful.

Generic `ResourceRelationship` edges complement these known relationships. They
do not replace good specialist modelling.

Secret material is never a specialist-field concern. Specialist records link to
Vault Credentials rather than adding password/token/private-key columns.

---

## 6. Generic resource relationships

`ResourceRelationship` supplies the cross-domain topology graph without a graph
database.

Relationship semantics include concepts such as:

- `depends_on`;
- `hosted_on`;
- `connects_to`;
- `managed_by`;
- `backed_up_to`;
- `protected_by`;
- `routes_to`;
- `uses`;
- `contains`;
- `related_to`.

Relationships are directed, may carry human context, and must enforce:

- no self-link;
- no duplicate equivalent relationship;
- target visibility;
- Client ownership boundaries.

The graph should ultimately support useful contextual/topology views such as:

```text
Website
  -> Application Environment
  -> Application
  -> Server/Provider Account
  -> Database
  -> Domain/DNS/TLS
  -> Monitoring
  -> Credentials
  -> Knowledge/runbooks
```

---

## 7. Providers and Provider Accounts

Provider identity is data, not a hard-coded choice list.

`ServiceProvider` represents organisations/services such as DigitalOcean, AWS,
Microsoft, Cloudflare, GitHub, Hetzner, registrars and other vendors.

`ProviderAccount` represents the actual account/tenant/project used by ADB or a
Client and is resource-backed so Credentials, Knowledge, Monitoring and
relationships attach consistently.

Safe account metadata may include:

- account/customer ID;
- tenant/project ID;
- portal URL;
- default region;
- support plan;
- billing/reference identifiers.

Passwords, API tokens, client secrets and private keys never belong directly on
ProviderAccount. They are stored in the Credential Vault and linked to the
Provider Account resource.

The operational Provider workspace implements server-side catalogue/account
search and filtering, current-first account lifecycle, scoped Client/Internal
creation, safe metadata editing and explicit archive actions. Provider Account
ownership is immutable after creation so an edit cannot silently invalidate
Credential/resource ownership boundaries. Account credentials remain explicit
Vault links visible through the shared resource workspace.

---

## 8. Legacy specialist reconciliation

The repository contains older flat specialist models including Server,
Database, Website, Domain, SSLCertificate, Licence, Application, MobileApp, API,
Bot and EmailSystem.

These rows are preserved while the structured model becomes the operational
identity.

### Implemented transition model

Every current legacy family has a typed one-to-one identity bridge to
`InfrastructureResource`.

The bridge enforces resource-type compatibility: a legacy Server reconciles
only to a resource whose type is Server, a legacy Website only to Website, and
so on.

Reconciliation is explicit/operator-driven. The system does **not** guess
Client/Internal ownership from historical data.

The operator chooses/validates:

- ownership type;
- Client when Client-owned;
- resource name;
- lifecycle;
- environment;
- criticality.

The dedicated `reconcile_legacy_infrastructure` permission protects this
migration operation. Normal Client scope still applies.

Each legacy row is reconciled only once.

### Safe specialist projection

During transition, structured resource detail may project safe specialist
metadata from the legacy record.

Secret-bearing legacy fields such as licence keys, passwords/API material and
general sensitive notes must not leak through the structured resource API.
Where those values are migrated, the target is an encrypted Vault Credential,
not another Infrastructure metadata field.

The workspace retains provenance/back-links while the bridge remains useful.

### Migration discipline

1. preserve historical migrations;
2. preserve legacy rows/model identity;
3. do not guess ownership;
4. add/keep typed identity bridges;
5. make the structured resource the operational relationship anchor once
   reconciled;
6. introduce mature specialist CRUD progressively;
7. migrate secret-bearing legacy values into the Credential Vault before
   removing duplicate plaintext fields;
8. retire duplicated legacy fields only after structured replacements are
   migrated and verified.

---

## 9. Credential integration

Credentials are an implemented, separate security boundary attached to
resources rather than plaintext fields embedded in Infrastructure.

The authoritative Vault design is `CREDENTIAL_VAULT_ARCHITECTURE.md`.

### Resource links

A Credential may link to one or more Infrastructure resources with purpose and
primary semantics.

Examples:

```text
SSH Credential       -> Server
Database Login       -> Database + Application Environment
Cloudflare API Token -> Provider Account + managed Domains
Kubeconfig            -> Kubernetes Cluster
Certificate Keypair  -> TLS/Endpoint resource
```

Client-owned Credentials may link only to resources owned by that same Client.
Internal Credentials may link to Internal or Client resources where this
represents a real shared ADB operational credential.

### Security rules

- ordinary APIs/search return credential metadata only;
- secret values remain in the encrypted, versioned credential payload;
- `CREDENTIAL_ENCRYPTION_KEYS` supplies the ordered MultiFernet key ring;
- reveal/copy/download are explicit separately permissioned actions;
- audit records field/context only, never the secret value;
- revealed browser values are ephemeral and are not persisted to local/session
  storage, routes or normal application caches;
- Infrastructure must reference Credentials instead of duplicating plaintext
  secrets;
- missing/invalid encryption configuration fails closed.

### Implemented workspace integration

- `/admin/credentials` is Active-first with explicit history views;
- typed create/edit forms use credential-template schemas;
- Client workspaces surface active Client-owned Credentials;
- Infrastructure Resource workspaces surface linked active Credentials;
- legacy StoredCredential plaintext values can be atomically reconciled into
  the encrypted payload before legacy columns are removed later.

---

## 10. Knowledge Base integration

Structured resources and Knowledge documents are distinct but deeply linked.

The agreed KB direction is a Client/Internal filesystem-like documentation tree
with Markdown/controlled rich text, versions and secure attachments.

A document/resource relationship may express semantics such as:

- documentation;
- runbook;
- deployment procedure;
- troubleshooting;
- architecture;
- disaster recovery;
- restore procedure;
- configuration.

A mature Resource workspace should surface linked documentation. A KB document
should surface related resources.

The KB must not become an alternative plaintext password store. Sensitive
access material belongs in the Credential Vault; documentation can link to the
Credential record without embedding its secret value.

---

## 11. Monitoring architecture

Monitoring is a separate cross-cutting subsystem attached to Resources. It must
not be represented by a single `is_up` field on Server or Website.

Initial target check types:

- ICMP/ping;
- TCP port;
- HTTP/HTTPS;
- expected/forbidden text/regex;
- TLS certificate validity/expiry;
- DNS record checks;
- domain registration expiry.

Checks carry scheduling, timeout, failure/recovery thresholds and severity.
Historical results record observations; Incidents represent meaningful
failure-to-recovery periods.

Celery Beat/workers execute due checks through reusable monitoring services.

The Monitoring UI should follow the platform's current-first rule:

- open incidents and unhealthy resources first;
- healthy history available but not dominant;
- global and Client-scoped health views;
- uptime/response history;
- expiring domain/TLS alerts.

If a check needs authentication, it references an encrypted Vault Credential.
Monitoring result/history records never copy the secret into their metadata.

Detailed retention/escalation/notification schema should be decided in the
Monitoring slice rather than guessed now.

---

## 12. Target specialist families

### Compute and networking

- Servers/VMs/bare-metal/container hosts;
- network interfaces/IP addresses;
- networks/VPCs/VLANs/subnets/VPNs;
- firewall/load-balancer/network-device records where operationally useful.

### Applications and source

- logical Applications;
- Application Environments (production/staging/development etc.);
- Source Repositories and role/context;
- APIs/background services/bots/integrations/mobile apps;
- useful technology/version catalogue links.

### Databases

- Database Instances/services;
- managed versus self-hosted semantics;
- Logical Databases;
- Server/Provider/endpoints/TLS/HA/replication metadata;
- Credentials by Vault reference.

### Web, domains and TLS

- Websites/endpoints;
- Domains;
- DNS Zones/Records where useful;
- TLS Certificates;
- registrar/DNS/CDN/WAF Provider Account relationships;
- administrative credentials/keypairs by Vault reference.

### Containers and Kubernetes

- Docker/Podman/container stacks/services;
- Kubernetes Clusters;
- Namespaces;
- workloads;
- Services/Ingresses;
- Helm releases;
- persistent storage links;
- kubeconfigs/service tokens/certificates through Vault Credentials.

Document the useful operational shape without manually cloning the Kubernetes
API into Django.

### Operations

- storage resources;
- backup plans;
- system services;
- scheduled jobs/cron/systemd timers;
- licences/subscriptions;
- email systems and other useful operational configuration.

---

## 13. Resource workspace UX

Mature resource workspaces should converge on a recognisable pattern:

```text
Resource
├── Overview
├── Relationships
├── Credentials
├── Monitoring
├── Knowledge / Documentation
└── Activity
```

Overview remains specialist-specific. Cross-cutting sections use the shared
resource identity.

The Credentials section is already backed by the Vault's scoped resource-link
API and must retain independent secret-action permissions.

Normal clicks may open resources in the shared right-side Record drawer while
full-page deep links remain available.

Client workspaces should expose Client-scoped Infrastructure/Credentials/KB/
Monitoring through the same policies as the global modules.

---

## 14. Search and topology

Global and Client-context search should cover useful non-secret metadata such
as:

- resource names;
- hostnames/IPs;
- domains/URLs;
- provider identifiers;
- technology metadata;
- tags;
- linked KB metadata;
- credential metadata only.

PostgreSQL-backed search is acceptable initially. Dedicated search/graph
infrastructure should not be introduced until scale/quality justifies it.

Search never indexes decrypted Vault secrets and never bypasses normal scope.

---

## 15. Current implemented boundary

The technical foundation now provides:

- `InfrastructureResource`;
- tags;
- `ServiceProvider`;
- resource-backed `ProviderAccount` with scoped create/edit/archive APIs and
  operational workspace;
- permissioned searchable Service Provider catalogue and current-first Provider
  Account register;
- `ResourceRelationship`;
- ownership/cross-Client validation;
- current-first global/Client resource collections;
- scoped resource detail/drawer workspaces;
- relationship target/options/create/delete APIs/UI;
- typed identity bridges for every current legacy specialist family;
- explicit permission-aware legacy reconciliation;
- safe specialist projection/provenance;
- the typed encrypted Credential Vault;
- Credential -> Infrastructure Resource links with ownership validation;
- Client and Resource contextual Credential registers;
- explicit reveal/copy/download audit boundaries;
- atomic legacy StoredCredential secret reconciliation.

It does **not** yet provide:

- complete modern specialist Server/Database/Application/etc. CRUD;
- mature Web/Domain/DNS/TLS specialist structures;
- Monitoring checks/results/incidents;
- redesigned KB folder/editor/resource links;
- Docker/Kubernetes specialist structures;
- final broad technical topology/search polish.

---

## 16. Current technical-operations sequence

1. core Server/network/Database/Application specialist structures;
2. Website/Domain/DNS/TLS specialist structures;
3. Monitoring checks/history/incidents + technical dashboards;
4. Knowledge Base folder/editor/version/attachment work;
5. KB/resource backlinks + contextual search foundations;
6. Docker/Kubernetes structures;
7. storage/backups/system services/scheduled jobs and remaining specialist
   operations records;
8. unified topology/search/activity/audit polish;
9. Credential expiry/rotation health and bulk rotation tooling as operational
   follow-up rather than a blocker for typed Infrastructure.

Client Command Centre integration should continue incrementally as these domains
mature rather than waiting for one giant final integration PR.

Every slice must preserve Client/Internal ownership, capability/scope, current-
first UX, audit boundaries and the Credential Vault secret-handling contract.
