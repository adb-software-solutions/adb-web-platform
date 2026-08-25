# Microsoft Graph Ticketing Setup

## Purpose

This is the deployment/runbook for connecting the ADB Business Platform to
Microsoft 365 Shared Mailboxes through Microsoft Graph.

It documents the agreed ADB operating model:

```text
one Microsoft 365 tenant
+ one Microsoft Entra application
+ one certificate credential
+ one MicrosoftGraphConnection
+ many Shared Mailboxes configured in ADB
```

Adding a new Shared Mailbox to Ticketing should **not** require a new Entra
application, another certificate, another tenant/client ID entry or a new
Exchange RBAC assignment every time.

Application/message architecture lives in `TICKETING_ARCHITECTURE.md`.
Credential storage, reveal/copy/download permissions, key rotation and browser
secret handling are defined in `CREDENTIAL_VAULT_ARCHITECTURE.md`.

---

## 1. Intended production architecture

```text
Microsoft 365 tenant
    |
    +-- Entra application: ADB Business Platform Ticketing
    |       |
    |       +-- RSA certificate public key registered in Entra
    |       +-- Exchange Online RBAC for Applications
    |               |
    |               +-- Application Mail.ReadWrite
    |               +-- Application Mail.Send
    |               +-- SharedMailbox dynamic resource scope
    |
    +-- Shared Mailboxes
            |
            +-- support@...
            +-- enquiries/sales@...
            +-- accounts@...
            +-- other operational addresses

ADB Business Platform
    |
    +-- Credential Vault
    |       |
    |       +-- certificate/private-key Credential
    |
    +-- one MicrosoftGraphConnection
    |       |
    |       +-- references the Vault Credential
    |
    +-- one Mailbox row per Shared Mailbox actually used by Ticketing
            |
            +-- Brand
            +-- purpose
            +-- default Ticket Queue
            +-- enabled state
            +-- Graph sync/delta state
```

There are two different boundaries:

1. **Exchange Online RBAC** controls which mailboxes the application is
   technically authorised to access at Microsoft.
2. **ADB Mailbox records** are the narrower operational allow-list. Celery only
   synchronises enabled Mailbox rows.

The database allow-list does not replace the Microsoft-side security boundary.
The Credential Vault does not replace either boundary; it securely stores the
application authentication material used by the Graph connection.

---

## 2. Required Graph/Exchange capabilities

Ticketing needs to:

- read messages/headers;
- retrieve attachments;
- maintain delta synchronisation state;
- update mailbox state where required by the sync implementation;
- send replies/new messages from configured Shared Mailboxes.

The Exchange application roles used by this design are:

- `Application Mail.ReadWrite`;
- `Application Mail.Send`.

`Mail.ReadWrite` does not include send capability, so both are required.

Background mailbox processing is app-only. It does not depend on an
interactive/licensed staff user's delegated OAuth session.

---

## 3. Least-privilege rule: do not undo the Exchange scope

The recommended deployment uses **Exchange Online RBAC for Applications** rather
than equivalent organisation-wide Microsoft Graph Mail application permissions
on the Entra app.

Exchange RBAC assignments and Entra application grants are additive. If the
same app also receives broad Entra `Mail.ReadWrite`/`Mail.Send` application
permissions, those grants can restore access outside the Exchange resource
scope.

Therefore:

- use the scoped Exchange application roles below;
- do not add equivalent broad Entra Mail application permissions merely to make
  the app work;
- remove/audit broad Mail grants left from experiments before calling the
  deployment least-privilege.

A future non-mail Graph capability should be granted separately and narrowly.

---

## 4. Prerequisites

You need:

- Microsoft 365 with Exchange Online;
- operational addresses created as **Shared Mailboxes**;
- rights to manage the Entra app registration;
- rights to configure Exchange Online RBAC for Applications;
- ExchangeOnlineManagement PowerShell module;
- an RSA certificate/private key;
- the ADB backend migrated/running;
- valid `CREDENTIAL_ENCRYPTION_KEYS` in every process that decrypts Vault
  Credentials, including Celery workers;
- permission to create/update the Graph certificate Credential in the Vault;
- Celery worker and Beat in production.

---

## 5. Connect to Exchange Online PowerShell

Install/import the module as appropriate for the administrator workstation:

```powershell
Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser
Import-Module ExchangeOnlineManagement
Connect-ExchangeOnline
```

Inspect the installed version if troubleshooting:

```powershell
Get-InstalledModule ExchangeOnlineManagement |
    Format-List Name,Version,InstalledLocation
```

---

## 6. Create the Microsoft Entra application

In Microsoft Entra admin center:

1. Open **Entra ID -> App registrations -> New registration**.
2. Use a clear name, e.g. `ADB Business Platform Ticketing`.
3. Use **Accounts in this organizational directory only** for the normal ADB
   single-tenant deployment.
4. No interactive redirect URI is required for app-only background sync.
5. Record:
    - **Application (client) ID**;
    - **Directory (tenant) ID**.

Exchange also needs the **service principal Object ID** from Enterprise
Applications, not the App Registration application-object ID.

---

## 7. Create and register the certificate

Production should use a securely managed/rotated RSA certificate. Only the
public certificate is uploaded to Entra. The private key remains a Vault
secret.

A disposable local/test self-signed example:

```bash
mkdir -p "$HOME/.adb-secrets/graph"
chmod 700 "$HOME/.adb-secrets/graph"

openssl req \
  -x509 \
  -newkey rsa:3072 \
  -sha256 \
  -days 365 \
  -nodes \
  -keyout "$HOME/.adb-secrets/graph/adb-ticketing-graph.key.pem" \
  -out "$HOME/.adb-secrets/graph/adb-ticketing-graph.cert.pem" \
  -subj "/CN=ADB Business Platform Ticketing"

chmod 600 "$HOME/.adb-secrets/graph/adb-ticketing-graph.key.pem"
chmod 644 "$HOME/.adb-secrets/graph/adb-ticketing-graph.cert.pem"
```

Upload the public certificate under **Certificates & secrets -> Certificates**
in the Entra app registration.

Never commit/upload the private-key file to Git.

After the Vault Credential has been created and verified, remove disposable
private-key copies from ordinary working directories according to the local
secret-handling policy.

---

## 8. Get the service principal Object ID

Open **Enterprise applications**, locate the Ticketing application and copy its
**Object ID**.

Set convenient PowerShell variables:

```powershell
$AppId = "<APPLICATION-CLIENT-ID>"
$ServicePrincipalObjectId = "<ENTERPRISE-APPLICATION-OBJECT-ID>"
$DisplayName = "ADB Business Platform Ticketing"
```

Do not confuse this Object ID with the application-object ID shown elsewhere in
App registrations.

---

## 9. Register the service principal with Exchange

```powershell
New-ServicePrincipal `
  -AppId $AppId `
  -ObjectId $ServicePrincipalObjectId `
  -DisplayName $DisplayName
```

If it already exists, inspect/reuse it instead of creating a duplicate:

```powershell
Get-ServicePrincipal -Identity $ServicePrincipalObjectId |
  Format-List DisplayName,ObjectId,AppId
```

---

## 10. Create the Exchange mailbox resource scope

### ADB default — all Shared Mailboxes

The agreed normal ADB tenant design scopes the application dynamically to
Exchange recipients whose type is `SharedMailbox`:

```powershell
New-ManagementScope `
  -Name "ADB Ticketing Shared Mailboxes" `
  -RecipientRestrictionFilter "RecipientTypeDetails -eq 'SharedMailbox'"
```

Why this is the default:

- the operational addresses ADB wants to ingest are Shared Mailboxes;
- licensed `UserMailbox` identities remain outside the resource scope;
- a newly created Shared Mailbox automatically matches without changing RBAC;
- the ADB database still decides which matching Shared Mailboxes are actually
  synchronised.

This directly supports the operational requirement that adding a new Shared
Mailbox to Ticketing is an ADB configuration step, not a Microsoft RBAC project.

Verify the scope population:

```powershell
Get-Recipient `
  -Filter "RecipientTypeDetails -eq 'SharedMailbox'" |
  Format-Table DisplayName,PrimarySmtpAddress,RecipientTypeDetails
```

### Optional tighter alternative — tagged Shared Mailboxes

If the tenant later contains Shared Mailboxes that the Ticketing application
must **not even technically access**, use a dedicated Exchange custom attribute
and a narrower dynamic scope.

Example only:

```powershell
Set-Mailbox "support@example.com" `
  -CustomAttribute15 "ADBTicketing"

New-ManagementScope `
  -Name "ADB Ticketing Shared Mailboxes" `
  -RecipientRestrictionFilter "(RecipientTypeDetails -eq 'SharedMailbox') -and (CustomAttribute15 -eq 'ADBTicketing')"
```

This is stricter but reintroduces one Microsoft-side tagging action whenever a
new Ticket mailbox is added. Use it only if that tighter boundary is actually
needed.

Do not create one management scope/role assignment per mailbox.

---

## 11. Assign the Exchange application roles once

```powershell
New-ManagementRoleAssignment `
  -Name "ADB Ticketing Mail ReadWrite" `
  -App $ServicePrincipalObjectId `
  -Role "Application Mail.ReadWrite" `
  -CustomResourceScope "ADB Ticketing Shared Mailboxes"

New-ManagementRoleAssignment `
  -Name "ADB Ticketing Mail Send" `
  -App $ServicePrincipalObjectId `
  -Role "Application Mail.Send" `
  -CustomResourceScope "ADB Ticketing Shared Mailboxes"
```

Inspect the role assignments:

```powershell
Get-ManagementRoleAssignment `
  -RoleAssignee $ServicePrincipalObjectId |
  Format-Table Name,Role,RoleAssigneeName,CustomResourceScope
```

These assignments are connection/application setup. Do **not** repeat them for
every Mailbox row.

---

## 12. Test Exchange authorisation before ADB configuration

Test an intended Shared Mailbox:

```powershell
Test-ServicePrincipalAuthorization `
  -Identity $ServicePrincipalObjectId `
  -Resource "support@your-shared-mailbox.example" |
  Format-Table RoleName,GrantedPermissions,AllowedResourceScope,ScopeType,InScope
```

The required roles should report the mailbox in scope.

Also test a licensed user mailbox that should be outside the ADB Ticketing
resource boundary:

```powershell
Test-ServicePrincipalAuthorization `
  -Identity $ServicePrincipalObjectId `
  -Resource "licensed.user@yourtenant.example" |
  Format-Table RoleName,GrantedPermissions,AllowedResourceScope,ScopeType,InScope
```

The Ticketing application roles should not be in scope for that UserMailbox.

Remember that `Test-ServicePrincipalAuthorization` evaluates Exchange RBAC;
broad Entra grants are separate and must be audited independently.

Microsoft-side permission propagation can take time even after configuration is
correct.

---

## 13. Audit Entra API permissions

Open the Entra app's **API permissions** page.

For this design:

- do not add broad Graph `Mail.ReadWrite` / `Mail.Send` Application permissions;
- remove equivalent broad grants left from previous experiments after the
  Exchange RBAC configuration is verified;
- grant any unrelated Graph capabilities independently/least-privilege.

---

## 14. Configure Credential Vault encryption

Graph private-key material is encrypted using the Credential Vault.

Generate a Fernet key:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Configure the backend/worker environment:

```env
CREDENTIAL_ENCRYPTION_KEYS=<FERNET-KEY>
```

The setting accepts an ordered comma-separated key ring for rotation:

```env
CREDENTIAL_ENCRYPTION_KEYS=<NEW-PRIMARY>,<OLD-KEY>
```

New writes use the first key. Keep old keys available until affected payloads
have been re-encrypted and verified.

Every process that needs Graph credentials must receive the same usable key
ring.

Never commit encryption keys.

See `CREDENTIAL_VAULT_ARCHITECTURE.md` for the full key-rotation and failure
behaviour.

---

## 15. Store the Graph certificate/private key in the Vault

Use `/admin/credentials` and the certificate/private-key credential template for
normal operator administration.

Create an **Internal** Credential for the Graph application and populate the
certificate/private-key fields through the typed Vault form. If the private key
has a passphrase, store it as an encrypted secret field in the same Credential.

The Vault ensures:

- private-key material is written to the encrypted secret payload;
- ordinary list/detail responses do not return it;
- reveal, copy and download are independently permission checked/audited;
- secret values are not persisted to browser storage/routes/normal caches;
- missing encryption configuration fails closed.

Do not populate the legacy plaintext `password`, `api_key`, `secret_key`,
`private_key` or sensitive `notes` columns.

A controlled Django shell path may still be useful for disaster recovery or
bootstrap automation, but it must call the same encrypted credential service
rather than writing plaintext model columns. The Vault UI is the normal
operational path.

---

## 16. Create/verify `MicrosoftGraphConnection`

Create the connection once for the tenant/application using:

- tenant ID;
- application/client ID;
- certificate authentication method;
- the encrypted Vault Credential containing certificate/private key;
- enabled state.

Use the custom Settings UI where the current implementation supports the
operation; controlled Django shell/admin bootstrap is acceptable only for
fields not yet exposed safely.

Verify the connection before relying on mailbox sync.

The connection is reusable by many Mailbox records.

The Graph integration's backend decryption path does not grant a human operator
permission to reveal the same Credential in the UI. Service decryption and
human secret actions are separate security paths.

---

## 17. Add Shared Mailboxes to ADB

For each mailbox ADB should actually ingest:

1. ensure it exists as a Microsoft 365 **Shared Mailbox**;
2. open the Ticketing/Graph settings area under `/admin/settings`;
3. add the mailbox email/display identity;
4. select/confirm the Graph connection if more than one is available;
5. choose Brand;
6. choose mailbox purpose;
7. choose default Ticket Queue;
8. verify Graph access;
9. enable the Mailbox.

With one enabled Graph connection, the normal UX should reuse it rather than
asking the operator to enter connection credentials again.

Under the ADB default Exchange scope, there is no new RBAC role assignment when
a new Shared Mailbox is created.

Celery only processes enabled Mailbox rows.

---

## 18. Celery/runtime requirements

Production mailbox processing requires the Celery worker and scheduled/Beat
orchestration used by the platform.

Ensure workers receive:

- Django/database configuration;
- Redis/broker configuration;
- `CREDENTIAL_ENCRYPTION_KEYS`;
- any attachment/malware-scanning settings;
- network access to Microsoft Graph.

Mailbox sync stores delta state/cursors in the database so restarts do not force
unsafe unread-only polling or duplicate imports.

Outbound delivery also runs through Celery with retry/duplicate-send controls.

---

## 19. Certificate rotation

A safe certificate rotation is:

1. generate/provision the new RSA certificate/private key;
2. upload the **new public certificate** to the same Entra application;
3. update/store the new private/public material in the Vault Credential;
4. verify app-only token acquisition and Mailbox access;
5. confirm inbound sync and outbound send;
6. remove the old public certificate from Entra after the new path is proven;
7. retire old private material according to the Vault lifecycle/audit policy.

Do not create a new Entra application/Exchange scope just to rotate a
certificate.

If rotating Fernet application-encryption keys as well, follow the Vault key-
ring procedure separately. Certificate rotation and Vault encryption-key
rotation are different operations.

---

## 20. Adding a brand-new Shared Mailbox: normal checklist

Under the agreed ADB default setup:

```text
Microsoft 365
[ ] Create Shared Mailbox

ADB
[ ] Add Mailbox row
[ ] Select Brand/purpose/default Queue
[ ] Verify Graph access
[ ] Enable

Done
```

You do **not** normally need to:

- create another Entra app;
- create/upload another application certificate;
- enter the tenant/client ID again;
- create another Exchange service principal;
- create another management scope;
- create another Mail.ReadWrite role assignment;
- create another Mail.Send role assignment;
- create another Vault Credential for each Shared Mailbox.

The Graph application Credential belongs to the connection/application and is
reused across its configured Shared Mailboxes.

If the optional tagged Exchange scope is used instead of the ADB default, tag
the new Shared Mailbox with the reserved custom attribute before verification.

---

## 21. Troubleshooting

### A Shared Mailbox fails verification

Check in order:

1. it really is `RecipientTypeDetails = SharedMailbox`;
2. `Test-ServicePrincipalAuthorization` reports the two application roles in
   scope;
3. no typo exists in tenant/client IDs;
4. the certificate public key registered in Entra matches the private key
   stored in the Vault;
5. the ADB process can decrypt the Credential with
   `CREDENTIAL_ENCRYPTION_KEYS`;
6. Microsoft permission propagation has completed;
7. the Mailbox uses the intended Graph connection.

### Vault reveal fails but Graph sync still works

Human reveal permission and backend service decryption are separate. Check the
staff user's `credentials.reveal_storedcredential` capability and Client/Internal
scope rather than assuming the Graph connection is broken.

### Graph sync fails because the Credential cannot decrypt

Check that the web and Celery processes have the correct ordered
`CREDENTIAL_ENCRYPTION_KEYS` key ring. Do not re-enter the private key into a
plaintext model field as a workaround.

### A licensed user mailbox is accessible unexpectedly

Audit broad Entra Graph Mail Application permissions immediately. The Exchange
SharedMailbox scope alone should not place a normal UserMailbox in scope.

### New Shared Mailbox is technically in scope but not syncing

That is expected until an enabled ADB `Mailbox` record exists. Exchange scope
and ADB operational allow-list are separate.

### Celery sync fails while API verification works

Confirm the worker has the same credential-encryption key ring and network
configuration as the web/backend process.

### Duplicate messages

Inspect provider message IDs, internet Message-ID/thread references and stored
delta state before changing routing. Do not “fix” duplicates by making subject
matching looser.

---

## 22. Security checklist

Before production:

- [ ] production RSA certificate is managed outside Git;
- [ ] private key is stored only through the encrypted Credential Vault;
- [ ] `CREDENTIAL_ENCRYPTION_KEYS` is secret-managed and available to workers;
- [ ] human Vault reveal/copy/download permissions follow least privilege;
- [ ] Exchange RBAC uses the intended SharedMailbox resource scope;
- [ ] equivalent broad Entra Mail application grants are absent;
- [ ] an intended Shared Mailbox tests in-scope;
- [ ] a licensed UserMailbox tests out-of-scope;
- [ ] only intended ADB Mailbox rows are enabled;
- [ ] inbound delta sync is working;
- [ ] outbound send works from the correct Shared Mailbox;
- [ ] Client/Contact/routing behaviour is correct;
- [ ] attachments follow quarantine/malware policy;
- [ ] logs/audit events do not contain certificate/private-key/token material;
- [ ] revealed Vault values are not stored in browser storage/routes/analytics.

The deployment should preserve the distinction between **Microsoft technical
access**, **ADB operational mailbox selection** and **Vault secret access**
throughout its lifetime.
