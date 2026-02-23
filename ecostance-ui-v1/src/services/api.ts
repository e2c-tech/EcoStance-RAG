// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Token configuration
const TOKEN_EXPIRY_KEY = 'token_expiry';

// Token management in memory (initialized from localStorage for persistence)
let accessToken: string | null = localStorage.getItem('access_token');
let tokenExpiryTime: number | null = null;

// Get token from memory
export const getAccessToken = (): string | null => {
  return accessToken;
};

// Set token in memory and local storage
export const setAccessToken = (token: string | null, expiresIn?: number): void => {
  accessToken = token;

  if (token) {
    localStorage.setItem('access_token', token);
    if (expiresIn) {
      // Calculate expiry time (current time + expiresIn seconds)
      tokenExpiryTime = Date.now() + expiresIn * 1000;
      // Store expiry in sessionStorage for persistence across page reloads
      sessionStorage.setItem(TOKEN_EXPIRY_KEY, tokenExpiryTime.toString());
    }
  } else {
    tokenExpiryTime = null;
    localStorage.removeItem('access_token');
    sessionStorage.removeItem(TOKEN_EXPIRY_KEY);
  }
};

// Check if token is expired or about to expire
export const isTokenExpired = (): boolean => {
  if (!tokenExpiryTime) {
    const storedExpiry = sessionStorage.getItem(TOKEN_EXPIRY_KEY);
    if (storedExpiry) {
      tokenExpiryTime = parseInt(storedExpiry, 10);
    } else {
      return true;
    }
  }

  // Consider token expired if less than 5 minutes remaining
  const bufferTime = 5 * 60 * 1000; // 5 minutes in milliseconds
  return Date.now() >= (tokenExpiryTime - bufferTime);
};

// Get time until token expires (in seconds)
export const getTimeUntilExpiry = (): number => {
  if (!tokenExpiryTime) {
    const storedExpiry = sessionStorage.getItem(TOKEN_EXPIRY_KEY);
    if (storedExpiry) {
      tokenExpiryTime = parseInt(storedExpiry, 10);
    } else {
      return 0;
    }
  }

  const timeRemaining = tokenExpiryTime - Date.now();
  return Math.max(0, Math.floor(timeRemaining / 1000));
};

// Clear all tokens
export const clearTokens = (): void => {
  accessToken = null;
  tokenExpiryTime = null;
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  sessionStorage.removeItem(TOKEN_EXPIRY_KEY);
};

// Fetch wrapper with automatic token injection
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  console.log('🚀 fetchWithAuth:', url, options.method || 'GET');
  // Check for trial expiration from stored user data
  const storedUser = localStorage.getItem('user');
  if (storedUser && !url.includes('/auth/') && !url.includes('/tenants/me') && !url.includes('/superadmin/')) {
    try {
      const user = JSON.parse(storedUser);
      if (user.billingTier === 'free' && user.trialEndsAt) {
        if (new Date(user.trialEndsAt).getTime() <= Date.now()) {
          throw new Error('Trial expired');
        }
      }
    } catch (e) {
      // Ignore parse errors or date errors
    }
  }

  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (token) {
    console.log('🔑 Sending request with token:', token.substring(0, 20) + '...');
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  console.log('📡 Making request to:', url);
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: 'include', // Important for httpOnly cookies
  });

  console.log('📥 Response status:', response.status, response.statusText);

  // Handle 401 Unauthorized - attempt token refresh
  if (response.status === 401 && !url.includes('/auth/refresh')) {
    try {
      // Attempt to refresh the token
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        const { access_token, expires_in } = data;
        setAccessToken(access_token, expires_in);

        // Retry the original request with new token
        headers.set('Authorization', `Bearer ${access_token}`);
        return fetch(`${API_BASE_URL}${url}`, {
          ...options,
          headers,
          credentials: 'include',
        });
      } else {
        // Refresh failed, clear tokens and redirect to login
        clearTokens();
        // Redirect to appropriate login page
        const isSuperAdminPath = window.location.pathname.startsWith('/admin');
        window.location.href = isSuperAdminPath ? '/admin/login' : '/login';
        throw new Error('Session expired');
      }
    } catch (error) {
      clearTokens();
      const isSuperAdminPath = window.location.pathname.startsWith('/admin');
      window.location.href = isSuperAdminPath ? '/admin/login' : '/login';
      throw error;
    }
  }

  return response;
}

// Helper to handle JSON responses
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || error.message || 'Request failed');
  }

  // Handle 204 No Content explicitly
  if (response.status === 204) {
    return {} as T;
  }

  const text = await response.text();
  try {
    return text ? JSON.parse(text) : ({} as T);
  } catch (e) {
    console.warn('Failed to parse JSON response:', e);
    return {} as T;
  }
}

// API Service Methods
export const authAPI = {
  login: async (email: string, password: string) => {
    // Don't use fetchWithAuth for login - use direct fetch to avoid auth loops
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        email,
        password,
      }),
    });
    return handleResponse(response);
  },

  refresh: async () => {
    const response = await fetchWithAuth('/auth/refresh', {
      method: 'POST',
    });
    return handleResponse(response);
  },

  verify: async () => {
    const response = await fetchWithAuth('/auth/verify');
    return handleResponse(response);
  },

  logout: async () => {
    const response = await fetchWithAuth('/auth/logout', {
      method: 'POST',
    });
    clearTokens();
    return handleResponse(response);
  },

  setPassword: async (token: string, password: string) => {
    const response = await fetchWithAuth('/auth/set-password', {
      method: 'POST',
      body: JSON.stringify({ token, password }),
    });
    return handleResponse(response);
  },
};

export const tenantUsersAPI = {
  list: async () => {
    const response = await fetchWithAuth('/tenant/users');
    return handleResponse(response);
  },

  invite: async (data: { email: string; full_name?: string; role_id: string }) => {
    const response = await fetchWithAuth('/tenant/users/invite', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  inviteBulk: async (data: { emails: string[]; role_id: string }) => {
    const response = await fetchWithAuth('/tenant/users/invite-bulk', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  update: async (userId: string, data: { full_name?: string; role_id?: string; is_active?: boolean }) => {
    const response = await fetchWithAuth(`/tenant/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  remove: async (userId: string) => {
    const response = await fetchWithAuth(`/tenant/users/${userId}`, {
      method: 'DELETE',
    });
    if (response.status === 204) {
      return;
    }
    return handleResponse(response);
  },
};

export const tenantRolesAPI = {
  list: async () => {
    const response = await fetchWithAuth('/tenant/roles');
    return handleResponse(response);
  },

  create: async (data: { name: string; permissions: string[] }) => {
    const response = await fetchWithAuth('/tenant/roles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },
};

export const tenantsAPI = {
  register: async (data: {
    name: string;
    company?: string;
    email: string;
    phone?: string;
    billing_tier: string;
    password: string;
  }) => {
    const response = await fetchWithAuth('/tenants/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  getCurrentTenant: async () => {
    const response = await fetchWithAuth('/tenants/me');
    return handleResponse(response);
  },

  listTenants: async (skip = 0, limit = 100) => {
    const response = await fetchWithAuth(`/tenants/?skip=${skip}&limit=${limit}`);
    return handleResponse(response);
  },

  getTenant: async (tenantId: string) => {
    const response = await fetchWithAuth(`/tenants/${tenantId}`);
    return handleResponse(response);
  },

  updateTenant: async (tenantId: string, data: Record<string, unknown>) => {
    const response = await fetchWithAuth(`/tenants/${tenantId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  deleteTenant: async (tenantId: string, hardDelete = false) => {
    const response = await fetchWithAuth(`/tenants/${tenantId}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  activateTenant: async (tenantId: string) => {
    const response = await fetchWithAuth(`/tenants/${tenantId}/activate`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  deactivateTenant: async (tenantId: string) => {
    const response = await fetchWithAuth(`/tenants/${tenantId}/deactivate`, {
      method: 'POST',
    });
    return handleResponse(response);
  },
};

export const databaseAPI = {
  uploadSQLite: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetchWithAuth('/db/upload-sqlite', {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  connect: async (dbUri: string) => {
    const response = await fetchWithAuth('/db/connect', {
      method: 'POST',
      body: JSON.stringify({ db_uri: dbUri }),
    });
    return handleResponse(response);
  },

  generateQuery: async (question: string) => {
    const response = await fetchWithAuth('/db/generate-query', {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
    return handleResponse(response);
  },

  executeQuery: async (query: string) => {
    const response = await fetchWithAuth('/db/execute-query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
    return handleResponse(response);
  },

  saveConnection: async (data: {
    name: string;
    db_type: string;
    host?: string;
    port?: string;
    username?: string;
    password?: string;
    database?: string;
    db_path?: string;
  }) => {
    const response = await fetchWithAuth('/db/connections/save', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  listConnections: async () => {
    const response = await fetchWithAuth('/db/connections/list');
    return handleResponse(response);
  },

  loadConnection: async (name: string) => {
    const response = await fetchWithAuth(`/db/connections/${name}`);
    return handleResponse(response);
  },

  deleteConnection: async (name: string) => {
    const response = await fetchWithAuth(`/db/connections/${name}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  getSchema: async () => {
    const response = await fetchWithAuth('/db/schema');
    return handleResponse(response);
  },
};

export const quotaAPI = {
  getStatus: async () => {
    const response = await fetchWithAuth('/quota/status');
    return handleResponse(response);
  },

  getLimits: async () => {
    const response = await fetchWithAuth('/quota/limits');
    return handleResponse(response);
  },

  getUsage: async (period = 'daily') => {
    const response = await fetchWithAuth(`/quota/usage?period=${period}`);
    return handleResponse(response);
  },

  getHistory: async (days = 30) => {
    const response = await fetchWithAuth(`/quota/history?days=${days}`);
    return handleResponse(response);
  },
};

export const metricsAPI = {
  getTenantMetrics: async (metricType = 'daily', days = 30) => {
    const response = await fetchWithAuth(`/metrics/?metric_type=${metricType}&days=${days}`);
    return handleResponse(response);
  },

  getAllTenantMetrics: async (metricType = 'daily', limit = 100) => {
    const response = await fetchWithAuth(`/metrics/admin/all?metric_type=${metricType}&limit=${limit}`);
    return handleResponse(response);
  },
};

export const apiKeysAPI = {
  create: async (data: { name: string; expires_in_days?: number; permissions?: string[] }) => {
    const response = await fetchWithAuth('/api-keys/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  list: async () => {
    const response = await fetchWithAuth('/api-keys/');
    return handleResponse(response);
  },

  revoke: async (keyId: string) => {
    const response = await fetchWithAuth(`/api-keys/${keyId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  rotate: async (keyId: string, newKeyName?: string) => {
    const response = await fetchWithAuth(`/api-keys/${keyId}/rotate`, {
      method: 'POST',
      body: JSON.stringify({ new_key_name: newKeyName }),
    });
    return handleResponse(response);
  },
};

// Memory cache for knowledge base data
const kbCache = {
  list: null as any,
  details: {} as Record<string, any>,
  lastFetchedList: 0,
};

const KB_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

const clearKBCache = (kbName?: string) => {
  kbCache.list = null;
  if (kbName) {
    delete kbCache.details[kbName];
  } else {
    kbCache.details = {};
  }
};

// File Upload & Management API
export const filesAPI = {
  upload: async (file: File, processNow = false, kbName = 'default') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('process_now', String(processNow));
    formData.append('kb_name', kbName);

    const response = await fetchWithAuth('/upload/', {
      method: 'POST',
      body: formData,
    });

    const result = await handleResponse(response);
    // Invalidate cache if uploaded to a KB
    if (kbName) {
      clearKBCache(kbName);
    }
    return result;
  },

  list: async () => {
    const response = await fetchWithAuth('/files/');
    return handleResponse(response);
  },

  download: async (filename: string) => {
    const response = await fetchWithAuth(`/files/${filename}`);
    return response.blob();
  },

  delete: async (filename: string) => {
    const response = await fetchWithAuth(`/files/${filename}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  getStorageUsage: async () => {
    const response = await fetchWithAuth('/files/storage/usage');
    return handleResponse(response);
  },

  checkQuota: async (fileSizeMb: number) => {
    const formData = new FormData();
    formData.append('file_size_mb', fileSizeMb.toString());

    const response = await fetchWithAuth('/files/storage/check-quota', {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  deleteAll: async () => {
    const response = await fetchWithAuth('/files/', {
      method: 'DELETE',
    });
    return handleResponse(response);
  },
};

// Document Processing API
export const documentProcessingAPI = {
  processToKnowledgeBase: async (filePath: string, kbName = 'default') => {
    const formData = new FormData();
    formData.append('file_path', filePath);
    formData.append('kb_name', kbName);

    const response = await fetchWithAuth('/upload-to-qdrant/', {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  getProcessingStatus: async (jobId: string) => {
    const response = await fetchWithAuth(`/processing-status/${jobId}`);
    return handleResponse(response);
  },

  listJobs: async () => {
    const response = await fetchWithAuth('/jobs/');
    return handleResponse(response);
  },
};


// Knowledge Base Management API
export const knowledgeBaseAPI = {
  list: async (forceRefresh = false) => {
    const now = Date.now();
    if (!forceRefresh && kbCache.list && (now - kbCache.lastFetchedList < KB_CACHE_TTL)) {
      console.log('API: Returning cached knowledge base list');
      return kbCache.list;
    }

    console.log('API: Fetching knowledge bases from /manage/knowledge-bases/', forceRefresh ? '(forced)' : '');
    const response = await fetchWithAuth('/manage/knowledge-bases/');
    const data = await handleResponse(response);

    kbCache.list = data;
    kbCache.lastFetchedList = now;
    return data;
  },

  getDetails: async (kbName: string, forceRefresh = false) => {
    const now = Date.now();
    const cachedItem = kbCache.details[kbName];

    if (!forceRefresh && cachedItem && (now - cachedItem.timestamp < KB_CACHE_TTL)) {
      console.log(`API: Returning cached details for ${kbName}`);
      return cachedItem.data;
    }

    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}/details`);
    const data = await handleResponse(response);

    kbCache.details[kbName] = {
      data,
      timestamp: now
    };
    return data;
  },

  getFiles: async (kbName: string) => {
    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}/files`);
    return handleResponse(response);
  },

  deleteFile: async (kbName: string, filename: string) => {
    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}/files/${filename}`, {
      method: 'DELETE',
    });
    // Invalidate details cache when a file is deleted as document count changes
    clearKBCache(kbName);
    return handleResponse(response);
  },

  delete: async (kbName: string) => {
    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}`, {
      method: 'DELETE',
    });
    // Invalidate list cache
    clearKBCache(kbName);
    return handleResponse(response);
  },

  reindexFile: async (kbName: string, filename: string) => {
    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}/files/${filename}/reindex`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  // Create a new knowledge base
  create: async (kbName: string) => {
    const response = await fetchWithAuth('/manage/knowledge-bases/', {
      method: 'POST',
      body: JSON.stringify({ kb_name: kbName }),
    });
    // Invalidate list cache
    kbCache.list = null;
    return handleResponse(response);
  },

  // Get detailed file information
  getFileDetails: async (kbName: string, filename: string) => {
    const encodedFilename = encodeURIComponent(filename);
    const response = await fetchWithAuth(`/manage/knowledge-bases/${kbName}/files/${encodedFilename}/details`);
    return handleResponse(response);
  },
};

// RAG Query API
export const ragQueryAPI = {
  query: async (kbName: string, query: string, chatHistory?: string[]) => {
    const body = {
      kb_name: kbName,
      query: query,
      chat_history: chatHistory || []
    };

    const response = await fetchWithAuth('/query/', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return handleResponse(response);
  },
};

// Usage Analytics API
export const usageAPI = {
  getStats: async (days = 7) => {
    const response = await fetchWithAuth(`/usage/stats?days=${days}`);
    return handleResponse(response);
  },

  getEndpointStats: async (endpoint: string, days = 7) => {
    const response = await fetchWithAuth(`/usage/endpoint/${encodeURIComponent(endpoint)}?days=${days}`);
    return handleResponse(response);
  },

  exportData: async (days = 30) => {
    const response = await fetchWithAuth(`/usage/export?days=${days}`);
    return handleResponse(response);
  },
};

// Extended Metrics API
export const extendedMetricsAPI = {
  getStorageMetrics: async (days = 30) => {
    const response = await fetchWithAuth(`/metrics/storage?days=${days}`);
    return handleResponse(response);
  },

  getQueryMetrics: async (days = 7) => {
    const response = await fetchWithAuth(`/metrics/queries?days=${days}`);
    return handleResponse(response);
  },

  getErrorMetrics: async (days = 7) => {
    const response = await fetchWithAuth(`/metrics/errors?days=${days}`);
    return handleResponse(response);
  },

  getActiveAlerts: async () => {
    const response = await fetchWithAuth('/metrics/alerts');
    return handleResponse(response);
  },

  getAlertHistory: async (days = 7, severity?: string) => {
    const url = severity
      ? `/metrics/alerts/history?days=${days}&severity=${severity}`
      : `/metrics/alerts/history?days=${days}`;
    const response = await fetchWithAuth(url);
    return handleResponse(response);
  },

  exportMetrics: async (format = 'csv', days = 30) => {
    const response = await fetchWithAuth(`/metrics/export?format=${format}&days=${days}`);
    if (format === 'csv') {
      return response.blob();
    }
    return handleResponse(response);
  },

  triggerAggregation: async (period = 'hourly') => {
    const response = await fetchWithAuth(`/metrics/admin/aggregate?period=${period}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },
};

// Extended Quota API
export const extendedQuotaAPI = {
  updateTenantQuotas: async (tenantId: string, quotas: {
    max_queries_per_day?: number;
    max_queries_per_month?: number;
    max_documents?: number;
    max_storage_bytes?: number;
    max_db_connections?: number;
    max_concurrent_queries?: number;
    max_api_calls_per_minute?: number;
    max_api_calls_per_hour?: number;
  }) => {
    const response = await fetchWithAuth(`/quota/admin/tenant/${tenantId}`, {
      method: 'PUT',
      body: JSON.stringify(quotas),
    });
    return handleResponse(response);
  },

  resetTenantQuotas: async (tenantId: string, period = 'daily') => {
    const response = await fetchWithAuth(`/quota/admin/tenant/${tenantId}/reset?period=${period}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },
};

// Admin Operations API
export const adminAPI = {
  deleteTenant: async (tenantId: string, softDelete = true, confirm = true) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}`, {
      method: 'DELETE',
      body: JSON.stringify({ soft_delete: softDelete, confirm }),
    });
    return handleResponse(response);
  },

  exportTenantData: async (tenantId: string, exportPath?: string) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}/export`, {
      method: 'POST',
      body: JSON.stringify({ export_path: exportPath }),
    });
    return handleResponse(response);
  },

  getTenantStorage: async (tenantId: string) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}/storage`);
    return handleResponse(response);
  },

  cleanupSessions: async (maxAgeHours = 24) => {
    const response = await fetchWithAuth(`/admin/cleanup/sessions?max_age_hours=${maxAgeHours}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  cleanupTempFiles: async (maxAgeDays = 7) => {
    const response = await fetchWithAuth(`/admin/cleanup/temp-files?max_age_days=${maxAgeDays}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  archiveAuditLogs: async (maxAgeDays = 90) => {
    const response = await fetchWithAuth(`/admin/cleanup/audit-logs?max_age_days=${maxAgeDays}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  runDailyCleanup: async () => {
    const response = await fetchWithAuth('/admin/cleanup/all', {
      method: 'POST',
    });
    return handleResponse(response);
  },

  getSystemHealth: async () => {
    const response = await fetchWithAuth('/admin/health/system');
    return handleResponse(response);
  },

  getDashboardSummary: async () => {
    const response = await fetchWithAuth('/admin/dashboard/summary');
    return handleResponse(response);
  },

  searchTenants: async (query: string, limit = 20) => {
    const response = await fetchWithAuth(`/admin/tenants/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    return handleResponse(response);
  },

  suspendTenant: async (tenantId: string, reason: string) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}/suspend`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
    return handleResponse(response);
  },

  reactivateTenant: async (tenantId: string) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}/reactivate`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  getTenantActivity: async (tenantId: string, days = 7) => {
    const response = await fetchWithAuth(`/admin/tenants/${tenantId}/activity?days=${days}`);
    return handleResponse(response);
  },
};

export const billingAPI = {
  createCheckout: async (planId: string, currency: 'USD' | 'INR' = 'USD') => {
    // Backend expects plan_id and currency in the query string based on the 422 error
    const params = new URLSearchParams({ plan_id: planId, currency });
    const response = await fetchWithAuth(`/billing/checkout?${params.toString()}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },
};

// AI Agent Beta API
export const agentAPI = {
  chat: async (
    message: string,
    sessionId?: string,
    knowledgeBase?: string,
    databaseConnection?: string,
    agentType?: string
  ) => {
    const body: any = {
      message,
    };

    if (sessionId) body.session_id = sessionId;
    if (agentType) body.agent_type = agentType;
    if (knowledgeBase) {
      body.knowledge_base = knowledgeBase;
      body.kb_name = knowledgeBase; // Added for compatibility
      body.knowledge_bases = [knowledgeBase]; // Added for plural compatibility
    }
    if (databaseConnection) body.database_connection = databaseConnection;

    const response = await fetchWithAuth('/beta/agent/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return handleResponse(response);
  },

  getConfig: async () => {
    const response = await fetchWithAuth('/beta/agent/config');
    return handleResponse(response);
  },

  getHistory: async (sessionId: string) => {
    const response = await fetchWithAuth(`/beta/agent/history/${sessionId}`);
    return handleResponse(response);
  },

  reset: async (sessionId: string) => {
    const response = await fetchWithAuth(`/beta/agent/reset/${sessionId}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  listSessions: async () => {
    const response = await fetchWithAuth('/beta/agent/sessions');
    return handleResponse(response);
  },

  deleteSession: async (sessionId: string) => {
    const response = await fetchWithAuth(`/beta/agent/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },
};

// Custom CRM Integration API
export const customCrmAPI = {
  sync: async () => {
    const response = await fetchWithAuth('/custom-crm/sync', {
      method: 'POST',
    });
    return handleResponse(response);
  },

  getEmails: async (limit = 100) => {
    const response = await fetchWithAuth(`/custom-crm/emails?limit=${limit}`);
    return handleResponse(response);
  },
};

// Public Chat API
export const publicChatAPI = {
  // Public endpoints (no auth required)
  getConfig: async () => {
    console.log('[publicChatAPI.getConfig] Fetching from:', `${API_BASE_URL}/public-chat/config`);
    const response = await fetch(`${API_BASE_URL}/public-chat/config`);
    console.log('[publicChatAPI.getConfig] Response status:', response.status, response.statusText);
    const data = await handleResponse<any>(response);
    console.log('[publicChatAPI.getConfig] Raw data from backend:', JSON.stringify(data, null, 2));
    // Backend returns { success, message, config }, extract the config
    const config = data.config || data;
    console.log('[publicChatAPI.getConfig] Extracted config:', JSON.stringify(config, null, 2));
    return config;
  },

  query: async (data: {
    session_id: string;
    query: string;
    conversation_history?: Array<{ role: string; content: string }>;
  }) => {
    const response = await fetch(`${API_BASE_URL}/public-chat/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  submitFeedback: async (data: {
    session_id: string;
    message_id: string;
    feedback_type: 'positive' | 'negative';
    comment?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/public-chat/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  // Admin endpoints (auth required)
  admin: {
    getConfig: async () => {
      const response = await fetchWithAuth('/admin/public-chat/config');
      const data = await handleResponse<any>(response);
      // Backend returns { success, message, config }, extract the config
      return data.config || data;
    },

    updateConfig: async (config: {
      enabled: boolean;
      allowed_kbs: string[];
      welcome_message?: string;
      suggested_questions?: string[];
      branding?: {
        logo_url?: string;
        primary_color?: string;
        company_name?: string;
      };
      rate_limit?: {
        queries_per_minute?: number;
        max_messages_per_session?: number;
      };
      features?: {
        show_sources?: boolean;
        allow_feedback?: boolean;
        show_suggested_questions?: boolean;
      };
    }) => {
      const response = await fetchWithAuth('/admin/public-chat/config', {
        method: 'PUT',
        body: JSON.stringify(config),
      });
      return handleResponse(response);
    },

    getAvailableKBs: async () => {
      const response = await fetchWithAuth('/manage/knowledge-bases/');
      return handleResponse(response);
    },

    getAnalytics: async (days = 30) => {
      const response = await fetchWithAuth(`/admin/public-chat/analytics?days=${days}`);
      return handleResponse(response);
    },

    getSessionDetails: async (sessionId: string) => {
      const response = await fetchWithAuth(`/admin/public-chat/sessions/${sessionId}`);
      return handleResponse(response);
    },
  },
};

// Public AI Agent API
export const publicAgentAPI = {
  // Public endpoints (no auth required)
  getConfig: async () => {
    const response = await fetch(`${API_BASE_URL}/public-agent/config`);
    const data = await handleResponse<any>(response);
    return data.config || data;
  },

  chat: async (data: {
    session_id: string;
    message: string;
    conversation_history?: Array<{ role: string; content: string }>;
  }) => {
    const response = await fetch(`${API_BASE_URL}/public-agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  submitFeedback: async (data: {
    session_id: string;
    message_id: string;
    feedback_type: 'positive' | 'negative';
    comment?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/public-agent/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  // Admin endpoints (auth required)
  admin: {
    getConfig: async () => {
      const response = await fetchWithAuth('/admin/public-agent/config');
      const data = await handleResponse<any>(response);
      return data.config || data;
    },

    updateConfig: async (config: {
      enabled: boolean;
      allowed_kbs: string[];
      allowed_dbs: string[];
      welcome_message?: string;
      suggested_questions?: string[];
      branding?: {
        logo_url?: string;
        primary_color?: string;
        company_name?: string;
      };
      rate_limit?: {
        queries_per_minute?: number;
        max_messages_per_session?: number;
      };
      features?: {
        show_sources?: boolean;
        allow_feedback?: boolean;
        show_suggested_questions?: boolean;
        enable_database_tools?: boolean;
        enable_knowledge_base?: boolean;
      };
    }) => {
      const response = await fetchWithAuth('/admin/public-agent/config', {
        method: 'PUT',
        body: JSON.stringify(config),
      });
      return handleResponse(response);
    },

    getAvailableKBs: async () => {
      const response = await fetchWithAuth('/manage/knowledge-bases/');
      return handleResponse(response);
    },

    getAvailableDBs: async () => {
      const response = await fetchWithAuth('/db/connections/list');
      return handleResponse(response);
    },

    getAnalytics: async (days = 30) => {
      const response = await fetchWithAuth(`/admin/public-agent/analytics?days=${days}`);
      return handleResponse(response);
    },

    getSessionDetails: async (sessionId: string) => {
      const response = await fetchWithAuth(`/admin/public-agent/sessions/${sessionId}`);
      return handleResponse(response);
    },

    getAvailableAgents: async () => {
      const response = await fetchWithAuth('/admin/public-agent/available-agents');
      return handleResponse(response);
    },
  },

  // Super Admin endpoints for cross-tenant agent management
  superAdmin: {
    getTenantAgentConfig: async (tenantId: string) => {
      const response = await fetchWithAuth(`/superadmin/public-agent/config/${tenantId}`);
      const data = await handleResponse<any>(response);
      return data.config || data.data || data;
    },

    updateTenantAgentConfig: async (tenantId: string, config: {
      agent_type: string;
      enabled?: boolean;
      allowed_tools?: string[];
      branding?: {
        logo_url?: string;
        primary_color?: string;
        company_name?: string;
      };
    }) => {
      const response = await fetchWithAuth(`/superadmin/public-agent/config/${tenantId}`, {
        method: 'PUT',
        body: JSON.stringify(config),
      });
      return handleResponse(response);
    },
  },
};

// RBAC API
export const rbacAPI = {
  // Debug endpoint to check current user permissions
  debug: {
    getMyPermissions: async () => {
      const response = await fetchWithAuth('/debug/my-permissions');
      return handleResponse(response);
    },
  },

  // Tenant Role Management
  roles: {
    list: async () => {
      const response = await fetchWithAuth('/tenant/roles');
      return handleResponse(response);
    },

    create: async (data: { name: string; description?: string; permissions: string[] }) => {
      const response = await fetchWithAuth('/tenant/roles', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },

    update: async (roleId: string, data: { name?: string; description?: string; permissions?: string[] }) => {
      const response = await fetchWithAuth(`/tenant/roles/${roleId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },

    delete: async (roleId: string) => {
      const response = await fetchWithAuth(`/tenant/roles/${roleId}`, {
        method: 'DELETE',
      });
      return handleResponse(response);
    },

    getUsers: async (roleId: string) => {
      const response = await fetchWithAuth(`/tenant/roles/${roleId}/users`);
      return handleResponse(response);
    },
  },

  // User Role Assignment
  users: {
    create: async (data: { email: string; full_name: string; password?: string; role_id?: string; is_active?: boolean }) => {
      const response = await fetchWithAuth('/tenant/users', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },

    get: async (userId: string) => {
      const response = await fetchWithAuth(`/tenant/users/${userId}`);
      return handleResponse(response);
    },

    update: async (userId: string, data: { full_name?: string; is_active?: boolean; role_id?: string }) => {
      const response = await fetchWithAuth(`/tenant/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },

    delete: async (userId: string) => {
      const response = await fetchWithAuth(`/tenant/users/${userId}`, {
        method: 'DELETE',
      });
      return handleResponse(response);
    },

    assignRole: async (userId: string, roleId: string) => {
      const response = await fetchWithAuth(`/tenant/users/${userId}/assign-role`, {
        method: 'POST',
        body: JSON.stringify({ role_id: roleId }),
      });
      return handleResponse(response);
    },

    removeRole: async (userId: string, roleId: string) => {
      const response = await fetchWithAuth(`/tenant/users/${userId}/remove-role`, {
        method: 'DELETE',
        body: JSON.stringify({ role_id: roleId }),
      });
      return handleResponse(response);
    },

    list: async () => {
      const response = await fetchWithAuth('/tenant/users');
      return handleResponse(response);
    },
  },

  // Permission Management
  permissions: {
    list: async () => {
      const response = await fetchWithAuth('/tenant/permissions');
      return handleResponse(response);
    },

    getCategories: async () => {
      const response = await fetchWithAuth('/tenant/permissions/categories');
      return handleResponse(response);
    },

    getMyPermissions: async () => {
      const response = await fetchWithAuth('/tenant/permissions/my-permissions');
      return handleResponse(response);
    },
  },

  // System Administration (Super Admin only)
  admin: {
    listTenants: async () => {
      const response = await fetchWithAuth('/admin/tenants');
      return handleResponse(response);
    },

    getTenantUsers: async (tenantId: string) => {
      const response = await fetchWithAuth(`/admin/tenants/${tenantId}/users`);
      return handleResponse(response);
    },

    promoteUser: async (tenantId: string, userId: string, systemRole: string) => {
      const response = await fetchWithAuth(`/admin/tenants/${tenantId}/promote-admin`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, system_role: systemRole }),
      });
      return handleResponse(response);
    },

    getSystemRoles: async () => {
      const response = await fetchWithAuth('/admin/system/roles');
      return handleResponse(response);
    },

    getMetrics: async () => {
      const response = await fetchWithAuth('/admin/metrics');
      return handleResponse(response);
    },
  },
};

// Gmail Integration API
export const gmailAPI = {
  auth: {
    getStatus: async () => {
      const response = await fetchWithAuth('/gmail/status');
      return handleResponse<{ connected: boolean; email: string | null }>(response);
    },
    getAuthUrl: async () => {
      const response = await fetchWithAuth('/gmail/auth');
      return handleResponse<{ auth_url: string }>(response);
    },
    handleCallback: async (code: string) => {
      const response = await fetchWithAuth('/gmail/callback', {
        method: 'POST',
        body: JSON.stringify({ code }),
      });
      return handleResponse<{ message: string; email: string }>(response);
    },
  },
  recipients: {
    list: async () => {
      const response = await fetchWithAuth('/gmail/recipients');
      return handleResponse<any[]>(response);
    },
    add: async (data: { email_address: string; display_name?: string; group_name?: string; enabled?: boolean }) => {
      const response = await fetchWithAuth('/gmail/recipients', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },
    remove: async (id: string) => {
      const response = await fetchWithAuth(`/gmail/recipients/${id}`, {
        method: 'DELETE',
      });
      return handleResponse(response);
    },
  },
  schedules: {
    list: async () => {
      const response = await fetchWithAuth('/gmail/schedules');
      return handleResponse<any[]>(response);
    },
    create: async (data: {
      name: string;
      schedule_type: string;
      schedule_config: { minutes?: number;[key: string]: any };
      recipient_ids: string[];
      enabled: boolean;
    }) => {
      const response = await fetchWithAuth('/gmail/schedules', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return handleResponse(response);
    },
    sync: async (scheduleId: string) => {
      const response = await fetchWithAuth(`/gmail/schedules/${scheduleId}/sync`, {
        method: 'POST',
      });
      return handleResponse(response);
    },
  },
  messages: {
    list: async (limit = 50, offset = 0) => {
      const response = await fetchWithAuth(`/gmail/messages?limit=${limit}&offset=${offset}`);
      return handleResponse<any[]>(response);
    },
    delete: async (id: string) => {
      const response = await fetchWithAuth(`/gmail/messages/${id}`, {
        method: 'DELETE',
      });
      return handleResponse(response);
    },
  },
};

// Generic API client for custom requests
export const apiClient = {
  get: async <T = unknown>(url: string): Promise<T> => {
    const response = await fetchWithAuth(url);
    return handleResponse<T>(response);
  },

  post: async <T = unknown>(url: string, data?: unknown): Promise<T> => {
    const response = await fetchWithAuth(url, {
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  put: async <T = unknown>(url: string, data?: unknown): Promise<T> => {
    const response = await fetchWithAuth(url, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  delete: async <T = unknown>(url: string): Promise<T> => {
    const response = await fetchWithAuth(url, {
      method: 'DELETE',
    });
    return handleResponse<T>(response);
  },
};

export default apiClient;
