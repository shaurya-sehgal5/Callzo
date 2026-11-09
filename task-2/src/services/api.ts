import type {
  AccountsResponse,
  AccountFilters,
  SummaryResponse,
} from "../types";

const API_BASE = "/api";

function buildQuery(params: Record<string, string | number>) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== undefined && value !== null) {
      query.set(key, String(value));
    }
  });

  return query.toString();
}

async function request<T>(
  endpoint: string,
  signal?: AbortSignal
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    signal,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return response.json();
}

export function getAccounts(
  filters: AccountFilters,
  signal?: AbortSignal
): Promise<AccountsResponse> {
  const query = buildQuery({
    page: filters.page,
    page_size: filters.page_size,
    search: filters.search,
    status: filters.status,
    country: filters.country,
    plan: filters.plan,
    date_from: filters.date_from,
    date_to: filters.date_to,
    sort_by: filters.sort_by,
    sort_dir: filters.sort_dir,
  });

  return request<AccountsResponse>(`/accounts?${query}`, signal);
}

export function getSummary(
  dateFrom: string,
  dateTo: string,
  signal?: AbortSignal
): Promise<SummaryResponse> {
  const query = buildQuery({
    date_from: dateFrom,
    date_to: dateTo,
  });

  return request<SummaryResponse>(`/accounts/summary?${query}`, signal);
}