export interface QueryOptions {
  enable_graph_expansion: boolean;
  max_hops: number;
  similarity_threshold: number;
  filters?: Record<string, string[]>;
}

export interface ResultMetadata {
  source_file?: string;
  entity_name?: string;
  chunk_type?: string;
  line_start?: number;
  line_end?: number;
  language?: string;
  version?: string;
}

export interface GraphContext {
  entity?: string;
  file?: string;
  relationship?: string;
  hop?: number;
}

export interface QueryResult {
  chunk_id: string;
  content: string;
  relevance_score: number;
  score_breakdown: {
    vector_score: number;
    graph_score: number;
  };
  metadata: ResultMetadata;
  graph_context: GraphContext[];
}

export interface QueryResponse {
  query: string;
  results: QueryResult[];
  total_results: number;
  retrieval_method: string;
  status?: string | null;
  message?: string | null;
}

export interface HealthResponse {
  status: string;
  services: Record<string, unknown>;
  timestamp: string;
}

export interface IngestStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  files_processed: number;
  files_failed: number;
  chunks_created: number;
  nodes_created: number;
}

export interface ToolCall {
  name: string;
  status: "SUCCESS" | "ERROR";
  input: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  loading?: boolean;
  toolCall?: ToolCall;
  results?: QueryResult[];
}
