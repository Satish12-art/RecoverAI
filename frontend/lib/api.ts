import {
  HealthStatus,
  ConfigData,
  DashboardMetrics,
  RecoveryCaseItem,
  CaseDetailData,
  SimulationRunResult,
  FailureBreakdownData,
  AuditEventItem,
  EvaluationSummaryData,
} from "../types";

// If NEXT_PUBLIC_API_URL is provided, use it directly; otherwise use relative path (proxied by Next.js rewrites)
const getApiBase = () => {
  if (typeof window !== "undefined") {
    const publicUrl = process.env.NEXT_PUBLIC_API_URL;
    if (publicUrl) {
      return publicUrl.replace(/\/+$/, "").replace(/\/api$/, "");
    }
    return ""; // Relative URL in browser -> handled by Next.js rewrites proxy
  }
  const serverUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return serverUrl.replace(/\/+$/, "").replace(/\/api$/, "");
};

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}${url}`, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = "API request failed";
    try {
      const err = await res.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

// 1. Health & Config
export async function fetchHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>("/api/health");
}

export async function fetchConfig(): Promise<ConfigData> {
  return fetchJson<ConfigData>("/api/config");
}

// 2. Dashboard
export async function fetchDashboard(): Promise<DashboardMetrics> {
  return fetchJson<DashboardMetrics>("/api/dashboard");
}

// 3. Cases
export async function fetchCases(params: {
  page?: number;
  page_size?: number;
  status?: string;
  action?: string;
  failure_code?: string;
  search?: string;
  sort_by?: string;
} = {}): Promise<{
  items: RecoveryCaseItem[];
  total: number;
  page: number;
  page_size: number;
}> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", params.page.toString());
  if (params.page_size) q.set("page_size", params.page_size.toString());
  if (params.status) q.set("status", params.status);
  if (params.action) q.set("action", params.action);
  if (params.failure_code) q.set("failure_code", params.failure_code);
  if (params.search) q.set("search", params.search);
  if (params.sort_by) q.set("sort_by", params.sort_by);

  return fetchJson(`/api/cases?${q.toString()}`);
}

export async function fetchCaseDetail(caseId: number): Promise<CaseDetailData> {
  return fetchJson<CaseDetailData>(`/api/cases/${caseId}`);
}

export async function triggerAgentRecovery(caseId: number): Promise<any> {
  return fetchJson(`/api/agent/recover/${caseId}`, { method: "POST" });
}

// 4. Analytics
export async function fetchFailureBreakdown(): Promise<FailureBreakdownData> {
  return fetchJson<FailureBreakdownData>("/api/analytics/failure-breakdown");
}

// 5. Audit
export async function fetchAuditEvents(params: {
  page?: number;
  page_size?: number;
  tool_name?: string;
  policy_decision?: string;
  search?: string;
} = {}): Promise<{
  items: AuditEventItem[];
  total: number;
  page: number;
  page_size: number;
}> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", params.page.toString());
  if (params.page_size) q.set("page_size", params.page_size.toString());
  if (params.tool_name) q.set("tool_name", params.tool_name);
  if (params.policy_decision) q.set("policy_decision", params.policy_decision);
  if (params.search) q.set("search", params.search);

  return fetchJson(`/api/audit?${q.toString()}`);
}

// 6. Simulation
export async function runSimulation(payload: {
  limit?: number;
  seed?: number;
  all_payments?: boolean;
  mode?: string;
}): Promise<SimulationRunResult> {
  return fetchJson<SimulationRunResult>("/api/simulate/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resetSimulation(params: { seed?: number; initial_limit?: number } = {}): Promise<any> {
  const q = new URLSearchParams();
  if (params.seed) q.set("seed", params.seed.toString());
  if (params.initial_limit) q.set("initial_limit", params.initial_limit.toString());
  return fetchJson(`/api/simulate/reset?${q.toString()}`, {
    method: "POST",
  });
}

// 7. Evaluation
export async function fetchEvaluationSummary(): Promise<EvaluationSummaryData> {
  return fetchJson<EvaluationSummaryData>("/api/evaluation/summary");
}

export async function fetchConfusionMatrix(): Promise<any> {
  return fetchJson("/api/evaluation/confusion-matrix");
}

export async function fetchCalibration(): Promise<any> {
  return fetchJson("/api/evaluation/calibration");
}

export async function fetchRevenueComparison(): Promise<any> {
  return fetchJson("/api/evaluation/revenue-comparison");
}

export async function fetchRegret(): Promise<any> {
  return fetchJson("/api/evaluation/regret");
}

// 8. Razorpay Test Mode & Webhook Test Console
export async function fetchRazorpayStatus(): Promise<{
  configured: boolean;
  mode: string;
  webhook_ready: boolean;
  webhook_endpoint: string;
  last_event_at?: string;
  last_event_type?: string;
  last_processing_result?: string;
}> {
  return fetchJson("/api/webhooks/razorpay/status");
}

export async function triggerRazorpayTestWebhook(payload: {
  event_type: string;
  amount: number;
  failure_code: string;
  failure_reason: string;
  customer_email: string;
  customer_name: string;
}): Promise<any> {
  return fetchJson("/api/webhooks/razorpay/test-trigger", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
