import { useEffect, useState } from 'react';
import { Card } from '../../components/ui/Card';
import { Building, Users, Search, Heart, TrendingUp, AlertCircle, Brain } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { adminAPI, tenantsAPI, publicAgentAPI } from '../../services/api';
import { cn } from '../../lib/utils';

interface Tenant {
  id: string;
  name: string;
  agent_type?: string;
  status: string;
}

interface DashboardSummary {
  total_tenants: number;
  total_users: number;
  total_queries_today: number;
  system_health: 'healthy' | 'warning' | 'critical';
  uptime_percentage: number;
  tenant_growth: number;
  active_users_30d: number;
  queries_yesterday: number;
}

interface ActivityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  tenant_name: string;
  details: string;
}

export default function SuperAdminDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [summaryData, tenantsData] = await Promise.all([
        adminAPI.getDashboardSummary(),
        tenantsAPI.listTenants(0, 100)
      ]) as any;

      // Handle response structure { success, data: { ... } }
      const dashboardData = summaryData.data || summaryData;
      setTenants(Array.isArray(tenantsData) ? tenantsData : tenantsData.data || []);

      // Background fetch agent configs in batches of 3 to avoid DB connection exhaustion
      const rawTenants = Array.isArray(tenantsData) ? tenantsData : tenantsData.data || [];
      const batchSize = 3;
      for (let i = 0; i < rawTenants.length; i += batchSize) {
        const batch = rawTenants.slice(i, i + batchSize);
        await Promise.all(batch.map(async (tenant: any) => {
          try {
            const config = await publicAgentAPI.superAdmin.getTenantAgentConfig(tenant.id) as any;
            if (config) {
              setTenants(prev => prev.map(t =>
                t.id === tenant.id
                  ? { ...t, agent_type: config.agent_type || config.config?.agent_type || t.agent_type }
                  : t
              ));
            }
          } catch (err) {
            // Ignore individual fetch errors
          }
        }));
      }

      setSummary({
        total_tenants: dashboardData.total_tenants || 0,
        total_users: dashboardData.total_users || 0,
        total_queries_today: dashboardData.total_queries_today || 0,
        system_health: dashboardData.system_health || 'healthy',
        uptime_percentage: dashboardData.uptime_percentage || 99.9,
        tenant_growth: dashboardData.tenant_growth || 0,
        active_users_30d: dashboardData.active_users_30d || 0,
        queries_yesterday: dashboardData.queries_yesterday || 0,
      });

      setActivities(dashboardData.recent_events || dashboardData.activities || []);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      // Set empty data on error
      setSummary({
        total_tenants: 0,
        total_users: 0,
        total_queries_today: 0,
        system_health: 'healthy',
        uptime_percentage: 99.9,
        tenant_growth: 0,
        active_users_30d: 0,
        queries_yesterday: 0,
      });
      setActivities([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Platform overview and metrics</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={fetchDashboardData}>
            Refresh
          </Button>
          <Button onClick={() => window.location.href = '/admin/tenants/create'}>
            Create New Tenant
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Total Tenants</p>
              <p className="text-3xl font-bold text-text mt-2">
                {summary?.total_tenants || 0}
              </p>
              <p className="text-sm text-green-400 mt-2 flex items-center">
                <TrendingUp className="w-4 h-4 mr-1" />
                +{summary?.tenant_growth || 0}% vs last month
              </p>
            </div>
            <Building className="w-12 h-12 text-blue-400" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Total Users</p>
              <p className="text-3xl font-bold text-text mt-2">
                {summary?.total_users || 0}
              </p>
              <p className="text-sm text-text-secondary mt-2">
                {summary?.active_users_30d || 0} active (30d)
              </p>
            </div>
            <Users className="w-12 h-12 text-purple-400" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Queries Today</p>
              <p className="text-3xl font-bold text-text mt-2">
                {summary?.total_queries_today || 0}
              </p>
              <p className="text-sm text-text-secondary mt-2">
                vs {summary?.queries_yesterday || 0} yesterday
              </p>
            </div>
            <Search className="w-12 h-12 text-indigo-400" />
          </div>
        </Card>

        <Card className={cn(
          "p-6 border-none shadow-premium",
          summary?.system_health === 'healthy' ? "bg-green-500/10 text-green-600" :
            summary?.system_health === 'warning' ? "bg-yellow-500/10 text-yellow-600" :
              "bg-red-500/10 text-red-600"
        )}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-bold uppercase tracking-widest opacity-70">System Health</p>
              <p className="text-3xl font-black mt-2 capitalize">
                {summary?.system_health || 'Healthy'}
              </p>
              <p className="text-xs font-bold mt-2 opacity-60">
                {summary?.uptime_percentage || 99.9}% uptime (24h)
              </p>
            </div>
            <Heart className="w-12 h-12 opacity-20" />
          </div>
        </Card>
      </div>

      {/* Agent Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="p-6">
          <h2 className="text-xl font-bold text-text mb-6 flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            AI Agent Distribution
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'EcoStance', count: tenants.filter((t: any) => t.agent_type === 'ecostance').length, color: 'bg-green-500' },
              { label: 'E-commerce', count: tenants.filter((t: any) => t.agent_type === 'ecommerce').length, color: 'bg-blue-500' },
              { label: 'QuickShip', count: tenants.filter((t: any) => t.agent_type === 'quickship').length, color: 'bg-purple-500' },
              { label: 'Security Analyst', count: tenants.filter((t: any) => t.agent_type === 'security_analyst').length, color: 'bg-red-500' },
              { label: 'Generic', count: tenants.filter((t: any) => t.agent_type === 'generic' || !t.agent_type).length, color: 'bg-gray-500' },
            ].map((agent) => (
              <div key={agent.label} className="p-4 bg-surface-hover rounded-lg border border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${agent.color}`} />
                  <span className="text-sm font-medium">{agent.label}</span>
                </div>
                <span className="text-xl font-bold">{agent.count}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Recent Activity (Moved into grid) */}
        <Card className="p-6">
          <h2 className="text-xl font-bold text-text mb-6">Recent Platform Events</h2>
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
            {activities.length === 0 ? (
              <p className="text-text-secondary text-center py-8">No recent activity</p>
            ) : (
              activities.map((event) => (
                <div key={event.id} className="flex items-start gap-3 pb-3 border-b border-border last:border-0">
                  <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-text">{event.event_type}</p>
                    <p className="text-xs text-text-secondary">{event.tenant_name} - {event.details}</p>
                    <p className="text-[10px] text-text-secondary mt-1">
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h2 className="text-xl font-bold text-text mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Button variant="outline" className="h-20 text-text border-border hover:bg-surface-hover" onClick={() => window.location.href = '/admin/tenants'}>
            View All Tenants
          </Button>
          <Button variant="outline" className="h-20 text-text border-border hover:bg-surface-hover" onClick={() => window.location.href = '/admin/system'}>
            System Health
          </Button>
          <Button variant="outline" className="h-20 text-text border-border hover:bg-surface-hover" onClick={() => window.location.href = '/admin/settings'}>
            Platform Settings
          </Button>
          <Button variant="outline" className="h-20 text-text border-border hover:bg-surface-hover" onClick={() => window.location.href = '/admin/maintenance'}>
            Run Cleanup
          </Button>
        </div>
      </Card>
    </div>
  );
}
