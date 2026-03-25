import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import CreateTenantModal from '../../components/modals/CreateTenantModal';
import AgentAssignmentModal from '../../components/modals/AgentAssignmentModal';
import ManageTenantModal from '../../components/modals/ManageTenantModal';
import { Search, Plus, Brain, Settings } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { adminAPI, tenantsAPI, publicAgentAPI } from '../../services/api';

interface Tenant {
  id: string;
  name: string;
  company: string;
  status: 'active' | 'suspended' | 'inactive';
  tier: 'free' | 'starter' | 'professional' | 'pro' | 'enterprise';
  user_count: number;
  kb_count: number;
  storage_gb: number;
  queries_30d: number;
  email: string;
  created_at: string;
  agent_type?: string;
  agent_enabled?: boolean;
}

export default function TenantManagementPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTenants();
  }, [searchQuery, statusFilter, tierFilter]);

  const fetchTenants = async () => {
    try {
      setError(null);
      let data: any;

      // Use search if there's a query, otherwise list all
      if (searchQuery) {
        data = await adminAPI.searchTenants(searchQuery);
      } else {
        data = await tenantsAPI.listTenants(0, 100);
      }

      console.log('Raw tenant data received:', data);

      // Handle different response formats and map backend fields to frontend interface
      let rawTenants: any[] = [];
      if (Array.isArray(data)) {
        rawTenants = data;
      } else if (data.tenants && Array.isArray(data.tenants)) {
        rawTenants = data.tenants;
      } else if (data.data && Array.isArray(data.data)) {
        rawTenants = data.data;
      }

      // Map backend fields to frontend Tenant interface
      const tenantList: Tenant[] = rawTenants.map((t: any) => ({
        id: t.id,
        name: t.name,
        company: t.company || t.name,
        status: t.status || (t.is_active ? 'active' : 'inactive'),
        tier: t.billing_tier || 'free',
        user_count: t.user_count || 0,
        kb_count: t.kb_count || 0,
        storage_gb: t.storage_gb || 0,
        queries_30d: t.queries_30d || 0,
        email: t.email || '',
        created_at: t.created_at,
        agent_type: t.agent_type || t.public_agent_type || t.agent_config?.agent_type || (typeof t.agent_config === 'string' ? t.agent_config : null) || 'generic',
        agent_enabled: t.agent_enabled ?? t.is_agent_enabled ?? t.agent_config?.enabled ?? (t.agent_config ? true : false),
      }));

      console.log('Tenant list length:', tenantList.length);
      console.log('First mapped tenant:', tenantList[0]);

      // Apply client-side filters for status and tier
      let filteredTenants = tenantList;
      if (statusFilter !== 'all') {
        filteredTenants = filteredTenants.filter(t => t.status === statusFilter);
      }
      if (tierFilter !== 'all') {
        filteredTenants = filteredTenants.filter(t => t.tier === tierFilter);
      }

      setTenants(filteredTenants);

      // Background fetch agent configs in batches of 3 to avoid DB connection exhaustion
      const batchSize = 3;
      for (let i = 0; i < filteredTenants.length; i += batchSize) {
        const batch = filteredTenants.slice(i, i + batchSize);
        await Promise.all(batch.map(async (tenant) => {
          try {
            const config = await publicAgentAPI.superAdmin.getTenantAgentConfig(tenant.id) as any;
            if (config) {
              setTenants(prev => prev.map(t =>
                t.id === tenant.id
                  ? {
                    ...t,
                    agent_type: config.agent_type || config.config?.agent_type || t.agent_type,
                    agent_enabled: config.enabled ?? config.config?.enabled ?? t.agent_enabled
                  }
                  : t
              ));
            }
          } catch (err) {
            console.debug(`Could not fetch agent config for tenant ${tenant.id}`);
          }
        }));
      }
    } catch (error: any) {
      console.error('Failed to fetch tenants:', error);
      setError(error.message || 'Failed to load tenants. Please check if the backend server is running.');
      setTenants([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-success/20 text-success',
      suspended: 'bg-warning/20 text-warning',
      inactive: 'bg-text-secondary/20 text-text-secondary',
    };
    const safeStatus = status || 'unknown';
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[safeStatus] || 'bg-text-secondary/20 text-text-secondary'}`}>
        {safeStatus.toUpperCase()}
      </span>
    );
  };

  const getTierBadge = (tier: string) => {
    const colors: Record<string, string> = {
      free: 'bg-text-secondary/20 text-text-secondary',
      starter: 'bg-emerald-500/20 text-emerald-500',
      professional: 'bg-secondary/20 text-secondary',
      pro: 'bg-secondary/20 text-secondary',
      enterprise: 'bg-primary/20 text-primary',
    };
    const safeTier = tier || 'free';
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[safeTier] || 'bg-text-secondary/20 text-text-secondary'}`}>
        {safeTier.toUpperCase()}
      </span>
    );
  };

  const handleQuickAgentAssign = async (tenantId: string, agentType: string) => {
    try {
      await publicAgentAPI.superAdmin.updateTenantAgentConfig(tenantId, {
        agent_type: agentType as any,
        enabled: true,
        allowed_tools: [],
        branding: {
          primary_color: '#0066CC',
          company_name: 'Company'
        }
      });
      // Refresh tenant list to show updated status
      fetchTenants();
    } catch (error) {
      console.error('Failed to assign agent:', error);
    }
  };

  const handleOpenAgentModal = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setShowAgentModal(true);
  };

  return (
    <div className="p-8 space-y-6 bg-background min-h-screen">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text">Tenant Management</h1>
          <p className="text-text-secondary mt-1">Manage all tenant organizations</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)} className="bg-primary hover:bg-primary/90">
          <Plus className="w-4 h-4 mr-2" />
          Create New Tenant
        </Button>
      </div>

      <CreateTenantModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={fetchTenants}
      />

      {selectedTenant && (
        <>
          <AgentAssignmentModal
            isOpen={showAgentModal}
            onClose={() => {
              setShowAgentModal(false);
              setSelectedTenant(null);
            }}
            tenantName={selectedTenant.name}
            tenantId={selectedTenant.id}
            onAssign={handleQuickAgentAssign}
          />
          <ManageTenantModal
            isOpen={showManageModal}
            onClose={() => {
              setShowManageModal(false);
              setSelectedTenant(null);
            }}
            tenant={selectedTenant}
            onUpdate={fetchTenants}
          />
        </>
      )}

      {/* Error Message */}
      {error && (
        <Card className="p-4 bg-error/10 border-error/20">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 text-error">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-error">Backend Error</h3>
              <p className="text-sm text-error mt-1">{error}</p>
              <p className="text-xs text-text-secondary mt-2">
                Check your backend server logs at http://localhost:8000 for details.
              </p>
              <Button onClick={fetchTenants} size="sm" className="mt-3 bg-error hover:bg-error/90" variant="outline">
                Retry
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card className="p-4 bg-surface border-border">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[300px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-secondary w-5 h-5" />
              <Input
                placeholder="Search by name, company, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-background border-border text-text"
              />
            </div>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-border rounded-md bg-background text-text"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="inactive">Inactive</option>
          </select>
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="px-4 py-2 border border-border rounded-md bg-background text-text"
          >
            <option value="all">All Tiers</option>
            <option value="free">Free</option>
            <option value="starter">Starter</option>
            <option value="professional">Professional</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </Card>

      {/* Tenant Table */}
      <Card className="bg-surface border-border">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Tenant</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Tier</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">AI Agent</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Users</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">KBs</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Storage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center text-text-secondary">
                    Loading tenants...
                  </td>
                </tr>
              ) : !Array.isArray(tenants) || tenants.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center">
                    <div className="text-text-secondary">
                      <p className="mb-2">No tenants found</p>
                      <p className="text-sm">
                        {!Array.isArray(tenants)
                          ? 'API endpoint may not be configured correctly'
                          : 'Create your first tenant to get started'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <button
                          onClick={() => navigate(`/admin/tenants/${tenant.id}`)}
                          className="font-medium text-primary hover:underline"
                        >
                          {tenant.name}
                        </button>
                        <p className="text-sm text-text-secondary">{tenant.company}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(tenant.status)}</td>
                    <td className="px-6 py-4">{getTierBadge(tenant.tier)}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <Badge variant={tenant.agent_enabled ? "success" : "secondary"} className="w-fit text-[10px] uppercase">
                          {tenant.agent_type || 'generic'}
                        </Badge>
                        <span className="text-[10px] text-text-secondary">
                          {tenant.agent_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-text">{tenant.user_count}</td>
                    <td className="px-6 py-4 text-sm text-text">{tenant.kb_count}</td>
                    <td className="px-6 py-4 text-sm text-text">{tenant.storage_gb.toFixed(2)} GB</td>
                    <td className="px-6 py-4 text-sm text-text-secondary">
                      {new Date(tenant.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedTenant(tenant);
                            setShowManageModal(true);
                          }}
                          className="text-primary hover:bg-primary/10"
                        >
                          <Settings className="w-4 h-4 mr-1" />
                          Manage
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenAgentModal(tenant)}
                          className="text-secondary hover:bg-secondary/10"
                        >
                          <Brain className="w-4 h-4 mr-1" />
                          Agent
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
