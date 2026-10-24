# OAuth Authorisation Server

The Django backend is an OAuth 2.1 authorisation server for services outside
this repository, starting with the MCP "brain" service. It lets those services
accept ADB platform identities without sharing the session cookie, a database
or any Django code.

OAuth is **additive**. Login, sessions, passkeys, TOTP and recovery codes are
unchanged; the authorisation endpoint simply relies on an existing platform
session, sending the browser through the normal `/login?next=…` flow when
there is none.

## Access rule

**Only active superusers can authorise OAuth clients.** This is a deliberate
exception to the least-privilege staff model in
[the permissions model](PERMISSIONS_AND_ACCESS_MODEL.md): the services
protected so far are personal tooling for the platform owner, not staff
workflow.

The rule is enforced in the backend at every step, not only on the consent
screen:

- the consent API (`/api/oauth/*`) authenticates with `SessionAuthSuperUser`,
  which also enforces CSRF on unsafe methods;
- the decision service rejects non-superusers;
- the code exchange, every refresh and every introspection re-check that the
  user is still an active superuser. Demoting or deactivating the account
  invalidates all of its tokens immediately.

If staff access is ever needed, replace the superuser check in
`authentication/oauth/services.py::is_superuser_allowed` with a narrow
capability and add permission-boundary tests.

## Endpoints

The issuer is `OAUTH_ISSUER`, defaulting to `https://api.$SITE_DOMAIN` in
production and `http://localhost:8000` with `DEBUG=1`.

| Endpoint                                      | Standard  | Notes                                                                                                  |
| --------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| `GET /.well-known/oauth-authorization-server` | RFC 8414  | Discovery metadata.                                                                                    |
| `POST /oauth/register`                        | RFC 7591  | Public clients only (`token_endpoint_auth_method=none`). Rate limited.                                 |
| `GET /oauth/authorize`                        | OAuth 2.1 | Code flow only, S256 PKCE mandatory, `resource` mandatory (RFC 8707). Redirects to the consent screen. |
| `POST /oauth/token`                           | OAuth 2.1 | `authorization_code` and `refresh_token` grants.                                                       |
| `POST /oauth/introspect`                      | RFC 7662  | Resource servers only, HTTP Basic `<resource server id>:<secret>`.                                     |
| `POST /oauth/revoke`                          | RFC 7009  | Revoking a refresh token revokes the whole grant.                                                      |

Browser consent lives in the authentication frontend at `/oauth/consent`, which
calls:

| Endpoint                                 | Purpose                                           |
| ---------------------------------------- | ------------------------------------------------- |
| `GET /api/oauth/requests/{id}`           | Describe a pending request.                       |
| `POST /api/oauth/requests/{id}/decision` | Approve or deny; returns the client redirect URL. |
| `GET /api/oauth/grants`                  | List connected applications.                      |
| `POST /api/oauth/grants/{id}/revoke`     | Revoke a connected application.                   |

Connected applications are listed under **Account → Security → Sessions**.

## Flow

```
client ── GET /oauth/authorize ──► Django validates client, redirect URI,
                                   PKCE, resource and scope
                                   │ stores OAuthAuthorizationRequest (10 min)
                                   ▼
        auth frontend /oauth/consent?request=…
          no session ──► /login?next=/oauth/consent?request=… (unchanged login)
          superuser approves ──► code (60 s, single use) ──► client redirect URI
client ── POST /oauth/token ──► access token (1 h) + refresh token (30 d, rotated)
resource server ── POST /oauth/introspect ──► active / inactive
```

Errors before the client and redirect URI are validated are shown on the
consent screen and never sent to the unverified redirect URI.

## Security properties

- **Opaque tokens.** Access and refresh tokens are random strings stored only
  as SHA-256 digests. There are no JWTs and no signing keys to rotate; resource
  servers validate through introspection, so revocation is immediate.
- **PKCE S256 is mandatory** for every client, including confidential ones.
- **Single-use codes.** Replaying a code revokes the grant it produced.
- **Refresh rotation with reuse detection.** Each refresh issues a new pair and
  revokes the previous access token. Presenting a rotated refresh token revokes
  the whole grant.
- **Audience binding.** Grants are tied to one resource server. Introspection
  by any other resource server reports the token as inactive.
- **Redirect URIs.** Exact match, except that loopback URIs ignore the port as
  RFC 8252 requires. Registration accepts HTTPS for any host and plain HTTP
  only for `localhost`, `127.0.0.1` and `::1`. The consent screen shows the
  destination host and warns for non-loopback destinations.
- **Grants expire** after 90 days regardless of refreshes, so access is
  re-confirmed periodically.
- **CORS.** Metadata, registration, token and revocation endpoints send
  `Access-Control-Allow-Origin: *` without credentials for browser-based MCP
  clients. Introspection does not.
- Expired authorisation requests and tokens are purged opportunistically when
  new ones are created, so no scheduled task is required.

## Registering a resource server

Each protected service needs a resource server record. Run this once per
service and store the printed secret in that service's secret store; it is
shown only once:

```bash
python manage.py create_oauth_resource_server "ADB Brain" https://brain.adbsoftwaresolutions.co.uk/mcp
```

Use `--scope` to declare scopes (default `mcp`) and `--rotate-secret` to
replace a leaked secret. The resource URI must exactly match what the service
advertises in its protected resource metadata.

The resource server must:

1. serve `/.well-known/oauth-protected-resource` (RFC 9728) with
   `resource` set to its resource URI and `authorization_servers` set to the
   issuer;
2. answer unauthenticated requests with `401` and
   `WWW-Authenticate: Bearer resource_metadata="<that URL>"`;
3. validate bearer tokens through `/oauth/introspect`, caching active results
   for no longer than about a minute so revocation stays prompt.

## Pre-registered confidential clients

Server-side applications, such as a Next.js frontend that holds tokens in an
encrypted server-side session, should be pre-registered instead of using
dynamic registration:

```bash
python manage.py create_oauth_client "ADB Brain web" \
  --redirect-uri https://brain.adbsoftwaresolutions.co.uk/auth/callback
```

They authenticate to the token endpoint with HTTP Basic (or
`--auth-method client_secret_post`) and still use PKCE.

## Code map

| Location                                                                     | Responsibility                                                    |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `backend/authentication/oauth/models.py`                                     | Clients, resource servers, authorisation requests, grants, tokens |
| `backend/authentication/oauth/services.py`                                   | Protocol rules, token issuing, introspection, revocation          |
| `backend/authentication/oauth/endpoints.py`                                  | Plain Django protocol endpoints                                   |
| `backend/authentication/oauth/views.py`                                      | Session-authenticated consent and connected-app API               |
| `backend/authentication/oauth/tests/`                                        | Flow and permission-boundary tests                                |
| `sites/auth-adb-software-solutions/src/screens/OAuthConsentPage.tsx`         | Consent screen                                                    |
| `sites/auth-adb-software-solutions/src/components/ConnectedApplications.tsx` | Connected applications list                                       |
