# SAP BTP Full Automation

Python automation framework covering every layer of SAP Business Technology Platform: accounts, entitlements, environments, security, service lifecycle, Cloud Foundry operations, Destination Service, and SAP Integration Suite — all accessible from one interactive TUI or scripted CLI.

---

## Table of Contents

- [What It Can Do](#what-it-can-do)
- [Architecture](#architecture)
- [Credential Management](#credential-management)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Authentication](#authentication)
- [Interactive Mode](#interactive-mode)
- [CLI Reference](#cli-reference)
- [Scripts](#scripts)
- [API Coverage](#api-coverage)
- [Project Structure](#project-structure)
- [Library Usage](#library-usage)
- [Extending](#extending)
- [Troubleshooting](#troubleshooting)

---

## What It Can Do

| Layer | Capabilities |
|-------|-------------|
| **Account hierarchy** | Global account, subaccounts, directories |
| **Entitlements** | Assign / unassign service plan quotas per subaccount |
| **Environments** | Provision / delete CF and Kyma runtime environments |
| **Security** | Roles, role collections, user assignments (XSUAA) |
| **Service lifecycle** | Create / delete service instances and bindings (any offering) |
| **Cloud Foundry** | Spaces, apps (push/start/stop/logs), CF services, service keys, env vars |
| **Destinations** | HTTP, BasicAuth, OAuth2, on-premise destinations via Destination Service REST API |
| **Integration Suite** | Integration packages, iFlow deploy/undeploy, runtime monitoring, message logs |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        btp_cli.py (Click CLI)                        │
│            Interactive TUI  +  scriptable command groups             │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────┘
       │          │          │          │          │          │
  accounts  entitlements  security  services   cf        destinations
  provision                                              integration_suite
       │          │          │          │          │          │
       └──────────┴──────────┘          │          │          │
                  │                     │          │          │
       ┌──────────▼──────────┐    ┌─────▼──────┐  │   ┌──────▼──────┐
       │   btp/btp_cli.py    │    │ btp/       │  │   │ btp/        │
       │  (BTP CLI wrapper)  │    │ services.py│  │   │ destinations│
       │  subprocess → `btp` │    └─────┬──────┘  │   │ .py (REST)  │
       └──────────┬──────────┘          │          │   └──────▼──────┘
                  │               btp/btp_cli.py   │   Destination Svc
       ┌──────────▼──────────┐    instance/binding │   REST API
       │   SAP BTP CLI       │    CRUD via `btp`   │
       │   (btp binary)      │                     │   ┌──────▼──────┐
       │   Handles SSO +     │         ┌───────────▼─▶ │ btp/cf.py   │
       │   token refresh     │         │               │ (CF wrapper)│
       └─────────────────────┘         │               │ subprocess→ │
                                       │               │ `cf` binary │
                                       │               └─────────────┘
                                       │
                                       │               ┌─────────────┐
                                       └──────────────▶│ btp/        │
                                                       │ integration  │
                                                       │ _suite.py   │
                                                       │ (OData REST)│
                                                       └─────────────┘
```

**Auth paths:**

| Path | Used by | Mechanism |
|------|---------|-----------|
| BTP CLI subprocess | Accounts, entitlements, provisioning, security, service instances/bindings | Interactive SSO — browser login, token cached 24 h |
| CF CLI subprocess | Spaces, apps, CF services, service keys | `cf login --sso`, session cached |
| Destination Service REST API | Destinations CRUD | OAuth2 `client_credentials` — token from service binding |
| Integration Suite OData API | Packages, iFlows, message logs | OAuth2 `client_credentials` — from Process Integration Runtime service key |

---

## Credential Management

All secrets live in one place: the `.env` file. Nothing is hardcoded in Python or YAML.

```
config/btp_config.yaml   ← non-secret: endpoints, account GUIDs, env var names
         │
         │  env var names (not values) stored in yaml
         ▼
.env  ───────────────────► btp/config.py (BTPConfig)   ← single source of truth
      loaded by python-dotenv         │
                                      ▼
                              btp/auth.py (TokenManager)
                              OAuth2 client_credentials + in-memory token cache
```

### Configuration files

| File | Purpose | Committed? |
|------|---------|-----------|
| `config/btp_config.yaml` | Endpoints, account GUIDs, env var names, defaults | Yes |
| `.env` | Actual secrets — client IDs, client secrets | **No** — gitignored |
| `.env.example` | Variable name template (no real values) | Yes |

### Required `.env` variables

```bash
# CIS Central — for account/entitlement/provisioning/service instance APIs
BTP_CIS_CLIENT_ID=sb-ut-<uuid>-clone!b<n>|cis-central!b<n>
BTP_CIS_CLIENT_SECRET=<uuid>$<base64>

# XSUAA — for authorization/roles operations
BTP_XSUAA_CLIENT_ID=sb-<app>!t<n>
BTP_XSUAA_CLIENT_SECRET=<uuid>$<base64>

# CF login (used by cf CLI interactive login — not a secret stored here)
BTP_CF_USERNAME=your-email@example.com

# Integration Suite (optional — needed only for `isuit` commands)
IS_BASE_URL=https://<tenant>.integrationsuite.cfapps.us10.hana.ondemand.com
IS_TOKEN_URL=https://<tenant>.authentication.us10.hana.ondemand.com/oauth/token
IS_CLIENT_ID=sb-<app>!t<n>
IS_CLIENT_SECRET=<uuid>$<base64>
```

---

## Prerequisites

```bash
# Python 3.10+
python3 --version

# SAP BTP CLI
brew install btp
# or: https://tools.hana.ondemand.com/#cloud-btpcli

# Cloud Foundry CLI v8+
brew install cloudfoundry/tap/cf-cli@8
# or: https://github.com/cloudfoundry/cli/releases

# Python dependencies
pip install -e .           # preferred — reads pyproject.toml
# or:
pip install -r requirements.txt
```

---

## Setup

### 1. Install

```bash
git clone <repo-url>
cd btp-automation
pip install -e .           # installs btp-auto entry point + all deps
```

### 2. Configure credentials

```bash
cp .env.example .env
# edit .env — fill in client IDs and secrets
```

**Get CIS Central credentials:**
```bash
cf service-key btp-mcp-cis cis-key
# copy clientid  → BTP_CIS_CLIENT_ID
# copy clientsecret → BTP_CIS_CLIENT_SECRET
```

**Get XSUAA credentials:**
```bash
cf service-key btp-mcp-xsuaa xsuaa-key
# copy clientid  → BTP_XSUAA_CLIENT_ID
# copy clientsecret → BTP_XSUAA_CLIENT_SECRET
```

**Get Integration Suite credentials** (if using `isuit` commands):
```bash
# 1. Create a Process Integration Runtime service instance (plan: api) in BTP Cockpit
# 2. Create a service key:
cf create-service-key <is-instance-name> is-api-key
cf service-key <is-instance-name> is-api-key
# copy url      → IS_BASE_URL
# copy tokenUrl → IS_TOKEN_URL
# copy clientId → IS_CLIENT_ID
# copy clientSecret → IS_CLIENT_SECRET
```

### 3. Verify `config/btp_config.yaml`

```yaml
global_account:
  guid: "<your-global-account-guid>"
  subdomain: "<your-ga-subdomain>"

subaccount:
  guid: "<your-subaccount-guid>"
  subdomain: "<your-subaccount-subdomain>"
  region: us10
```

### 4. Log in to BTP CLI and CF CLI

```bash
# BTP CLI — one-time SSO login (cached 24 h)
btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso

# CF CLI — one-time SSO login (cached by cf)
cf login -a https://api.cf.us10-001.hana.ondemand.com --sso
```

---

## Interactive Mode

Run with no arguments to launch the full interactive TUI:

```bash
python3 btp_cli.py
# or via installed entry point:
btp-auto
```

The TUI presents a hierarchical menu covering every operation:

```
╭──────────────────────────────────────────────────────╮
│  SAP BTP Automation                                  │
│  Global: a6ff9d4dtrial | Subaccount: a6ff9d4dtrial  │
╰──────────────────────────────────────────────────────╯

  Main Menu
    1  Accounts & Hierarchy
    2  Entitlements
    3  Provisioning / Environments
    4  Security: Roles & Users
    5  Services: Instances & Bindings
    6  Cloud Foundry
    7  Destinations
    8  SAP Integration Suite
    9  Account Snapshot
    0  Exit
```

Each section opens a submenu. All inputs prompt with defaults from `config/btp_config.yaml`. Destructive operations always ask for `y/n` confirmation.

**Explicit launch:**
```bash
python3 btp_cli.py interactive
btp-auto interactive
```

---

## CLI Reference

```bash
python3 btp_cli.py [--format table|json|yaml] <group> <command> [options]
# or via installed entry point:
btp-auto [--format table|json|yaml] <group> <command> [options]
```

### accounts

```bash
python3 btp_cli.py accounts global-account
python3 btp_cli.py accounts list-subaccounts
python3 btp_cli.py accounts get-subaccount <guid>
python3 btp_cli.py accounts create-subaccount --name "Dev" --subdomain my-dev --region us10
python3 btp_cli.py accounts update-subaccount <guid> --name "Dev Updated"
python3 btp_cli.py accounts delete-subaccount <guid>
python3 btp_cli.py accounts list-directories
python3 btp_cli.py accounts create-directory --name Engineering --description "Eng team"
python3 btp_cli.py accounts delete-directory <guid>
```

### entitlements

```bash
python3 btp_cli.py entitlements list                                  # all global
python3 btp_cli.py entitlements list --subaccount <guid>              # subaccount quota
python3 btp_cli.py entitlements assign --subaccount <guid> --service destination --plan lite
python3 btp_cli.py entitlements assign --subaccount <guid> --service hana-cloud --plan hana --amount 1
python3 btp_cli.py entitlements unassign --subaccount <guid> --service destination --plan lite
python3 btp_cli.py entitlements data-centers
```

### provisioning

```bash
python3 btp_cli.py provisioning list-available --subaccount <guid>
python3 btp_cli.py provisioning list --subaccount <guid>
python3 btp_cli.py provisioning create-cf --subaccount <guid> --org-name my-org --landscape cf-us10-001
python3 btp_cli.py provisioning delete --subaccount <guid> --instance-id <id>
```

### auth

```bash
python3 btp_cli.py auth list-apps
python3 btp_cli.py auth list-roles
python3 btp_cli.py auth create-role --name MyRole --template MyTemplate --app-id myapp!t123
python3 btp_cli.py auth delete-role --name MyRole --template MyTemplate --app-id myapp!t123
python3 btp_cli.py auth list-role-collections
python3 btp_cli.py auth get-role-collection "BTP Admin"
python3 btp_cli.py auth create-role-collection --name MyRC --description "Custom RC"
python3 btp_cli.py auth delete-role-collection MyRC
python3 btp_cli.py auth add-role-to-collection --collection MyRC --role-name MyRole --template MyTemplate --app-id myapp!t123
python3 btp_cli.py auth list-users
python3 btp_cli.py auth assign-user --collection MyRC --user user@company.com
python3 btp_cli.py auth unassign-user --collection MyRC --user user@company.com
```

### services — full lifecycle

```bash
# Discover
python3 btp_cli.py services list-offerings
python3 btp_cli.py services list-plans
python3 btp_cli.py services list-plans --offering xsuaa
python3 btp_cli.py services list-instances

# Instance CRUD
python3 btp_cli.py services create-instance \
  --name my-xsuaa \
  --offering xsuaa \
  --plan application \
  --params '{"xsappname":"my-app","tenant-mode":"dedicated"}'

python3 btp_cli.py services delete-instance my-xsuaa   # bindings must be removed first

# Binding lifecycle (generates credentials)
python3 btp_cli.py services list-bindings
python3 btp_cli.py services create-binding --binding my-key --instance my-xsuaa
python3 btp_cli.py services get-binding my-key               # shows full credentials JSON
python3 btp_cli.py services get-binding my-key --format json # pipe to jq
python3 btp_cli.py services delete-binding my-key
```

### cf — Cloud Foundry

```bash
# Session
python3 btp_cli.py cf target
python3 btp_cli.py cf set-target --org my-org --space dev

# Spaces
python3 btp_cli.py cf list-spaces
python3 btp_cli.py cf create-space staging
python3 btp_cli.py cf delete-space staging

# Apps
python3 btp_cli.py cf list-apps
python3 btp_cli.py cf push my-app --path ./dist
python3 btp_cli.py cf push my-app --path ./dist --no-start
python3 btp_cli.py cf start my-app
python3 btp_cli.py cf stop my-app
python3 btp_cli.py cf restage my-app
python3 btp_cli.py cf delete-app my-app
python3 btp_cli.py cf logs my-app

# Environment variables
python3 btp_cli.py cf env my-app
python3 btp_cli.py cf set-env my-app DB_URL "jdbc:postgresql://..."

# CF services
python3 btp_cli.py cf list-services
python3 btp_cli.py cf create-service destination lite my-dest
python3 btp_cli.py cf delete-service my-dest

# App ↔ service bindings
python3 btp_cli.py cf bind-service my-app my-dest
python3 btp_cli.py cf unbind-service my-app my-dest

# Service keys (credentials without a CF app)
python3 btp_cli.py cf create-service-key my-dest dest-key
python3 btp_cli.py cf get-service-key my-dest dest-key
```

### destinations — Destination Service

Requires a destination service instance with a service binding (auto-detected by name).

```bash
python3 btp_cli.py destinations list
python3 btp_cli.py destinations get MY_BACKEND

# HTTP destination (no auth)
python3 btp_cli.py destinations create-http \
  --name MY_BACKEND \
  --url https://api.example.com

# HTTP with basic auth
python3 btp_cli.py destinations create-http \
  --name MY_BACKEND \
  --url https://api.example.com \
  --auth BasicAuthentication \
  --user myuser \
  --password mysecret

# HTTP on-premise (via Cloud Connector)
python3 btp_cli.py destinations create-http \
  --name MY_ONPREM \
  --url http://internal-host:8080 \
  --proxy OnPremise

# OAuth2 client credentials destination
python3 btp_cli.py destinations create-oauth \
  --name MY_API \
  --url https://api.service.com \
  --client-id sb-myapp!t123 \
  --client-secret "abc$xyz" \
  --token-url https://tenant.authentication.us10.hana.ondemand.com/oauth/token

python3 btp_cli.py destinations delete MY_BACKEND
```

### isuit — SAP Integration Suite

Requires `IS_BASE_URL`, `IS_TOKEN_URL`, `IS_CLIENT_ID`, `IS_CLIENT_SECRET` in `.env`.

```bash
# Design-time
python3 btp_cli.py isuit list-packages
python3 btp_cli.py isuit list-iflows <PackageId>

# Runtime deployment
python3 btp_cli.py isuit deploy <iFlowId>
python3 btp_cli.py isuit deploy <iFlowId> --version active
python3 btp_cli.py isuit undeploy <iFlowId>
python3 btp_cli.py isuit list-runtime

# Monitoring
python3 btp_cli.py isuit logs --top 50
python3 btp_cli.py isuit logs --status FAILED
python3 btp_cli.py isuit failed-messages --top 20
```

### Output formats

All commands accept `--format`:

```bash
btp-auto --format json services list-instances
btp-auto --format yaml auth list-role-collections
btp-auto --format table entitlements list     # default
```

---

## Scripts

Standalone scripts for batch operations — in `scripts/`.

### `scripts/list_all.py` — Full BTP Snapshot

```bash
python3 scripts/list_all.py
```

Prints: global account → subaccounts → directories → entitlements → data centers → environments → role collections → users → service offerings → service instances.

### `scripts/manage_entitlements.py` — Bulk Entitlement Operations

```bash
python3 scripts/manage_entitlements.py --list
python3 scripts/manage_entitlements.py --list --subaccount <guid>
python3 scripts/manage_entitlements.py --apply   # applies ASSIGNMENTS list in the script
```

### `scripts/manage_roles.py` — Role / Role Collection Management

```bash
python3 scripts/manage_roles.py --list-collections
python3 scripts/manage_roles.py --list-roles
python3 scripts/manage_roles.py --create-collection --name MyRC --desc "Description"
python3 scripts/manage_roles.py --delete-collection --name MyRC
python3 scripts/manage_roles.py --assign-user --collection MyRC --user user@company.com
python3 scripts/manage_roles.py --add-role --collection MyRC --role-name MyRole --template MyTemplate --app-id myapp!t123
```

### `scripts/setup_new_subaccount.py` — End-to-End Subaccount Setup

Edit `CONFIG` dict at top of file, then:

```bash
python3 scripts/setup_new_subaccount.py
```

Steps: create subaccount → assign entitlements → provision CF environment.

---

## API Coverage

| Domain | Operations | Backend |
|--------|-----------|---------|
| **Global Account** | Get | BTP CLI |
| **Subaccounts** | List, Get, Create, Update, Delete | BTP CLI |
| **Directories** | List, Get, Create, Update, Delete | BTP CLI |
| **Entitlements** | List, Assign, Unassign, Bulk assign | BTP CLI |
| **Data Centers** | List available regions | BTP CLI |
| **CF Environments** | List available, List instances, Create, Delete | BTP CLI |
| **XSUAA Apps** | List | BTP CLI |
| **Roles** | List, Create, Delete | BTP CLI |
| **Role Collections** | List, Get, Create, Update, Delete | BTP CLI |
| **Role → Collection** | Add, Remove | BTP CLI |
| **User → Collection** | Assign, Remove, List users | BTP CLI |
| **Service Offerings** | List | BTP CLI |
| **Service Plans** | List, filter by offering | BTP CLI |
| **Service Instances** | List, Create, Delete | BTP CLI |
| **Service Bindings** | List, Create, Get (credentials), Delete | BTP CLI |
| **CF Spaces** | List, Create, Delete | CF CLI |
| **CF Apps** | List, Push, Start, Stop, Restage, Delete, Logs | CF CLI |
| **CF Env vars** | Get, Set | CF CLI |
| **CF Services** | List, Create, Delete | CF CLI |
| **CF Service Bindings** | Bind app, Unbind app | CF CLI |
| **CF Service Keys** | Create, Get (credentials), Delete | CF CLI |
| **Destinations** | List, Get, Create (HTTP/Basic/OAuth2/OnPremise), Update, Delete | Destination Service REST |
| **Integration Packages** | List, Get | Integration Suite OData |
| **iFlows** | List, Get, Deploy, Undeploy | Integration Suite OData |
| **Runtime Artifacts** | List, Get | Integration Suite OData |
| **Message Logs** | List (all/failed/by-status), Get attachments | Integration Suite OData |
| **Value Mappings** | List | Integration Suite OData |

---

## Project Structure

```
btp-automation/
├── .env                         ← YOUR SECRETS (gitignored)
├── .env.example                 ← Variable name template (no real values)
├── .gitignore
├── pyproject.toml               ← Package metadata, deps, tool config
├── requirements.txt             ← Flat dep list (fallback to pyproject.toml)
├── btp_cli.py                   ← Main CLI entry point (Click) + interactive TUI
│
├── config/
│   └── btp_config.yaml          ← Central config: endpoints, GUIDs, defaults
│
├── btp/                         ← Core library
│   ├── __init__.py              ← Public exports for all services
│   ├── config.py                ← BTPConfig: loads yaml + .env, exposes typed properties
│   ├── auth.py                  ← TokenManager: OAuth2 client_credentials + in-memory cache
│   ├── client.py                ← BTPClient: HTTP session with auth for XSUAA REST
│   ├── btp_cli.py               ← BTP CLI subprocess wrapper (all btp commands)
│   ├── cf.py                    ← CF CLI subprocess wrapper (all cf commands)
│   ├── accounts.py              ← AccountsService: subaccounts + directories
│   ├── entitlements.py          ← EntitlementsService: service plan entitlements
│   ├── provisioning.py          ← ProvisioningService: CF + Kyma environments
│   ├── authorization.py         ← AuthorizationService: roles + role collections
│   ├── services.py              ← ServicesService: instances + bindings (full lifecycle)
│   ├── destinations.py          ← DestinationService: HTTP/OAuth/RFC destinations (REST)
│   ├── integration_suite.py     ← IntegrationSuiteService: packages, iFlows, logs
│   ├── exceptions.py            ← BTPError, BTPAuthError, BTPNotFoundError, etc.
│   └── output.py                ← Rich-based output: tables, JSON, YAML
│
└── scripts/
    ├── list_all.py              ← Full BTP snapshot
    ├── manage_entitlements.py   ← Bulk entitlement operations
    ├── manage_roles.py          ← Role / role collection management
    └── setup_new_subaccount.py  ← End-to-end subaccount provisioning
```

---

## Library Usage

Use the modules directly in Python scripts:

```python
from btp import (
    AccountsService, EntitlementsService, ProvisioningService,
    AuthorizationService, ServicesService, DestinationService,
    IntegrationSuiteService,
)
from btp import cf   # CF CLI wrapper functions

# --- Account hierarchy ---
accounts = AccountsService()
subs = accounts.list_subaccounts()
new_sa = accounts.create_subaccount("Dev", "my-dev", "us10")

# --- Service lifecycle ---
services = ServicesService()
services.create_instance("my-xsuaa", "xsuaa", "application",
                         {"xsappname": "my-app", "tenant-mode": "dedicated"})
services.create_binding("my-key", "my-xsuaa")
credentials = services.get_binding("my-key")   # full credentials dict
services.delete_binding("my-key")
services.delete_instance("my-xsuaa")

# --- Cloud Foundry ---
from btp import cf
cf.set_target(space="dev")
cf.push_app("my-app", path="./dist")
cf.bind_service("my-app", "my-xsuaa")
cf.start_app("my-app")
print(cf.recent_logs("my-app"))

# --- Destinations ---
from btp.config import BTPConfig
cfg = BTPConfig()
dest = DestinationService(cfg.subaccount_guid)   # auto-detects binding

dest.create(DestinationService.http_destination(
    name="MY_BACKEND",
    url="https://api.example.com",
    auth="NoAuthentication",
))

dest.create(DestinationService.oauth_destination(
    name="MY_OAUTH_API",
    url="https://protected-api.example.com",
    client_id="client-id",
    client_secret="client-secret",
    token_url="https://tenant.auth.example.com/oauth/token",
))

for d in dest.list():
    print(d["Name"], d["Type"])

# --- Integration Suite ---
is_svc = IntegrationSuiteService()   # reads IS_* from .env
packages = is_svc.list_packages()
iflows = is_svc.list_iflows(packages[0]["Id"])
is_svc.deploy_iflow(iflows[0]["Id"])
failed = is_svc.get_failed_messages(top=10)

# --- Security ---
auth = AuthorizationService()
auth.create_role_collection("My-RC", "Custom access")
auth.add_role_to_collection("My-RC", "Developer", "Developer", "us10-app-studio!t5804")
auth.assign_user_to_collection("My-RC", "user@company.com")
```

---

## Extending

### Add a new service module

1. Create `btp/my_service.py` — use `btp_cli._run([...])` for BTP CLI calls or `requests` for REST
2. Add to `btp/__init__.py`
3. Add a Click group to `btp_cli.py`
4. Add a submenu to `_launch_interactive()` in `btp_cli.py`

### Add a new CLI command

```python
@cli.group()
def mygroup():
    """Description shown in --help."""

@mygroup.command("do-something")
@click.option("--param", required=True)
@click.pass_context
def do_something(ctx, param):
    try:
        svc = MyService()
        _print(svc.do_something(param), ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e)); sys.exit(1)
```

### Change default output format

```yaml
# config/btp_config.yaml
defaults:
  output_format: "json"   # table | json | yaml
```

---

## Troubleshooting

### "BTP CLI not found"
```bash
brew install btp
# or: https://tools.hana.ondemand.com/#cloud-btpcli
```

### "Not logged in to BTP CLI"
```bash
btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso
```

### "CF CLI not found"
```bash
brew install cloudfoundry/tap/cf-cli@8
```

### "Not logged in to CF"
```bash
cf login -a https://api.cf.us10-001.hana.ondemand.com --sso
cf target -o <org> -s <space>
```

### "No destination service binding found"
Create a binding for your destination service instance:
```bash
btp-auto services create-binding --binding dest-key --instance btp-mcp-destination
```
Or pass `--binding dest-key` explicitly to `destinations` commands.

### "Integration Suite credentials not configured"
Add to `.env`:
```bash
IS_BASE_URL=https://<tenant>.integrationsuite.cfapps.us10.hana.ondemand.com
IS_TOKEN_URL=https://<tenant>.authentication.us10.hana.ondemand.com/oauth/token
IS_CLIENT_ID=sb-<app>!t<n>
IS_CLIENT_SECRET=<uuid>$<base64>
```
Get values from a Process Integration Runtime service key (`plan: api`).

### "401 Unauthorized" on authorization commands
Re-create the XSUAA service key and update `.env`:
```bash
cf delete-service-key btp-mcp-xsuaa xsuaa-key
cf create-service-key btp-mcp-xsuaa xsuaa-key
cf service-key btp-mcp-xsuaa xsuaa-key
# copy clientid → BTP_XSUAA_CLIENT_ID
# copy clientsecret → BTP_XSUAA_CLIENT_SECRET
```

### "KeyError: 'BTP_CIS_CLIENT_ID'" (or similar)
```bash
cp .env.example .env
# fill in .env with your values
```

### Service instance deletion fails with "has active bindings"
Delete all bindings for the instance first:
```bash
btp-auto services list-bindings --format json   # find binding names
btp-auto services delete-binding <binding-name>
btp-auto services delete-instance <instance-name>
```
