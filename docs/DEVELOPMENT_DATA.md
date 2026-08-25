# Development data

## Purpose

The ADB Business Platform includes deterministic fake-data tooling so the
operations UI can be developed against realistic cross-domain context rather
than empty tables.

Development data should exercise the product's current-first workspaces,
Client/Internal ownership, permission boundaries and relationships without ever
containing real Client secrets or private infrastructure data.

---

## 1. Canonical development seed command

After applying migrations, run from `backend/`:

```bash
python manage.py seed_all_development --reset
```

For denser pagination/search/workspace testing:

```bash
python manage.py seed_all_development --reset --scale 3
```

The seeders refuse normal use when `DEBUG=False`. A `--force` escape hatch is
only for disposable non-production environments and must never be used against
real platform data.

`--reset` removes records created by the development seeders and rebuilds the
demo dataset. It does not intentionally flush unrelated development records.

Lower-level commands remain available for focused work:

- `seed_development`;
- `seed_task_workflows_development`;
- `seed_infrastructure_development`;
- `seed_ticketing_development`.

For normal local work, prefer `seed_all_development` because it handles the
required ordering/dependencies between seeders.

---

## 2. Data represented

At normal scale, the development dataset covers realistic examples across:

- the three ADB Brands;
- fake Clients and multiple Contacts;
- active/inactive/history lifecycle examples;
- Projects and project notes;
- CRM Leads and pipeline reference data;
- Tasks, Task Lists, Sections, Subtasks and Dependencies;
- recurring/current/completed work examples;
- Task/Project/Internal Time entries;
- Knowledge Base documents and version-history foundations;
- fake Credential metadata/encrypted demo secret values;
- Server, Database, Website, Domain, TLS, Licence, Application and related
  infrastructure specialist examples;
- Mobile App/API/Bot/Email-system examples;
- Ticket Queues, configured demo Mailboxes, Tickets, Messages, Notes and
  attachment/scan-state examples;
- Brand-aware Blog/FAQ/Testimonial/Case Study content;
- Audit events/recent activity.

The exact counts are seed implementation detail and may grow as a domain
matures. Tests should not rely on specific production-like IDs/counts from the
development seed command.

### Structured Infrastructure transition

The platform now has `InfrastructureResource`, Provider and relationship
foundations plus explicit specialist reconciliation.

Development data for older specialist records remains useful because the
reconciliation workspace needs realistic legacy rows to review. Do not
silently auto-assign Client/Internal ownership merely to make every seeded
legacy row look reconciled.

Where a seeder creates structured resources/relationships directly, it must obey
the same ownership and cross-Client validation as normal application code.

### Credential data

Fake credential secrets must be obvious placeholders such as
`demo-password-not-a-real-secret` and should exercise the encrypted credential
service where the current branch supports it.

At the time of this documentation refresh, the full typed Credential Vault is
still an unmerged feature slice. Seed data on `main` must therefore not pretend
that every Vault template/action is already available.

Never copy real Microsoft Graph certificates/private keys, Client passwords,
API tokens, SSH keys or production recovery codes into seeders/fixtures.

---

## 3. Local workflow

For a fresh/newly migrated environment:

```bash
cd backend
python manage.py migrate
python manage.py seed_all_development --reset
```

Then start the normal backend/frontend/Celery development processes and sign in
through the authentication application.

Use a local superuser when reviewing the complete cross-domain dataset. Use
restricted staff users when reviewing capability/Client/Queue-scope behaviour;
a restricted account correctly sees only part of the seeded data.

Create a local superuser when needed:

```bash
python manage.py createsuperuser
```

---

## 4. Reference fixture

`apps/core/fixtures/development_reference.json` remains the small baseline
fixture for reference/taxonomy data such as Lead sources, Task statuses,
Credential types and Knowledge Base sections.

It can be loaded with:

```bash
python manage.py loaddata apps/core/fixtures/development_reference.json
```

The comprehensive seed commands create/update the reference data they need, so
prefer `seed_all_development` for normal platform development.

---

## 5. Seeder expectations for new work

When a domain gains meaningful UX, add representative development data where it
materially improves hands-on review.

Examples for upcoming phases:

- current + retired Infrastructure Resources and useful topology relationships;
- Credential metadata/resource links using only fake encrypted values after the
  Vault merges;
- unhealthy/healthy Monitoring checks and incidents once Monitoring exists;
- nested Client/Internal KB folders/documents/resource links after the KB
  redesign;
- varied staff access/default Ticket Queue preferences for Users & Access and
  Dashboard work;
- commercial examples only once those models are explicitly designed.

Seed data should make current-first views meaningful: include enough history to
test history filters without making all demo records inactive/closed.

---

## 6. Rules

- Never use real Client/contact/credential/infrastructure data.
- Use reserved/example domains and clearly fake people/organisations.
- Keep generation deterministic unless randomness is itself under test.
- Use application/domain services where that is required to preserve invariants
  rather than bypassing them with unsafe direct inserts.
- Keep Client/Internal ownership internally consistent.
- Never use seeders to bypass permission/security design.
- Never write plaintext production-style secrets merely because the environment
  is development.
- Seed data is for development/demos, not a substitute for focused unit/
  permission-boundary tests.
