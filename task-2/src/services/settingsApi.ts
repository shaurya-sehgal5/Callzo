
const API_BASE = "/api";

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    },
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw Object.assign(
      new Error(body.detail?.message || `Request failed (${response.status})`),
      { status: response.status, body }
    );
  }

  return body as T;
}

export function getAccountSettings(accountId: number) {
  return request<Record<string, unknown>>(
    `/accounts/${accountId}/settings`
  );
}

export function saveSettingsStep(
  accountId: number,
  step: number,
  data: Record<string, unknown>
) {
  return request<{ step: number; saved: boolean; data: unknown }>(
    `/accounts/${accountId}/settings/step/${step}`,
    {
      method: "PUT",
      body: JSON.stringify({ data }),
    }
  );
}

export function submitAccountSettings(accountId: number) {
  return request<{ submitted?: boolean; message?: string }>(
    `/accounts/${accountId}/settings/submit`,
    { method: "POST" }
  );
}
