
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAccounts, getSummary } from "./services/api";
import type {
  Account,
  AccountFilters,
  SummaryResponse,
} from "./types";

const initialFilters: AccountFilters = {
  search: "",
  status: "",
  country: "",
  plan: "",
  date_from: "",
  date_to: "",
  sort_by: "signup_date",
  sort_dir: "desc",
  page: 1,
  page_size: 50,
};

function formatMoney(cents: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}
function readFiltersFromUrl(): AccountFilters {
  const params = new URLSearchParams(window.location.search);

  const allowedStatuses = ["", "active", "trial", "suspended"];
  const allowedPlans = ["", "basic", "pro", "enterprise"];
  const allowedSorts = [
    "id",
    "name",
    "company",
    "country",
    "plan",
    "status",
    "signup_date",
    "current_month_minutes",
    "current_month_sms",
    "cost_cents",
    "last_active",
  ];

  const page = Number(params.get("page") || 1);
  const pageSize = Number(params.get("page_size") || 50);
  const sortBy = params.get("sort_by") || "signup_date";

  return {
    search: params.get("search") || "",
    status: allowedStatuses.includes(params.get("status") || "")
      ? params.get("status") || ""
      : "",
    country: params.get("country") || "",
    plan: allowedPlans.includes(params.get("plan") || "")
      ? params.get("plan") || ""
      : "",
    date_from: params.get("date_from") || "",
    date_to: params.get("date_to") || "",
    sort_by: allowedSorts.includes(sortBy) ? sortBy : "signup_date",
    sort_dir: params.get("sort_dir") === "asc" ? "asc" : "desc",
    page: Number.isInteger(page) && page > 0 ? page : 1,
    page_size: [10, 25, 50, 100, 200].includes(pageSize) ? pageSize : 50,
  };
}
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-emerald-50 text-emerald-700",
    trial: "bg-blue-50 text-blue-700",
    suspended: "bg-red-50 text-red-700",
  };

  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status] || "bg-gray-100 text-gray-700"}`}>
      {status}
    </span>
  );
}

export default function App() {
  const [filters, setFilters] = useState<AccountFilters>(readFiltersFromUrl);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [loading, setLoading] = useState(true);
  const [tableError, setTableError] = useState("");

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");

  const [searchInput, setSearchInput] = useState(
    () => readFiltersFromUrl().search
  );

  const totalPages = Math.max(1, Math.ceil(total / filters.page_size));

  const updateFilter = useCallback(
    (key: keyof AccountFilters, value: string | number) => {
      setFilters((current) => ({
        ...current,
        [key]: value,
        ...(key === "page" ? {} : { page: 1 }),
      }));
    },
    []
  );
  // Keep URL synchronized with table state.
  useEffect(() => {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "" && value !== initialFilters[key as keyof AccountFilters]) {
        params.set(key, String(value));
      }
    });

    const query = params.toString();
    const nextUrl = query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname;

    window.history.replaceState(null, "", nextUrl);
  }, [filters]);

  // Restore table state when browser history changes.
  useEffect(() => {
    function handlePopState() {
      const restored = readFiltersFromUrl();
      setFilters(restored);
      setSearchInput(restored.search);
    }

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);
  // Server-side account data. Polling refreshes the current query
  // without clearing selection or resetting pagination.
  const loadAccounts = useCallback(
    async (signal?: AbortSignal, background = false) => {
      if (!background) setLoading(true);

      try {
        const result = await getAccounts(filters, signal);

        if (signal?.aborted) return;

        setAccounts(result.data);
        setTotal(result.total);
        setTableError("");
      } catch (error) {
        if (signal?.aborted) return;

        setTableError(
          error instanceof Error ? error.message : "Unable to load accounts"
        );
      } finally {
        if (!signal?.aborted && !background) setLoading(false);
      }
    },
    [filters]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadAccounts(controller.signal);

    return () => controller.abort();
  }, [loadAccounts]);

  // Quiet refresh every 30 seconds.
  useEffect(() => {
    const interval = window.setInterval(() => {
      loadAccounts(undefined, true);
    }, 30000);

    return () => window.clearInterval(interval);
  }, [loadAccounts]);

  // Summary chart has independent loading and error handling.
  const loadSummary = useCallback(async (signal?: AbortSignal) => {
    setSummaryLoading(true);

    try {
      const result = await getSummary(
        filters.date_from,
        filters.date_to,
        signal
      );

      if (signal?.aborted) return;

      setSummary(result);
      setSummaryError("");
    } catch (error) {
      if (signal?.aborted) return;

      setSummaryError(
        error instanceof Error ? error.message : "Unable to load summary"
      );
    } finally {
      if (!signal?.aborted) setSummaryLoading(false);
    }
  }, [filters.date_from, filters.date_to]);

  useEffect(() => {
    const controller = new AbortController();
    loadSummary(controller.signal);

    return () => controller.abort();
  }, [loadSummary]);

  function toggleSelection(id: string) {
    setSelected((previous) => {
      const next = new Set(previous);

      if (next.has(id)) next.delete(id);
      else next.add(id);

      return next;
    });
  }

  function toggleCurrentPage() {
    setSelected((previous) => {
      const next = new Set(previous);
      const allSelected = accounts.length > 0 &&
        accounts.every((account) => next.has(account.id));

      accounts.forEach((account) => {
        if (allSelected) next.delete(account.id);
        else next.add(account.id);
      });

      return next;
    });
  }

  const allCurrentSelected = useMemo(
    () => accounts.length > 0 && accounts.every((a) => selected.has(a.id)),
    [accounts, selected]
  );

  function handleSort(field: string) {
    setFilters((current) => ({
      ...current,
      sort_by: field,
      sort_dir:
        current.sort_by === field && current.sort_dir === "asc"
          ? "desc"
          : "asc",
      page: 1,
    }));
  }

  function applySearch() {
    updateFilter("search", searchInput);
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Callzo
            </h1>
            <p className="text-xs text-slate-500">Usage Administration</p>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-slate-500 sm:inline">
              Admin Console
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
              A
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <section className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">
              Accounts
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Monitor customer accounts and usage activity.
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm">
            <span className="text-slate-500">Total accounts: </span>
            <strong>{total.toLocaleString("en-IN")}</strong>
          </div>
        </section>

        {/* Summary */}
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
          <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h3 className="font-semibold text-slate-900">Usage overview</h3>
              <p className="text-sm text-slate-500">
                Account usage for the selected signup date range.
              </p>
            </div>

            <button
              onClick={() => loadSummary()}
              disabled={summaryLoading}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
            >
              {summaryLoading ? "Refreshing..." : "Refresh chart"}
            </button>
          </div>

          {summaryError ? (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-sm font-medium text-red-800">
                Could not load the usage summary.
              </p>
              <p className="mt-1 text-xs text-red-700">{summaryError}</p>
              <button
                onClick={() => loadSummary()}
                className="mt-3 rounded-md bg-red-700 px-3 py-2 text-sm text-white hover:bg-red-800"
              >
                Retry
              </button>
            </div>
          ) : summaryLoading && !summary ? (
            <div className="flex h-64 items-center justify-center text-sm text-slate-500">
              Loading usage summary...
            </div>
          ) : summary ? (
            <>
              <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Metric label="Total accounts" value={summary.total_accounts.toLocaleString()} />
                <Metric
                  label="Total minutes"
                  value={summary.series.reduce((sum, item) => sum + item.minutes, 0).toLocaleString()}
                />
                <Metric
                  label="Total SMS"
                  value={summary.series.reduce((sum, item) => sum + item.sms, 0).toLocaleString()}
                />
                <Metric
                  label="Total cost"
                  value={formatMoney(summary.series.reduce((sum, item) => sum + item.cost_cents, 0))}
                />
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={summary.series}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(value) => String(value).slice(5)}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="minutes"
                      name="Minutes"
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="sms"
                      name="SMS"
                      stroke="#059669"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <p className="py-12 text-center text-sm text-slate-500">
              No summary data available.
            </p>
          )}
        </section>

        {/* Filters */}
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
            <h3 className="font-semibold text-slate-900">Account directory</h3>
            <span className="text-xs text-slate-500">
              {selected.size} accounts selected across pages
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="flex gap-2 sm:col-span-2">
              <input
                aria-label="Search accounts"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applySearch()}
                placeholder="Search name, email or company..."
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                onClick={applySearch}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
              >
                Search
              </button>
            </div>

            <select
              aria-label="Filter by status"
              value={filters.status}
              onChange={(e) => updateFilter("status", e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="trial">Trial</option>
              <option value="suspended">Suspended</option>
            </select>

            <select
              aria-label="Filter by country"
              value={filters.country}
              onChange={(e) => updateFilter("country", e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All countries</option>
              {["US", "IN", "GB", "CA", "AU"].map((country) => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>

            <select
              aria-label="Filter by plan"
              value={filters.plan}
              onChange={(e) => updateFilter("plan", e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All plans</option>
              <option value="basic">Basic</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>

            <label className="text-xs text-slate-600">
              Signup from
              <input
                type="date"
                aria-label="Signup date from"
                value={filters.date_from}
                onChange={(e) => updateFilter("date_from", e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>

            <label className="text-xs text-slate-600">
              Signup to
              <input
                type="date"
                aria-label="Signup date to"
                value={filters.date_to}
                onChange={(e) => updateFilter("date_to", e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>

            <button
              onClick={() => {
                setSearchInput("");
                setFilters(initialFilters);
              }}
              className="self-end rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Clear filters
            </button>
          </div>
        </section>

        {/* Table */}
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {tableError && (
            <div role="alert" className="m-4 rounded-lg bg-red-50 p-4 text-sm text-red-800">
              {tableError}
              <button
                onClick={() => loadAccounts()}
                className="ml-3 font-semibold underline"
              >
                Retry
              </button>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[1050px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label="Select all accounts on this page"
                      checked={allCurrentSelected}
                      onChange={toggleCurrentPage}
                    />
                  </th>
                  {[
                    ["name", "Account"],
                    ["company", "Company"],
                    ["country", "Country"],
                    ["plan", "Plan"],
                    ["status", "Status"],
                    ["current_month_minutes", "Minutes"],
                    ["current_month_sms", "SMS"],
                    ["cost_cents", "Cost"],
                    ["signup_date", "Signup date"],
                  ].map(([field, label]) => (
                    <th key={field} className="whitespace-nowrap px-4 py-3">
                      <button
                        onClick={() => handleSort(field)}
                        className="font-semibold hover:text-slate-900"
                      >
                        {label}
                        {filters.sort_by === field &&
                          (filters.sort_dir === "asc" ? " ↑" : " ↓")}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-16 text-center text-slate-500">
                      Loading accounts...
                    </td>
                  </tr>
                ) : accounts.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-16 text-center text-slate-500">
                      No accounts match your filters.
                    </td>
                  </tr>
                ) : (
                  accounts.map((account) => (
                    <tr key={account.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          aria-label={`Select ${account.name}`}
                          checked={selected.has(account.id)}
                          onChange={() => toggleSelection(account.id)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">{account.name}</p>
                        <p className="text-xs text-slate-500">{account.email}</p>
                      </td>
                      <td className="px-4 py-3">{account.company}</td>
                      <td className="px-4 py-3">{account.country}</td>
                      <td className="px-4 py-3 capitalize">{account.plan}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={account.status} />
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {account.current_month_minutes.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {account.current_month_sms.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatMoney(account.cost_cents)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {account.signup_date}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col justify-between gap-3 border-t border-slate-200 px-4 py-4 sm:flex-row sm:items-center">
            <p className="text-sm text-slate-500">
              Showing {accounts.length ? (filters.page - 1) * filters.page_size + 1 : 0}
              {"–"}
              {(filters.page - 1) * filters.page_size + accounts.length}
              {" of "}{total.toLocaleString()} accounts
            </p>

            <div className="flex items-center gap-2">
              <button
                disabled={filters.page <= 1 || loading}
                onClick={() => updateFilter("page", filters.page - 1)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm tabular-nums">
                Page {filters.page} / {totalPages}
              </span>
              <button
                disabled={filters.page >= totalPages || loading}
                onClick={() => updateFilter("page", filters.page + 1)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}
