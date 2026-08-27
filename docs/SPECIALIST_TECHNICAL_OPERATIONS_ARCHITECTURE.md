# Specialist Technical Operations Architecture

## Purpose

Stage 5 extends the shared Infrastructure resource graph with the operational
records needed to describe how ADB and Client systems actually run. It covers
storage and backups, container stacks, Kubernetes, host services and scheduled
jobs without creating a separate technical inventory or duplicating secrets.

The canonical identity remains `InfrastructureResource`. Specialist models add
native structured metadata to resource types that already exist in the shared
resource taxonomy.

## Core rules

- every top-level specialist record is backed by exactly one
  `InfrastructureResource`;
- every resource is either ADB Internal or Client-owned;
- parent/child operational relationships must use the same ownership type and,
  for Client-owned resources, the same Client;
- API visibility is the intersection of Django model permissions and the shared
  Infrastructure scope policy;
- inaccessible related resources are treated as not found rather than leaking
  their existence;
- secrets, tokens, passwords, private keys, kubeconfigs and similar access
  material are never stored in specialist operational fields;
- access material belongs in Credential Vault and is associated through the
  existing resource/credential relationship layer;
- specialist operational records describe current intended/runtime structure;
  they do not execute infrastructure changes.

## Resource-backed specialist records

The following models extend top-level `InfrastructureResource` identities.

| Resource type          | Specialist model             | Purpose                                                                     |
| ---------------------- | ---------------------------- | --------------------------------------------------------------------------- |
| `storage`              | `StorageProfile`             | Block, object, file, volume, disk, bucket and NAS metadata.                 |
| `backup_plan`          | `BackupPlanProfile`          | Backup policy, retention, destination and recovery-health metadata.         |
| `container_stack`      | `ContainerStackProfile`      | Docker Compose, Swarm, Nomad or other stack context.                        |
| `kubernetes_cluster`   | `KubernetesClusterProfile`   | Cluster distribution, version, provider and operational metadata.           |
| `kubernetes_namespace` | `KubernetesNamespaceProfile` | Namespace identity and quota/purpose context.                               |
| `kubernetes_workload`  | `KubernetesWorkloadProfile`  | Deployment, StatefulSet, DaemonSet, Job, CronJob and similar workloads.     |
| `system_service`       | `SystemServiceProfile`       | systemd, Supervisor, Windows Service, launchd and similar services.         |
| `scheduled_job`        | `ScheduledJobProfile`        | cron, systemd timer, Celery Beat, Kubernetes CronJob and similar schedules. |

These records use the ordinary Infrastructure lifecycle, environment,
criticality, ownership, tagging, Credential links, Knowledge Base links and
Monitoring context supplied by the shared resource identity.

## Storage and backup model

`StorageProfile` records operational storage characteristics such as storage
type, provider account, provider resource ID, region, capacity, filesystem,
storage class, mount path, endpoint, encryption state and retention notes.

`BackupPlanProfile` records the policy rather than a backup execution engine. It
can reference:

- a scoped `StorageProfile` destination;
- a scoped Provider Account;
- one or more `BackupSource` rows pointing at protected
  `InfrastructureResource` identities.

A source or destination from another Client/ownership scope is rejected. Source
replacement in the write API is transactional, so validation failure cannot
leave a partially changed backup plan.

Recent success/failure/restore-test timestamps are operational metadata only.
Stage 5 does not itself run backups or perform restore tests.

## Container stacks

`ContainerStackProfile` represents a Docker Compose, Docker Swarm, Nomad or
other stack. It can point to a Server resource acting as its host.

`ContainerService` is intentionally nested rather than a separate
`InfrastructureResource`. It stores runtime structure including:

- service name and image;
- replica count;
- port mappings;
- volume mappings;
- healthcheck summary;
- restart policy;
- non-secret environment/configuration notes.

Environment notes are descriptive only. Secret environment variable values must
remain outside this model.

The full resource page exposes scoped create/edit/delete controls for container
services.

## Kubernetes model

### Resource identities

The Kubernetes hierarchy uses resource-backed identities where the record is
useful independently across Monitoring, Knowledge Base, Credentials and Client
context:

1. `KubernetesClusterProfile`;
2. `KubernetesNamespaceProfile`;
3. `KubernetesWorkloadProfile`.

A Namespace must belong to a Cluster in the same ownership scope. A Workload
must belong to a Namespace in the same ownership scope.

### Nested operational records

Objects that are primarily details of a namespace remain nested records:

- `KubernetesService`;
- `KubernetesIngress`;
- `HelmRelease`;
- `KubernetesPersistentStorage`.

This follows the existing Website/DNS design: useful child operational records
do not automatically become top-level resource identities.

A Kubernetes Service may target only a Workload in its own Namespace. An
Ingress may target only a Service in its own Namespace. Persistent storage may
link to a structured Storage resource only when the ownership scope matches.

Helm `values_summary` is deliberately non-secret. It may document configuration
shape and important operating choices, but credentials and secret values belong
in Credential Vault.

The namespace resource page provides create/edit/delete controls for all four
nested record types. Workload selectors are filtered to the current Namespace
before being presented to the operator.

## System services

`SystemServiceProfile` represents a service managed on a Server, including:

- manager (`systemd`, Supervisor, Windows Service, launchd or other);
- unit/service name and display name;
- expected state and startup type;
- executable and configuration path;
- working directory and log location;
- restart policy;
- non-secret notes.

The backing Server is required and must use the same ownership scope.

## Scheduled jobs

`ScheduledJobProfile` represents operational schedules such as cron jobs,
systemd timers, Celery Beat entries, Kubernetes CronJobs and Windows scheduled
tasks.

It records the scheduler, optional host/context resource, schedule expression,
timezone, non-secret command/job summary, configuration path, working directory,
run-as identity, enabled state and recent/next execution timestamps.

`command_summary` is documentation, not a place for embedded credentials or
secret-bearing command lines.

## API and permissions

Stage 5 uses Django Ninja routes beneath `/api/admin/infrastructure/operations`.

Top-level create/update APIs exist for all eight resource-backed specialist
types. They reuse the same Infrastructure resource creation/update helpers as
the earlier structured Infrastructure stages, including Client scope,
lifecycle, environment and criticality handling.

Nested APIs provide CRUD for:

- Container Services;
- Kubernetes Services;
- Kubernetes Ingresses;
- Helm Releases;
- Kubernetes Persistent Storage.

Every endpoint checks the relevant Django model capability and resolves parent
resources through the shared Infrastructure scope policy. Permission and scope
checks therefore remain backend-enforced even when the frontend hides actions.

## Resource projections and editing

Specialist operational metadata participates in the existing native
Infrastructure projections:

- `operational_resource_snapshot()` adds safe fields to the standard resource
  detail view;
- `operational_edit_values()` supplies native edit values through the shared
  specialist-edit endpoint.

The `/admin/infrastructure/operations` workspace gives operators a focused view
of Stage 5 resources, while `/admin/infrastructure/resources` remains the
canonical cross-type resource register.

The full resource detail page also exposes Stage 5 editing and, where
applicable, nested container/Kubernetes controls. Monitoring, Knowledge Base and
Credential relationships therefore remain attached to the same resource page
rather than being split into another inventory.

## Development data

`seed_specialist_operations_development` builds deterministic examples on top
of `seed_infrastructure_development`, including:

- structured backup storage and a backup plan protecting the demo server;
- an ADB Docker Compose stack with multiple nested services;
- a Kubernetes cluster, Namespace and Workload;
- a Kubernetes Service, Ingress, Helm release and persistent-storage record;
- a system service and scheduled job;
- a Client-owned container stack using the existing seeded Client server;
- additional deterministic scheduled jobs when development seed scale is
  increased.

The command is included in `seed_all_development` after the base Infrastructure
seed so its required Provider Account and Server records already exist.

No development record contains real access credentials.

## Deliberate deferrals

Stage 5 does **not** add:

- live Docker daemon control;
- Kubernetes API discovery/reconciliation;
- kubeconfig or token storage outside Credential Vault;
- Helm install/upgrade execution;
- backup execution or restore orchestration;
- automatic service restart/control actions;
- scheduled-job execution;
- a general-purpose infrastructure-as-code engine.

Those capabilities require explicit execution, audit, approval and credential
boundaries and should be designed separately if real operational need justifies
them.

## Relationship to later stages

Stage 6 can project these mature technical records into the Client Command
Centre without introducing new technical ownership models. Later topology,
Activity, audit and search work should continue to use the shared
`InfrastructureResource` identity and the structured relationships established
here.
