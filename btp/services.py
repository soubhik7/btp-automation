"""CF service marketplace management — via BTP CLI."""
from typing import Dict, List, Optional
from . import btp_cli as cli
from .config import BTPConfig


class ServicesService:
    """Browse and manage CF service instances and offerings."""

    def __init__(self, client=None, subaccount_guid: str = None):
        self._sa = subaccount_guid or BTPConfig().subaccount_guid

    def list_offerings(self, subaccount_guid: str = None) -> List[Dict]:
        return cli.list_service_offerings(subaccount_guid or self._sa)

    def list_plans(self, offering_name: str = None, subaccount_guid: str = None) -> List[Dict]:
        return cli.list_service_plans(subaccount_guid or self._sa, offering_name)

    def list_instances(self, subaccount_guid: str = None) -> List[Dict]:
        return cli.list_service_instances(subaccount_guid or self._sa)
