export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
export const CLINICAL_USER_ID = "USR_TECH_ANALYST";

function newId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function clinicalApiPath(path) {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `/Clinical${normalized}`;
}

export async function postClinicalEvent(event) {
  const response = await fetch(`${API_BASE_URL}${clinicalApiPath("/api/clinical/events")}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": event?.actorUserId || CLINICAL_USER_ID,
      "X-Correlation-Id": event?.correlationId || event?.correlation_id || newId()
    },
    body: JSON.stringify(event)
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(payload?.error || `${response.status} ${response.statusText}`);
  }

  return payload;
}

export function sendClinicalEvent(event) {
  postClinicalEvent(event).catch((error) => {
    console.warn("Clinical event write failed", error);
  });
}

export async function getClinicalHealth() {
  const response = await fetch(`${API_BASE_URL}${clinicalApiPath("/api/clinical/health")}`, {
    method: "GET",
    headers: {
      "Accept": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function getClinicalRecentEvents(limit = 20) {
  const response = await fetch(`${API_BASE_URL}${clinicalApiPath(`/api/clinical/events/recent?limit=${encodeURIComponent(limit)}`)}`, {
    method: "GET",
    headers: {
      "Accept": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}