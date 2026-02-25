import { useState, useEffect, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Database, FileText, Send, Loader2, AlertCircle, X, RefreshCw, Shield, Truck, ShoppingCart, Leaf, Sparkles, MessageSquare, Plus, Trash2, Archive, Clock, PanelLeftClose, PanelLeftOpen, Edit2, Check } from 'lucide-react';
import { agentAPI } from '../services/api';
import type { AgentChatResponse, AgentSession } from '../services/api.types';
import { useAuth } from '../context/AuthContext.v2';
import { useKnowledgeBases } from '../context/KnowledgeBaseContext';
import { useDatabase } from '../context/DatabaseContext';
import { cn } from '../lib/utils';
import { parseAgentResponse } from '../lib/agent-utils';


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



export default function AIAgentPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const {
    connections: dbConnections,
    fetchConnections: loadDatabaseConnections,
    isConnected: isDatabaseConnected,
    selectedConnection: selectedDBConnection,
    connect: handleConnect,
    connectionStep,
  } = useDatabase();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Connection management state
  const [showDBModal, setShowDBModal] = useState(false);
  const [showKBModal, setShowKBModal] = useState(false);
  const [showPersonaModal, setShowPersonaModal] = useState(false);
  const [connectionLoading, setConnectionLoading] = useState(false);
  const [connectingDB, setConnectingDB] = useState<string | null>(null);
  const [agentConfig, setAgentConfig] = useState<{ agent_type: string; is_customized: boolean } | null>(null);
  const { knowledgeBases, fetchKnowledgeBases, isLoading: isKBLoading } = useKnowledgeBases();
  const [selectedKB, setSelectedKB] = useState<string>('');
  const [selectedPersona, setSelectedPersona] = useState<string>('generic');

  // Session history state
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [isSessionsLoading, setIsSessionsLoading] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    // Clear state when tenant changes
    // setSelectedKB(''); // Actually maybe we want to KEEP it?
    // setSelectedDBConnection('');
    // setIsDatabaseConnected(false);
    setMessages([]);
    setAgentConfig(null);
    setSessionId(null);

    // Load fresh data for the current tenant
    if (user?.tenantId) {
      fetchKnowledgeBases();
      loadDatabaseConnections();
      fetchAgentConfig();
      loadSessions();

      // Restore session if exists
      const savedSessionId = localStorage.getItem(`ai_agent_session_${user.tenantId}`);
      if (savedSessionId) {
        console.log('AI Agent: Found saved session:', savedSessionId);
        setSessionId(savedSessionId);
        loadSessionHistory(savedSessionId);
      }
    }
  }, [user?.tenantId]); // Reload when tenant changes

  const loadSessions = async () => {
    try {
      setIsSessionsLoading(true);
      const response = await agentAPI.listSessions() as any;
      // Handle both direct array and { sessions: [] } wrapper
      const sessionsData = Array.isArray(response) ? response : (response?.sessions || []);
      setSessions(sessionsData);
    } catch (err) {
      console.error('AI Agent: Failed to load sessions:', err);
    } finally {
      setIsSessionsLoading(false);
    }
  };

  const categorizeSessions = (sessions: AgentSession[]) => {
    if (!Array.isArray(sessions)) return { active: [], archived: [] };

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const active: AgentSession[] = [];
    const archived: AgentSession[] = [];

    sessions.forEach(s => {
      const dateStr = s.updated_at || s.created_at;
      const sessionDate = dateStr ? new Date(dateStr) : new Date();

      if (!isNaN(sessionDate.getTime()) && sessionDate < thirtyDaysAgo) {
        archived.push(s);
      } else {
        active.push(s);
      }
    });

    // If for some reason filtering resulted in empty lists but we have sessions, 
    // put them all in active to ensure the user sees them.
    if (sessions.length > 0 && active.length === 0 && archived.length === 0) {
      return { active: sessions, archived: [] };
    }

    return { active, archived };
  };

  const loadSessionHistory = async (sid: string) => {
    try {
      setLoading(true);
      const response = await agentAPI.getHistory(sid) as any;

      // Handle both { messages: [] } and direct array responses
      const rawMessages = Array.isArray(response)
        ? response
        : (response?.messages || response?.data?.messages || []);

      console.log('AI Agent: Loaded history:', rawMessages.length, 'messages');

      const mappedMessages: Message[] = rawMessages.map((msg: any, index: number) => {
        // Handle inconsistent field names between live chat and history
        const content = msg.content || msg.response || msg.message || '';
        const role = msg.role || msg.type || 'assistant';

        return {
          id: msg.id || `hist-${index}-${Date.now()}`,
          type: role === 'user' || role === 'human' ? 'user' : 'assistant',
          content: role === 'user' || role === 'human' ? content : parseAgentResponse(content),
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          agent_type: msg.agent_type || msg.metadata?.agent_type,
          source: msg.source || msg.metadata?.source,
          metadata: msg.metadata || {}
        };
      });

      setMessages(mappedMessages);
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


  const handleConnectSavedDB = async (connectionName: string) => {
    setConnectionLoading(true);
    setConnectingDB(connectionName);
    try {
      await handleConnect(connectionName);
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
      setConnectingDB(null);
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
        loadSessions(); // Refresh session list
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: parseAgentResponse(response.content || (response as any).response), // Fallback for transition
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

  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation?')) {
      try {
        await agentAPI.deleteSession(sid);
        if (sid === sessionId) {
          setMessages([]);
          setSessionId(null);
          if (user?.tenantId) {
            localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
          }
        }
        loadSessions();
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    }
  };

  const handleRenameSession = async (e: React.FormEvent, sid: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!editingTitle.trim()) {
      setEditingSessionId(null);
      return;
    }
    try {
      await agentAPI.renameSession(sid, editingTitle.trim());
      loadSessions();
    } catch (err) {
      console.error('AI Agent: Failed to rename session:', err);
    } finally {
      setEditingSessionId(null);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    if (user?.tenantId) {
      localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
    }
  };

  const { active: activeSessions, archived: archivedSessions } = categorizeSessions(sessions);

  return (
    <div className="p-6 max-w-full mx-auto h-[calc(100vh-4rem)] flex overflow-hidden relative">
      {/* Sidebar - Chat History */}
      <div className={cn(
        "flex flex-col gap-4 shrink-0 transition-all duration-300 ease-in-out h-full overflow-hidden",
        isSidebarCollapsed ? "w-0 opacity-0" : "w-80 opacity-100 mr-6"
      )}>
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2 shadow-sm py-6 text-base"
          variant="outline"
        >
          <Plus className="w-5 h-5 text-primary" />
          New Conversation
        </Button>

        <Card className="flex-1 overflow-hidden flex flex-col bg-surface border-border shadow-sm">
          <div className="p-4 border-b border-border flex items-center justify-between bg-background/50">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-text-secondary" />
              <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">Chat History</span>
            </div>
            {sessions.length > 0 && (
              <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">
                {sessions.length}
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-1.5 custom-scrollbar">
            {activeSessions.length === 0 && archivedSessions.length === 0 && !isSessionsLoading && (
              <div className="flex flex-col items-center justify-center h-40 text-center opacity-50 grayscale">
                <MessageSquare className="w-8 h-8 mb-2" />
                <p className="text-xs">No previous chats</p>
              </div>
            )}

            {isSessionsLoading && activeSessions.length === 0 && (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
              </div>
            )}

            {activeSessions.map(s => (
              <div
                key={s.session_id}
                onClick={() => {
                  setSessionId(s.session_id);
                  loadSessionHistory(s.session_id);
                  if (user?.tenantId) {
                    localStorage.setItem(`ai_agent_session_${user.tenantId}`, s.session_id);
                  }
                }}
                className={cn(
                  "group p-3 rounded-xl cursor-pointer transition-all border flex items-start gap-3 relative",
                  sessionId === s.session_id
                    ? "bg-primary/10 border-primary/30 shadow-sm"
                    : "bg-transparent border-transparent hover:bg-surface-hover hover:border-border"
                )}
              >
                <div className={cn(
                  "p-2 rounded-lg shrink-0",
                  sessionId === s.session_id ? "bg-primary text-white" : "bg-background text-text-secondary"
                )}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0 pr-6">
                  {editingSessionId === s.session_id ? (
                    <form
                      onSubmit={(e) => handleRenameSession(e, s.session_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="flex items-center gap-1"
                    >
                      <input
                        autoFocus
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        className="bg-background border border-primary/50 text-xs px-1 py-0.5 rounded w-full outline-none focus:ring-1 focus:ring-primary"
                        onBlur={() => setEditingSessionId(null)}
                      />
                      <button type="submit" className="text-primary hover:text-primary/70">
                        <Check className="w-3 h-3" />
                      </button>
                    </form>
                  ) : (
                    <div className={cn(
                      "text-sm font-semibold truncate flex items-center gap-2",
                      sessionId === s.session_id ? "text-primary" : "text-text"
                    )}>
                      {s.title || s.last_message || 'New Conversation'}
                    </div>
                  )}
                  <div className="text-[10px] text-text-secondary mt-1 font-medium">
                    {(() => {
                      const dateStr = s.updated_at || s.created_at;
                      const date = dateStr ? new Date(dateStr) : null;
                      if (!date || isNaN(date.getTime())) return 'Recently';
                      return date.toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      });
                    })()}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, s.session_id)}
                  className="absolute right-3 top-3.5 opacity-0 group-hover:opacity-100 p-1.5 hover:text-error text-text-secondary transition-all rounded-md hover:bg-error/10"
                  title="Delete conversation"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingSessionId(s.session_id);
                    setEditingTitle(s.title || s.last_message || 'New Conversation');
                  }}
                  className="absolute right-9 top-1/2 -translate-y-1/2 p-1 text-text-secondary opacity-0 group-hover:opacity-100 hover:text-primary transition-all rounded-md hover:bg-surface"
                  title="Rename session"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {archivedSessions.length > 0 && (
              <div className="pt-4 mt-4 border-t border-border/50">
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  className="w-full p-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-widest text-text-secondary hover:text-text transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Archive className="w-3.5 h-3.5" />
                    <span>Archived Chats</span>
                  </div>
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0">
                    {archivedSessions.length}
                  </Badge>
                </button>

                {showArchived && (
                  <div className="mt-2 space-y-1.5">
                    {archivedSessions.map(s => (
                      <div
                        key={s.session_id}
                        onClick={() => {
                          setSessionId(s.session_id);
                          loadSessionHistory(s.session_id);
                          if (user?.tenantId) {
                            localStorage.setItem(`ai_agent_session_${user.tenantId}`, s.session_id);
                          }
                        }}
                        className={cn(
                          "group p-2.5 rounded-lg cursor-pointer transition-all border flex items-start gap-3",
                          sessionId === s.session_id
                            ? "bg-primary/5 border-primary/20"
                            : "bg-transparent border-transparent hover:bg-surface-hover/50"
                        )}
                      >
                        <MessageSquare className="w-3.5 h-3.5 mt-1 shrink-0 text-text-secondary/50" />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-text-secondary truncate">
                            {s.last_message || 'Archived Conversation'}
                          </div>
                          <div className="text-[9px] text-text-secondary/60 mt-0.5">
                            {new Date(s.updated_at || s.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        <button
                          onClick={(e) => handleDeleteSession(e, s.session_id)}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:text-error transition-all"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
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
                      className="w-full p-3 bg-background border border-border rounded-lg text-left hover:bg-surface-hover transition-colors disabled:opacity-50 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-medium text-text">{conn.name}</div>
                        <div className="text-xs text-text-secondary">{conn.type} - {conn.database}</div>
                        {connectingDB === conn.name && connectionStep && (
                          <div className="text-[10px] text-primary mt-1 font-medium animate-pulse">
                            {connectionStep}
                          </div>
                        )}
                      </div>
                      {connectingDB === conn.name && <Loader2 className="w-5 h-5 text-primary animate-spin" />}
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
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              className="bg-surface border-border hover:bg-surface-hover shadow-sm h-10 w-10 shrink-0"
              title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isSidebarCollapsed ? <PanelLeftOpen className="w-5 h-5 text-primary" /> : <PanelLeftClose className="w-5 h-5 text-text-secondary" />}
            </Button>
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
              <p className="text-text-secondary mt-1 text-sm">
                {PERSONA_CONFIG[selectedPersona]?.description || PERSONA_CONFIG.generic.description}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            {user?.role === 'superadmin' && (
              <Button
                variant="outline"
                onClick={() => setShowPersonaModal(true)}
                className="bg-surface hover:bg-surface-hover shadow-sm border-border h-10"
              >
                <Sparkles className="w-4 h-4 mr-2 text-primary" />
                Switch Persona
              </Button>
            )}
          </div>
        </div>

        {/* Controls */}
        <Card className="p-4 bg-surface border-border mb-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-4">
            {/* KB Selection */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">Knowledge Base:</span>
              <button
                onClick={() => setShowKBModal(true)}
                disabled={knowledgeBases.length === 0}
                className={`px-3 py-1.5 border rounded-lg text-sm text-text transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${selectedKB
                  ? 'bg-primary/10 border-primary/20 hover:bg-primary/20'
                  : 'bg-background border-border hover:bg-surface-hover'
                  }`}
              >
                <FileText className={`w-4 h-4 ${selectedKB ? 'text-primary' : ''}`} />
                {selectedKB || (knowledgeBases.length > 0 ? 'Select' : 'None')}
              </button>
              <button
                onClick={handleRefreshKBs}
                className="p-1.5 text-text-secondary hover:text-text transition-colors"
                title="Refresh knowledge bases"
              >
                <RefreshCw className={cn("w-4 h-4", isKBLoading && "animate-spin")} />
              </button>
            </div>

            <div className="h-6 w-px bg-border/50"></div>

            {/* Database Selection */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">Database:</span>
              <button
                onClick={() => setShowDBModal(true)}
                disabled={dbConnections.length === 0 && !isDatabaseConnected}
                className={`px-3 py-1.5 border rounded-lg text-sm text-text transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${isDatabaseConnected
                  ? 'bg-primary/10 border-primary/20 hover:bg-primary/20'
                  : 'bg-background border-border hover:bg-surface-hover'
                  }`}
              >
                {connectionLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                ) : (
                  <Database className={`w-4 h-4 ${isDatabaseConnected ? 'text-primary' : ''}`} />
                )}
                {selectedDBConnection || (isDatabaseConnected
                  ? 'Connected'
                  : (dbConnections.length > 0 ? 'Select' : 'None'))}
              </button>
            </div>

            {/* Session Info & Actions */}
            <div className="ml-auto flex items-center gap-3">
              {sessionId && (
                <div className="flex items-center gap-2 bg-background/50 px-3 py-1.5 rounded-lg border border-border">
                  <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></div>
                  <span className="text-[10px] font-mono text-text-secondary uppercase">
                    Session: {sessionId.slice(0, 8)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2 custom-scrollbar">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full">
              <Card className="p-10 text-center bg-surface border-border max-w-2xl shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 via-primary to-primary/50"></div>
                {(() => {
                  const config = agentConfig && PERSONA_CONFIG[agentConfig.agent_type] ? PERSONA_CONFIG[agentConfig.agent_type] : PERSONA_CONFIG.generic;
                  const Icon = config.icon;
                  return (
                    <div className="inline-flex p-4 rounded-2xl bg-primary/10 mb-6 transition-transform group-hover:scale-110">
                      <Icon className="w-12 h-12 text-primary" />
                    </div>
                  );
                })()}
                <h3 className="text-2xl font-bold text-text mb-3">
                  How can I help you today?
                </h3>
                <p className="text-text-secondary mb-8 text-base leading-relaxed max-w-md mx-auto">
                  I'm your {agentConfig && PERSONA_CONFIG[agentConfig.agent_type] ? PERSONA_CONFIG[agentConfig.agent_type].label : 'AI assistant'}.
                  Ask me anything about your documents or databases.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                  <button
                    onClick={() => setInput("How many users registered last month?")}
                    className="p-4 bg-background border border-border rounded-xl hover:border-primary/50 hover:bg-surface-hover transition-all group/card"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Database className="w-4 h-4 text-primary" />
                      <span className="text-sm font-bold text-text">Database Query</span>
                    </div>
                    <p className="text-sm text-text-secondary group-hover/card:text-text italic">
                      "How many users registered last month?"
                    </p>
                  </button>
                  <button
                    onClick={() => setInput("What is the refund policy?")}
                    className="p-4 bg-background border border-border rounded-xl hover:border-primary/50 hover:bg-surface-hover transition-all group/card"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-4 h-4 text-primary" />
                      <span className="text-sm font-bold text-text">Document Search</span>
                    </div>
                    <p className="text-sm text-text-secondary group-hover/card:text-text italic">
                      "What is the refund policy?"
                    </p>
                  </button>
                </div>
              </Card>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] ${msg.type === 'user' ? 'order-2' : 'order-1'} group/msg relative`}>
                {msg.type === 'user' ? (
                  <div className="bg-primary text-white px-5 py-3 rounded-2xl rounded-tr-none shadow-md">
                    <p className="text-sm leading-relaxed">
                      {(() => {
                        const content = parseAgentResponse(msg.content);
                        return typeof content === 'object' ? JSON.stringify(content) : content;
                      })()}
                    </p>
                    <span className="text-[9px] opacity-60 mt-1 block text-right">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ) : (
                  <Card className={`p-5 rounded-2xl rounded-tl-none shadow-sm ${msg.type === 'system' && msg.isError ? 'bg-error/5 border-error/20' : 'bg-surface border-border'}`}>
                    {msg.type === 'assistant' && (
                      <div className="flex items-center gap-2 mb-3">
                        <div className="p-1 px-2 rounded-lg bg-primary/10 text-xs font-bold text-primary flex items-center gap-1.5">
                          {(() => {
                            const personaKey = msg.agent_type || selectedPersona;
                            const config = PERSONA_CONFIG[personaKey] || PERSONA_CONFIG.generic;
                            const Icon = config.icon;
                            return (
                              <>
                                <Icon className="w-3.5 h-3.5" />
                                <span className="uppercase tracking-wider">{config.label}</span>
                              </>
                            );
                          })()}
                        </div>
                        {msg.source && (
                          <div className="flex items-center gap-1 text-[10px] text-text-secondary font-medium uppercase tracking-tighter">
                            {msg.source === 'database' ? (
                              <><Database className="w-3 h-3" /> Source: DB</>
                            ) : (
                              <><FileText className="w-3 h-3" /> Source: KB</>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {msg.type === 'system' && msg.isError && (
                      <div className="flex items-center gap-2 mb-3 text-error">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span className="text-xs font-bold uppercase">System Error</span>
                      </div>
                    )}

                    <div className="text-text text-sm leading-relaxed whitespace-pre-wrap">
                      {(() => {
                        const content = parseAgentResponse(msg.content);

                        if (typeof content === 'object' && content !== null) {
                          const type = content.type || content.component;
                          switch (type) {
                            case 'certificate_card':
                              return (
                                <div className="my-4">
                                  <CertificateCard
                                    project={content.project}
                                    status={content.status}
                                    date={content.date}
                                    tonnage={content.tonnage}
                                  />
                                </div>
                              );
                            case 'product_gallery':
                            case 'product_list':
                              return <div className="my-4"><ProductGallery products={content.products || []} /></div>;
                            case 'impact_stats':
                              return (
                                <div className="my-4">
                                  <ImpactStats
                                    contribution={content.contribution}
                                    trees_equivalent={content.trees_equivalent}
                                    rank={content.rank}
                                  />
                                </div>
                              );
                            case 'text':
                            case 'message':
                              return content.response || content.content || content.answer || JSON.stringify(content);
                            case 'url_action':
                              return (
                                <div className="my-4">
                                  <UrlAction
                                    label={content.label}
                                    url={content.url}
                                    type={content.action_type}
                                  />
                                </div>
                              );
                            default:
                              return <pre className="text-xs bg-background p-3 rounded-xl border border-border mt-2 overflow-x-auto">{JSON.stringify(content, null, 2)}</pre>;
                          }
                        }

                        return content;
                      })()}
                    </div>

                    {msg.metadata?.sql && (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        <details className="group/sql">
                          <summary className="text-[10px] font-bold uppercase tracking-widest text-text-secondary cursor-pointer hover:text-primary transition-colors flex items-center gap-1.5 list-none">
                            <span className="w-4 h-4 rounded bg-background flex items-center justify-center transition-transform group-open/sql:rotate-90">›</span>
                            SQL Query
                          </summary>
                          <div className="mt-3 p-3 bg-background rounded-xl border border-border text-xs font-mono text-primary/80 overflow-x-auto">
                            {msg.metadata.sql}
                          </div>
                        </details>
                      </div>
                    )}

                    {msg.metadata?.results && msg.metadata.results.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        <details className="group/results" open>
                          <summary className="text-[10px] font-bold uppercase tracking-widest text-text-secondary cursor-pointer hover:text-primary transition-colors flex items-center gap-1.5 list-none mb-3">
                            <span className="w-4 h-4 rounded bg-background flex items-center justify-center transition-transform group-open/results:rotate-90">›</span>
                            Query Results ({msg.metadata.results.length})
                          </summary>
                          <div className="overflow-x-auto rounded-xl border border-border bg-background">
                            <table className="w-full text-xs text-left border-collapse">
                              <thead>
                                <tr className="bg-background/80">
                                  {Object.keys(msg.metadata.results[0]).map((col) => (
                                    <th key={col} className="px-3 py-2 font-bold text-text-secondary border-b border-border uppercase tracking-tighter">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border/50">
                                {msg.metadata.results.slice(0, 5).map((row, idx) => (
                                  <tr key={idx} className="hover:bg-primary/5 transition-colors">
                                    {Object.values(row).map((val, i) => (
                                      <td key={i} className="px-3 py-2 text-text font-medium">
                                        {val === null ? <span className="text-text-secondary italic opacity-50">null</span> : String(val)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {msg.metadata.results.length > 5 && (
                              <div className="p-2 text-center border-t border-border/50 bg-background/30">
                                <span className="text-[10px] font-bold text-text-secondary uppercase">
                                  + {msg.metadata.results.length - 5} more rows
                                </span>
                              </div>
                            )}
                          </div>
                        </details>
                      </div>
                    )}

                    {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        <details className="group/sources">
                          <summary className="text-[10px] font-bold uppercase tracking-widest text-text-secondary cursor-pointer hover:text-primary transition-colors flex items-center gap-1.5 list-none">
                            <span className="w-4 h-4 rounded bg-background flex items-center justify-center transition-transform group-open/sources:rotate-90">›</span>
                            Context Sources ({msg.metadata.sources.length})
                          </summary>
                          <div className="mt-3 space-y-2">
                            {msg.metadata.sources.map((source, idx) => (
                              <div key={idx} className="flex items-center justify-between p-3 bg-background rounded-xl border border-border group/source hover:border-primary/30 transition-all">
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-lg bg-primary/5 flex items-center justify-center">
                                    <FileText className="w-4 h-4 text-primary" />
                                  </div>
                                  <div>
                                    <p className="text-xs font-bold text-text truncate max-w-[200px]">{source.filename}</p>
                                    <p className="text-[10px] text-text-secondary font-medium uppercase mt-0.5">Rank #{idx + 1}</p>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className="text-xs font-bold text-primary">{(source.relevance_score * 100).toFixed(0)}%</p>
                                  <p className="text-[9px] text-text-secondary uppercase font-semibold">Match</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}

                    <span className="text-[9px] text-text-secondary mt-3 block">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </Card>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-3 bg-surface border border-border px-4 py-3 rounded-2xl rounded-tl-none shadow-sm">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></div>
                </div>
                <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">AI is thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <Card className="p-4 bg-surface border-border shadow-lg relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-primary/20 to-transparent opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                className="w-full px-4 py-3 bg-background border border-border rounded-xl resize-none text-sm text-text placeholder:text-text-secondary focus:border-primary/50 focus:outline-none focus:ring-4 focus:ring-primary/5 transition-all min-h-[56px] max-h-32"
                rows={1}
                placeholder="Message your AI assistant..."
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = `${e.target.scrollHeight}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                disabled={loading}
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="h-14 w-14 rounded-xl shadow-lg shadow-primary/20 shrink-0"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </Button>
          </div>
          <p className="text-[10px] text-text-secondary mt-2 text-center font-medium uppercase tracking-tighter opacity-70">
            AI can make mistakes. Verify important information.
          </p>
        </Card>
      </div >
    </div >
  );
}
