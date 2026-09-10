export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

const CONVERSION_KEY = "synapse_erp_conversion";
const WORKSPACE_KEY = "synapse_erp_workspace";

export function absoluteUrl(url) {
  if (!url) return "";
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

export function formatMoney(value) {
  return `Rs ${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  })}`;
}

export function saveConversion(conversion) {
  saveJson(CONVERSION_KEY, conversion);
}

export function loadConversion() {
  return loadJson(CONVERSION_KEY);
}

export function saveWorkspace(workspace) {
  saveJson(WORKSPACE_KEY, workspace);
}

export function loadWorkspace() {
  return loadJson(WORKSPACE_KEY);
}

export function getErpOutput(conversion) {
  return conversion?.outputs?.find((output) => output.format === "html");
}

export function getWorkspaceToken(conversion = loadConversion()) {
  const token = conversion?.workspace_token;
  if (!token) throw new Error("This conversion has no workspace access token. Run a new conversion.");
  return token;
}

export async function fetchWorkspace(conversionId, conversion = loadConversion()) {
  const token = getWorkspaceToken(conversion);
  const response = await fetch(`${API_BASE}/api/workspaces/${conversionId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error(await response.text());
  const workspace = await response.json();
  saveWorkspace(workspace);
  return workspace;
}

export function saveJson(key, value) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

export function loadJson(key) {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
