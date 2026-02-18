import { useState, useEffect, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Database, FileText, Send, Loader2, AlertCircle, X, RefreshCw, Shield, Truck, ShoppingCart, Leaf, Sparkles } from 'lucide-react';
import { databaseAPI, agentAPI } from '../services/api';
import type { AgentChatResponse } from '../services/api.types';
import { useAuth } from '../context/AuthContext.v2';
import { useKnowledgeBases } from '../context/KnowledgeBaseContext';
import { cn } from '../lib/utils';

const PERSONA_CONFIG: Record<string, { label: string; icon: any; description: string }> = {
  security_analyst: {
    label: 'SOC Assistant',
    icon: Shield,
    description: 'Expert in log discovery, security events, and threat analysis'
  },
  quickship: {
    label: 'Logistics Support',
    icon: Truck,
    description: 'Specialized in shipment tracking, logistics, and supply chain'
  },
  ecommerce: {
    label: 'Shopping Assistant',
    icon: ShoppingCart,
    description: 'Expert in product discovery and e-commerce support'
  },
  ecostance: {
    label: 'Sustainability Expert',
    icon: Leaf,
    description: 'Focused on environmental impact and carbon offsets'
  },
  generic: {
    label: 'AI Assistant',
    icon: Sparkles,
    description: 'General-purpose AI assistant with access to your data'
  }
};
import {
  CertificateCard,
  ProductGallery,
  ImpactStats,
  UrlAction
} from '../components/chat/components';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: any; // Changed from string to any
  timestamp: Date;
  source?: 'database' | 'knowledge-base';
  isError?: boolean;
  metadata?: {
    sql?: string;
    results?: any[];
    sources?: Array<{
      filename: string;
      chunk_index: number;
      relevance_score: number;
    }>;
  };
  agent_type?: string;
}


interface DatabaseConnection {
  name: string;
  type: string;
  host: string;
  database: string;
}

export default function AIAgentPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isDatabaseConnected, setIsDatabaseConnected] = useState(false);
  const { knowledgeBases, fetchKnowledgeBases, isLoading: isKBLoading } = useKnowledgeBases();
  const [selectedKB, setSelectedKB] = useState<string>('');
  const [selectedDBConnection, setSelectedDBConnection] = useState<string>('');
  const [selectedPersona, setSelectedPersona] = useState<string>('generic');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Connection management state
  const [showDBModal, setShowDBModal] = useState(false);
  const [showKBModal, setShowKBModal] = useState(false);
  const [showPersonaModal, setShowPersonaModal] = useState(false);
  const [dbConnections, setDbConnections] = useState<DatabaseConnection[]>([]);
  const [connectionLoading, setConnectionLoading] = useState(false);
  const [agentConfig, setAgentConfig] = useState<{ agent_type: string; is_customized: boolean } | null>(null);

  useEffect(() => {
    // Clear state when tenant changes
    setDbConnections([]);
    setSelectedKB('');
    setSelectedDBConnection('');
    setIsDatabaseConnected(false);
    setMessages([]);
    setAgentConfig(null);
    setSessionId(null);

    // Load fresh data for the current tenant
    if (user?.tenantId) {
      fetchKnowledgeBases();
      checkDatabaseConnection();
      loadDatabaseConnections();
      fetchAgentConfig();

      // Restore session if exists
      const savedSessionId = localStorage.getItem(`ai_agent_session_${user.tenantId}`);
      if (savedSessionId) {
        console.log('AI Agent: Found saved session:', savedSessionId);
        setSessionId(savedSessionId);
        loadSessionHistory(savedSessionId);
      }
    }
  }, [user?.tenantId]); // Reload when tenant changes

  const loadSessionHistory = async (sid: string) => {
    try {
      setLoading(true);
      const history = await agentAPI.getHistory(sid) as any;
      if (history && history.messages && Array.isArray(history.messages)) {
        console.log('AI Agent: Loaded history:', history.messages.length, 'messages');
        const mappedMessages: Message[] = history.messages.map((msg: any, index: number) => ({
          id: `hist-${index}-${Date.now()}`,
          type: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          agent_type: msg.agent_type // Assuming backend stores/returns this, otherwise undefined (generic)
        }));
        setMessages(mappedMessages);
      }
    } catch (err) {
      console.error('AI Agent: Failed to load session history:', err);
      // If session is invalid, clear it
      if (user?.tenantId) {
        localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
      }
      setSessionId(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgentConfig = async () => {
    try {
      const config = await agentAPI.getConfig() as any;
      setAgentConfig(config);
      if (config?.agent_type) {
        setSelectedPersona(config.agent_type);
      }
    } catch (err) {
      console.error('Failed to fetch agent config:', err);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleRefreshKBs = async () => {
    try {
      console.log('AI Agent: Refreshing knowledge bases...');
      await fetchKnowledgeBases(true);
    } catch (err) {
      console.error('AI Agent: Failed to refresh knowledge bases:', err);
    }
  };

  const handleSelectKB = (kbName: string) => {
    setSelectedKB(kbName);
    setShowKBModal(false);

    const successMsg: Message = {
      id: Date.now().toString(),
      type: 'system',
      content: `✅ Selected knowledge base: ${kbName}`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, successMsg]);
  };

  const checkDatabaseConnection = async () => {
    try {
      console.log('AI Agent: Checking database connection...');
      await databaseAPI.getSchema();
      setIsDatabaseConnected(true);
      console.log('AI Agent: Database connected');
    } catch (err) {
      console.log('AI Agent: Database not connected');
      setIsDatabaseConnected(false);
    }
  };

  const loadDatabaseConnections = async () => {
    try {
      const data = await databaseAPI.listConnections() as any;
      setDbConnections(data);
    } catch (err) {
      console.error('Failed to load database connections:', err);
    }
  };

  const handleConnectSavedDB = async (connectionName: string) => {
    setConnectionLoading(true);
    try {
      const conn = await databaseAPI.loadConnection(connectionName) as any;

      let dbUri: string;
      if (conn.db_uri) {
        dbUri = conn.db_uri;
      } else if (conn.type === 'sqlite') {
        dbUri = conn.db_path || conn.database;
      } else {
        dbUri = `${conn.type}://${conn.username}:${conn.password}@${conn.host}:${conn.port}/${conn.database}`;
      }

      console.log('AI Agent: Connecting with URI:', dbUri.replace(/:[^:@]+@/, ':****@'));
      await databaseAPI.connect(dbUri);
      setIsDatabaseConnected(true);
      setSelectedDBConnection(connectionName);
      setShowDBModal(false);

      const successMsg: Message = {
        id: Date.now().toString(),
        type: 'system',
        content: `✅ Connected to database: ${connectionName}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, successMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        type: 'system',
        content: `❌ Failed to connect: ${err.message}`,
        timestamp: new Date(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setConnectionLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const questionText = input.trim();

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: questionText,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    console.log('AI Agent: Processing query:', questionText);
    console.log('AI Agent: Session ID:', sessionId);

    try {
      // Use the new AI Agent Beta API with KB and DB connection
      const response = await agentAPI.chat(
        questionText,
        sessionId || undefined,
        selectedKB || undefined,
        selectedDBConnection || undefined,
        selectedPersona
      ) as AgentChatResponse;

      // Update session ID if new
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
        console.log('AI Agent: New session ID:', response.session_id);
        if (user?.tenantId) {
          localStorage.setItem(`ai_agent_session_${user.tenantId}`, response.session_id);
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date(response.timestamp),
        agent_type: response.agent_type || agentConfig?.agent_type,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('AI Agent: Error processing query:', err);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: err.message || 'Failed to process query',
        timestamp: new Date(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!sessionId) return;

    if (window.confirm('Are you sure you want to reset the conversation?')) {
      try {
        await agentAPI.reset(sessionId);
        setMessages([]);
        setSessionId(null);
        if (user?.tenantId) {
          localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
        }
      } catch (err) {
        console.error('Failed to reset conversation:', err);
      }
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto h-[calc(100vh-4rem)] flex flex-col">
      {/* Database Connection Modal */}
      {showDBModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowDBModal(false)}>
          <Card className="p-6 bg-surface border-border max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-text flex items-center gap-2">
                <Database className="w-5 h-5" />
                Select Database
              </h2>
              <button onClick={() => setShowDBModal(false)} className="text-text-secondary hover:text-text">
                <X className="w-5 h-5" />
              </button>
            </div>

            {dbConnections.length > 0 ? (
              <div className="space-y-2">
                {dbConnections.map((conn) => (
                  <button
                    key={conn.name}
                    onClick={() => handleConnectSavedDB(conn.name)}
                    disabled={connectionLoading}
                    className="w-full p-3 bg-background border border-border rounded-lg text-left hover:bg-surface-hover transition-colors disabled:opacity-50"
                  >
                    <div className="font-medium text-text">{conn.name}</div>
                    <div className="text-xs text-text-secondary">{conn.type} - {conn.database}</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Database className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                <p className="text-text-secondary mb-2">No saved database connections</p>
                <p className="text-xs text-text-secondary">
                  Go to Database Chat page to create connections
                </p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Persona Selection Modal */}
      {showPersonaModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowPersonaModal(false)}>
          <Card className="p-6 bg-surface border-border max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-text flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary" />
                Select Persona
              </h2>
              <button onClick={() => setShowPersonaModal(false)} className="text-text-secondary hover:text-text">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              {Object.entries(PERSONA_CONFIG).map(([key, config]) => {
                const Icon = config.icon;
                return (
                  <button
                    key={key}
                    onClick={() => {
                      setSelectedPersona(key);
                      setShowPersonaModal(false);
                      const msg: Message = {
                        id: Date.now().toString(),
                        type: 'system',
                        content: `🎭 Persona switched to: ${config.label}`,
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, msg]);
                    }}
                    className={`w-full p-4 border rounded-xl text-left transition-all flex items-start gap-4 ${selectedPersona === key
                      ? 'bg-primary/10 border-primary/30 shadow-sm'
                      : 'bg-background border-border hover:bg-surface-hover'
                      }`}
                  >
                    <div className={`p-2 rounded-lg ${selectedPersona === key ? 'bg-primary text-white' : 'bg-surface text-primary'}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-text">{config.label}</div>
                      <div className="text-sm text-text-secondary leading-tight mt-1">
                        {config.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* Knowledge Base Selection Modal */}
      {showKBModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowKBModal(false)}>
          <Card className="p-6 bg-surface border-border max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-text flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Select Knowledge Base
              </h2>
              <button onClick={() => setShowKBModal(false)} className="text-text-secondary hover:text-text">
                <X className="w-5 h-5" />
              </button>
            </div>

            {knowledgeBases.length > 0 ? (
              <div className="space-y-2">
                {knowledgeBases.map((kb) => (
                  <button
                    key={kb.id}
                    onClick={() => handleSelectKB(kb.name)}
                    disabled={connectionLoading}
                    className={`w-full p-3 border rounded-lg text-left transition-colors disabled:opacity-50 ${selectedKB === kb.name
                      ? 'bg-primary/10 border-primary/20'
                      : 'bg-background border-border hover:bg-surface-hover'
                      }`}
                  >
                    <div className="font-medium text-text">{kb.name}</div>
                    <div className="text-xs text-text-secondary">
                      {(kb.totalVectors || 0).toLocaleString()} vectors
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                {isKBLoading ? (
                  <p className="text-text-secondary mb-2 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Loading...
                  </p>
                ) : (
                  <>
                    <p className="text-text-secondary mb-2">No knowledge bases available</p>
                    <p className="text-xs text-text-secondary">
                      Go to Knowledge Base page to create one
                    </p>
                  </>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text flex items-center gap-2">
            {(() => {
              const persona = PERSONA_CONFIG[selectedPersona] || PERSONA_CONFIG.generic;
              const Icon = persona.icon;
              return (
                <>
                  <Icon className="w-6 h-6 text-primary" />
                  {persona.label}
                </>
              );
            })()}
            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-normal">BETA</span>
          </h1>
          <p className="text-text-secondary mt-1">
            {PERSONA_CONFIG[selectedPersona]?.description || PERSONA_CONFIG.generic.description}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => setShowPersonaModal(true)}
          className="bg-surface hover:bg-surface-hover shadow-sm border-border"
        >
          <Sparkles className="w-4 h-4 mr-2 text-primary" />
          Switch Persona
        </Button>
      </div>

      {/* Controls */}
      <Card className="p-4 bg-surface border-border mb-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* KB Selection */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">Knowledge Base:</span>
            <button
              onClick={() => setShowKBModal(true)}
              disabled={knowledgeBases.length === 0}
              className={`px-3 py-1.5 border rounded-lg text-sm text-text transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${selectedKB
                ? 'bg-primary/10 border-primary/20 hover:bg-primary/20'
                : 'bg-background border-border hover:bg-surface-hover'
                }`}
            >
              <FileText className={`w-4 h-4 ${selectedKB ? 'text-primary' : ''}`} />
              {selectedKB || (knowledgeBases.length > 0 ? 'Select Knowledge Base' : 'No KBs Available')}
            </button>
            <button
              onClick={handleRefreshKBs}
              className="p-1.5 text-text-secondary hover:text-text transition-colors"
              title="Refresh knowledge bases"
            >
              <RefreshCw className={cn("w-4 h-4", isKBLoading && "animate-spin")} />
            </button>
          </div>

          {/* Database Selection */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">Database:</span>
            <button
              onClick={() => setShowDBModal(true)}
              disabled={dbConnections.length === 0 && !isDatabaseConnected}
              className={`px-3 py-1.5 border rounded-lg text-sm text-text transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${isDatabaseConnected
                ? 'bg-primary/10 border-primary/20 hover:bg-primary/20'
                : 'bg-background border-border hover:bg-surface-hover'
                }`}
            >
              <Database className={`w-4 h-4 ${isDatabaseConnected ? 'text-primary' : ''}`} />
              {selectedDBConnection || (isDatabaseConnected
                ? 'Connected'
                : (dbConnections.length > 0 ? 'Select Connection' : 'No Connections'))}
            </button>
          </div>

          {/* Session Info & Reset */}
          <div className="ml-auto flex items-center gap-3">
            {sessionId && (
              <>
                <span className="text-xs text-text-secondary">
                  Session: {sessionId.slice(0, 8)}...
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleReset}
                  disabled={loading || messages.length === 0}
                >
                  Reset
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.length === 0 && (
          <Card className="p-8 text-center bg-surface border-border">
            {(() => {
              const config = agentConfig && PERSONA_CONFIG[agentConfig.agent_type] ? PERSONA_CONFIG[agentConfig.agent_type] : PERSONA_CONFIG.generic;
              const Icon = config.icon;
              return <Icon className="w-12 h-12 text-text-secondary mx-auto mb-4" />;
            })()}
            <h3 className="text-lg font-medium text-text mb-2">
              Ask {agentConfig && PERSONA_CONFIG[agentConfig.agent_type] ? `your ${PERSONA_CONFIG[agentConfig.agent_type].label}` : 'me'} anything
            </h3>
            <p className="text-text-secondary mb-4">
              I can answer questions using your database or knowledge base documents
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto text-left">
              <div className="p-3 bg-background rounded-lg">
                <Database className="w-4 h-4 text-primary mb-1" />
                <p className="text-sm text-text font-medium">Database Queries</p>
                <p className="text-xs text-text-secondary mt-1">
                  "How many users registered last month?"
                </p>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <FileText className="w-4 h-4 text-primary mb-1" />
                <p className="text-sm text-text font-medium">Document Questions</p>
                <p className="text-xs text-text-secondary mt-1">
                  "What is the refund policy?"
                </p>
              </div>
            </div>
          </Card>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.type === 'user' ? 'order-2' : 'order-1'}`}>
              {msg.type === 'user' ? (
                <div className="bg-primary text-white px-4 py-2 rounded-lg">
                  {msg.content}
                </div>
              ) : (
                <Card className={`p-4 ${msg.type === 'system' && msg.isError ? 'bg-error/10 border-error/20' : 'bg-surface border-border'}`}>
                  {msg.type === 'assistant' && (
                    <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-primary/80">
                      {(() => {
                        const personaKey = msg.agent_type || selectedPersona;
                        const config = PERSONA_CONFIG[personaKey] || PERSONA_CONFIG.generic;
                        const Icon = config.icon;
                        return (
                          <>
                            <Icon className="w-3.5 h-3.5" />
                            {config.label}
                          </>
                        );
                      })()}
                    </div>
                  )}
                  {msg.type === 'system' && msg.isError && (
                    <div className="flex items-start gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
                      <span className="text-sm font-medium text-error">Error</span>
                    </div>
                  )}

                  {msg.source && (
                    <div className="flex items-center gap-1.5 mb-2 text-xs text-text-secondary">
                      {msg.source === 'database' ? (
                        <><Database className="w-3 h-3" /> Database Query</>
                      ) : (
                        <><FileText className="w-3 h-3" /> Knowledge Base</>
                      )}
                    </div>
                  )}

                  <div className="text-text whitespace-pre-wrap">
                    {(() => {
                      let content = msg.content;
                      if (typeof content === 'string' && content.trim().startsWith('{')) {
                        try {
                          content = JSON.parse(content);
                        } catch (e) { }
                      }

                      if (typeof content === 'object' && content !== null) {
                        const type = content.type || content.component;
                        switch (type) {
                          case 'certificate_card':
                            return (
                              <CertificateCard
                                project={content.project}
                                status={content.status}
                                date={content.date}
                                tonnage={content.tonnage}
                              />
                            );
                          case 'product_gallery':
                          case 'product_list':
                            return <ProductGallery products={content.products || []} />;
                          case 'impact_stats':
                            return (
                              <ImpactStats
                                contribution={content.contribution}
                                trees_equivalent={content.trees_equivalent}
                                rank={content.rank}
                              />
                            );
                          case 'url_action':
                            return (
                              <UrlAction
                                label={content.label}
                                url={content.url}
                                type={content.action_type}
                              />
                            );
                          default:
                            return <pre className="text-xs bg-background p-2 rounded">{JSON.stringify(content, null, 2)}</pre>;
                        }
                      }
                      return content;
                    })()}
                  </div>

                  {msg.metadata?.sql && (
                    <details className="mt-3">
                      <summary className="text-xs text-text-secondary cursor-pointer hover:text-text">
                        View SQL Query
                      </summary>
                      <pre className="mt-2 p-2 bg-background rounded text-xs overflow-x-auto">
                        {msg.metadata.sql}
                      </pre>
                    </details>
                  )}

                  {msg.metadata?.results && msg.metadata.results.length > 0 && (
                    <details className="mt-3" open>
                      <summary className="text-xs text-text-secondary cursor-pointer hover:text-text mb-2">
                        View Results ({msg.metadata.results.length} rows)
                      </summary>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs border border-border">
                          <thead className="bg-background">
                            <tr>
                              {Object.keys(msg.metadata.results[0]).map((col) => (
                                <th key={col} className="px-2 py-1 text-left font-medium text-text border-b border-border">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {msg.metadata.results.slice(0, 10).map((row, idx) => (
                              <tr key={idx} className="hover:bg-surface-hover">
                                {Object.values(row).map((val, i) => (
                                  <td key={i} className="px-2 py-1 text-text">
                                    {val === null ? <span className="text-text-secondary italic">null</span> : String(val)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {msg.metadata.results.length > 10 && (
                          <p className="text-xs text-text-secondary mt-2">
                            Showing 10 of {msg.metadata.results.length} rows
                          </p>
                        )}
                      </div>
                    </details>
                  )}

                  {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-xs text-text-secondary cursor-pointer hover:text-text">
                        Sources ({msg.metadata.sources.length})
                      </summary>
                      <div className="mt-2 space-y-1">
                        {msg.metadata.sources.map((source, idx) => (
                          <div key={idx} className="text-xs p-2 bg-background rounded">
                            <span className="font-medium text-text">{source.filename}</span>
                            <span className="text-text-secondary ml-2">
                              (relevance: {(source.relevance_score * 100).toFixed(1)}%)
                            </span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </Card>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <Card className="p-4 bg-surface border-border">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm text-text-secondary">Thinking...</span>
              </div>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <Card className="p-4 bg-surface border-border">
        <div className="flex gap-2">
          <textarea
            className="flex-1 px-3 py-2 bg-background border border-border rounded-lg resize-none text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
            rows={2}
            placeholder="Ask a question about your data..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={loading}
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </Card>
    </div>
  );
}
