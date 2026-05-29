# SAP BTP Full Automation

Python automation framework covering all SAP Business Technology Platform operations: accounts, entitlements, environments, and authorization — everything available in the BTP Cockpit, scripted.

---

## Table of Contents

- [Architecture](#architecture)
- [Credential Management](#credential-management)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Authentication](#authentication)
- [CLI Reference](#cli-reference)
- [Scripts](#scripts)
- [API Coverage](#api-coverage)
- [Project Structure](#project-structure)
- [Extending](#extending)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   btp_cli.py (Click CLI)                │
│              Interactive + command-line interface        │
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        │                  │                       │
┌───────▼──────┐  ┌────────▼───────┐  ┌───────────▼──────┐
│ AccountsService│ │EntitlementsService│ │AuthorizationService│
│ProvisioningService      │           └──────────┬───────┘
└───────┬──────┘  └────────┬───────┘             │
        │                  │                     │
┌───────▼──────────────────▼──────┐    ┌─────────▼────────┐
│       btp/btp_cli.py            │    │  btp/client.py   │
│  (BTP CLI subprocess wrapper)   │    │  (REST + OAuth2) │
│  btp accounts/entitlements/...  │    │  XSUAA REST API  │
└─────────────────────────────────┘    └──────────────────┘
        │                                        │
┌───────▼─────────┐               ┌──────────────▼───────┐
│  SAP BTP CLI    │               │  XSUAA REST API      │
│  (btp binary)   │               │  (roles, role-colls) │
│  Handles OAuth  │               │  a6ff9d4dtrial.auth  │
│  token refresh  │               │  entication.us10     │
└─────────────────┘               └──────────────────────┘
```

**Two auth paths:**
| Path | Used by | Auth mechanism |
|------|---------|----------------|
| BTP CLI subprocess | Accounts, Entitlements, Provisioning | Interactive SSO (browser login, cached 24h) |
| XSUAA REST API | Authorization (roles, role collections) | OAuth2 `client_credentials` via service key |

---

## Credential Management

All secrets and credentials are managed in **one place**: the `.env` file at the project root.

### Where credentials come from

```
config/btp_config.yaml          ← non-secret config (endpoints, guids, env var names)
         │
         │  reads env var names from yaml
         ▼
.env     ────────────────────────► btp/config.py (BTPConfig)
         ← loaded via python-dotenv                  │
                                                     ▼
                                            btp/auth.py (TokenManager)
                                            OAuth2 client_credentials
                                                     │
                                                     ▼
                                              XSUAA REST API
```

**Nothing is hardcoded.** The yaml file stores *which environment variable* to read; the `.env` file stores the actual secret. Change credentials by editing `.env` only — no code changes needed.

### Configuration files

| File | Purpose | In git? |
|------|---------|---------|
| `config/btp_config.yaml` | All endpoints, account GUIDs, env var names, defaults | Yes |
| `.env` | Actual secrets: client IDs, client secrets | **No** — gitignored |
| `.env.example` | Template showing required variable names | Yes |

### How to update credentials

1. Get new service key from CF: `cf service-key <instance> <key-name>`
2. Update the relevant variable in `.env`
3. That's it — `BTPConfig` reloads `.env` on next process start

### Where each endpoint comes from

All API base URLs live in `config/btp_config.yaml` under `endpoints:` and `auth:`. To point to a different subaccount or region, change only the yaml file:

```yaml
endpoints:
  accounts_service:    "https://accounts-service.cfapps.eu10.hana.ondemand.com"
  entitlements_service: "https://entitlements-service.cfapps.eu10.hana.ondemand.com"
  provisioning_service: "https://provisioning-service.cfapps.eu10.hana.ondemand.com"
  xsuaa_api:           "https://<subdomain>.authentication.<region>.hana.ondemand.com"

auth:
  cis_central:
    client_id_env: "BTP_CIS_CLIENT_ID"        # name of env var, not the value
    client_secret_env: "BTP_CIS_CLIENT_SECRET"
    token_url: "https://<subdomain>-ga.authentication.<region>.hana.ondemand.com/oauth/token"
  xsuaa:
    client_id_env: "BTP_XSUAA_CLIENT_ID"
    client_secret_env: "BTP_XSUAA_CLIENT_SECRET"
    token_url: "https://<subdomain>.authentication.<region>.hana.ondemand.com/oauth/token"
```

---

## Prerequisites

```bash
# Python 3.10+
python3 --version

# SAP BTP CLI
brew install btp          # macOS
# or download from https://tools.hana.ondemand.com/#cloud-btpcli

# Cloud Foundry CLI
brew install cloudfoundry/tap/cf-cli@8

# Python dependencies
pip install -r requirements.txt
```

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd btp-automation

pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your actual values
```

Get credentials from CF service keys:
```bash
# CIS Central credentials
cf service-key cis-central-instance cis-central-key
# Copy "clientid" → BTP_CIS_CLIENT_ID
# Copy "clientsecret" → BTP_CIS_CLIENT_SECRET

# XSUAA credentials
cf service-key xsuaa-mcp-instance xsuaa-mcp-key
# Copy "clientid" → BTP_XSUAA_CLIENT_ID
# Copy "clientsecret" → BTP_XSUAA_CLIENT_SECRET
```

### 3. Update `config/btp_config.yaml`

Verify the account GUIDs and endpoints match your BTP account:
- `global_account.guid` — from BTP Cockpit → Global Account → Settings
- `subaccount.guid` — from BTP Cockpit → Subaccount → Overview
- `endpoints.xsuaa_api` — replace `<subdomain>` with your subaccount subdomain

---

## Authentication

### For Authorization API (roles, role collections)

Handled automatically. `BTPConfig` reads `BTP_XSUAA_CLIENT_ID` and `BTP_XSUAA_CLIENT_SECRET` from `.env`, then `TokenManager` fetches and caches OAuth2 tokens (refreshed 60s before expiry).

No manual step needed — works immediately after `.env` is populated.

### For Account/Entitlement/Provisioning APIs

Uses the BTP CLI binary, which maintains its own session. **One-time login required:**

```bash
btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso
```

A browser window opens. Log in with your SAP Universal ID (`sou1bhik@gmail.com`). The CLI caches the token for 24 hours. Re-run if you see "Not logged in" errors.

To verify login status:
```bash
btp list accounts/global-account
```

---

## CLI Reference

The main CLI is `btp_cli.py` at the project root.

```bash
python btp_cli.py [--format table|json|yaml] <group> <command> [options]
```

### Accounts

```bash
# Global account
python btp_cli.py accounts global-account

# Subaccounts
python btp_cli.py accounts list-subaccounts
python btp_cli.py accounts get-subaccount <guid>
python btp_cli.py accounts create-subaccount --name "Dev" --subdomain "my-dev" --region us10
python btp_cli.py accounts update-subaccount <guid> --name "Dev Updated"
python btp_cli.py accounts delete-subaccount <guid>

# Directories
python btp_cli.py accounts list-directories
python btp_cli.py accounts create-directory --name "Engineering" --description "Eng team"
python btp_cli.py accounts delete-directory <guid>
```

### Entitlements

```bash
# List all entitlements across global account
python btp_cli.py entitlements list

# Filter by subaccount or service
python btp_cli.py entitlements list --subaccount <guid>
python btp_cli.py entitlements list --service destination

# Assign / unassign
python btp_cli.py entitlements assign --subaccount <guid> --service destination --plan lite
python btp_cli.py entitlements assign --subaccount <guid> --service hana-cloud --plan hana --amount 1
python btp_cli.py entitlements unassign --subaccount <guid> --service destination --plan lite

# Available regions / data centers
python btp_cli.py entitlements data-centers
```

### Provisioning (Environments)

```bash
# List available environment types for a subaccount
python btp_cli.py provisioning list-available --subaccount <guid>

# List provisioned instances
python btp_cli.py provisioning list --subaccount <guid>

# Create Cloud Foundry environment
python btp_cli.py provisioning create-cf \
  --subaccount <guid> \
  --org-name my-cf-org \
  --landscape cf-us10-001

# Delete environment instance
python btp_cli.py provisioning delete --subaccount <guid> --instance-id <id>
```

### Authorization (XSUAA)

```bash
# Applications and role templates
python btp_cli.py auth list-apps
python btp_cli.py auth list-role-templates
python btp_cli.py auth list-role-templates --app-id <appId>

# Roles
python btp_cli.py auth list-roles
python btp_cli.py auth create-role --name "MyRole" --template "RoleTemplate" --app-id "app!t123"
python btp_cli.py auth delete-role --template "RoleTemplate" --app-id "app!t123" --name "MyRole"

# Role Collections
python btp_cli.py auth list-role-collections
python btp_cli.py auth get-role-collection "BTP Admin"
python btp_cli.py auth create-role-collection --name "MyCollection" --description "Custom collection"
python btp_cli.py auth delete-role-collection "MyCollection"

# Add role to collection
python btp_cli.py auth add-role-to-collection \
  --collection "MyCollection" \
  --role-name "MyRole" \
  --template "RoleTemplate" \
  --app-id "app!t123"

# Assign user to collection
python btp_cli.py auth assign-user --collection "BTP Admin" --user user@email.com
```

### Interactive Mode

```bash
python btp_cli.py interactive
```

Launches a menu-driven shell — no flags needed, prompts for all values.

### Output Formats

All commands support `--format`:

```bash
python btp_cli.py --format json accounts list-subaccounts   # JSON output
python btp_cli.py --format yaml auth list-role-collections  # YAML output
python btp_cli.py --format table entitlements list          # Rich table (default)
```

---

## Scripts

Located in `scripts/` — standalone scripts for batch operations.

### `scripts/list_all.py` — Full BTP Snapshot

Prints everything: global account → subaccounts → directories → entitlements → data centers → environments → role collections → roles.

```bash
python scripts/list_all.py
```

### `scripts/manage_entitlements.py` — Bulk Entitlement Operations

Edit the `ASSIGNMENTS` and `UNASSIGNMENTS` lists in the file, then run:

```bash
# List current entitlements
python scripts/manage_entitlements.py --list
python scripts/manage_entitlements.py --list --subaccount <guid>

# Apply the ASSIGNMENTS list defined in the script
python scripts/manage_entitlements.py --apply
```

### `scripts/manage_roles.py` — Role / Role Collection Management

```bash
python scripts/manage_roles.py --list-collections
python scripts/manage_roles.py --list-roles
python scripts/manage_roles.py --list-templates
python scripts/manage_roles.py --list-apps

python scripts/manage_roles.py --create-collection --name "MyRC" --desc "Description"
python scripts/manage_roles.py --delete-collection --name "MyRC"

python scripts/manage_roles.py --assign-user --collection "MyRC" --user user@email.com

python scripts/manage_roles.py --add-role \
  --collection "MyRC" \
  --role-name "MyRole" \
  --template "RoleTemplate" \
  --app-id "app!t123"
```

### `scripts/setup_new_subaccount.py` — End-to-End Subaccount Setup

Edit the `CONFIG` dict at the top of the file, then run:

```bash
python scripts/setup_new_subaccount.py
```

Steps automated:
1. Create subaccount
2. Assign entitlements
3. Provision CF environment (optional, set `enable_cf: True`)

---

## API Coverage

| Domain | Operations | Backend |
|--------|-----------|---------|
| **Global Account** | Get details | BTP CLI |
| **Subaccounts** | List, Get, Create, Update, Delete | BTP CLI |
| **Directories** | List, Get, Create, Update, Delete | BTP CLI |
| **Entitlements** | List, Assign, Unassign, Bulk assign | BTP CLI |
| **Data Centers** | List available regions | BTP CLI |
| **Environments** | List available, List instances, Create CF, Create Kyma, Delete | BTP CLI |
| **XSUAA Apps** | List, Get | XSUAA REST |
| **Role Templates** | List (global + per-app), Get | XSUAA REST |
| **Roles** | List, Get, Create, Delete | XSUAA REST |
| **Role Collections** | List, Get, Create, Update, Delete | XSUAA REST |
| **Role → Collection** | Add role, Remove role | XSUAA REST |
| **User → Collection** | Assign user, Remove user | XSUAA REST |

---

## Project Structure

```
btp-automation/
├── .env                          ← YOUR SECRETS (gitignored)
├── .env.example                  ← Template — copy to .env
├── .mcp.json                     ← Project-level MCP server config (Claude Code)
├── .gitignore
├── requirements.txt
├── btp_cli.py                    ← Main CLI entry point (Click)
│
├── config/
│   └── btp_config.yaml           ← Central config: endpoints, GUIDs, defaults
│
├── btp/                          ← Core library
│   ├── __init__.py
│   ├── config.py                 ← BTPConfig: loads yaml + .env, exposes properties
│   ├── auth.py                   ← TokenManager: OAuth2 client_credentials + caching
│   ├── client.py                 ← BTPClient: HTTP client for XSUAA REST API
│   ├── btp_cli.py                ← BTP CLI subprocess wrapper (accounts/ent/prov)
│   ├── accounts.py               ← AccountsService: subaccounts + directories
│   ├── entitlements.py           ← EntitlementsService: service plan entitlements
│   ├── provisioning.py           ← ProvisioningService: CF + Kyma environments
│   ├── authorization.py          ← AuthorizationService: roles + role collections
│   ├── exceptions.py             ← BTPError, BTPAuthError, BTPNotFoundError, etc.
│   └── output.py                 ← Rich-based output: tables, JSON, YAML
│
└── scripts/
    ├── list_all.py               ← Full BTP snapshot
    ├── manage_entitlements.py    ← Bulk entitlement operations
    ├── manage_roles.py           ← Role / role collection management
    └── setup_new_subaccount.py  ← End-to-end subaccount provisioning
```

### Key design principles

- **One `.env` file** — all secrets in one place, never in code or yaml
- **One yaml config** — all endpoints, GUIDs, defaults; env var *names* (not values) are stored here
- **`BTPConfig` is the single source of truth** — all modules get config through it
- **Token caching** — OAuth2 tokens cached in memory, refreshed 60s before expiry
- **Two clear auth paths** — BTP CLI for global account ops (SSO), XSUAA REST for authorization ops (service key)
- **Typed exceptions** — `BTPAuthError`, `BTPNotFoundError`, `BTPConflictError`, `BTPValidationError`

---

## Extending

### Add a new service

1. Create `btp/my_service.py` with a class that uses `btp/client.py` for REST calls or `btp/btp_cli.py` for BTP CLI calls
2. Add it to `btp/__init__.py`
3. Add a command group to `btp_cli.py`

### Add a new CLI command

```python
@cli.group()
def mygroup():
    """My new command group."""

@mygroup.command("do-something")
@click.option("--param", required=True)
@click.pass_context
def do_something(ctx, param):
    try:
        svc = MyService()
        data = svc.do_something(param)
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)
```

### Change output format globally

Edit `config/btp_config.yaml`:
```yaml
defaults:
  output_format: "json"   # table | json | yaml
```

Or pass `--format` on any command for one-off overrides.

### Use as a library

```python
from btp.config import BTPConfig
from btp.client import BTPClient
from btp.authorization import AuthorizationService

cfg = BTPConfig()                  # loads .env automatically
client = BTPClient(cfg)
auth = AuthorizationService(client)

collections = auth.list_role_collections()
auth.create_role_collection("My-Collection", "Created via API")
auth.assign_user_to_collection("My-Collection", "user@company.com")
```

---

## Troubleshooting

### "BTP CLI not found"
```bash
brew install btp
# or download from https://tools.hana.ondemand.com/#cloud-btpcli
```

### "Not logged in to BTP CLI"
```bash
btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso
```

### "401 Unauthorized" on authorization commands
Check `.env` — `BTP_XSUAA_CLIENT_ID` or `BTP_XSUAA_CLIENT_SECRET` may be wrong or expired. Re-create the service key:
```bash
cf delete-service-key xsuaa-mcp-instance xsuaa-mcp-key
cf create-service-key xsuaa-mcp-instance xsuaa-mcp-key
cf service-key xsuaa-mcp-instance xsuaa-mcp-key
# update .env with new values
```

### "KeyError: 'BTP_XSUAA_CLIENT_ID'"
The `.env` file is missing or the variable is not set. Run:
```bash
cp .env.example .env
# fill in .env with your values
```
