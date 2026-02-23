import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { tenantsAPI, quotaAPI, publicAgentAPI } from '../services/api';
import { useAuth } from './AuthContext.v2';

export interface Tenant {
    id: string;
    name: string;
    email: string;
    phone?: string;
    billing_tier: string;
    billing_status: string;
    created_at: string;
    gmail_config?: {
        is_connected: boolean;
        connected_email?: string;
    };
}

export interface QuotaStatus {
    storage: { limit_bytes: number; used_bytes: number; usage_percent: number };
    queries: { daily_limit: number; daily_used: number; monthly_limit: number; monthly_used: number };
    documents: { limit: number; used: number; usage_percent: number };
}

interface AgentConfig {
    agent_type: string;
    enabled: boolean;
    allowed_tools: string[];
    branding: {
        logo_url?: string;
        primary_color: string;
        company_name: string;
    };
}

interface TenantContextType {
    tenant: Tenant | null;
    quotaStatus: QuotaStatus | null;
    agentConfig: AgentConfig | null;
    isLoading: boolean;
    error: string | null;
    fetchTenantData: (force?: boolean) => Promise<void>;
    fetchQuotaStatus: (force?: boolean) => Promise<void>;
    fetchAgentConfig: (force?: boolean) => Promise<void>;
    refreshAll: () => Promise<void>;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export const TenantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { user } = useAuth();
    const [tenant, setTenant] = useState<Tenant | null>(null);
    const [quotaStatus, setQuotaStatus] = useState<QuotaStatus | null>(null);
    const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [hasLoadedTenant, setHasLoadedTenant] = useState(false);
    const [hasLoadedQuota, setHasLoadedQuota] = useState(false);
    const [hasLoadedAgent, setHasLoadedAgent] = useState(false);

    // Clear data when user switches
    useEffect(() => {
        setTenant(null);
        setQuotaStatus(null);
        setAgentConfig(null);
        setHasLoadedTenant(false);
        setHasLoadedQuota(false);
        setHasLoadedAgent(false);
    }, [user?.tenantId]);

    const fetchTenantData = useCallback(async (force = false) => {
        if (hasLoadedTenant && !force && tenant) return;

        try {
            setIsLoading(true);
            const data = await tenantsAPI.getCurrentTenant() as Tenant;
            setTenant(data);
            setHasLoadedTenant(true);
        } catch (err: any) {
            setError(err.message || 'Failed to load tenant data');
        } finally {
            setIsLoading(false);
        }
    }, [hasLoadedTenant, tenant]);

    const fetchQuotaStatus = useCallback(async (force = false) => {
        if (hasLoadedQuota && !force && quotaStatus) return;

        try {
            const response = await quotaAPI.getStatus() as { data: QuotaStatus };
            setQuotaStatus(response.data);
            setHasLoadedQuota(true);
        } catch (err: any) {
            console.error('Failed to load quota:', err);
        }
    }, [hasLoadedQuota, quotaStatus]);

    const fetchAgentConfig = useCallback(async (force = false) => {
        if (hasLoadedAgent && !force && agentConfig) return;

        try {
            const config = await publicAgentAPI.admin.getConfig();
            setAgentConfig(config as AgentConfig);
            setHasLoadedAgent(true);
        } catch (err: any) {
            console.error('Failed to load agent config:', err);
            // Even if it fails, mark as loaded to prevent constant retries if backend returns 404
            setHasLoadedAgent(true);
            if (!agentConfig) {
                setAgentConfig({
                    agent_type: 'generic',
                    enabled: false,
                    allowed_tools: [],
                    branding: {
                        primary_color: '#0066CC',
                        company_name: tenant?.name || 'Company'
                    }
                });
            }
        }
    }, [hasLoadedAgent, agentConfig, tenant?.name]);

    const refreshAll = useCallback(async () => {
        setIsLoading(true);
        await Promise.allSettled([
            fetchTenantData(true),
            fetchQuotaStatus(true),
            fetchAgentConfig(true)
        ]);
        setIsLoading(false);
    }, [fetchTenantData, fetchQuotaStatus, fetchAgentConfig]);

    return (
        <TenantContext.Provider value={{
            tenant,
            quotaStatus,
            agentConfig,
            isLoading,
            error,
            fetchTenantData,
            fetchQuotaStatus,
            fetchAgentConfig,
            refreshAll
        }}>
            {children}
        </TenantContext.Provider>
    );
};

export const useTenant = () => {
    const context = useContext(TenantContext);
    if (context === undefined) {
        throw new Error('useTenant must be used within a TenantProvider');
    }
    return context;
};
