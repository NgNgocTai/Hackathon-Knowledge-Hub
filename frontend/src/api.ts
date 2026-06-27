import type { HealthResponse, IngestStatus, QueryOptions, QueryResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-secret-key";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function queryCodebase(query: string, topK: number, options: QueryOptions): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({
      query,
      top_k: topK,
      options,
    }),
  });
}

export function startIngest(path: string): Promise<{ job_id: string }> {
  return request<{ job_id: string }>("/ingest", {
    method: "POST",
    body: JSON.stringify({
      sources: [
        {
          type: "directory",
          path,
          include_patterns: ["*.py", "*.md"],
          exclude_patterns: ["__pycache__/*", "*.pyc"],
        },
      ],
    }),
  });
}

export function ingestStatus(jobId: string): Promise<IngestStatus> {
  return request<IngestStatus>(`/ingest/${jobId}`);
}
