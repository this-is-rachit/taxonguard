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
  annotation_id?: number | null;
  annotation_url?: string | null;
  manual_instructions?: string | null;
}

export interface ClusterSummary {
  cluster_id: string;
  taxon: string;
  count: number;
  max_score: number;
  mean_score: number;
  latitude: number;
  longitude: number;
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

export interface CleanIssue {
  label: string;
  count: number;
}

export interface CleanRecord {
  gbif_id: number | null;
  scientific_name: string | null;
  latitude: number;
  longitude: number;
  flagged: boolean;
  suspicion_score: number;
  confidence: number;
  reasons: string[];
}

export interface CleanSummary {
  total_records: number;
  flagged_records: number;
  clean_records: number;
  taxa: number;
  checks_run: string[];
  issues: CleanIssue[];
}

export interface CleanReport {
  clean_id: string;
  summary: CleanSummary;
  flagged: CleanRecord[];
  flagged_truncated: boolean;
  download_url: string;
}

export interface SpeciesSuggestion {
  key: number;
  name: string;
  rank: string | null;
  kingdom: string | null;
}

export interface SpeciesScoreReport {
  taxon: string;
  summary: CleanSummary;
  records: CleanRecord[];
  records_truncated: boolean;
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

// Upload an occurrence file to be checked by the engine. FormData sets its own
// multipart Content-Type (with the boundary), so this does not reuse the JSON
// request helper. A 400 carries a plain reason in the response detail.
export async function postCleanUpload(file: File): Promise<CleanReport> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/clean`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data?.detail) detail = data.detail;
    } catch {
      // Keep the default message if the error body is not JSON.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as CleanReport;
}

// Build an absolute URL for the cleaned-CSV download from the path the report
// returns, so a plain anchor can link to it.
export function cleanDownloadUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

// Autocomplete scientific names for the search box (proxies GBIF's suggest API).
export function suggestSpecies(query: string): Promise<SpeciesSuggestion[]> {
  return request<SpeciesSuggestion[]>(
    `/species/suggest?q=${encodeURIComponent(query)}`,
  );
}

// Fetch and score a species on demand. The first call for a species runs the
// engine and can take a few seconds; the API caches the result after that.
export function scoreTaxon(taxon: string): Promise<SpeciesScoreReport> {
  return request<SpeciesScoreReport>(
    `/score?taxon=${encodeURIComponent(taxon)}`,
  );
}

export { ApiError };
