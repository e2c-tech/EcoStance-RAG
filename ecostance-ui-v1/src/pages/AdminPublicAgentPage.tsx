import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Checkbox } from '@/components/ui/Checkbox';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { Icons } from '@/components/icons';
import { Badge } from '@/components/ui/Badge';
import { publicAgentAPI } from '@/services/api';

interface KnowledgeBase {
  kb_name: string;
  document_count: number;
}

interface DatabaseConnection {
  name: string;
  type: string;
}

interface PublicAgentConfig {
  enabled: boolean;
  agent_type: string;
  allowed_kbs: string[];
  allowed_dbs: string[];
  welcome_message: string;
  system_prompt?: string;
  suggested_questions: string[];
  branding: {
    logo_url?: string;
    primary_color: string;
    company_name: string;
    font_family?: string;
    font_size_base?: number;
  };
  rate_limit: {
    queries_per_minute: number;
    max_messages_per_session: number;
  };
  features: {
    show_sources: boolean;
    allow_feedback: boolean;
    show_suggested_questions: boolean;
    enable_database_tools: boolean;
    enable_knowledge_base: boolean;
  };
}

const FONT_OPTIONS = [
  { value: 'Inter, sans-serif', label: 'Inter (Default)' },
  { value: 'Roboto, sans-serif', label: 'Roboto' },
  { value: 'Open Sans, sans-serif', label: 'Open Sans' },
  { value: 'Lato, sans-serif', label: 'Lato' },
  { value: 'Poppins, sans-serif', label: 'Poppins' },
  { value: 'Montserrat, sans-serif', label: 'Montserrat' },
  { value: 'Playfair Display, serif', label: 'Playfair Display' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Times New Roman, serif', label: 'Times New Roman' },
];

const PERSONA_CONFIG: Record<string, { label: string; icon: any; description: string }> = {
  security_analyst: {
    label: 'SOC Assistant',
    icon: Icons.Shield,
    description: 'Expert in log discovery, security events, and threat analysis'
  },
  quickship: {
    label: 'Logistics Support',
    icon: Icons.Truck || Icons.Package,
    description: 'Specialized in shipment tracking, logistics, and supply chain'
  },
  ecommerce: {
    label: 'Shopping Assistant',
    icon: Icons.ShoppingCart || Icons.LayoutGrid,
    description: 'Expert in product discovery and e-commerce support'
  },
  ecostance: {
    label: 'Sustainability Expert',
    icon: Icons.Leaf || Icons.Activity,
    description: 'Focused on environmental impact and carbon offsets'
  },
  generic: {
    label: 'AI Assistant',
    icon: Icons.Sparkles,
    description: 'General-purpose AI assistant with access to your data'
  }
};


const AdminPublicAgentPage: React.FC = () => {
  const [config, setConfig] = useState<PublicAgentConfig | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [databases, setDatabases] = useState<DatabaseConnection[]>([]);
  const [newQuestion, setNewQuestion] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('[AdminPublicAgentPage] Loading data...');
        const [configData, kbsData, dbsData] = await Promise.all([
          publicAgentAPI.admin.getConfig(),
          publicAgentAPI.admin.getAvailableKBs(),
          publicAgentAPI.admin.getAvailableDBs(),
        ]) as any;

        console.log('[AdminPublicAgentPage] Config data:', configData);
        console.log('[AdminPublicAgentPage] KBs data:', kbsData);
        console.log('[AdminPublicAgentPage] DBs data:', dbsData);

        // Ensure branding has font defaults
        const configWithDefaults = {
          ...configData,
          branding: {
            ...configData.branding,
            font_family: configData.branding?.font_family || 'Inter, sans-serif',
            font_size_base: configData.branding?.font_size_base || 14,
          }
        };

        setConfig(configWithDefaults as any);

        const transformedKBs: KnowledgeBase[] = Array.isArray(kbsData)
          ? (kbsData as any[]).map((kb: any) => {
            if (typeof kb === 'string') {
              return { kb_name: kb, document_count: 0 };
            }
            return {
              kb_name: kb.kb_name || kb.name || String(kb),
              document_count: kb.document_count || kb.documents?.length || 0,
            };
          })
          : [];

        console.log('[AdminPublicAgentPage] Transformed KBs:', transformedKBs);
        setKnowledgeBases(transformedKBs);
        setDatabases(Array.isArray(dbsData) ? dbsData : []);
      } catch (err: any) {
        console.error('Error loading data:', err);
        setError(err.message || 'Failed to load configuration');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  const handleKBToggle = (kbName: string) => {
    if (!config) return;
    setConfig(prev => prev ? ({
      ...prev,
      allowed_kbs: prev.allowed_kbs.includes(kbName)
        ? prev.allowed_kbs.filter(name => name !== kbName)
        : [...prev.allowed_kbs, kbName]
    }) : prev);
  };

  const handleDBToggle = (dbName: string) => {
    if (!config) return;
    setConfig(prev => prev ? ({
      ...prev,
      allowed_dbs: prev.allowed_dbs.includes(dbName)
        ? prev.allowed_dbs.filter(name => name !== dbName)
        : [...prev.allowed_dbs, dbName]
    }) : prev);
  };

  const handleAddQuestion = () => {
    if (!config || !newQuestion.trim() || config.suggested_questions.length >= 10) return;
    setConfig(prev => prev ? ({
      ...prev,
      suggested_questions: [...prev.suggested_questions, newQuestion.trim()]
    }) : prev);
    setNewQuestion('');
  };

  const handleRemoveQuestion = (index: number) => {
    if (!config) return;
    setConfig(prev => prev ? ({
      ...prev,
      suggested_questions: prev.suggested_questions.filter((_, i) => i !== index)
    }) : prev);
  };

  const handleSave = async () => {
    if (!config) return;

    console.log('[AdminPublicAgentPage] Saving config:', config);
    console.log('[AdminPublicAgentPage] Branding object:', config.branding);
    console.log('[AdminPublicAgentPage] Font family:', config.branding.font_family);
    console.log('[AdminPublicAgentPage] Font size:', config.branding.font_size_base);
    console.log('[AdminPublicAgentPage] Current allowed_kbs:', config.allowed_kbs);

    setIsSaving(true);
    setSaveStatus('idle');

    try {
      const result = await publicAgentAPI.admin.updateConfig(config);
      console.log('[AdminPublicAgentPage] Save result:', result);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);

      // Refresh the configuration to ensure we have the latest state
      console.log('[AdminPublicAgentPage] Refreshing config after save...');
      const updatedConfig = await publicAgentAPI.admin.getConfig();
      console.log('[AdminPublicAgentPage] Updated config from server:', updatedConfig);
      setConfig(updatedConfig as any);
    } catch (err: any) {
      console.error('Error saving config:', err);
      setSaveStatus('error');
      setError(err.message || 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Icons.Spinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-6">
        <div className="text-center">
          <Icons.AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text mb-2">Failed to Load Configuration</h2>
          <p className="text-text-secondary">{error || 'Unable to load public agent configuration'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-surface border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-primary/10 rounded-lg">
                {(() => {
                  const persona = PERSONA_CONFIG[config.agent_type] || PERSONA_CONFIG.generic;
                  const Icon = persona.icon;
                  return <Icon className="h-6 w-6 text-primary" />;
                })()}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-text">Public AI Agent</h1>
                <p className="text-sm text-text-secondary">Configure your public-facing AI assistant</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {saveStatus === 'success' && (
                <span className="text-sm text-success flex items-center gap-1 bg-success/10 px-3 py-1.5 rounded-lg">
                  <Icons.Check className="h-4 w-4" />
                  Saved
                </span>
              )}
              {saveStatus === 'error' && (
                <span className="text-sm text-error flex items-center gap-1 bg-error/10 px-3 py-1.5 rounded-lg">
                  <Icons.AlertCircle className="h-4 w-4" />
                  Failed
                </span>
              )}
              <Button onClick={handleSave} disabled={isSaving} className="bg-primary hover:bg-primary/90">
                {isSaving ? (
                  <>
                    <Icons.Spinner className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Icons.Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Column - Main Settings */}
          <div className="lg:col-span-2 space-y-6">
            {/* Persona Info Card */}
            {config.agent_type && (
              <Card className="bg-surface border-border overflow-hidden">
                <div className="bg-primary/5 p-4 border-b border-border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {(() => {
                        const persona = PERSONA_CONFIG[config.agent_type] || PERSONA_CONFIG.generic;
                        const Icon = persona.icon;
                        return <Icon className="h-5 w-5 text-primary" />;
                      })()}
                      <div>
                        <p className="text-sm font-bold text-text uppercase tracking-wider">Active Persona</p>
                        <p className="text-xs text-text-secondary">Managed by Super Admin</p>
                      </div>
                    </div>
                    <Badge variant="outline" className="bg-background border-primary/20 text-primary">
                      {PERSONA_CONFIG[config.agent_type]?.label || config.agent_type.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                </div>
                <div className="p-4 bg-background/50">
                  <p className="text-sm text-text-secondary italic">
                    "{PERSONA_CONFIG[config.agent_type]?.description || PERSONA_CONFIG.generic.description}"
                  </p>
                </div>
              </Card>
            )}

            {/* Status Card */}
            <Card className="bg-surface border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-full ${config.enabled ? 'bg-success/20' : 'bg-surface-hover'}`}>
                      <div className={`h-3 w-3 rounded-full ${config.enabled ? 'bg-success' : 'bg-text-secondary'}`} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-text">Agent Status</h3>
                      <p className="text-sm text-text-secondary mt-0.5">
                        {config.enabled ? 'Public access enabled at /public-agent' : 'Agent is currently disabled'}
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.enabled}
                      onChange={(e) => setConfig(prev => prev ? ({ ...prev, enabled: e.target.checked }) : prev)}
                      className="sr-only peer"
                    />
                    <div className="w-14 h-7 bg-surface-hover peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-text after:border-border after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </CardContent>
            </Card>


            {/* Features Card */}
            <Card className="bg-surface border-border">
              <CardHeader className="border-b border-border pb-4">
                <CardTitle className="text-lg font-semibold text-text">Features & Capabilities</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {[
                  { key: 'enable_database_tools', icon: Icons.Database, label: 'Database Tools', desc: 'Query connected databases' },
                  { key: 'enable_knowledge_base', icon: Icons.BookOpen, label: 'Knowledge Base', desc: 'Search document collections' },
                  { key: 'show_sources', icon: Icons.FileText, label: 'Show Sources', desc: 'Display source references' },
                  { key: 'allow_feedback', icon: Icons.CheckCircle, label: 'User Feedback', desc: 'Thumbs up/down ratings' },
                  { key: 'show_suggested_questions', icon: Icons.MessageSquare, label: 'Suggested Questions', desc: 'Show starter prompts' },
                ].map(({ key, icon: Icon, label, desc }) => (
                  <div key={key} className="flex items-center justify-between p-3 rounded-lg hover:bg-surface-hover transition-colors">
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-medium text-text">{label}</p>
                        <p className="text-sm text-text-secondary">{desc}</p>
                      </div>
                    </div>
                    <Checkbox
                      checked={config.features[key as keyof typeof config.features]}
                      onChange={(e) => setConfig(prev => prev ? ({
                        ...prev,
                        features: { ...prev.features, [key]: e.target.checked }
                      }) : prev)}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Knowledge Bases */}
            {config.features.enable_knowledge_base && (
              <Card className="bg-surface border-border">
                <CardHeader className="border-b border-border pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold text-text">Knowledge Bases</CardTitle>
                    <Badge variant="secondary">{config.allowed_kbs.length} selected</Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-6">
                  {knowledgeBases.length === 0 ? (
                    <div className="text-center py-8">
                      <Icons.BookOpen className="h-12 w-12 text-text-secondary mx-auto mb-3" />
                      <p className="text-sm text-text-secondary">No knowledge bases available</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {knowledgeBases.map((kb) => (
                        <div key={kb.kb_name} className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-primary hover:bg-surface-hover transition-all">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={config.allowed_kbs.includes(kb.kb_name)}
                              onChange={() => handleKBToggle(kb.kb_name)}
                            />
                            <div>
                              <p className="font-medium text-text">{kb.kb_name}</p>
                              <p className="text-xs text-text-secondary">{kb.document_count} documents</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Database Connections */}
            {config.features.enable_database_tools && (
              <Card className="bg-surface border-border">
                <CardHeader className="border-b border-border pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold text-text">Database Connections</CardTitle>
                    <Badge variant="secondary">{config.allowed_dbs.length} selected</Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-6">
                  {databases.length === 0 ? (
                    <div className="text-center py-8">
                      <Icons.Database className="h-12 w-12 text-text-secondary mx-auto mb-3" />
                      <p className="text-sm text-text-secondary">No database connections available</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {databases.map((db) => (
                        <div key={db.name} className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-primary hover:bg-surface-hover transition-all">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={config.allowed_dbs.includes(db.name)}
                              onChange={() => handleDBToggle(db.name)}
                            />
                            <div>
                              <p className="font-medium text-text">{db.name}</p>
                              <p className="text-xs text-text-secondary">{db.type}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Branding & Settings */}
          <div className="space-y-6">
            {/* Branding */}
            <Card className="bg-surface border-border">
              <CardHeader className="border-b border-border pb-4">
                <CardTitle className="text-lg font-semibold text-text">Branding</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label className="text-sm font-medium text-text">Company Name</Label>
                  <Input
                    value={config.branding.company_name}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      branding: { ...prev.branding, company_name: e.target.value }
                    }) : prev)}
                    placeholder="Your Company"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium text-text">Logo URL</Label>
                  <Input
                    value={config.branding.logo_url || ''}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      branding: { ...prev.branding, logo_url: e.target.value }
                    }) : prev)}
                    placeholder="https://example.com/logo.png"
                    className="mt-1.5"
                  />
                  <p className="text-xs text-text-secondary mt-1">Optional - leave empty for default</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-text">Primary Color</Label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      type="color"
                      value={config.branding.primary_color}
                      onChange={(e) => setConfig(prev => prev ? ({
                        ...prev,
                        branding: { ...prev.branding, primary_color: e.target.value }
                      }) : prev)}
                      className="w-16 h-10 p-1 cursor-pointer"
                    />
                    <Input
                      value={config.branding.primary_color}
                      onChange={(e) => setConfig(prev => prev ? ({
                        ...prev,
                        branding: { ...prev.branding, primary_color: e.target.value }
                      }) : prev)}
                      placeholder="#0066CC"
                      className="flex-1"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-text">Font Family</Label>
                  <Select
                    value={config.branding.font_family || 'Inter, sans-serif'}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      branding: { ...prev.branding, font_family: e.target.value }
                    }) : prev)}
                    className="mt-1.5"
                  >
                    {FONT_OPTIONS.map(font => (
                      <option key={font.value} value={font.value}>
                        {font.label}
                      </option>
                    ))}
                  </Select>
                </div>

                <div>
                  <Label className="text-sm font-medium text-text">Base Font Size (px)</Label>
                  <Input
                    type="number"
                    min="10"
                    max="20"
                    value={config.branding.font_size_base || 14}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      branding: { ...prev.branding, font_size_base: parseInt(e.target.value) || 14 }
                    }) : prev)}
                    className="mt-1.5"
                  />
                  <p className="text-xs text-text-secondary mt-1">Range: 10-20 pixels</p>
                </div>
              </CardContent>
            </Card>

            {/* Rate Limits */}
            <Card className="bg-surface border-border">
              <CardHeader className="border-b border-border pb-4">
                <CardTitle className="text-lg font-semibold text-text">Rate Limits</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label className="text-sm font-medium text-text">Queries Per Minute</Label>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={config.rate_limit.queries_per_minute}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      rate_limit: { ...prev.rate_limit, queries_per_minute: parseInt(e.target.value) || 10 }
                    }) : prev)}
                    className="mt-1.5"
                  />
                  <p className="text-xs text-text-secondary mt-1">Limit requests per user</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-text">Max Messages Per Session</Label>
                  <Input
                    type="number"
                    min="1"
                    max="200"
                    value={config.rate_limit.max_messages_per_session}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      rate_limit: { ...prev.rate_limit, max_messages_per_session: parseInt(e.target.value) || 50 }
                    }) : prev)}
                    className="mt-1.5"
                  />
                  <p className="text-xs text-text-secondary mt-1">Maximum conversation length</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Messages Section - Full Width */}
        <Card className="bg-surface border-border mt-6">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="text-lg font-semibold text-text">Messages & Prompts</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div>
              <Label className="text-sm font-medium text-text">Welcome Message</Label>
              <textarea
                className="w-full px-4 py-3 mt-1.5 bg-background border border-border rounded-lg text-text resize-none focus:ring-2 focus:ring-primary focus:border-transparent"
                rows={3}
                value={config.welcome_message}
                onChange={(e) => setConfig(prev => prev ? ({ ...prev, welcome_message: e.target.value }) : prev)}
                placeholder="Hi! How can I help you today?"
              />
              <p className="text-xs text-text-secondary mt-1">First message users see when they open the chat</p>
            </div>
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-sm font-medium text-text">Suggested Questions</Label>
                <span className="text-xs text-text-secondary">{config.suggested_questions.length}/10</span>
              </div>
              <div className="space-y-2">
                {config.suggested_questions.map((question, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 bg-surface-hover rounded-lg group">
                    <span className="text-sm text-text-secondary px-2">{index + 1}.</span>
                    <Input value={question} readOnly className="flex-1 bg-background border-border" />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRemoveQuestion(index)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Icons.X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {config.suggested_questions.length < 10 && (
                  <div className="flex gap-2 pt-2">
                    <Input
                      value={newQuestion}
                      onChange={(e) => setNewQuestion(e.target.value)}
                      placeholder="Add a suggested question..."
                      onKeyDown={(e) => e.key === 'Enter' && handleAddQuestion()}
                      className="flex-1"
                    />
                    <Button onClick={handleAddQuestion} disabled={!newQuestion.trim()} className="bg-primary hover:bg-primary/90">
                      <Icons.Plus className="h-4 w-4 mr-1" />
                      Add
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
};

export default AdminPublicAgentPage;

