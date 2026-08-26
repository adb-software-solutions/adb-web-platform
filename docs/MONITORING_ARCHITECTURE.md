# Monitoring and Technical Health Architecture

## Purpose

Monitoring is the ADB Business Platform's cross-cutting technical-health subsystem.
It is attached to the existing structured Infrastructure model rather than creating
another Website, Server, Domain or Client identity.

This document records the implementation boundary for the Monitoring slice. The
canonical platform direction remains `PLATFORM_MASTER_PLAN.md`; Credential handling
remains governed by `CREDENTIAL_VAULT_ARCHITECTURE.md`.

## Core model

Monitoring is anchored to `InfrastructureResource`:

```text
InfrastructureResource
└── MonitorCheck
    ├── MonitorResult
    └── MonitorIncident
```

`MonitorCheck` owns probe configuration and current operational state. It includes:

- check type and target;
- severity;
- enabled/paused lifecycle;
- interval and timeout;
- failure and recovery thresholds;
- expiry warning threshold where applicable;
- optional Credential reference;
- current status and consecutive result counters;
- last/next execution metadata.

`MonitorResult` is an immutable safe observation. It records outcome, timing,
status code where relevant, a bounded safe observed value and a message. It must not
store decrypted Credential material.

`MonitorIncident` represents a failure period. Failure thresholds open an incident;
recovery thresholds resolve it. Active incidents can be acknowledged without being
resolved manually.

The normal operator lifecycle is therefore:

```text
pending -> healthy/degraded/failing
                  |
                  +-> incident open -> acknowledged -> resolved

active check -> paused -> resumed/pending
```

Pausing a check is deliberately non-destructive. Historical Results and Incidents
remain available.

## Ownership, permissions and scope

Monitoring does not implement a second Client-access model.

All check and incident visibility is derived from the existing
`scope_infrastructure_resources_for_user()` boundary. Internal resources are visible
according to the normal staff rules; Client-owned resources remain constrained by the
staff user's Client grants.

Context filters such as `client_id` and `resource_id` are applied only after the
normal Infrastructure scope has been established. Supplying the ID of an inaccessible
Client or resource therefore cannot widen visibility.

Django permissions remain capability boundaries for:

- viewing checks/results/incidents;
- adding or changing checks;
- acknowledging incidents;
- viewing Credential metadata where applicable.

## Scheduling and execution

Celery Beat/workers drive monitoring rather than request-time execution.

The due-check dispatcher selects enabled checks whose `next_run_at` is due (or has not
been set yet) and queues individual executions. The execution/result services are
reusable so scheduling, result persistence and threshold state transitions remain
separate concerns.

Probe timeout values are bounded by the model. Executors return a `CheckObservation`;
the result service then persists the observation and applies failure/recovery
semantics.

## Implemented check types

### ICMP / ping

Runs the system `ping` executable with an argument vector rather than a shell command.
Execution is bounded by the configured timeout. The backend and Celery worker images
install `iputils-ping` so the same probe is available in deployed worker containers.

### TCP port

Attempts a TCP connection to the configured host and required port using the bounded
check timeout.

### HTTP / HTTPS

Performs an HTTP request with the ADB Monitor user agent and treats HTTP 2xx/3xx as
successful. Response bodies are bounded to 1 MB when content inspection is required.

### Content

Uses the HTTP probe and currently supports literal expected-content and
forbidden-content matching.

The master plan also mentions regex matching. Regex semantics are **not implemented
in the current slice** and must not be implied by the UI or API until they are added
explicitly with tests and bounded execution behaviour.

### DNS

Resolves the target and records the resolved addresses as a safe observed value. When
an expected value is configured, that exact address must be present in the resolved
set.

### TLS certificate

Opens a TLS connection using the platform trust store, validates the peer normally,
reads the certificate expiry date and fails the check once it is inside the configured
expiry-warning window.

### Domain registration expiry

Uses the structured `DomainProfile.expires_on` value attached to the monitored Domain
resource. It deliberately does not perform a live WHOIS/RDAP lookup on every check.
Registration metadata should be maintained by Infrastructure/provider reconciliation;
Monitoring evaluates the authoritative platform value.

## History and health projections

The check-detail API returns bounded recent history rather than an unbounded result
archive:

- up to 50 recent Results;
- up to 20 recent Incidents;
- 24-hour uptime percentage;
- 7-day uptime percentage;
- 24-hour average response duration;
- 7-day average response duration.

The global Monitoring workspace is current-problems-first. It shows enabled checks and
active incidents, while individual check workspaces expose the bounded historical
context.

The Monitoring overview API also supports server-side `client_id` and `resource_id`
filters for contextual health panels in Client and Infrastructure workspaces.

## Operator workflows

The admin UI provides:

- a global Monitoring workspace;
- per-check detail/history workspaces;
- permission-gated pause/resume;
- incident acknowledgement;
- permission-gated Add Check and Edit Check forms;
- resource selection constrained to the user's accessible, non-retired/non-archived
  Infrastructure resources;
- Client and individual Infrastructure contextual health panels.

Editing check configuration does not delete history or incidents.

## Credential Vault boundary

`MonitorCheck` has an optional `StoredCredential` reference because authenticated
monitoring belongs in this subsystem, but secret material must remain governed by the
Credential Vault.

The Credential Vault architecture provides
`load_credential_secrets_for_service()` for trusted backend integrations. Human
reveal/copy/download actions and server-side integration access are intentionally
separate paths.

The current probe executor is explicitly **unauthenticated** and does not consume
`check.credential`. The operator form therefore does not expose a Credential selector
as if authenticated monitoring already worked.

Before authenticated checks are enabled, Monitoring must model an explicit
authentication scheme (for example, the exact supported HTTP authentication/header
contract) and then:

1. validate that the chosen Credential type/fields are compatible with that scheme;
2. load decrypted values only inside the trusted worker execution path;
3. never persist decrypted values in Results, Incidents, logs, exception messages or
   observed values;
4. preserve normal Client/Internal Credential ownership rules;
5. add boundary tests proving secret values cannot leak through API, logging or
   monitoring history.

Until that contract exists, an attached Credential reference is retained safely but
must not be interpreted silently.

## Development data

`seed_monitoring_development` builds deterministic monitoring data against the
structured Infrastructure development records without executing real external probes.
It creates representative internal and Client-owned checks, observation history,
healthy/degraded/failing states, an active incident and resolved incident history.

`seed_all_development` includes this command after Infrastructure seeding.

## Deliberately deferred work

The current slice does not claim to provide:

- regex content matching;
- authenticated HTTP/content probes;
- arbitrary custom headers or request bodies;
- live WHOIS/RDAP registration discovery;
- distributed multi-region probe agents;
- public status pages;
- notification/escalation policy beyond the core Incident state model;
- long-term analytics storage beyond the current bounded operational projections.

Those features should be added only when their product/security semantics are agreed,
rather than being inferred from generic monitoring products.
