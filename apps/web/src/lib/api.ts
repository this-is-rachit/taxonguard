// Typed client for the TaxonGuard API. The base URL is read from
// NEXT_PUBLIC_API_BASE_URL and defaults to the local API. These types mirror the
// FastAPI response models in services/api.

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DecisionAction = "confirm" | "reject" | "refine";

export interface TaxonSummary {
  taxon: string;
  cluster_count: number;
  flagged_records: number;
}

export interface DecisionState {
  action: DecisionAction;
  value: string | null;
  note: string | null;
  written_to_gbif: boolean;
}

export interface ClusterSummary {
  cluster_id: string;
  taxon: string;
  count: number;
  max_score: number;
  mean_score: number;
  reason_counts: Record<string, number>;
  explanation: string;
  decision: DecisionState | null;
}

export interface RecordOut {
  gbif_id: number | null;
  latitude: number;
  longitude: number;
  suspicion_score: number;
  confidence: number;
  reasons: string[];
}

export interface RuleOut {
  taxon: string;
  geometry: string;
  value: string;
  record_count: number;
}

export interface ClusterDetail extends ClusterSummary {
  records: RecordOut[];
  rule: RuleOut;
}

export interface DecisionRequest {
  action: DecisionAction;
  value?: string | null;
  note?: string | null;
}

export interface DecisionResponse {
  cluster_id: string;
  decision: DecisionState;
  status: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getTaxa(): Promise<TaxonSummary[]> {
  return request<TaxonSummary[]>("/taxa");
}

export function getClusters(taxon?: string): Promise<ClusterSummary[]> {
  const query = taxon ? `?taxon=${encodeURIComponent(taxon)}` : "";
  return request<ClusterSummary[]>(`/clusters${query}`);
}

export function getCluster(clusterId: string): Promise<ClusterDetail> {
  return request<ClusterDetail>(`/clusters/${encodeURIComponent(clusterId)}`);
}

export function postDecision(
  clusterId: string,
  body: DecisionRequest,
): Promise<DecisionResponse> {
  return request<DecisionResponse>(
    `/clusters/${encodeURIComponent(clusterId)}/decision`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export { ApiError };
