export type AccountStatus = "active" | "trial" | "suspended";
export type Plan = "basic" | "pro" | "enterprise";

export interface Account {
  id: string;
  name: string;
  email: string;
  company: string;
  country: string;
  plan: Plan;
  status: AccountStatus;
  signup_date: string;
  current_month_minutes: number;
  current_month_sms: number;
  cost_cents: number;
  last_active: string;
}

export interface AccountsResponse {
  data: Account[];
  total: number;
  page: number;
  page_size: number;
}

export interface SummaryPoint {
  date: string;
  minutes: number;
  sms: number;
  cost_cents: number;
  signups: number;
}

export interface SummaryResponse {
  series: SummaryPoint[];
  total_accounts: number;
}

export interface AccountFilters {
  search: string;
  status: string;
  country: string;
  plan: string;
  date_from: string;
  date_to: string;
  sort_by: string;
  sort_dir: "asc" | "desc";
  page: number;
  page_size: number;
}