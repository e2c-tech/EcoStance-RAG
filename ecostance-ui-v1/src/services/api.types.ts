// API Response Types

// Authentication Types
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  tenant_id: string;
}

export interface TokenVerifyResponse {
  valid: boolean;
  message: string;
  tenant_id: string;
  expires_at: string;
}

// Tenant Types
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
  billing_tier: string;
  billing_status: string;
  trial_ends_at?: string | null;
  settings?: Record<string, unknown>;
  logo_url?: string | null;
}

export interface TenantRegistrationData {
  name: string;
  email: string;
  phone?: string;
  billing_tier?: string;
}

// API Key Types
export interface APIKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  permissions: string[];
  last_used_at?: string | null;
  usage_count: number;
  is_active: boolean;
  expires_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface CreateAPIKeyResponse extends APIKey {
  api_key: string;
  message: string;
}

// File Types
export interface FileInfo {
  filename: string;
  size_bytes: number;
  size_mb: number;
  created_at: string;
  path: string;
}

export interface UploadFileResponse {
  message: string;
  file_path: string;
  tenant_id: string;
  filename: string;
  size_mb: number;
  storage_usage: {
    total_files: number;
    total_mb: number;
    quota_mb: number;
    usage_percent: number;
  };
}

export interface StorageUsage {
  total_files: number;
  total_bytes: number;
  total_mb: number;
  total_gb: number;
}

export interface QuotaCheckResponse {
  within_quota: boolean;
  quota_mb: number;
  current_usage_mb: number;
  available_mb: number;
  usage_percent: number;
}

// Document Processing Types
export interface ProcessingJob {
  job_id: string;
  file_path: string;
  collection_name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_message: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  error_message?: string | null;
}

export interface ProcessFileResponse {
  message: string;
  job_id: string;
  tenant_id: string;
  kb_name: string;
  collection_name: string;
  status_url: string;
}

// Knowledge Base Types
export interface KnowledgeBaseFile {
  filename: string;
  chunk_count: number;
  file_type: string;
  upload_date: number;
  file_size: string;
  total_characters: number;
}

export interface KnowledgeBaseDetails {
  name: string;
  collection_name: string;
  total_points: number;
  vectors_count: number;
  vector_size: number;
  files_count: number;
  files: KnowledgeBaseFile[];
}

// RAG Query Types
export interface RAGQueryResponse {
  answer: string;
  tenant_id: string;
  kb_name: string;
}

// Database Types
export interface DatabaseConnection {
  name: string;
  type: string;
  host: string;
  database: string;
  username: string;
}

export interface DatabaseConnectionFull extends DatabaseConnection {
  port: string;
  password: string;
  db_path?: string;
}

export interface ConnectDatabaseResponse {
  message: string;
  database_type: string;
  schema_loaded: boolean;
}

export interface GenerateQueryResponse {
  sql_query: string;
  explanation: string;
  safety_check: 'SAFE' | 'UNSAFE';
}

// Quota Types
export interface QuotaStatus {
  success: boolean;
  data: {
    storage: {
      limit_bytes: number;
      used_bytes: number;
      available_bytes: number;
      usage_percent: number;
    };
    queries: {
      daily_limit: number;
      daily_used: number;
      monthly_limit: number;
      monthly_used: number;
      daily_percent: number;
      monthly_percent: number;
    };
    documents: {
      limit: number;
      used: number;
      available: number;
      usage_percent: number;
    };
    connections: {
      max_connections: number;
      active_connections: number;
    };
    api_calls: {
      hourly_limit: number;
      hourly_used: number;
      minute_limit: number;
      minute_used: number;
    };
  };
}

export interface QuotaLimits {
  success: boolean;
  data: {
    max_storage_bytes: number;
    max_queries_per_day: number;
    max_queries_per_month: number;
    max_documents: number;
    max_db_connections: number;
    max_concurrent_queries: number;
    max_api_calls_per_minute: number;
    max_api_calls_per_hour: number;
  };
}

export interface QuotaUsage {
  success: boolean;
  period: string;
  data: {
    query_count: number;
    document_count: number;
    storage_bytes: number;
    api_calls_count: number;
    active_db_connections: number;
    concurrent_queries: number;
  };
}

export interface QuotaHistoryRecord {
  date: string;
  period_type: string;
  query_count: number;
  document_count: number;
  storage_bytes: number;
  storage_gb: number;
  api_calls: number;
}

// Usage Analytics Types
export interface UsageStats {
  total_requests: number;
  status_codes: Record<string, number>;
  avg_response_time_ms: number;
  error_count: number;
  error_rate_percent: number;
  top_endpoints: Array<{
    endpoint: string;
    count: number;
    avg_response_time_ms: number;
  }>;
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
}

export interface EndpointStats {
  endpoint: string;
  total_requests: number;
  response_times: {
    min_ms: number;
    max_ms: number;
    avg_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
}

// Metrics Types
export interface MetricRecord {
  period_start: string;
  storage: {
    bytes: number;
    mb: number;
    gb: number;
    document_count: number;
  };
  queries: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
    avg_response_time_ms: number;
  };
  api: {
    total_calls: number;
    successful_calls: number;
    failed_calls: number;
    success_rate: number;
    avg_response_time_ms: number;
  };
}

export interface TenantMetrics {
  success: boolean;
  metric_type: string;
  days: number;
  count: number;
  data: MetricRecord[];
}

export interface StorageMetricRecord {
  date: string;
  storage_bytes: number;
  storage_gb: number;
  document_count: number;
  file_count: number;
  growth_bytes: number;
  growth_percent: number;
}

export interface QueryMetrics {
  success: boolean;
  days: number;
  data: {
    total_queries: number;
    successful_queries: number;
    failed_queries: number;
    success_rate: number;
    response_times: {
      min_ms: number;
      max_ms: number;
      avg_ms: number;
      p50_ms: number;
      p95_ms: number;
      p99_ms: number;
    };
    by_knowledge_base: Array<{
      kb_name: string;
      query_count: number;
      avg_response_time_ms: number;
    }>;
  };
}

export interface ErrorMetrics {
  success: boolean;
  days: number;
  data: {
    total_requests: number;
    total_errors: number;
    error_rate: number;
    by_status_code: Record<string, number>;
    by_endpoint: Array<{
      endpoint: string;
      error_count: number;
      error_rate: number;
    }>;
    trend: Array<{
      date: string;
      error_count: number;
    }>;
  };
}

export interface Alert {
  id: string;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  threshold: number;
  current_value: number;
  created_at: string;
  acknowledged: boolean;
}

export interface AlertsResponse {
  success: boolean;
  count: number;
  data: Alert[];
}

// Admin Types
export interface SystemHealth {
  success: boolean;
  data: {
    tenants: {
      total: number;
      active: number;
      inactive: number;
    };
    storage: {
      total_bytes: number;
      total_gb: number;
    };
    api: {
      calls_24h: number;
      errors_24h: number;
      error_rate: number;
    };
    timestamp: string;
  };
}

export interface DashboardSummary {
  success: boolean;
  data: {
    total_tenants: number;
    active_tenants: number;
    total_users: number;
    total_storage_gb: number;
    total_queries_today: number;
    total_api_calls_today: number;
    system_health: 'healthy' | 'degraded' | 'critical';
    recent_alerts: Alert[];
    timestamp: string;
  };
}

export interface TenantSearchResult {
  success: boolean;
  data: {
    query: string;
    count: number;
    tenants: Tenant[];
  };
}

export interface TenantStorage {
  success: boolean;
  data: {
    total_files: number;
    total_bytes: number;
    total_gb: number;
    by_file_type: Record<string, number>;
    knowledge_bases: Array<{
      kb_name: string;
      file_count: number;
      vector_count: number;
      storage_bytes: number;
    }>;
  };
}

export interface TenantActivity {
  success: boolean;
  data: {
    tenant_id: string;
    period_days: number;
    summary: {
      total_api_calls: number;
      total_errors: number;
      error_rate: number;
    };
    recent_activity: Array<{
      endpoint: string;
      method: string;
      status_code: number;
      timestamp: string;
    }>;
  };
}

// AI Agent Beta Types
export interface AgentChatRequest {
  message: string;
  session_id?: string;
}

export interface AgentChatResponse {
  response: any;
  agent_type?: string;
  session_id: string;
  timestamp: string;
}

export interface AgentHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface AgentHistoryResponse {
  session_id: string;
  messages: AgentHistoryMessage[];
  message_count: number;
}

export interface AgentSession {
  session_id: string;
  last_message?: string;
  updated_at: string;
  created_at: string;
}

export interface AgentResetResponse {
  message: string;
  session_id: string;
}

// Generic API Response
export interface APIResponse<T = unknown> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

// Error Response
export interface APIError {
  detail: string | Record<string, unknown>;
  error?: string;
  message?: string;
  code?: string;
  details?: Record<string, unknown>;
}
