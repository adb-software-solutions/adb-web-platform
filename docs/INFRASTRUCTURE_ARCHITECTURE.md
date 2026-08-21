# Infrastructure, Credentials and Knowledge Architecture

## Purpose

This document defines the structured technical-operations architecture for the ADB Business Platform. It should be read with:

- `PLATFORM_MASTER_PLAN.md`;
- `PERMISSIONS_AND_ACCESS_MODEL.md`;
- `DOMAIN_MODEL_AUDIT.md`;
- `CURRENT_STATE_AND_FOUNDATION_CHECKLIST.md`.

The target is an IT Glue-style operational workspace for software development, web delivery, DevOps, Linux/system administration and technical support. It is not intended to be a generic asset table or a collection of disconnected CRUD registers.

The key product requirement is contextual navigation. From a technical resource, authorised staff should be able to understand what it is, who owns it, what it depends on, what depends on it, how it is accessed, how it is monitored and where its documentation lives.

## 1. Core resource architecture

Structured technical records use a shared `InfrastructureResource` identity plus strongly typed specialist models.

```text
InfrastructureResource
├── Server
├── Database instance
├── Logical database
├── Application
├── Application environment
├── Website
├── Domain
├── Kubernetes cluster
├── Provider account
└── other specialist resource types
```

`InfrastructureResource` is the common identity/ownership/lifecycle layer. It does **not** replace specialist relational models with EAV, arbitrary JSON or a graph database.

Specialist models remain responsible for fields and invariants that belong to their technical domain. For example, a Server owns server-specific fields and a Kubernetes cluster owns Kubernetes-specific fields.

The common resource identity exists so cross-cutting domains can link consistently to any technical resource, including:

- Credentials;
- Knowledge Base documents;
- monitoring checks and incidents;
- tags;
- audit/activity context;
- generic technical relationships;
- future search and topology views.

## 2. Ownership

Every structured resource is deliberately one of:

```text
client-owned -> real Client
internal     -> ADB itself, Client is null
```

Never create a fake Internal/ADB Client.

Ownership validation must enforce:

- client-owned resources require a Client;
- internal resources must not reference a Client;
- Client A resources must not be directly related to Client B resources;
- Internal ADB resources may relate to Client resources where this represents a real shared dependency.

A common legitimate relationship is:

```text
Client website -> hosted on -> Internal ADB server
```

or:

```text
Client domain -> managed by -> Internal ADB Cloudflare account
```

Future client-portal access must never expose Internal resource details merely because an Internal resource is related to a Client resource.

## 3. Capability and scope

Infrastructure follows the established platform authorisation model:

```text
capability permission + ownership scope
```

Django permissions determine what a staff user may do. Client access grants determine which client-owned resources they may do it to.

Authorised staff may access Internal resources according to the domain capability. Client-owned resources additionally require access to the owning Client.

Infrastructure list, detail, search, relationship, selector and future monitoring endpoints must scope at queryset/service level before serialisation. Frontend filtering is never an authorisation boundary.

Inaccessible resource IDs should normally behave as unavailable/not-found records where this avoids leaking existence.

## 4. `InfrastructureResource`

The common resource record carries information that applies across specialist types:

- Client/Internal ownership;
- resource name;
- resource type;
- lifecycle status;
- environment;
- criticality;
- non-sensitive description;
- future portal-visibility metadata, private by default;
- tags;
- creator/updater metadata;
- archive and creation/update timestamps.

Lifecycle states distinguish current operational resources from history. Normal operational views should default to current resources and keep retired/archived records out of the way unless explicitly requested.

The shared resource type catalogue defines supported structured families without implying that every family must be implemented immediately.

## 5. Strongly typed specialist resources

The platform must prefer real relational fields and foreign keys for known technical semantics.

Examples:

- a database installed on a Server uses a Server relationship/field rather than only a generic `hosted_on` edge;
- an Application Environment belonging to an Application uses an explicit relational model;
- a Kubernetes Namespace belongs explicitly to a Kubernetes Cluster;
- a Website may explicitly reference an Application Environment.

Generic `ResourceRelationship` rows complement these known relationships. They do not replace good relational modelling.

## 6. Resource relationships

`ResourceRelationship` provides the cross-domain topology/relationship graph without introducing a graph database.

Initial relationship semantics include:

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

Relationships are directed, may have a human-readable label/notes and must not point a resource at itself.

Different Client-owned resources cannot be directly related across Clients. Internal-to-Client relationships are valid because shared ADB infrastructure/provider accounts may genuinely serve Client resources.

The relationship graph should later power contextual sections and topology views such as:

```text
Website
  -> Application environment
  -> Server
  -> Provider account
  -> Database
  -> Domain/TLS
  -> Monitoring
  -> Credentials
  -> Documentation
```

## 7. Providers and provider accounts

Provider identity is data, not a hard-coded choice list.

`ServiceProvider` represents organisations/services such as DigitalOcean, AWS, Microsoft, Cloudflare, GitHub, Hetzner, domain registrars and other vendors.

`ProviderAccount` represents the actual account/tenant/project ADB or a Client uses with that provider. A Provider Account is itself resource-backed so Credentials, documentation, monitoring and relationships can attach to it consistently.

Provider-account metadata may include non-secret identifiers such as:

- account/customer identifier;
- tenant ID;
- provider project ID;
- portal URL;
- default region;
- support plan;
- billing reference.

Passwords, API keys, private keys, client secrets and tokens must never be stored directly on Provider Account.

## 8. Credential integration

Credentials remain a separate security boundary.

A future `CredentialResourceLink` (or equivalent explicit relationship model) will allow a Credential to be linked to one or more Infrastructure resources with a purpose/primary marker.

Examples:

```text
SSH credential -> Server
Database login -> Logical database + Application environment
Cloudflare API token -> Provider account + managed domains
Kubeconfig -> Kubernetes cluster
```

Credential metadata remains searchable; secret material does not.

Secret material includes passwords, private SSH keys, passphrases, API tokens, client secrets, recovery codes, service-account payloads, licence keys and sensitive credential notes.

The existing encrypted `StoredCredential.encrypted_secret_payload` and MultiFernet/key-rotation service remain the foundation. Human reveal/copy remains permission-separated and audited without writing secret values to AuditEvent metadata or logs.

Infrastructure records must reference Credentials rather than duplicate plaintext secrets.

## 9. Knowledge Base integration

Knowledge Base documentation and structured resources remain distinct but deeply linked.

The KB target is a filesystem-like Internal/Client folder tree with Markdown documents, immutable versions and secure attachments.

Documents may link to resources with semantics such as:

- documentation;
- runbook;
- deployment procedure;
- troubleshooting;
- architecture;
- disaster recovery;
- restore procedure;
- configuration.

A Server/Database/Application/Domain/etc. workspace should surface its linked documentation. A KB document should surface its related technical resources.

Documentation must not become an alternative plaintext credential store. Sensitive access data belongs in Credentials.

## 10. Target specialist resource families

The architecture is designed to support at least the following structured technical families progressively.

### Compute and networking

- Servers/VMs/bare metal/container hosts;
- network interfaces and IP addresses;
- networks/VPCs/VLANs/VPNs/subnets;
- network devices, firewalls and load balancers where justified.

### Applications and source

- logical Applications;
- Application Environments such as production/staging/development;
- Source Repositories and their roles;
- APIs, background services, bots, integrations and mobile apps;
- technology/version catalogue relationships.

### Databases

- Database Instances/services;
- managed versus self-hosted semantics;
- Logical Databases;
- server/provider/endpoints/TLS/HA/replication metadata;
- linked Credentials rather than embedded passwords.

### Web and domains

- Websites and Website Endpoints;
- Domains;
- DNS Zones and DNS Records;
- TLS Certificates and certificate/domain relationships;
- registrar/DNS/CDN/WAF provider accounts.

### Containers and Kubernetes

- Docker/Podman/container stacks and services;
- Kubernetes clusters;
- namespaces;
- workloads;
- services/ingresses;
- Helm releases;
- persistent storage links.

The platform should document the useful operational shape of Kubernetes without manually reimplementing the entire Kubernetes API.

### Operations

- storage resources;
- backup plans;
- system services;
- scheduled jobs/cron/systemd timers;
- licences/subscriptions;
- email systems and related service configuration.

## 11. Monitoring architecture

Monitoring is a separate cross-cutting subsystem attached to resources. It must not be represented by a single `is_up` field on Server/Website.

Target monitor types include:

- ICMP/ping;
- TCP port;
- HTTP/HTTPS;
- expected/forbidden HTML/text/regex checks;
- TLS certificate validity/expiry;
- DNS record checks;
- domain registration expiry.

Checks have scheduling, timeout, failure/recovery thresholds and severity. Results are stored historically and incidents represent periods of failure/recovery.

Celery Beat/workers should execute due checks through reusable monitoring services.

The resulting operations dashboard should support global and Client-scoped health views, uptime, response time, open incidents and expiring domains/certificates.

Monitoring credentials, when required, must reference encrypted Credential objects.

## 12. Resource workspace UX

Every mature specialist resource should converge on a consistent workspace pattern:

```text
Resource
├── Overview
├── Relationships
├── Credentials
├── Monitoring
├── Documentation
└── Activity
```

Overview is specialist-specific. Other sections use the common resource identity.

The user should not need to search unrelated global registers to understand a technical object.

Client workspaces should expose Client-scoped Infrastructure, Credentials, Knowledge and Monitoring sections using the same permission policies as the global modules.

## 13. Search

Global and Client-context search should cover non-sensitive infrastructure metadata, including resource names, hostnames, IPs, domains, URLs, provider identifiers, technology metadata and tags.

Credential search indexes metadata only, never decrypted secret payloads.

PostgreSQL-backed search is acceptable initially. Dedicated search infrastructure is not required until scale/quality justifies it.

## 14. Legacy infrastructure migration

The repository contains existing flat `Server`, `Database`, `Website`, `Domain`, `SSLCertificate`, `Licence`, `Application`, `MobileApp`, `API`, `Bot` and `EmailSystem` models.

These records must be preserved while the structured architecture is introduced.

Migration rules:

1. do not rewrite or delete historical migrations;
2. introduce the shared resource layer alongside existing records first;
3. do not guess Client/Internal ownership for legacy rows;
4. add explicit specialist-to-resource links before making the shared identity mandatory;
5. migrate/assign ownership through deterministic rules or explicit operator input;
6. only make specialist resource identity mandatory after legacy rows have been reconciled;
7. remove/deprecate duplicated legacy provider/secrets fields only after the new structured replacement is active and migrated.

Moving legacy Python model definitions between modules must preserve their Django app/model identity and database schema.

## 15. Current foundation boundary

The initial Resource Foundation provides:

- `InfrastructureResource`;
- reusable tags;
- `ServiceProvider`;
- resource-backed `ProviderAccount`;
- typed `ResourceRelationship`;
- ownership and cross-Client relationship validation;
- permission-aware resource list/detail APIs;
- normal operational defaults that exclude retired/archived history;
- preservation of the existing infrastructure records without guessing ownership.

It intentionally does **not** yet implement:

- specialist resource create/edit workflows;
- automatic legacy ownership conversion;
- credential-resource links;
- monitoring checks/results/incidents;
- KB-resource links;
- the full Infrastructure frontend workspace;
- Kubernetes/Docker specialist models.

Those belong to subsequent focused changes built on this foundation.

## 16. Implementation sequence

The current technical-operations sequence is:

1. shared resource/provider/relationship foundation;
2. specialist resource identity links and explicit legacy reconciliation;
3. Credential vault expansion and resource linking;
4. core typed Server/network/Database/Application structures;
5. Website/Domain/DNS/TLS structures;
6. monitoring checks/history/incidents and health dashboards;
7. Knowledge Base folder/editor/attachment/version work;
8. KB/resource backlinks and contextual search;
9. Docker/Kubernetes structured resources;
10. storage/backups/system services/scheduled jobs and further specialist operations records.

Each slice must keep Client/Internal ownership, permission scoping, audit boundaries and secret handling consistent with the rest of the platform.
