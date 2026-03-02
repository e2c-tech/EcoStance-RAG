import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { rbacAPI } from '../services/api';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import RoleManagement from '../components/rbac/RoleManagement';
import UserManagement from '../components/rbac/UserManagement';
import { usePermissions } from '../hooks/usePermissions';
import { Settings, CreditCard, Bell, BarChart3, AlertCircle, Shield, Users, Plug, Brain } from 'lucide-react';
import { useTenant, Tenant } from '../context/TenantContext';
import GmailSettings from '../components/gmail/GmailSettings';
import DynamicsSettings from '../components/dynamics/DynamicsSettings';
import CustomCrmSettings from '../components/custom-crm/CustomCrmSettings';
import { PricingGrid } from '../components/PricingGrid';



const AGENT_TYPE_INFO = {
  generic: {
    label: 'Generic Assistant',
    description: 'General-purpose AI assistant',
    color: 'bg-gray-500',
    icon: '🤖'
  },
  ecommerce: {
    label: 'E-commerce Agent',
    description: 'Shopping and retail focused',
    color: 'bg-blue-500',
    icon: '🛒'
  },
  ecostance: {
    label: 'EcoStance Agent',
    description: 'Sustainability focused',
    color: 'bg-green-500',
    icon: '🌱'
  },
  quickship: {
    label: 'QuickShip Agent',
    description: 'Logistics and shipping focused',
    color: 'bg-purple-500',
    icon: '📦'
  },
  security_analyst: {
    label: 'Security Analyst',
    description: 'Security, logs, and threat analysis focused',
    color: 'bg-red-500',
    icon: '🛡️'
  }
};

const DEFAULT_AGENT_INFO = {
  label: 'AI Assistant',
  description: 'Specialized AI assistant',
  color: 'bg-primary',
  icon: '🤖'
};

export default function TenantSettingsPage() {
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<'profile' | 'usage' | 'billing' | 'notifications' | 'rbac' | 'integrations'>((searchParams.get('tab') as any) || 'profile');

  const {
    tenant,
    quotaStatus,
    agentConfig,
    isLoading: tenantLoading,
    error: error,
    fetchTenantData,
    fetchQuotaStatus,
    fetchAgentConfig
  } = useTenant();

  const agentLoading = tenantLoading; // Map loading state

  const { canManageRoles, canViewTenantSettings, loading: permissionsLoading } = usePermissions();

  useEffect(() => {
    fetchTenantData();
    fetchQuotaStatus();
    fetchAgentConfig();
  }, [fetchTenantData, fetchQuotaStatus, fetchAgentConfig]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text flex items-center gap-2">
          <Settings className="w-6 h-6 text-primary" />
          Tenant Settings
        </h1>
        <p className="text-text-secondary mt-1">Manage your account settings and preferences</p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          <p className="text-error">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 border-b border-border">
        <div className="flex gap-6">
          {[
            { id: 'profile', label: 'Profile', icon: Settings },
            // { id: 'usage', label: 'Usage & Quotas', icon: BarChart3 },
            { id: 'rbac', label: 'Access Control', icon: Shield },
            { id: 'integrations', label: 'Integrations', icon: Plug },
            { id: 'billing', label: 'Billing', icon: CreditCard },
            { id: 'notifications', label: 'Notifications', icon: Bell },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-2 ${activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-text-secondary hover:text-text'
                }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && tenant && (
        <div className="space-y-6">
          {/* AI Agent Configuration Card */}
          <Card className="p-6 bg-surface border-border">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Brain className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-text">AI Agent Assignment</h2>
                <p className="text-sm text-text-secondary">Your assigned AI agent configuration</p>
              </div>
            </div>

            {agentLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" >
                Loading ...
                  </div>
              </div>
            ) : agentConfig ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-background rounded-lg border border-border">
                  <div className="text-2xl">
                    {(AGENT_TYPE_INFO as any)[agentConfig.agent_type]?.icon || DEFAULT_AGENT_INFO.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-text">
                        {(AGENT_TYPE_INFO as any)[agentConfig.agent_type]?.label || agentConfig.agent_type}
                      </h3>
                      <div className={`w-3 h-3 rounded-full ${(AGENT_TYPE_INFO as any)[agentConfig.agent_type]?.color || DEFAULT_AGENT_INFO.color}`} />
                      <span className={`px-2 py-1 rounded text-xs font-medium ${agentConfig.enabled
                        ? 'bg-success/20 text-success'
                        : 'bg-text-secondary/20 text-text-secondary'
                        }`}>
                        {agentConfig.enabled ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </div>
                    <p className="text-sm text-text-secondary">
                      {(AGENT_TYPE_INFO as any)[agentConfig.agent_type]?.description || 'Custom configured agent'}
                    </p>
                  </div>
                </div>

                {agentConfig.enabled && agentConfig.allowed_tools.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text mb-2">Available Tools:</h4>
                    <div className="flex flex-wrap gap-2">
                      {agentConfig.allowed_tools.map((tool) => (
                        <span key={tool} className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-md">
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-xs text-text-secondary">
                  <p>• Agent configuration is managed by your system administrator</p>
                  <p>• Contact support if you need different agent capabilities</p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Brain className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                <p className="text-text-secondary">No AI agent assigned</p>
                <p className="text-sm text-text-secondary mt-1">Contact your administrator to configure an AI agent</p>
              </div>
            )}
          </Card>

          {/* Profile Information Card */}
          <Card className="p-6 bg-surface border-border">
            <h2 className="text-lg font-semibold mb-4 text-text">Profile Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Tenant ID</label>
                <input
                  type="text"
                  value={tenant.id}
                  disabled
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Organization Name</label>
                <input
                  type="text"
                  value={tenant.name}
                  disabled
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Email</label>
                <input
                  type="email"
                  value={tenant.email}
                  disabled
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Phone</label>
                <input
                  type="text"
                  value={tenant.phone || 'Not provided'}
                  disabled
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Member Since</label>
                <input
                  type="text"
                  value={formatDate(tenant.created_at)}
                  disabled
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text"
                />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Usage & Quotas Tab */}
      {activeTab === 'usage' && quotaStatus && (
        <div className="space-y-4">
          <Card className="p-6 bg-surface border-border">
            <h2 className="text-lg font-semibold mb-4 text-text">Storage Usage</h2>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Used</span>
                <span className="font-medium text-text">
                  {formatBytes(quotaStatus.storage.used_bytes)} / {formatBytes(quotaStatus.storage.limit_bytes)}
                </span>
              </div>
              <div className="w-full bg-background rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full"
                  style={{ width: `${Math.min(quotaStatus.storage.usage_percent, 100)}%` }}
                />
              </div>
              <p className="text-xs text-text-secondary">{quotaStatus.storage.usage_percent.toFixed(1)}% used</p>
            </div>
          </Card>

          <Card className="p-6 bg-surface border-border">
            <h2 className="text-lg font-semibold mb-4 text-text">Query Usage</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium text-text-secondary mb-2">Daily</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Used</span>
                    <span className="font-medium text-text">
                      {quotaStatus.queries.daily_used} / {quotaStatus.queries.daily_limit}
                    </span>
                  </div>
                  <div className="w-full bg-background rounded-full h-2">
                    <div
                      className="bg-success h-2 rounded-full"
                      style={{ width: `${Math.min((quotaStatus.queries.daily_used / quotaStatus.queries.daily_limit) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-text-secondary mb-2">Monthly</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Used</span>
                    <span className="font-medium text-text">
                      {quotaStatus.queries.monthly_used} / {quotaStatus.queries.monthly_limit}
                    </span>
                  </div>
                  <div className="w-full bg-background rounded-full h-2">
                    <div
                      className="bg-success h-2 rounded-full"
                      style={{ width: `${Math.min((quotaStatus.queries.monthly_used / quotaStatus.queries.monthly_limit) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-surface border-border">
            <h2 className="text-lg font-semibold mb-4 text-text">Document Usage</h2>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Documents</span>
                <span className="font-medium text-text">
                  {quotaStatus.documents.used} / {quotaStatus.documents.limit}
                </span>
              </div>
              <div className="w-full bg-background rounded-full h-2">
                <div
                  className="bg-accent h-2 rounded-full"
                  style={{ width: `${Math.min(quotaStatus.documents.usage_percent, 100)}%` }}
                />
              </div>
              <p className="text-xs text-text-secondary">{quotaStatus.documents.usage_percent.toFixed(1)}% used</p>
            </div>
          </Card>
        </div>
      )}

      {/* RBAC Tab */}
      {activeTab === 'rbac' && (
        <div className="space-y-6">
          {permissionsLoading && (
            <div className="p-4 bg-background border border-border rounded-lg">
              <p className="text-text-secondary">Loading permissions...</p>
            </div>
          )}

          {/* Debug Section */}
          <Card className="p-4 bg-warning/5 border-warning/20">
            <h3 className="text-sm font-medium text-warning mb-2">🔍 Debug Information</h3>
            <div className="text-xs space-y-1">
              <p>Permissions Loading: {permissionsLoading ? 'Yes' : 'No'}</p>
              <p>Can Manage Roles: {canManageRoles() ? 'Yes' : 'No'}</p>
              <p>Can View Tenant Settings: {canViewTenantSettings() ? 'Yes' : 'No'}</p>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  try {
                    const debug = await rbacAPI.debug.getMyPermissions();
                    console.log('🔍 Current user permissions:', debug);
                    alert('Check console for permission details');
                  } catch (err) {
                    console.error('Debug failed:', err);
                    alert('Debug failed - check console');
                  }
                }}
                className="mt-2"
              >
                Check My Permissions
              </Button>
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-4 bg-surface border-border">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Shield className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium text-text">Role Management</h3>
                  <p className="text-sm text-text-secondary">Create and manage custom roles</p>
                </div>
              </div>
              <p className="text-xs text-text-secondary mb-2">
                {canManageRoles() ? 'You can manage roles' : 'View-only access'}
              </p>
            </Card>

            <Card className="p-4 bg-surface border-border">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Users className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="font-medium text-text">User Management</h3>
                  <p className="text-sm text-text-secondary">Invite and manage team members</p>
                </div>
              </div>
              <p className="text-xs text-text-secondary mb-2">
                {canManageRoles() ? 'You can assign roles' : 'View-only access'}
              </p>
            </Card>
          </div>

          <RoleManagement />
          <UserManagement />
        </div>
      )}

      {/* Billing Tab */}
      {activeTab === 'billing' && tenant && (
        <PricingGrid currentTier={tenant.billing_tier} />
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <Card className="p-6 bg-surface border-border">
          <h2 className="text-lg font-semibold mb-4 text-text">Notification Preferences</h2>
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-primary" defaultChecked />
              <span className="text-sm text-text">Email notifications for quota warnings</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-primary" defaultChecked />
              <span className="text-sm text-text">Email notifications for API errors</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-primary" />
              <span className="text-sm text-text">Weekly usage reports</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-primary" />
              <span className="text-sm text-text">Product updates and announcements</span>
            </label>
            <Button>Save Preferences</Button>
          </div>
        </Card>
      )}
      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <IntegrationsSection tenant={tenant} />
      )}
    </div>
  );
}



function IntegrationsSection({ tenant }: { tenant: Tenant | null }) {
  const { hasPermission, isSystemAdmin } = usePermissions();
  // Use lowercase permission strings to match backend response
  const canGmail = hasPermission('gmail:configure') || isSystemAdmin();
  const canDynamics = hasPermission('dynamics:configure') || isSystemAdmin();
  // Allow if has specific permission OR if can manage gmail (as a temporary fallback for existing admins)
  const canCustomCrm = hasPermission('custom_crm:configure') || hasPermission('gmail:configure') || isSystemAdmin();

  // Determine default tab
  const defaultTab = canGmail ? 'gmail' : (canDynamics ? 'dynamics' : (canCustomCrm ? 'custom-crm' : 'gmail'));
  const [activeIntegration, setActiveIntegration] = useState<'gmail' | 'dynamics' | 'custom-crm'>(defaultTab);

  if (!canGmail && !canDynamics && !canCustomCrm) {
    return (
      <Card className="p-6 bg-surface border-border">
        <div className="flex items-center gap-3 text-warning">
          <AlertCircle className="w-5 h-5" />
          <p>You do not have permission to configure integrations.</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-4 border-b border-border">
        {canGmail && (
          <button
            onClick={() => setActiveIntegration('gmail')}
            className={`pb-2 px-1 border-b-2 transition-colors ${activeIntegration === 'gmail'
              ? 'border-primary text-primary font-medium'
              : 'border-transparent text-text-secondary hover:text-text'
              }`}
          >
            Gmail
          </button>
        )}
        {canDynamics && (
          <button
            onClick={() => setActiveIntegration('dynamics')}
            className={`pb-2 px-1 border-b-2 transition-colors ${activeIntegration === 'dynamics'
              ? 'border-primary text-primary font-medium'
              : 'border-transparent text-text-secondary hover:text-text'
              }`}
          >
            Dynamics 365
          </button>
        )}
        {canCustomCrm && (
          <button
            onClick={() => setActiveIntegration('custom-crm')}
            className={`pb-2 px-1 border-b-2 transition-colors ${activeIntegration === 'custom-crm'
              ? 'border-primary text-primary font-medium'
              : 'border-transparent text-text-secondary hover:text-text'
              }`}
          >
            Custom CRM (Beta)
          </button>
        )}
      </div>

      <div className="text-xs text-gray-400 mb-2">
        Debug: G={canGmail ? 'Yes' : 'No'}, D={canDynamics ? 'Yes' : 'No'}, C={canCustomCrm ? 'Yes' : 'No'}
      </div>

      {activeIntegration === 'gmail' && canGmail && (
        <GmailSettings tenant={tenant} />
      )}

      {activeIntegration === 'dynamics' && canDynamics && (
        <DynamicsSettings />
      )}

      {activeIntegration === 'custom-crm' && canCustomCrm && (
        <CustomCrmSettings />
      )}
    </div>
  );
}

