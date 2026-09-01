export interface HealthStatus {
  status: string;
  version: string;
  mode: string;
  demo_mode: boolean;
}

export interface ConfigData {
  recovery_mode: string;
  demo_mode: boolean;
  version: string;
  recovery_probability_threshold: number;
  scorer_confidence_threshold: number;
  auto_recovery_amount_limit: number;
  max_retries: number;
}

export interface DashboardMetrics {
  gross_revenue_at_risk: number;
  potentially_recoverable_revenue: number;
  revenue_recovered: number;
  recovery_rate: number;
  total_expected_recovery_value: number;
  cases_processed: number;
  mode: string;
  last_updated?: string;
}

export interface RecoveryCaseItem {
  id: number;
  payment_id: number;
  external_payment_id: string;
  customer_id: number;
  customer_name: string;
  amount_at_risk: number;
  currency: string;
  failure_code?: string;
  recovery_probability?: number;
  scorer_confidence?: number;
  expected_recovery_value?: number;
  recommended_action?: string;
  actual_action?: string;
  status: string;
  outcome_status?: string;
  amount_recovered: number;
  created_at?: string;
  updated_at?: string;
}

export interface CaseDetailData {
  case: {
    id: number;
    payment_id: number;
    customer_id: number;
    amount_at_risk: number;
    expected_recovery_value: number;
    diagnosis?: string;
    recoverability?: string;
    recovery_probability?: number;
    scorer_confidence?: number;
    recommended_action?: string;
    actual_action?: string;
    status: string;
    escalation_reason?: string;
    retry_count: number;
    created_at?: string;
    updated_at?: string;
  };
  payment: {
    id: number;
    external_payment_id: string;
    amount: number;
    currency: string;
    status: string;
    payment_method: string;
    failure_code?: string;
    failure_reason?: string;
    risk_flagged: boolean;
    created_at?: string;
  };
  customer: {
    id: number;
    external_customer_id: string;
    name: string;
    email?: string;
    total_orders: number;
    successful_payments: number;
    failed_payments: number;
    refund_count: number;
    chargeback_count: number;
    customer_tenure_days: number;
    opted_out: boolean;
  };
  scoring_factors?: {
    recovery_probability: number;
    confidence: number;
    expected_recovery_value: number;
    factors: {
      factor_name: string;
      weight: number;
      value: number;
      impact: string;
      description: string;
    }[];
  };
  actions: {
    id: number;
    action_type: string;
    tool_name: string;
    reasoning_summary: string;
    policy_decision: string;
    policy_reason: string;
    created_at?: string;
  }[];
  outcomes: {
    id: number;
    action: string;
    outcome_status: string;
    successful?: boolean;
    amount_recovered: number;
    failure_reason?: string;
    outcome_source?: string;
    outcome_observed_at?: string;
  }[];
}

export interface SimulationRunResult {
  simulation_id: string;
  seed: number;
  mode: string;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  payments_processed: number;
  eligible_count: number;
  stopped_count: number;
  escalated_count: number;
  actions_executed: number;
  outcomes_observed: number;
  recovered_cases: number;
  failed_cases: number;
  batch_revenue_recovered?: number;
  batch_recovery_rate?: number;
  batch_gross_revenue_at_risk?: number;
  cumulative_revenue_recovered?: number;
  gross_revenue_at_risk: number;
  potentially_recoverable_revenue: number;
  expected_recovery_value: number;
  revenue_recovered: number;
  recovery_rate: number;
  ai_recommendations: Record<string, number>;
  policy_decisions: Record<string, number>;
}

export interface FailureBreakdownData {
  total_failures: number;
  count_by_code: Record<string, number>;
  amount_by_code: Record<string, number>;
}

export interface AuditEventItem {
  id: number;
  recovery_case_id?: number;
  external_payment_id?: string;
  payment_amount?: number;
  action_type: string;
  tool_name: string;
  reasoning_summary: string;
  policy_decision: string;
  policy_reason: string;
  created_at?: string;
  actor: string;
}

export interface EvaluationSummaryData {
  evaluation_id: string;
  seed: number;
  cases_evaluated: number;
  recoverai_action_metrics: {
    confusion_matrix_raw: Record<string, Record<string, number>>;
    confusion_matrix_normalized: Record<string, Record<string, number>>;
    per_action: Record<string, {
      precision: number;
      recall: number;
      f1_score: number;
      support: number;
    }>;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
    weighted_f1: number;
    overall_accuracy: number;
  };
  baseline_action_metrics: {
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
    weighted_f1: number;
    overall_accuracy: number;
  };
  recoverability_metrics: {
    true_positives: number;
    false_positives: number;
    true_negatives: number;
    false_negatives: number;
    precision: number;
    recall: number;
    f1_score: number;
    accuracy: number;
  };
  calibration: {
    bins: {
      bin_range: string;
      case_count: number;
      avg_predicted_probability: number;
      actual_recovery_rate: number;
      calibration_error: number;
    }[];
    brier_score: number;
    expected_calibration_error: number;
    total_evaluated: number;
  };
  regret: {
    total_regret: number;
    average_regret: number;
    median_regret: number;
    p95_regret: number;
    total_cases_evaluated: number;
    zero_regret_case_count: number;
    zero_regret_rate: number;
  };
  revenue: {
    recoverai_revenue: number;
    baseline_revenue: number;
    ground_truth_revenue: number;
    absolute_uplift: number;
    percentage_uplift: number;
    ground_truth_revenue_capture_rate: number;
  };
  safety: {
    policy_violations: number;
    risk_violations: number;
    opt_out_violations: number;
    amount_limit_violations: number;
    retry_limit_violations: number;
    fabricated_outcomes: number;
    unauthorized_tool_calls: number;
    all_safety_checks_passed: boolean;
  };
  efficiency: {
    total_payments_evaluated: number;
    average_llm_calls_per_case: number;
    median_llm_calls: number;
    max_llm_calls: number;
    average_agent_steps_per_case: number;
    average_runtime_ms_per_case: number;
    total_runtime_seconds: number;
  };
}
