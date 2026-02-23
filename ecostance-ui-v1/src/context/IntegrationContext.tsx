import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { gmailAPI, customCrmAPI } from '../services/api';
import { dynamicsAPI, DynamicsConfigPayload } from '../services/dynamicsAPI';
import { useAuth } from './AuthContext.v2';

interface GmailStatus {
    connected: boolean;
    email: string | null;
}

interface DynamicsConfig extends DynamicsConfigPayload {
    is_configured?: boolean;
    last_sync?: string;
}

interface SyncedEmail {
    internal_id: string;
    original_crm_id: string;
    subject: string;
    sender: string;
    received_at: string;
}

interface IntegrationContextType {
    gmailStatus: GmailStatus;
    dynamicsConfig: DynamicsConfig;
    customCrmEmails: SyncedEmail[];
    isLoading: boolean;
    error: string | null;
    fetchGmailStatus: (force?: boolean) => Promise<void>;
    fetchDynamicsConfig: (force?: boolean) => Promise<void>;
    fetchCustomCrmEmails: (force?: boolean) => Promise<void>;
    refreshAll: () => Promise<void>;
}

const IntegrationContext = createContext<IntegrationContextType | undefined>(undefined);

export const IntegrationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { user } = useAuth();
    const [gmailStatus, setGmailStatus] = useState<GmailStatus>({ connected: false, email: null });
    const [dynamicsConfig, setDynamicsConfig] = useState<DynamicsConfig>({
        tenant_id: '',
        client_id: '',
        client_secret: '',
        resource_url: '',
        is_configured: false
    });
    const [customCrmEmails, setCustomCrmEmails] = useState<SyncedEmail[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loadedStates, setLoadedStates] = useState({ gmail: false, dynamics: false, customCrm: false });

    // Clear state when tenant changes
    useEffect(() => {
        setGmailStatus({ connected: false, email: null });
        setDynamicsConfig({
            tenant_id: '',
            client_id: '',
            client_secret: '',
            resource_url: '',
            is_configured: false
        });
        setCustomCrmEmails([]);
        setLoadedStates({ gmail: false, dynamics: false, customCrm: false });
        setError(null);
    }, [user?.tenantId]);

    const fetchGmailStatus = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.gmail && !force) return;

        try {
            setIsLoading(true);
            const status = await gmailAPI.auth.getStatus();
            setGmailStatus(status);
            setLoadedStates(prev => ({ ...prev, gmail: true }));
        } catch (err: any) {
            console.error('Failed to fetch Gmail status:', err);
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.gmail]);

    const fetchDynamicsConfig = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.dynamics && !force) return;

        try {
            setIsLoading(true);
            const data = await dynamicsAPI.getConfig();
            setDynamicsConfig({
                tenant_id: data.tenant_id || '',
                client_id: data.client_id || '',
                resource_url: data.resource_url || '',
                is_configured: data.is_configured,
                last_sync: data.last_sync || undefined,
                client_secret: '' // Don't cache secret
            });
            setLoadedStates(prev => ({ ...prev, dynamics: true }));
        } catch (err: any) {
            console.error('Failed to load dynamics config:', err);
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.dynamics]);

    const fetchCustomCrmEmails = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.customCrm && !force) return;

        try {
            setIsLoading(true);
            const data = await customCrmAPI.getEmails();
            if (Array.isArray(data)) {
                setCustomCrmEmails(data);
            } else if (data && Array.isArray((data as any).emails)) {
                setCustomCrmEmails((data as any).emails);
            } else {
                setCustomCrmEmails([]);
            }
            setLoadedStates(prev => ({ ...prev, customCrm: true }));
        } catch (err: any) {
            console.error('Failed to load custom CRM emails:', err);
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.customCrm]);

    const refreshAll = useCallback(async () => {
        await Promise.all([
            fetchGmailStatus(true),
            fetchDynamicsConfig(true),
            fetchCustomCrmEmails(true)
        ]);
    }, [fetchGmailStatus, fetchDynamicsConfig, fetchCustomCrmEmails]);

    return (
        <IntegrationContext.Provider value={{
            gmailStatus,
            dynamicsConfig,
            customCrmEmails,
            isLoading,
            error,
            fetchGmailStatus,
            fetchDynamicsConfig,
            fetchCustomCrmEmails,
            refreshAll
        }}>
            {children}
        </IntegrationContext.Provider>
    );
};

export const useIntegrations = () => {
    const context = useContext(IntegrationContext);
    if (context === undefined) {
        throw new Error('useIntegrations must be used within an IntegrationProvider');
    }
    return context;
};
