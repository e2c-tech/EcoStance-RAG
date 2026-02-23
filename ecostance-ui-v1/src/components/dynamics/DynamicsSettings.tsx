import React, { useState, useEffect } from 'react';
import { useIntegrations } from '../../context/IntegrationContext';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Badge } from '../ui/Badge';
import { dynamicsAPI } from '../../services/dynamicsAPI';
import { CheckCircle, XCircle, Loader2, Save, Play } from 'lucide-react';

export default function DynamicsSettings() {
    const {
        dynamicsConfig: config,
        fetchDynamicsConfig: loadConfig,
        isLoading: loading
    } = useIntegrations();

    const [configState, setConfigState] = useState(config);

    // Sync local state when context config changes
    useEffect(() => {
        setConfigState(config);
    }, [config]);

    const [localLoading, setLocalLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [testing, setTesting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        loadConfig();
    }, [loadConfig]);


    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setConfigState(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = async () => {
        try {
            setLocalLoading(true);
            setMessage(null);
            await dynamicsAPI.saveConfig({
                tenant_id: configState.tenant_id,
                client_id: configState.client_id,
                client_secret: configState.client_secret,
                resource_url: configState.resource_url
            });
            setMessage({ type: 'success', text: 'Configuration saved successfully' });
            // Reload to update status
            loadConfig(true);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Failed to save configuration' });
        } finally {
            setLocalLoading(false);
        }
    };

    const handleTest = async () => {
        try {
            setTesting(true);
            setMessage(null);
            const res = await dynamicsAPI.testConnection();
            if (res.success) {
                setMessage({ type: 'success', text: res.message });
            } else {
                setMessage({ type: 'error', text: res.message });
            }
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Connection failed' });
        } finally {
            setTesting(false);
        }
    };

    const handleSync = async () => {
        try {
            setSyncing(true);
            setMessage(null);
            const res = await dynamicsAPI.syncNow();
            setMessage({ type: 'success', text: `${res.message}. Found ${res.emails_found} emails.` });
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Sync failed' });
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="space-y-6">
            <Card className="p-6 bg-surface border-border">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="text-xl font-semibold flex items-center gap-2 text-text">
                            Dynamics 365 Integration
                        </h2>
                        <p className="text-sm text-text-secondary mt-1">
                            Connect your Microsoft Dynamics 365 environment to sync emails.
                        </p>
                    </div>
                    <div>
                        {configState.is_configured ? (
                            <Badge variant="success" className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Connected
                            </Badge>
                        ) : (
                            <Badge variant="secondary" className="flex items-center gap-1 text-text-secondary">
                                <XCircle className="w-3 h-3" /> Not Connected
                            </Badge>
                        )}
                    </div>
                </div>

                {message && (
                    <div className={`p-4 rounded-lg mb-6 ${message.type === 'success' ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}`}>
                        {message.text}
                    </div>
                )}

                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="tenant_id" className="text-text-secondary">Azure Tenant ID</Label>
                            <Input
                                id="tenant_id"
                                name="tenant_id"
                                value={configState.tenant_id}
                                onChange={handleInputChange}
                                placeholder="00000000-0000-0000-0000-000000000000"
                                className="bg-background border-border text-text"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="client_id" className="text-text-secondary">Client ID</Label>
                            <Input
                                id="client_id"
                                name="client_id"
                                value={configState.client_id}
                                onChange={handleInputChange}
                                placeholder="00000000-0000-0000-0000-000000000000"
                                className="bg-background border-border text-text"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="client_secret" className="text-text-secondary">Client Secret</Label>
                        <Input
                            id="client_secret"
                            name="client_secret"
                            type="password"
                            value={configState.client_secret}
                            onChange={handleInputChange}
                            placeholder="Value from App Registration"
                            className="bg-background border-border text-text"
                        />
                        <p className="text-xs text-text-secondary">Hidden for security. Only enter to update.</p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="resource_url" className="text-text-secondary">CRM URL</Label>
                        <Input
                            id="resource_url"
                            name="resource_url"
                            value={configState.resource_url}
                            onChange={handleInputChange}
                            placeholder="https://org123.crm.dynamics.com"
                            className="bg-background border-border text-text"
                        />
                    </div>
                </div>

                <div className="flex justify-end items-center gap-3 mt-8">
                    <Button variant="outline" onClick={handleTest} disabled={loading || testing || syncing}>
                        {testing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Test Connection
                    </Button>
                    <Button onClick={handleSave} disabled={loading || localLoading || testing || syncing}>
                        {localLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                        Save Configuration
                    </Button>
                </div>
            </Card>

            {config.is_configured && (
                <Card className="p-6 bg-surface border-border">
                    <h3 className="text-lg font-semibold mb-4 text-text">Actions</h3>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-text">Manual Sync</p>
                            <p className="text-xs text-text-secondary">Trigger a sync immediately (last sync: {config.last_sync || 'Never'})</p>
                        </div>
                        <Button variant="outline" onClick={handleSync} disabled={syncing}>
                            {syncing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                            Sync Now
                        </Button>
                    </div>
                </Card>
            )}
        </div>
    );
}
