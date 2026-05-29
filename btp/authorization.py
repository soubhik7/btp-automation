"""XSUAA authorization: roles, role collections, role templates, applications."""
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .client import BTPClient


class AuthorizationService:
    """Manage XSUAA roles and role collections in a subaccount."""

    def __init__(self, client: BTPClient):
        self._c = client
        self._path = client.cfg.authorization_path

    def _enc(self, value: str) -> str:
        return quote(value, safe="")

    # ── Applications ─────────────────────────────────────────────────────────

    def list_applications(self) -> List[Dict]:
        resp = self._c.xsuaa_get(f"{self._path}/apps")
        return resp if isinstance(resp, list) else resp.get("value", [])

    def get_application(self, app_id: str) -> Dict:
        return self._c.xsuaa_get(f"{self._path}/apps/{self._enc(app_id)}")

    # ── Role Templates ────────────────────────────────────────────────────────

    def list_role_templates(self, app_id: str = None) -> List[Dict]:
        path = f"{self._path}/roletemplates"
        if app_id:
            path = f"{self._path}/apps/{self._enc(app_id)}/roletemplates"
        resp = self._c.xsuaa_get(path)
        return resp if isinstance(resp, list) else resp.get("value", [])

    def get_role_template(self, app_id: str, role_template_name: str) -> Dict:
        return self._c.xsuaa_get(
            f"{self._path}/apps/{self._enc(app_id)}/roletemplates/{self._enc(role_template_name)}"
        )

    # ── Roles ─────────────────────────────────────────────────────────────────

    def list_roles(self) -> List[Dict]:
        resp = self._c.xsuaa_get(f"{self._path}/roles")
        return resp if isinstance(resp, list) else resp.get("value", [])

    def get_role(self, role_template_name: str, app_id: str, role_name: str) -> Dict:
        return self._c.xsuaa_get(
            f"{self._path}/roles/{self._enc(role_template_name)}"
            f"/{self._enc(app_id)}/{self._enc(role_name)}"
        )

    def create_role(
        self,
        role_name: str,
        role_template_name: str,
        app_id: str,
        description: str = "",
        attribute_values: List[Dict] = None,
    ) -> Dict:
        """Create a role from a role template, optionally with attribute restrictions."""
        body: Dict[str, Any] = {
            "name": role_name,
            "roleTemplateName": role_template_name,
            "roleTemplateAppId": app_id,
            "description": description,
        }
        if attribute_values:
            body["attributeList"] = attribute_values
        return self._c.xsuaa_post(f"{self._path}/roles", body)

    def delete_role(self, role_template_name: str, app_id: str, role_name: str) -> None:
        return self._c.xsuaa_delete(
            f"{self._path}/roles/{self._enc(role_template_name)}"
            f"/{self._enc(app_id)}/{self._enc(role_name)}"
        )

    # ── Role Collections ──────────────────────────────────────────────────────

    def list_role_collections(self) -> List[Dict]:
        resp = self._c.xsuaa_get(f"{self._path}/rolecollections")
        return resp if isinstance(resp, list) else resp.get("value", [])

    def get_role_collection(self, name: str) -> Dict:
        return self._c.xsuaa_get(f"{self._path}/rolecollections/{self._enc(name)}")

    def create_role_collection(self, name: str, description: str = "") -> Dict:
        body = {"name": name, "description": description, "roleReferences": []}
        return self._c.xsuaa_post(f"{self._path}/rolecollections", body)

    def update_role_collection(self, name: str, description: str = None,
                                role_references: List[Dict] = None) -> Dict:
        """Update a role collection's description or assigned roles."""
        existing = self.get_role_collection(name)
        body: Dict[str, Any] = {
            "name": name,
            "description": description if description is not None else existing.get("description", ""),
            "roleReferences": role_references if role_references is not None else existing.get("roleReferences", []),
        }
        return self._c.xsuaa_put(f"{self._path}/rolecollections/{self._enc(name)}", body)

    def delete_role_collection(self, name: str) -> None:
        return self._c.xsuaa_delete(f"{self._path}/rolecollections/{self._enc(name)}")

    def add_role_to_collection(
        self,
        collection_name: str,
        role_name: str,
        role_template_name: str,
        app_id: str,
    ) -> Dict:
        """Add a role to an existing role collection."""
        existing = self.get_role_collection(collection_name)
        refs = list(existing.get("roleReferences", []))
        refs.append({
            "roleTemplateName": role_template_name,
            "roleTemplateAppId": app_id,
            "name": role_name,
        })
        return self.update_role_collection(collection_name, role_references=refs)

    def remove_role_from_collection(
        self,
        collection_name: str,
        role_name: str,
    ) -> Dict:
        """Remove a role from a role collection by role name."""
        existing = self.get_role_collection(collection_name)
        refs = [r for r in existing.get("roleReferences", []) if r.get("name") != role_name]
        return self.update_role_collection(collection_name, role_references=refs)

    def assign_user_to_collection(self, collection_name: str, username: str,
                                   origin: str = "sap.default") -> Dict:
        """Assign a user to a role collection."""
        return self._c.xsuaa_put(
            f"{self._path}/rolecollections/{self._enc(collection_name)}/users",
            {"userName": username, "origin": origin},
        )

    def remove_user_from_collection(self, collection_name: str, username: str,
                                     origin: str = "sap.default") -> None:
        return self._c.xsuaa_delete(
            f"{self._path}/rolecollections/{self._enc(collection_name)}/users/{self._enc(username)}"
        )
