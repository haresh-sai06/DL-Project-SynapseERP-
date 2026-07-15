"""Authenticated generated ERP workspace with CRUD operations."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from synapse_erp.config import OUTPUT_DIR


class LoginRequest(BaseModel):
    shop_id: str = "synapse-demo"
    pin: str = "1234"


class DemoAuthService:
    """Small local auth service for demo mode.

    This is intentionally dependency-light. Production should replace it with
    OAuth/JWT, password hashing, refresh tokens, and tenant-aware database auth.
    """

    def __init__(self, secret: str = "synapse-erp-local-dev-secret") -> None:
        self.secret = secret.encode("utf-8")

    def login(self, request: LoginRequest) -> dict[str, Any]:
        if request.shop_id != "synapse-demo" or request.pin != "1234":
            raise PermissionError("Invalid demo credentials.")
        payload = {
            "sub": request.shop_id,
            "role": "owner",
            "exp": (datetime.utcnow() + timedelta(hours=8)).isoformat(timespec="seconds") + "Z",
        }
        token = self._sign(payload)
        return {
            "access_token": token,
            "token_type": "bearer",
            "shop_id": request.shop_id,
            "role": "owner",
            "demo_pin": "1234",
        }

    def verify(self, authorization: str | None) -> dict[str, Any]:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise PermissionError("Missing bearer token.")
        token = authorization.split(" ", 1)[1].strip()
        try:
            raw_payload, raw_signature = token.split(".", 1)
            expected = self._signature(raw_payload)
            if not hmac.compare_digest(raw_signature, expected):
                raise PermissionError("Invalid token signature.")
            payload = json.loads(_b64decode(raw_payload).decode("utf-8"))
            expiry = datetime.fromisoformat(payload["exp"].replace("Z", ""))
            if datetime.utcnow() >= expiry:
                raise PermissionError("Token expired.")
            return payload
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("Invalid token.") from exc

    def _sign(self, payload: dict[str, Any]) -> str:
        raw_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        return f"{raw_payload}.{self._signature(raw_payload)}"

    def _signature(self, raw_payload: str) -> str:
        digest = hmac.new(self.secret, raw_payload.encode("utf-8"), hashlib.sha256).digest()
        return _b64encode(digest)


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

    def _resource_name(self, resource: str) -> str:
        if resource not in self.resource_keys:
            raise ValueError("Resource must be one of inventory, customers, invoices.")
        return resource


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
