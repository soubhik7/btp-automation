#!/usr/bin/env python3
"""Show a full snapshot of your BTP account: global account, subaccounts, entitlements, environments, roles."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from btp.config import BTPConfig
from btp.client import BTPClient
from btp.accounts import AccountsService
from btp.entitlements import EntitlementsService
from btp.provisioning import ProvisioningService
from btp.authorization import AuthorizationService
from btp.exceptions import BTPError
import btp.output as out


def main():
    cfg = BTPConfig()
    client = BTPClient(cfg)

    accounts = AccountsService(client)
    entitlements = EntitlementsService(client)
    provisioning = ProvisioningService(client)
    auth = AuthorizationService(client)

    # ── Global Account ────────────────────────────────────────────────────────
    out.info("Fetching Global Account...")
    try:
        ga = accounts.get_global_account()
        out.print_table([ga], title="Global Account",
                        columns=["guid", "displayName", "subdomain", "entityState"])
    except BTPError as e:
        out.error(f"Global account: {e}")

    # ── Subaccounts ───────────────────────────────────────────────────────────
    out.info("\nFetching Subaccounts...")
    subaccount_guids = []
    try:
        subs = accounts.list_subaccounts()
        subaccount_guids = [s.get("guid") for s in subs if s.get("guid")]
        out.print_table(subs, title="Subaccounts",
                        columns=["guid", "displayName", "subdomain", "region", "state"])
    except BTPError as e:
        out.error(f"Subaccounts: {e}")

    # ── Directories ───────────────────────────────────────────────────────────
    out.info("\nFetching Directories...")
    try:
        dirs = accounts.list_directories()
        out.print_table(dirs, title="Directories",
                        columns=["guid", "displayName", "state"])
    except BTPError as e:
        out.error(f"Directories: {e}")

    # ── Entitlements ──────────────────────────────────────────────────────────
    out.info("\nFetching Entitlement Assignments...")
    try:
        ents = entitlements.list_assignments()
        out.print_table(ents, title="Entitlements",
                        columns=["name", "displayName"])
    except BTPError as e:
        out.error(f"Entitlements: {e}")

    # ── Data Centers ──────────────────────────────────────────────────────────
    out.info("\nFetching Allowed Data Centers...")
    try:
        dcs = entitlements.get_allowed_data_centers()
        out.print_table(dcs, title="Allowed Data Centers",
                        columns=["name", "displayName", "region", "environment"])
    except BTPError as e:
        out.error(f"Data centers: {e}")

    # ── Environments per subaccount ───────────────────────────────────────────
    for guid in subaccount_guids[:3]:  # limit to first 3 to avoid rate limits
        out.info(f"\nEnvironment instances in subaccount {guid}...")
        try:
            envs = provisioning.list_environment_instances(guid)
            out.print_table(envs, title=f"Environments ({guid})",
                            columns=["environmentInstanceID", "environmentType", "name", "state"])
        except BTPError as e:
            out.error(f"  Environments: {e}")

    # ── XSUAA Authorization ───────────────────────────────────────────────────
    out.info("\nFetching Role Collections...")
    try:
        rcs = auth.list_role_collections()
        out.print_table(rcs, title="Role Collections", columns=["name", "description"])
    except BTPError as e:
        out.error(f"Role collections: {e}")

    out.info("\nFetching Roles...")
    try:
        roles = auth.list_roles()
        out.print_table(roles, title="Roles",
                        columns=["name", "roleTemplateName", "description"])
    except BTPError as e:
        out.error(f"Roles: {e}")

    out.success("\nSnapshot complete.")


if __name__ == "__main__":
    main()
