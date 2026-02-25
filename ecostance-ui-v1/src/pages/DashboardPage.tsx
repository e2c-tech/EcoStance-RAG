import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.v2';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Progress } from '../components/ui/Progress';
import { Icons } from '../components/icons';
import { cn } from '../lib/utils';
import { quotaAPI, extendedMetricsAPI, knowledgeBaseAPI, metricsAPI, documentProcessingAPI, filesAPI } from '../services/api';

// Types
interface QuotaStatus {
  storage: { limit_bytes: number; used_bytes: number; usage_percent: number };
  queries: { daily_limit: number; daily_used: number; monthly_limit: number; monthly_used: number };
  documents: { limit: number; used: number; usage_percent: number };
  db_connections?: { max_connections: number; active_connections: number };
}

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: string;
}

interface OverviewData {
  knowledgeBases: number;
  documentsUploaded: number;
  storageUsedGB: number;
  storageLimitGB: number;
  queryCountThisMonth: number;
  activeConnections: number;
  queriesLast7Days: number;
}

interface ActivityEvent {
  id: string;
  type: 'query' | 'upload' | 'kb_create' | 'job' | 'db_query';
  description: string;
  timestamp: string;
  status: 'completed' | 'processing' | 'failed';
}

interface MetricPoint {
  period_start: string;
  queries: { total: number };
  storage: { gb: number };
}

const OverviewCard = ({ title, value, children }: { title: string; value: string | number; children?: React.ReactNode }) => (
  <Card className="w-full max-w-xs h-40 flex flex-col justify-between bg-surface border-none shadow-none">
    <CardHeader className="p-4 pb-2">
      <CardTitle className="text-base font-semibold text-primary">{title}</CardTitle>
      <div className="text-xs text-text-secondary">
        {children}
      </div>
    </CardHeader>
    <CardContent className="p-4 pt-0 text-3xl font-bold text-text flex items-center justify-between">
      {value}
      {title === 'Storage Usage' && (
        <span className="text-sm font-normal text-text-secondary">GB</span>
      )}
    </CardContent>
  </Card>
);

// --- Quick Actions ---
const QuickAction = ({ icon: Icon, label, onClick }: { icon: React.ElementType; label: string; onClick: () => void }) => (
  <Button variant="outline" onClick={onClick} className="flex flex-col items-center justify-center h-20 w-full max-w-xs border-dashed hover:bg-primary/5 border-border">
    <Icon className="h-5 w-5 mb-1 text-primary" />
    <span className="text-xs font-medium text-text">{label}</span>
  </Button>
);

// --- Recent Activity Feed ---
const ActivityItem = ({ item }: { item: ActivityEvent }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'query': return <Icons.Search className="h-4 w-4 text-blue-500" />;
      case 'upload': return <Icons.FileText className="h-4 w-4 text-green-500" />;
      case 'kb_create': return <Icons.BookOpen className="h-4 w-4 text-purple-500" />;
      case 'db_query': return <Icons.Database className="h-4 w-4 text-orange-500" />;
      case 'job': return <Icons.Cog className="h-4 w-4 text-yellow-500" />;
      default: return <Icons.Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-500';
      case 'processing': return 'text-yellow-500 animate-pulse';
      case 'failed': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="flex items-center py-3 border-b border-border/50 last:border-b-0 group hover:bg-surface-hover/50 px-2 rounded-lg transition-colors">
      <div className="p-2 rounded-full bg-surface shadow-sm mr-3">
        {getIcon(item.type)}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-text">{item.description}</p>
        <p className="text-[10px] text-text-secondary uppercase tracking-wider mt-0.5">
          {new Date(item.timestamp).toLocaleString()}
        </p>
      </div>
      <span className={cn("text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-md bg-surface border border-border shadow-sm", getStatusColor(item.status))}>
        {item.status}
      </span>
    </div>
  );
};

const UsageChart = ({ title, data, type }: { title: string; data: MetricPoint[]; type: 'queries' | 'storage' }) => {
  const maxValue = Math.max(...data.map(d => type === 'queries' ? d.queries.total : d.storage.gb), 10);

  return (
    <Card className="p-6 bg-surface border-border flex flex-col h-64">
      <h3 className="text-sm font-bold text-text mb-6 uppercase tracking-widest opacity-60">{title}</h3>
      <div className="flex-1 flex items-end gap-2 px-2">
        {data.map((d, i) => {
          const val = type === 'queries' ? d.queries.total : d.storage.gb;
          const height = (val / maxValue) * 100;
          return (
            <div key={i} className="flex-1 group relative flex flex-col items-center">
              <div
                className={cn(
                  "w-full rounded-t-sm transition-all duration-500 hover:opacity-80 cursor-help",
                  type === 'queries' ? "bg-primary shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]" : "bg-accent shadow-[0_0_15px_rgba(var(--accent-rgb),0.3)]"
                )}
                style={{ height: `${Math.max(height, 5)}%` }}
              >
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-text text-background text-[10px] px-2 py-1 rounded font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
                  {val.toFixed(type === 'storage' ? 2 : 0)} {type === 'storage' ? 'GB' : ''}
                </div>
              </div>
              <div className="text-[8px] text-text-secondary mt-2 font-mono rotate-45 origin-left">
                {new Date(d.period_start).toLocaleDateString(undefined, { weekday: 'short' })}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};


const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State for dashboard data
  const [overviewData, setOverviewData] = useState<OverviewData>({
    knowledgeBases: 0,
    documentsUploaded: 0,
    storageUsedGB: 0,
    storageLimitGB: 0,
    queryCountThisMonth: 0,
    activeConnections: 0,
    queriesLast7Days: 0,
  });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);

  // Load dashboard data on mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch quota status
      const quotaResponse = await quotaAPI.getStatus();

      // Handle different response formats
      let quotaData: QuotaStatus | null = null;
      if (quotaResponse && typeof quotaResponse === 'object') {
        if ('data' in quotaResponse && quotaResponse.data) {
          quotaData = quotaResponse.data as QuotaStatus;
        } else if ('storage' in quotaResponse || 'queries' in quotaResponse || 'documents' in quotaResponse) {
          quotaData = quotaResponse as QuotaStatus;
        }
      }

      // Fetch additional data in parallel
      const [kbResponse, metricsResponse, jobsResponse, filesResponse] = await Promise.all([
        knowledgeBaseAPI.list().catch(() => ({ knowledge_bases: [] })),
        metricsAPI.getTenantMetrics('daily', 7).catch(() => ({ data: [] })),
        documentProcessingAPI.listJobs().catch(() => []),
        filesAPI.list().catch(() => [])
      ]) as any;

      const kbs = kbResponse.knowledge_bases || (Array.isArray(kbResponse) ? kbResponse : []);
      const metricHistory = metricsResponse.data || (Array.isArray(metricsResponse) ? metricsResponse : []);
      const jobs = Array.isArray(jobsResponse) ? jobsResponse : [];
      const files = Array.isArray(filesResponse) ? filesResponse : [];

      // Construct Activity Feed
      const combinedActivities: ActivityEvent[] = [
        ...kbs.map((kb: any) => ({
          id: `kb-${kb.name}`,
          type: 'kb_create' as const,
          description: `Created knowledge base: ${kb.name}`,
          timestamp: new Date().toISOString(), // Mocking timestamp if missing
          status: 'completed' as const
        })),
        ...files.slice(0, 5).map((f: any) => ({
          id: `file-${f.filename}`,
          type: 'upload' as const,
          description: `Uploaded file: ${f.filename}`,
          timestamp: f.created_at || new Date().toISOString(),
          status: 'completed' as const
        })),
        ...jobs.slice(0, 5).map((j: any) => ({
          id: `job-${j.job_id}`,
          type: 'job' as const,
          description: `Processing job ${j.job_id.slice(0, 8)}`,
          timestamp: j.created_at || new Date().toISOString(),
          status: j.status === 'completed' ? 'completed' : j.status === 'failed' ? 'failed' : 'processing' as any
        }))
      ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      setActivities(combinedActivities.slice(0, 8));
      setMetrics(metricHistory);

      // Fetch active alerts
      try {
        const alertsResponse = await extendedMetricsAPI.getActiveAlerts() as any;
        setAlerts(Array.isArray(alertsResponse) ? alertsResponse : []);
      } catch (err) {
        setAlerts([]);
      }

      // Update overview data
      setOverviewData({
        knowledgeBases: kbs.length,
        documentsUploaded: quotaData?.documents?.used || 0,
        storageUsedGB: (quotaData?.storage?.used_bytes || 0) / (1024 ** 3),
        storageLimitGB: (quotaData?.storage?.limit_bytes || 0) / (1024 ** 3),
        queryCountThisMonth: quotaData?.queries?.monthly_used || 0,
        activeConnections: quotaData?.db_connections?.active_connections || 0,
        queriesLast7Days: metricHistory.reduce((acc: number, curr: any) => acc + (curr.queries?.total || 0), 0),
      });

      setLoading(false);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
      setLoading(false);
    }
  };

  const handleUploadDocument = () => {
    window.location.href = '/knowledge-bases';
  };

  const handleCreateKnowledgeBase = () => {
    window.location.href = '/knowledge-bases';
  };

  const handleConnectDatabase = () => {
    window.location.href = '/database-chat';
  };

  const handleQuickSearch = () => {
    if (searchQuery.trim()) {
      window.location.href = `/knowledge-bases?query=${encodeURIComponent(searchQuery)}`;
    }
  };

  const storageUsagePercentage = overviewData.storageLimitGB > 0
    ? (overviewData.storageUsedGB / overviewData.storageLimitGB) * 100
    : 0;

  if (loading) {
    return (
      <main className="min-h-screen w-full bg-background flex items-center justify-center">
        <div className="text-center">
          <Icons.Spinner className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-text-secondary">Loading dashboard...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen w-full bg-background flex flex-col items-center justify-start p-4 md:p-8 font-sans text-text">
      <div className="w-full max-w-6xl text-center">
        <h1 className="text-3xl font-bold text-primary mb-3">
          Dashboard
        </h1>
        <p className="text-sm text-text-secondary mb-4">
          Welcome back, <strong className="text-text">{user?.email}</strong>
          {user?.role && (
            <span className={cn(
              "ml-2 px-2 py-0.5 text-xs font-semibold rounded",
              user.role === 'super_admin' || user.role === 'admin'
                ? "bg-red-100 text-red-700"
                : "bg-blue-100 text-blue-700"
            )}>
              {user.role === 'super_admin' ? 'SUPER ADMIN' : user.role.toUpperCase()}
            </span>
          )}
        </p>
        <p className="text-xs text-text-secondary mb-6">
          Tenant ID: <span className="font-mono bg-surface px-1.5 py-0.5 rounded">{user?.tenantId}</span>
        </p>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-error/10 border border-error/20 rounded-lg">
            <p className="text-error text-sm">{error}</p>
            <Button onClick={loadDashboardData} size="sm" className="mt-2">
              Retry
            </Button>
          </div>
        )}

        {/* Active Alerts */}
        {alerts.length > 0 && (
          <section className="mb-6">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "p-4 rounded-lg mb-2 flex items-start gap-3",
                  alert.severity === 'critical' && "bg-error/10 border border-error/20",
                  alert.severity === 'warning' && "bg-warning/10 border border-warning/20",
                  alert.severity === 'info' && "bg-primary/10 border border-primary/20"
                )}
              >
                <Icons.AlertCircle className={cn(
                  "h-5 w-5 flex-shrink-0 mt-0.5",
                  alert.severity === 'critical' && "text-error",
                  alert.severity === 'warning' && "text-warning",
                  alert.severity === 'info' && "text-primary"
                )} />
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium text-text">{alert.message}</p>
                  <p className="text-xs text-text-secondary mt-1">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </section>
        )}

        {/* Overview Cards */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-left mb-4 text-primary">Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <OverviewCard title="Knowledge Bases" value={overviewData.knowledgeBases} />
            <OverviewCard title="Documents Uploaded" value={overviewData.documentsUploaded} />
            <OverviewCard
              title="Storage Usage"
              value={`${overviewData.storageUsedGB.toFixed(1)} / ${overviewData.storageLimitGB.toFixed(1)}`}
            >
              <Progress value={storageUsagePercentage} className="h-1.5 mt-1 bg-primary/10" indicatorClassName="bg-primary" />
            </OverviewCard>
            <OverviewCard title="Queries This Month" value={overviewData.queryCountThisMonth} />
          </div>
        </section>

        {/* Quick Actions section hidden per user request */}
        <section className="mb-8">
          {/* <h2 className="text-xl font-semibold text-left mb-4 text-primary">Quick Actions</h2> */}
          <div className="flex flex-wrap justify-center lg:justify-start gap-4">
            {/* 
            <QuickAction icon={Icons.Upload} label="Upload Document" onClick={handleUploadDocument} />
            <QuickAction icon={Icons.BookOpen} label="Create Knowledge Base" onClick={handleCreateKnowledgeBase} />
            <QuickAction icon={Icons.Database} label="Connect Database" onClick={handleConnectDatabase} />
            */}
            <div className="flex-1 min-w-[200px]">
              <Input
                type="search"
                placeholder="Ask a question..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleQuickSearch(); }}
                className="h-20"
              />
            </div>
            <Button onClick={handleQuickSearch} className="max-w-xs h-20 px-6">Search</Button>
          </div>
        </section>

        {/* Recent Activity Feed */}
        <section className="mb-0">
          <div className="flex items-center justify-between mb-4 px-2">
            <h2 className="text-xl font-semibold text-primary">Recent Activity</h2>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="h-8 text-[10px] uppercase font-bold tracking-widest">
              Refresh Feed
            </Button>
          </div>
          <Card className="w-full bg-surface border-border overflow-hidden">
            <CardContent className="p-4 space-y-1">
              {activities.length > 0 ? (
                activities.map((item) => (
                  <ActivityItem key={item.id} item={item} />
                ))
              ) : (
                <div className="py-12 text-center text-text-secondary">
                  <Icons.Activity className="w-8 h-8 mx-auto mb-3 opacity-20" />
                  <p className="text-sm font-medium">No activity recorded yet</p>
                  <p className="text-xs opacity-60">Upload documents or query the AI to see activity here.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        {/* Usage Charts */}
        <section className="mt-12">
          <h2 className="text-xl font-semibold text-left mb-6 text-primary px-2">Usage Trends</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <UsageChart title="Queries (Last 7 Days)" data={metrics} type="queries" />
            <UsageChart title="Storage Usage Growth (GB)" data={metrics} type="storage" />
          </div>
        </section>

        <div className="mt-8">
          <Button onClick={logout} className="max-w-xs mx-auto bg-transparent text-primary border-primary hover:bg-primary/10">
            Log Out
          </Button>
        </div>
      </div>
    </main>
  );
};

export default DashboardPage;
