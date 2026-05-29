#!/usr/bin/env python3
"""
BTP Automation CLI
Interactive command-line interface for all SAP BTP operations.

Usage:
    python btp_cli.py accounts list-subaccounts
    python btp_cli.py accounts get-subaccount <guid>
    python btp_cli.py accounts create-subaccount --name trial2 --subdomain trial2 --region us10
    python btp_cli.py entitlements list
    python btp_cli.py entitlements assign --subaccount <guid> --service hana-cloud --plan hana
    python btp_cli.py provisioning list-environments --subaccount <guid>
    python btp_cli.py auth list-role-collections
    python btp_cli.py auth create-role-collection --name MyRC --description "My RC"
"""
import sys
import click

from btp.config import BTPConfig
from btp.client import BTPClient
from btp.accounts import AccountsService
from btp.entitlements import EntitlementsService
from btp.provisioning import ProvisioningService
from btp.authorization import AuthorizationService
from btp.services import ServicesService
from btp.exceptions import BTPError
import btp.output as out


def _client() -> BTPClient:
    return BTPClient(BTPConfig())


# ── Root group ────────────────────────────────────────────────────────────────

@click.group()
@click.option("--format", "fmt", default="table",
              type=click.Choice(["table", "json", "yaml"]), show_default=True)
@click.pass_context
def cli(ctx, fmt):
    """SAP BTP Full Automation CLI"""
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = fmt


def _print(data, fmt="table", title="", columns=None):
    if fmt == "json":
        out.print_json(data)
    elif fmt == "yaml":
        out.print_yaml(data)
    else:
        if isinstance(data, list):
            out.print_table(data, columns=columns, title=title)
        else:
            out.print_json(data)


# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def accounts():
    """Global account, subaccounts, and directories."""


@accounts.command("global-account")
@click.pass_context
def global_account(ctx):
    """Show global account details."""
    try:
        svc = AccountsService(_client())
        data = svc.get_global_account()
        _print(data, ctx.obj["fmt"], "Global Account")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("list-subaccounts")
@click.pass_context
def list_subaccounts(ctx):
    """List all subaccounts."""
    try:
        svc = AccountsService(_client())
        data = svc.list_subaccounts()
        _print(data, ctx.obj["fmt"], "Subaccounts",
               columns=["guid", "displayName", "subdomain", "region", "state"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("get-subaccount")
@click.argument("guid")
@click.pass_context
def get_subaccount(ctx, guid):
    """Get a subaccount by GUID."""
    try:
        svc = AccountsService(_client())
        _print(svc.get_subaccount(guid), ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("create-subaccount")
@click.option("--name", required=True, help="Display name")
@click.option("--subdomain", required=True, help="Unique subdomain")
@click.option("--region", required=True, help="Region, e.g. us10")
@click.option("--description", default="", help="Description")
@click.option("--parent-guid", default=None, help="Parent directory GUID")
@click.pass_context
def create_subaccount(ctx, name, subdomain, region, description, parent_guid):
    """Create a new subaccount."""
    try:
        svc = AccountsService(_client())
        data = svc.create_subaccount(name, subdomain, region, description, parent_guid)
        out.success(f"Subaccount '{name}' created: {data.get('guid', '')}")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("update-subaccount")
@click.argument("guid")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.pass_context
def update_subaccount(ctx, guid, name, description):
    """Update a subaccount."""
    try:
        svc = AccountsService(_client())
        data = svc.update_subaccount(guid, display_name=name, description=description)
        out.success(f"Subaccount {guid} updated")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("delete-subaccount")
@click.argument("guid")
@click.confirmation_option(prompt="This permanently deletes the subaccount. Continue?")
@click.pass_context
def delete_subaccount(ctx, guid):
    """Delete a subaccount."""
    try:
        svc = AccountsService(_client())
        svc.delete_subaccount(guid)
        out.success(f"Subaccount {guid} deleted")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("list-directories")
@click.pass_context
def list_directories(ctx):
    """List all directories."""
    try:
        svc = AccountsService(_client())
        data = svc.list_directories()
        _print(data, ctx.obj["fmt"], "Directories",
               columns=["guid", "displayName", "state"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("create-directory")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.option("--parent-guid", default=None)
@click.pass_context
def create_directory(ctx, name, description, parent_guid):
    """Create a directory."""
    try:
        svc = AccountsService(_client())
        data = svc.create_directory(name, description, parent_guid)
        out.success(f"Directory '{name}' created: {data.get('guid', '')}")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@accounts.command("delete-directory")
@click.argument("guid")
@click.confirmation_option(prompt="Delete this directory?")
@click.pass_context
def delete_directory(ctx, guid):
    """Delete a directory."""
    try:
        svc = AccountsService(_client())
        svc.delete_directory(guid)
        out.success(f"Directory {guid} deleted")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# ENTITLEMENTS
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def entitlements():
    """Service plan entitlement management."""


@entitlements.command("list")
@click.option("--subaccount", default=None, help="Filter by subaccount GUID")
@click.option("--service", default=None, help="Filter by service name")
@click.pass_context
def list_entitlements(ctx, subaccount, service):
    """List entitlement assignments."""
    try:
        svc = EntitlementsService(_client())
        data = svc.list_assignments(subaccount_guid=subaccount, service_name=service)
        # Subaccount-filtered response uses {service, plan, quota} fields
        # Global response uses {name, displayName, servicePlans}
        if subaccount and data and "service" in (data[0] if data else {}):
            cols = ["service", "plan", "quota", "unlimited"]
        else:
            cols = ["name", "displayName"]
        _print(data, ctx.obj["fmt"], "Entitlements", columns=cols)
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@entitlements.command("assign")
@click.option("--subaccount", required=True, help="Subaccount GUID")
@click.option("--service", required=True, help="Service technical name")
@click.option("--plan", required=True, help="Service plan name")
@click.option("--amount", default=None, type=int, help="Quota amount (omit for unlimited)")
@click.pass_context
def assign_entitlement(ctx, subaccount, service, plan, amount):
    """Assign a service plan entitlement to a subaccount."""
    try:
        svc = EntitlementsService(_client())
        svc.assign_entitlement(subaccount, service, plan, amount)
        out.success(f"Entitlement {service}/{plan} assigned to {subaccount}")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@entitlements.command("unassign")
@click.option("--subaccount", required=True)
@click.option("--service", required=True)
@click.option("--plan", required=True)
@click.confirmation_option(prompt="Remove this entitlement?")
@click.pass_context
def unassign_entitlement(ctx, subaccount, service, plan):
    """Remove a service plan entitlement from a subaccount."""
    try:
        svc = EntitlementsService(_client())
        svc.unassign_entitlement(subaccount, service, plan)
        out.success(f"Entitlement {service}/{plan} removed from {subaccount}")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@entitlements.command("data-centers")
@click.pass_context
def data_centers(ctx):
    """List available data centers."""
    try:
        svc = EntitlementsService(_client())
        data = svc.get_allowed_data_centers()
        _print(data, ctx.obj["fmt"], "Available Data Centers",
               columns=["name", "displayName", "region", "environment"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# PROVISIONING (Environments)
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def provisioning():
    """Runtime environment instance management (CF, Kyma)."""


@provisioning.command("list-available")
@click.option("--subaccount", required=True, help="Subaccount GUID")
@click.pass_context
def list_available(ctx, subaccount):
    """List environment types available for provisioning."""
    try:
        svc = ProvisioningService(_client())
        data = svc.list_available_environments(subaccount)
        _print(data, ctx.obj["fmt"], "Available Environments",
               columns=["environmentType", "planName", "displayName"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@provisioning.command("list")
@click.option("--subaccount", required=True, help="Subaccount GUID")
@click.pass_context
def list_envs(ctx, subaccount):
    """List provisioned environment instances."""
    try:
        svc = ProvisioningService(_client())
        data = svc.list_environment_instances(subaccount)
        _print(data, ctx.obj["fmt"], "Environment Instances",
               columns=["environmentInstanceID", "environmentType", "name", "state"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@provisioning.command("create-cf")
@click.option("--subaccount", required=True)
@click.option("--org-name", required=True, help="CF org name")
@click.option("--landscape", default=None, help="Landscape label e.g. cf-us10-001")
@click.pass_context
def create_cf(ctx, subaccount, org_name, landscape):
    """Provision a Cloud Foundry environment."""
    try:
        svc = ProvisioningService(_client())
        data = svc.create_cf_environment(subaccount, org_name, landscape_label=landscape)
        out.success(f"CF environment '{org_name}' provisioning started")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@provisioning.command("delete")
@click.option("--subaccount", required=True)
@click.option("--instance-id", required=True, help="Environment instance ID")
@click.confirmation_option(prompt="Delete this environment instance?")
@click.pass_context
def delete_env(ctx, subaccount, instance_id):
    """Delete an environment instance."""
    try:
        svc = ProvisioningService(_client())
        svc.delete_environment_instance(subaccount, instance_id)
        out.success(f"Environment {instance_id} deletion started")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION (XSUAA)
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def auth():
    """Security: roles, role collections, users."""


@auth.command("list-apps")
@click.pass_context
def list_apps(ctx):
    """List registered XSUAA applications in the subaccount."""
    try:
        svc = AuthorizationService()
        data = svc.list_applications()
        _print(data, ctx.obj["fmt"], "Applications",
               columns=["appId", "appName", "description"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("list-roles")
@click.pass_context
def list_roles(ctx):
    """List all roles in the subaccount."""
    try:
        svc = AuthorizationService()
        data = svc.list_roles()
        _print(data, ctx.obj["fmt"], "Roles",
               columns=["name", "roleTemplateName", "roleTemplateAppId", "description"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("create-role")
@click.option("--name", required=True)
@click.option("--template", required=True, help="Role template name")
@click.option("--app-id", required=True, help="Application ID (e.g. myapp!t123)")
@click.option("--description", default="")
@click.pass_context
def create_role(ctx, name, template, app_id, description):
    """Create a role from a template."""
    try:
        svc = AuthorizationService()
        data = svc.create_role(name, template, app_id, description)
        out.success(f"Role '{name}' created")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("delete-role")
@click.option("--name", required=True, help="Role name")
@click.option("--template", required=True, help="Role template name")
@click.option("--app-id", required=True, help="Application ID")
@click.confirmation_option(prompt="Delete this role?")
@click.pass_context
def delete_role(ctx, name, template, app_id):
    """Delete a role."""
    try:
        svc = AuthorizationService()
        svc.delete_role(name, template, app_id)
        out.success(f"Role '{name}' deleted")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("list-role-collections")
@click.pass_context
def list_role_collections(ctx):
    """List all role collections."""
    try:
        svc = AuthorizationService()
        data = svc.list_role_collections()
        _print(data, ctx.obj["fmt"], "Role Collections",
               columns=["name", "description", "isReadOnly"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("get-role-collection")
@click.argument("name")
@click.pass_context
def get_role_collection(ctx, name):
    """Get a role collection by name."""
    try:
        svc = AuthorizationService()
        _print(svc.get_role_collection(name), ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("create-role-collection")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.pass_context
def create_role_collection(ctx, name, description):
    """Create a new role collection."""
    try:
        svc = AuthorizationService()
        data = svc.create_role_collection(name, description)
        out.success(f"Role collection '{name}' created")
        _print(data, ctx.obj["fmt"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("delete-role-collection")
@click.argument("name")
@click.confirmation_option(prompt="Delete this role collection?")
@click.pass_context
def delete_role_collection(ctx, name):
    """Delete a role collection."""
    try:
        svc = AuthorizationService()
        svc.delete_role_collection(name)
        out.success(f"Role collection '{name}' deleted")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("add-role-to-collection")
@click.option("--collection", required=True, help="Role collection name")
@click.option("--role-name", required=True, help="Role name")
@click.option("--template", required=True, help="Role template name")
@click.option("--app-id", required=True, help="Application ID")
@click.pass_context
def add_role_to_collection(ctx, collection, role_name, template, app_id):
    """Add a role to a role collection."""
    try:
        svc = AuthorizationService()
        svc.add_role_to_collection(collection, role_name, template, app_id)
        out.success(f"Role '{role_name}' added to '{collection}'")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("list-users")
@click.pass_context
def list_users(ctx):
    """List all users in the subaccount."""
    try:
        svc = AuthorizationService()
        data = svc.list_users()
        if isinstance(data, list) and data and isinstance(data[0], str):
            _print([{"email": u} for u in data], ctx.obj["fmt"], "Users", columns=["email"])
        else:
            _print(data, ctx.obj["fmt"], "Users", columns=["id", "userName"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("assign-user")
@click.option("--collection", required=True, help="Role collection name")
@click.option("--user", required=True, help="User email")
@click.option("--origin", default="sap.default", help="IDP origin (default: sap.default)")
@click.pass_context
def assign_user(ctx, collection, user, origin):
    """Assign a user to a role collection."""
    try:
        svc = AuthorizationService()
        svc.assign_user_to_collection(collection, user, origin)
        out.success(f"User '{user}' assigned to role collection '{collection}'")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@auth.command("unassign-user")
@click.option("--collection", required=True, help="Role collection name")
@click.option("--user", required=True, help="User email")
@click.option("--origin", default="sap.default")
@click.confirmation_option(prompt="Remove user from this role collection?")
@click.pass_context
def unassign_user(ctx, collection, user, origin):
    """Remove a user from a role collection."""
    try:
        svc = AuthorizationService()
        svc.remove_user_from_collection(collection, user, origin)
        out.success(f"User '{user}' removed from '{collection}'")
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# SERVICES
# ══════════════════════════════════════════════════════════════════════════════

@cli.group()
def services():
    """CF service marketplace: offerings, plans, and instances."""


@services.command("list-offerings")
@click.pass_context
def list_offerings(ctx):
    """List available service offerings."""
    try:
        from btp.services import ServicesService
        svc = ServicesService()
        data = svc.list_offerings()
        _print(data, ctx.obj["fmt"], "Service Offerings",
               columns=["name", "displayName", "description"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@services.command("list-plans")
@click.option("--offering", default=None, help="Filter by service offering name")
@click.pass_context
def list_plans(ctx, offering):
    """List service plans."""
    try:
        from btp.services import ServicesService
        svc = ServicesService()
        data = svc.list_plans(offering)
        _print(data, ctx.obj["fmt"], "Service Plans",
               columns=["name", "displayName", "serviceOfferingName", "free"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


@services.command("list-instances")
@click.pass_context
def list_instances(ctx):
    """List provisioned service instances."""
    try:
        from btp.services import ServicesService
        svc = ServicesService()
        data = svc.list_instances()
        _print(data, ctx.obj["fmt"], "Service Instances",
               columns=["name", "serviceOfferingName", "servicePlanName", "usable"])
    except BTPError as e:
        out.error(str(e))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MODE
# ══════════════════════════════════════════════════════════════════════════════

@cli.command("interactive")
def interactive_mode():
    """Launch interactive menu-driven BTP management shell."""
    try:
        from rich.prompt import Prompt, Confirm
        from rich.console import Console
        _console = Console()
    except ImportError:
        print("Install 'rich' for interactive mode: pip install rich")
        sys.exit(1)

    accounts_svc = AccountsService()
    entitlements_svc = EntitlementsService()
    provisioning_svc = ProvisioningService()
    auth_svc = AuthorizationService()
    services_svc = ServicesService()

    MENU = {
        "1": ("List Subaccounts", lambda: out.print_table(
            accounts_svc.list_subaccounts(), columns=["guid", "displayName", "subdomain", "region", "state"]
        )),
        "2": ("Get Subaccount", lambda: out.print_json(
            accounts_svc.get_subaccount(Prompt.ask("Subaccount GUID"))
        )),
        "3": ("Create Subaccount", lambda: _interactive_create_subaccount(accounts_svc)),
        "4": ("Delete Subaccount", lambda: _interactive_delete_subaccount(accounts_svc)),
        "5": ("List Entitlements", lambda: out.print_json(
            entitlements_svc.list_assignments(
                subaccount_guid=Prompt.ask("Subaccount GUID (blank=all)", default="") or None
            )
        )),
        "6": ("Assign Entitlement", lambda: _interactive_assign(entitlements_svc)),
        "7": ("List Environments", lambda: out.print_table(
            provisioning_svc.list_environment_instances(Prompt.ask("Subaccount GUID")),
            columns=["environmentInstanceID", "environmentType", "name", "state"],
        )),
        "8": ("List Role Collections", lambda: out.print_table(
            auth_svc.list_role_collections(), columns=["name", "description"]
        )),
        "9": ("Create Role Collection", lambda: _interactive_create_rc(auth_svc)),
        "10": ("Assign User to Role Collection", lambda: _interactive_assign_user(auth_svc)),
        "0": ("Exit", None),
    }

    while True:
        _console.print("\n[bold cyan]═══ BTP Automation Menu ═══[/bold cyan]")
        for k, (label, _) in MENU.items():
            _console.print(f"  [yellow]{k:>2}[/yellow]  {label}")
        choice = Prompt.ask("\nSelect", choices=list(MENU.keys()), default="0")
        if choice == "0":
            break
        label, fn = MENU[choice]
        try:
            fn()
        except BTPError as e:
            out.error(str(e))
        except KeyboardInterrupt:
            pass


def _interactive_create_subaccount(svc):
    from rich.prompt import Prompt
    name = Prompt.ask("Display name")
    subdomain = Prompt.ask("Subdomain")
    region = Prompt.ask("Region", default="us10")
    desc = Prompt.ask("Description", default="")
    result = svc.create_subaccount(name, subdomain, region, desc)
    out.success(f"Created: {result.get('guid')}")


def _interactive_delete_subaccount(svc):
    from rich.prompt import Prompt, Confirm
    guid = Prompt.ask("Subaccount GUID to delete")
    if Confirm.ask(f"Really delete {guid}?"):
        svc.delete_subaccount(guid)
        out.success("Deleted")


def _interactive_assign(svc):
    from rich.prompt import Prompt
    sub = Prompt.ask("Subaccount GUID")
    service = Prompt.ask("Service name")
    plan = Prompt.ask("Plan name")
    amt_str = Prompt.ask("Amount (blank=unlimited)", default="")
    amount = int(amt_str) if amt_str else None
    svc.assign_entitlement(sub, service, plan, amount)
    out.success("Entitlement assigned")


def _interactive_create_rc(svc):
    from rich.prompt import Prompt
    name = Prompt.ask("Role collection name")
    desc = Prompt.ask("Description", default="")
    svc.create_role_collection(name, desc)
    out.success(f"Role collection '{name}' created")


def _interactive_assign_user(svc):
    from rich.prompt import Prompt
    collection = Prompt.ask("Role collection name")
    user = Prompt.ask("User email")
    svc.assign_user_to_collection(collection, user)
    out.success(f"User '{user}' assigned to '{collection}'")


if __name__ == "__main__":
    cli(obj={})
