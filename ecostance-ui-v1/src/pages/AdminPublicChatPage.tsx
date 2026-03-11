import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Checkbox } from '@/components/ui/Checkbox';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { Icons } from '@/components/icons';
import { Badge } from '@/components/ui/Badge';
import { publicChatAPI } from '@/services/api';

interface KnowledgeBase {
  kb_name: string;
  document_count: number;
}

interface PublicChatConfig {
  enabled: boolean;
  allowed_kbs: string[];
  welcome_message: string;
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
  };
  agent_type: string;
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

const PERSONA_CONFIG: Record<string, { label: string; icon: any }> = {
  security_analyst: { label: 'SOC Assistant', icon: Icons.Shield },
  quickship: { label: 'Logistics Support', icon: Icons.Package },
  ecommerce: { label: 'Shopping Assistant', icon: Icons.ShoppingCart || Icons.LayoutGrid },
  ecostance: { label: 'Sustainability Expert', icon: Icons.Leaf || Icons.Activity },
  generic: { label: 'AI Assistant', icon: Icons.Sparkles },
};

const AdminPublicChatPage: React.FC = () => {
  const [config, setConfig] = useState<PublicChatConfig | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [newQuestion, setNewQuestion] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  // Load configuration and available KBs
  useEffect(() => {
    const loadData = async () => {
      try {
        const [configData, kbsData] = await Promise.all([
          publicChatAPI.admin.getConfig(),
          publicChatAPI.admin.getAvailableKBs(),
        ]);

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

        // Transform KB data - the endpoint returns an array of strings
        const transformedKBs: KnowledgeBase[] = Array.isArray(kbsData)
          ? (kbsData as any[]).map((kb: any) => {
            if (typeof kb === 'string') {
              return {
                kb_name: kb,
                document_count: 0,
              };
            }
            return {
              kb_name: kb.kb_name || kb.name || String(kb),
              document_count: kb.document_count || kb.documents?.length || 0,
            };
          })
          : [];

        setKnowledgeBases(transformedKBs);
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

  const handleAddQuestion = () => {
    if (!config) return;
    if (newQuestion.trim() && config.suggested_questions.length < 10) {
      setConfig(prev => prev ? ({
        ...prev,
        suggested_questions: [...prev.suggested_questions, newQuestion.trim()]
      }) : prev);
      setNewQuestion('');
    }
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

    setIsSaving(true);
    try {
      await publicChatAPI.admin.updateConfig(config);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error: any) {
      console.error('Error saving config:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePreview = () => {
    window.open('/public-chat', '_blank');
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-6xl">
        <div className="flex items-center justify-center h-64">
          <Icons.Spinner className="h-8 w-8 text-primary animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-6xl">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-text mb-2">Error Loading Configuration</h2>
          <p className="text-text-secondary">{error || 'Failed to load configuration'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text">Public Chat Configuration</h1>
            <p className="text-text-secondary mt-2">Configure the customer-facing chat interface</p>
          </div>
          <div className="flex space-x-3">
            <Button variant="outline" onClick={handlePreview}>
              <Icons.Eye className="h-4 w-4 mr-2" />
              Preview
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Icons.Spinner className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Icons.Check className="h-4 w-4 mr-2" />
              )}
              {isSaving ? 'Saving...' : 'Save Configuration'}
            </Button>
          </div>
        </div>

        {saveStatus === 'success' && (
          <div className="mt-4 p-3 bg-success/20 border border-success rounded-lg text-success">
            ✅ Configuration saved successfully!
          </div>
        )}

        {saveStatus === 'error' && (
          <div className="mt-4 p-3 bg-error/20 border border-error rounded-lg text-error">
            ❌ Error saving configuration. Please try again.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column */}
        <div className="space-y-6">
          {/* General Settings */}
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={config.enabled}
                  onChange={(e) => setConfig(prev => prev ? ({ ...prev, enabled: e.target.checked }) : prev)}
                />
                <Label>Enable Public Chat</Label>
              </div>

              {config.agent_type && (
                <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {(() => {
                      const persona = PERSONA_CONFIG[config.agent_type] || PERSONA_CONFIG.generic;
                      const Icon = persona.icon;
                      return <Icon className="w-4 h-4 text-primary" />;
                    })()}
                    <span className="text-sm font-medium text-text">Assigned Persona</span>
                  </div>
                  <Badge variant="secondary">
                    {PERSONA_CONFIG[config.agent_type]?.label || config.agent_type.replace(/_/g, ' ')}
                  </Badge>
                </div>
              )}

              <div>
                <Label htmlFor="welcomeMessage">Welcome Message</Label>
                <Input
                  id="welcomeMessage"
                  value={config.welcome_message}
                  onChange={(e) => setConfig(prev => prev ? ({ ...prev, welcome_message: e.target.value }) : prev)}
                  placeholder="Hi! How can I help you today?"
                  className="mt-1"
                />
              </div>
            </CardContent>
          </Card>

          {/* Branding */}
          <Card>
            <CardHeader>
              <CardTitle>Branding</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="companyName">Company Name</Label>
                <Input
                  id="companyName"
                  value={config.branding.company_name}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    branding: { ...prev.branding, company_name: e.target.value }
                  }) : prev)}
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="primaryColor">Primary Color</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Input
                    id="primaryColor"
                    type="color"
                    value={config.branding.primary_color}
                    onChange={(e) => setConfig(prev => prev ? ({
                      ...prev,
                      branding: { ...prev.branding, primary_color: e.target.value }
                    }) : prev)}
                    className="w-16 h-10 p-1 border rounded"
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
                <Label htmlFor="logo">Logo URL (optional)</Label>
                <Input
                  id="logo"
                  value={config.branding.logo_url || ''}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    branding: { ...prev.branding, logo_url: e.target.value || undefined }
                  }) : prev)}
                  placeholder="https://example.com/logo.png"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="fontFamily">Font Family (optional)</Label>
                <Select
                  id="fontFamily"
                  value={config.branding.font_family || 'Inter, sans-serif'}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    branding: { ...prev.branding, font_family: e.target.value }
                  }) : prev)}
                  className="mt-1"
                >
                  {FONT_OPTIONS.map(font => (
                    <option key={font.value} value={font.value}>
                      {font.label}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <Label htmlFor="fontSizeBase">Base Font Size (px)</Label>
                <Input
                  id="fontSizeBase"
                  type="number"
                  min="10"
                  max="20"
                  value={config.branding.font_size_base || 14}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    branding: { ...prev.branding, font_size_base: parseInt(e.target.value) || 14 }
                  }) : prev)}
                  className="mt-1"
                />
                <p className="text-xs text-text-secondary mt-1">Range: 10-20 pixels</p>
              </div>
            </CardContent>
          </Card>

          {/* Rate Limiting */}
          <Card>
            <CardHeader>
              <CardTitle>Rate Limiting</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="queriesPerMinute">Max Queries per Minute</Label>
                <Input
                  id="queriesPerMinute"
                  type="number"
                  min="1"
                  max="100"
                  value={config.rate_limit.queries_per_minute}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    rate_limit: { ...prev.rate_limit, queries_per_minute: parseInt(e.target.value) || 10 }
                  }) : prev)}
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="maxMessages">Max Messages per Session</Label>
                <Input
                  id="maxMessages"
                  type="number"
                  min="1"
                  max="200"
                  value={config.rate_limit.max_messages_per_session}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    rate_limit: { ...prev.rate_limit, max_messages_per_session: parseInt(e.target.value) || 50 }
                  }) : prev)}
                  className="mt-1"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Knowledge Bases */}
          <Card>
            <CardHeader>
              <CardTitle>Allowed Knowledge Bases</CardTitle>
              <p className="text-sm text-text-secondary mt-1">Select which knowledge bases customers can query</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {knowledgeBases.length === 0 ? (
                  <p className="text-text-secondary text-center py-4">No knowledge bases available</p>
                ) : (
                  <>
                    {knowledgeBases.map((kb, index) => {
                      console.log('Rendering KB:', JSON.stringify(kb), 'Type:', typeof kb, 'kb_name:', kb.kb_name);
                      return (
                        <div key={kb.kb_name || `kb-${index}`} className="flex items-center justify-between p-3 border border-border rounded-lg bg-background">
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              checked={config.allowed_kbs.includes(kb.kb_name)}
                              onChange={() => handleKBToggle(kb.kb_name)}
                            />
                            <div>
                              <p className="font-medium text-text">{kb.kb_name || 'Unnamed KB'}</p>
                              {kb.document_count > 0 && (
                                <p className="text-sm text-text-secondary">{kb.document_count} documents</p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>

              <div className="mt-4 p-3 bg-primary/10 border border-primary/30 rounded-lg">
                <p className="text-sm text-text">
                  💡 <strong>Tip:</strong> Only select knowledge bases that contain customer-appropriate content.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Suggested Questions */}
          <Card>
            <CardHeader>
              <CardTitle>Suggested Questions</CardTitle>
              <p className="text-sm text-text-secondary mt-1">Help customers get started with common questions</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {config.suggested_questions.map((question, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-background rounded border border-border">
                    <span className="text-sm text-text flex-1">{question}</span>
                    <button
                      onClick={() => handleRemoveQuestion(index)}
                      className="text-error hover:text-error/80 ml-2"
                    >
                      <Icons.X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>

              {config.suggested_questions.length < 10 && (
                <div className="flex space-x-2">
                  <Input
                    value={newQuestion}
                    onChange={(e) => setNewQuestion(e.target.value)}
                    placeholder="Add a suggested question..."
                    onKeyDown={(e) => e.key === 'Enter' && handleAddQuestion()}
                    className="flex-1"
                  />
                  <Button onClick={handleAddQuestion} disabled={!newQuestion.trim()}>
                    <Icons.Plus className="h-4 w-4" />
                  </Button>
                </div>
              )}

              <p className="text-xs text-text-secondary">
                {config.suggested_questions.length}/10 questions
              </p>
            </CardContent>
          </Card>

          {/* Features */}
          <Card>
            <CardHeader>
              <CardTitle>Features</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={config.features.show_sources}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    features: { ...prev.features, show_sources: e.target.checked }
                  }) : prev)}
                />
                <Label>Show Source Citations</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={config.features.allow_feedback}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    features: { ...prev.features, allow_feedback: e.target.checked }
                  }) : prev)}
                />
                <Label>Allow Feedback (👍 👎)</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={config.features.show_suggested_questions}
                  onChange={(e) => setConfig(prev => prev ? ({
                    ...prev,
                    features: { ...prev.features, show_suggested_questions: e.target.checked }
                  }) : prev)}
                />
                <Label>Show Suggested Questions</Label>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AdminPublicChatPage;

