"""
BTP CLI subprocess wrapper.
Calls the `btp` command-line tool and parses JSON output.
Requires one-time interactive login:
    btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso
"""
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .exceptions import BTPError, BTPNotFoundError, BTPAuthError


_BTP_BIN = "btp"


def _run(args: List[str], input_text: str = None) -> Any:
    """Run a btp CLI command and return parsed JSON output."""
    cmd = [_BTP_BIN, "--format", "json"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
        )
    except FileNotFoundError:
        raise BTPError(
            "BTP CLI not found. Install with: brew install btp\n"
            "Then login: btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso"
        )

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        if "not logged in" in err.lower() or "authentication" in err.lower():
            raise BTPAuthError(
                "Not logged in to BTP CLI.\n"
                "Run: btp login --url https://cpcli.cf.eu10.hana.ondemand.com --sso"
            )
        if "not found" in err.lower() or "does not exist" in err.lower():
            raise BTPNotFoundError(err)
        raise BTPError(f"btp CLI error: {err}")

    output = result.stdout.strip()
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Some btp commands return plain text on success
        return {"message": output}


def check_login() -> bool:
    """Return True if the BTP CLI has a valid session."""
    try:
        _run(["list", "accounts/global-account"])
        return True
    except (BTPAuthError, BTPError):
        return False


# ── Global Account ─────────────────────────────────────────────────────────────

def get_global_account() -> Dict:
    return _run(["list", "accounts/global-account"])


# ── Subaccounts ────────────────────────────────────────────────────────────────

def list_subaccounts() -> List[Dict]:
    result = _run(["list", "accounts/subaccounts"])
    if isinstance(result, list):
        return result
    return result.get("value", result.get("subaccounts", []))


def get_subaccount(guid: str) -> Dict:
    return _run(["get", "accounts/subaccount", guid])


def create_subaccount(
    display_name: str,
    subdomain: str,
    region: str,
    description: str = "",
    beta_enabled: bool = False,
    parent_guid: str = None,
) -> Dict:
    args = [
        "create", "accounts/subaccount",
        "--display-name", display_name,
        "--subdomain", subdomain,
        "--region", region,
        "--used-for-production", "NOT_USED_FOR_PRODUCTION",
    ]
    if description:
        args += ["--description", description]
    if beta_enabled:
        args += ["--beta-enabled", "true"]
    if parent_guid:
        args += ["--parent-directory", parent_guid]
    args += ["--confirm"]
    return _run(args)


def update_subaccount(guid: str, display_name: str = None, description: str = None) -> Dict:
    args = ["update", "accounts/subaccount", guid]
    if display_name:
        args += ["--display-name", display_name]
    if description:
        args += ["--description", description]
    args += ["--confirm"]
    return _run(args)


def delete_subaccount(guid: str) -> None:
    _run(["delete", "accounts/subaccount", guid, "--confirm"])


# ── Directories ────────────────────────────────────────────────────────────────

def list_directories() -> List[Dict]:
    result = _run(["list", "accounts/directories"])
    return result if isinstance(result, list) else result.get("value", [])


def get_directory(guid: str) -> Dict:
    return _run(["get", "accounts/directory", guid])


def create_directory(display_name: str, description: str = "", parent_guid: str = None) -> Dict:
    args = ["create", "accounts/directory", "--display-name", display_name]
    if description:
        args += ["--description", description]
    if parent_guid:
        args += ["--parent-directory", parent_guid]
    args += ["--confirm"]
    return _run(args)


def update_directory(guid: str, display_name: str = None, description: str = None) -> Dict:
    args = ["update", "accounts/directory", guid]
    if display_name:
        args += ["--display-name", display_name]
    if description:
        args += ["--description", description]
    args += ["--confirm"]
    return _run(args)


def delete_directory(guid: str) -> None:
    _run(["delete", "accounts/directory", guid, "--confirm"])


# ── Entitlements ────────────────────────────────────────────────────────────────

def list_entitlements(subaccount_guid: str = None) -> List[Dict]:
    args = ["list", "accounts/entitlements"]
    if subaccount_guid:
        args += ["--subaccount", subaccount_guid]
    result = _run(args)
    return result if isinstance(result, list) else result.get("entitledServices", result.get("value", [result]))


def assign_entitlement(
    subaccount_guid: str,
    service_name: str,
    plan_name: str,
    amount: int = None,
) -> None:
    args = [
        "assign", "accounts/entitlement",
        "--to-subaccount", subaccount_guid,
        "--for-service", service_name,
        "--plan", plan_name,
    ]
    if amount is not None:
        args += ["--amount", str(amount)]
    else:
        args += ["--enable"]
    args += ["--confirm"]
    _run(args)


def unassign_entitlement(subaccount_guid: str, service_name: str, plan_name: str) -> None:
    _run([
        "unassign", "accounts/entitlement",
        "--from-subaccount", subaccount_guid,
        "--for-service", service_name,
        "--plan", plan_name,
        "--confirm",
    ])


# ── Environment Instances ─────────────────────────────────────────────────────

def list_environment_instances(subaccount_guid: str) -> List[Dict]:
    result = _run(["list", "accounts/environment-instances", "--subaccount", subaccount_guid])
    return result if isinstance(result, list) else result.get("value", [])


def get_environment_instance(subaccount_guid: str, instance_id: str) -> Dict:
    return _run(["get", "accounts/environment-instance", instance_id,
                 "--subaccount", subaccount_guid])


def create_environment_instance(
    subaccount_guid: str,
    name: str,
    environment_type: str = "cloudfoundry",
    plan: str = "standard",
    landscape_label: str = None,
) -> Dict:
    args = [
        "create", "accounts/environment-instance",
        "--subaccount", subaccount_guid,
        "--display-name", name,
        "--environment", environment_type,
        "--service", environment_type,
        "--plan", plan,
    ]
    if landscape_label:
        args += ["--landscape-label", landscape_label]
    args += ["--confirm"]
    return _run(args)


def delete_environment_instance(subaccount_guid: str, instance_id: str) -> None:
    _run([
        "delete", "accounts/environment-instance", instance_id,
        "--subaccount", subaccount_guid,
        "--confirm",
    ])


# ── Available Services / Data Centers ─────────────────────────────────────────

def list_available_environments(subaccount_guid: str) -> List[Dict]:
    result = _run(["list", "accounts/available-environments", "--subaccount", subaccount_guid])
    return result if isinstance(result, list) else result.get("availableEnvironments", [])


def list_available_regions() -> List[Dict]:
    result = _run(["list", "accounts/available-regions"])
    return result if isinstance(result, list) else result.get("datacenters", [])
