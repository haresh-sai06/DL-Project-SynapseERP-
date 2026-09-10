"""Authenticated generated ERP workspace with CRUD operations."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from synapse_erp.config import OUTPUT_DIR


class WorkspaceStore:
    resource_keys = {
        "inventory": "sku",
        "customers": "name",
        "invoices": "invoice_id",
    }

    def __init__(self, output_root: Path | None = None) -> None:
        self.output_root = output_root or OUTPUT_DIR
        self.workspace_root = self.output_root / "workspaces"

    def get_workspace(self, conversion_id: str) -> dict[str, Any]:
        path = self._ensure_workspace(conversion_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def create_access_token(self, conversion_id: str) -> str:
        """Create a conversion-scoped bearer token and persist only its hash."""
        self._ensure_workspace(conversion_id)
        token = secrets.token_urlsafe(32)
        payload = {
            "conversion_id": conversion_id,
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        path = self._access_path(conversion_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return token

    def verify_access(self, conversion_id: str, authorization: str | None) -> None:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise PermissionError("Missing workspace bearer token.")
        path = self._access_path(conversion_id)
        if not path.exists():
            raise PermissionError("Workspace access has not been initialized.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        token = authorization.split(" ", 1)[1].strip()
        actual = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual, payload.get("token_hash", "")):
            raise PermissionError("Invalid workspace token.")

    def list_resource(self, conversion_id: str, resource: str) -> list[dict[str, Any]]:
        workspace = self.get_workspace(conversion_id)
        return workspace[self._resource_name(resource)]

    def add_item(self, conversion_id: str, resource: str, item: dict[str, Any]) -> dict[str, Any]:
        name = self._resource_name(resource)
        key = self.resource_keys[name]
        if key not in item or not str(item[key]).strip():
            raise ValueError(f"Missing required key `{key}`.")
        workspace = self.get_workspace(conversion_id)
        rows = workspace[name]
        item_id = str(item[key])
        if any(str(row.get(key)) == item_id for row in rows):
            raise ValueError(f"`{item_id}` already exists in {name}.")
        rows.append(item)
        self._save(conversion_id, workspace)
        return item

    def update_item(self, conversion_id: str, resource: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        name = self._resource_name(resource)
        key = self.resource_keys[name]
        workspace = self.get_workspace(conversion_id)
        for row in workspace[name]:
            if str(row.get(key)) == item_id:
                row.update(patch)
                if key not in row or not str(row[key]).strip():
                    row[key] = item_id
                self._save(conversion_id, workspace)
                return row
        raise KeyError(f"`{item_id}` not found in {name}.")

    def delete_item(self, conversion_id: str, resource: str, item_id: str) -> dict[str, Any]:
        name = self._resource_name(resource)
        key = self.resource_keys[name]
        workspace = self.get_workspace(conversion_id)
        kept = [row for row in workspace[name] if str(row.get(key)) != item_id]
        if len(kept) == len(workspace[name]):
            raise KeyError(f"`{item_id}` not found in {name}.")
        workspace[name] = kept
        self._save(conversion_id, workspace)
        return {"deleted": item_id, "resource": name}

    def _ensure_workspace(self, conversion_id: str) -> Path:
        path = self._workspace_path(conversion_id)
        if path.exists():
            return path
        snapshot_path = self.output_root / "conversions" / conversion_id / "snapshot.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"No conversion snapshot found for {conversion_id}.")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        workspace = {
            "conversion_id": conversion_id,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "inventory": snapshot.get("inventory", []),
            "customers": snapshot.get("customers", []),
            "invoices": snapshot.get("invoices", []),
            "analytics": snapshot.get("analytics", {}),
        }
        self._save(conversion_id, workspace)
        return path

    def _save(self, conversion_id: str, workspace: dict[str, Any]) -> None:
        workspace["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        path = self._workspace_path(conversion_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(workspace, indent=2), encoding="utf-8")

    def _workspace_path(self, conversion_id: str) -> Path:
        return self.workspace_root / conversion_id / "workspace.json"

    def _access_path(self, conversion_id: str) -> Path:
        path = self.workspace_root / conversion_id / "access.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _resource_name(self, resource: str) -> str:
        if resource not in self.resource_keys:
            raise ValueError("Resource must be one of inventory, customers, invoices.")
        return resource
