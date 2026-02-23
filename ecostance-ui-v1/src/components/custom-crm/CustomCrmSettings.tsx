import { useState, useEffect } from 'react';
import { customCrmAPI } from '../../services/api';
import { useIntegrations } from '../../context/IntegrationContext';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { RefreshCw, Mail, CheckCircle, AlertCircle, Loader2, Database } from 'lucide-react';


export default function CustomCrmSettings() {
    const {
        customCrmEmails: emails,
        fetchCustomCrmEmails: loadEmails,
        isLoading: loading
    } = useIntegrations();

    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadEmails();
    }, [loadEmails]);


    const handleSync = async () => {
        setSyncing(true);
        setError(null);
        setSuccess(null);
        try {
            await customCrmAPI.sync();
            setSuccess('Sync triggered successfully. Emails are being ingested in the background.');

            // Poll or reload after a delay
            setTimeout(() => {
                loadEmails(true);
            }, 3000);

        } catch (err: any) {
            setError(err.message || 'Failed to trigger sync.');
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="space-y-6">
            <Card className="p-6 bg-surface border-border">
                <div className="flex items-start justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-blue-500/10 rounded-xl">
                            <Database className="w-6 h-6 text-blue-500" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-text">Custom CRM Integration</h3>
                            <p className="text-sm text-text-secondary">Sync emails from your local Custom CRM to the Knowledge Base.</p>
                        </div>
                    </div>
                    <Button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2"
                    >
                        {syncing ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Syncing...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="w-4 h-4" />
                                Sync Now
                            </>
                        )}
                    </Button>
                </div>

                {error && (
                    <div className="mb-4 p-4 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-error">{error}</p>
                    </div>
                )}

                {success && (
                    <div className="mb-4 p-4 bg-success/10 border border-success/20 rounded-lg flex items-start gap-2">
                        <CheckCircle className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-success">{success}</p>
                    </div>
                )}

                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium text-text-secondary">Synced Emails History</h4>
                        <span className="text-xs text-text-secondary">
                            {emails.length} records found
                        </span>
                    </div>

                    <div className="border border-border rounded-lg overflow-hidden">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-background-secondary border-b border-border">
                                <tr>
                                    <th className="px-4 py-3 font-medium text-text-secondary">Subject</th>
                                    <th className="px-4 py-3 font-medium text-text-secondary">Sender</th>
                                    <th className="px-4 py-3 font-medium text-text-secondary">Received Date</th>
                                    <th className="px-4 py-3 font-medium text-text-secondary">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border bg-surface">
                                {loading ? (
                                    <tr>
                                        <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                                            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                                            Loading history...
                                        </td>
                                    </tr>
                                ) : emails.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                                            <Mail className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                            No emails synced yet. Click "Sync Now" to start.
                                        </td>
                                    </tr>
                                ) : (
                                    emails.map((email) => (
                                        <tr key={email.internal_id} className="hover:bg-background/50 transition-colors">
                                            <td className="px-4 py-3 text-text font-medium truncate max-w-[200px]" title={email.subject}>
                                                {email.subject || '(No Subject)'}
                                            </td>
                                            <td className="px-4 py-3 text-text-secondary truncate max-w-[150px]" title={email.sender}>
                                                {email.sender}
                                            </td>
                                            <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                                                {new Date(email.received_at).toLocaleDateString()} {new Date(email.received_at).toLocaleTimeString()}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-success/10 text-success border border-success/20">
                                                    <CheckCircle className="w-3 h-3" />
                                                    Synced
                                                </span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </Card>
        </div>
    );
}
