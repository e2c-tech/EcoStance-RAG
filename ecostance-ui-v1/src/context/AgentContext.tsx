import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { agentAPI } from '../services/api';
import type { AgentChatResponse, AgentSession } from '../services/api.types';
import { useAuth } from './AuthContext.v2';

export interface Message {
    id: string;
    type: 'user' | 'assistant' | 'system';
    content: any;
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

interface AgentContextType {
    messages: Message[];
    sessions: AgentSession[];
    input: string;
    setInput: (value: string) => void;
    loading: boolean;
    sessionId: string | null;
    setSessionId: (id: string | null) => void;
    isSessionsLoading: boolean;
    agentConfig: { agent_type: string; is_customized: boolean } | null;
    selectedKB: string;
    setSelectedKB: (kb: string) => void;
    selectedPersona: string;
    setSelectedPersona: (persona: string) => void;

    loadSessions: () => Promise<void>;
    loadSessionHistory: (sid: string) => Promise<void>;
    handleSend: (text: string, dbConnection?: string) => Promise<void>;
    handleDeleteSession: (sid: string) => Promise<void>;
    handleRenameSession: (sid: string, title: string) => Promise<void>;
    handleNewChat: () => void;
    clearState: () => void;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export const useAgent = () => {
    const context = useContext(AgentContext);
    if (!context) throw new Error('useAgent must be used within an AgentProvider');
    return context;
};

export const AgentProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { user } = useAuth();

    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);

    const [sessions, setSessions] = useState<AgentSession[]>([]);
    const [isSessionsLoading, setIsSessionsLoading] = useState(false);
    const [agentConfig, setAgentConfig] = useState<{ agent_type: string; is_customized: boolean } | null>(null);
    const [selectedKB, setSelectedKB] = useState<string>('');
    const [selectedPersona, setSelectedPersona] = useState<string>('generic');

    const [hasInitialized, setHasInitialized] = useState(false);

    // Clear state when tenant changes
    useEffect(() => {
        if (!user?.tenantId) return;

        // Only load initial data if we haven't already for this tenant
        // or if the tenant changed

        setHasInitialized(true);
        fetchAgentConfig();
        loadSessions();

        const savedSessionId = localStorage.getItem(`ai_agent_session_${user.tenantId}`);
        if (savedSessionId) {
            setSessionId(savedSessionId);
            loadSessionHistory(savedSessionId);
        } else {
            setMessages([]);
            setSessionId(null);
        }
    }, [user?.tenantId]);

    const clearState = useCallback(() => {
        setMessages([]);
        setSessionId(null);
        setAgentConfig(null);
        setHasInitialized(false);
    }, []);

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

    const loadSessions = async () => {
        try {
            setIsSessionsLoading(true);
            const response = await agentAPI.listSessions() as any;
            const sessionsData = Array.isArray(response) ? response : (response?.sessions || []);
            setSessions(sessionsData);
        } catch (err) {
            console.error('AI Agent: Failed to load sessions:', err);
        } finally {
            setIsSessionsLoading(false);
        }
    };

    const loadSessionHistory = async (sid: string) => {
        try {
            setLoading(true);
            const response = await agentAPI.getHistory(sid) as any;

            const rawMessages = Array.isArray(response)
                ? response
                : (response?.messages || response?.data?.messages || []);

            const mappedMessages: Message[] = rawMessages.map((msg: any, index: number) => {
                const content = msg.content || msg.response || msg.message || '';
                const role = msg.role || msg.type || 'assistant';

                return {
                    id: msg.id || `hist-${index}-${Date.now()}`,
                    type: role === 'user' || role === 'human' ? 'user' : 'assistant',
                    content: content,
                    timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                    agent_type: msg.agent_type || msg.metadata?.agent_type,
                    source: msg.source || msg.metadata?.source,
                    metadata: msg.metadata || {}
                };
            });

            setMessages(mappedMessages);
        } catch (err) {
            console.error('AI Agent: Failed to load session history:', err);
            if (user?.tenantId) {
                localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
            }
            setSessionId(null);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async (questionText: string, dbConnection?: string) => {
        if (!questionText.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            type: 'user',
            content: questionText,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await agentAPI.chat(
                questionText,
                sessionId || undefined,
                selectedKB || undefined,
                dbConnection || undefined,
                selectedPersona
            ) as AgentChatResponse;

            if (response.session_id && response.session_id !== sessionId) {
                setSessionId(response.session_id);
                if (user?.tenantId) {
                    localStorage.setItem(`ai_agent_session_${user.tenantId}`, response.session_id);
                }
                loadSessions();
            }

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: response.content || (response as any).response,
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

    const handleDeleteSession = async (sid: string) => {
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
    };

    const handleRenameSession = async (sid: string, title: string) => {
        try {
            await agentAPI.renameSession(sid, title);
            loadSessions();
        } catch (err) {
            console.error('AI Agent: Failed to rename session:', err);
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        setSessionId(null);
        if (user?.tenantId) {
            localStorage.removeItem(`ai_agent_session_${user.tenantId}`);
        }
    };

    return (
        <AgentContext.Provider value={{
            messages,
            sessions,
            input,
            setInput,
            loading,
            sessionId,
            setSessionId,
            isSessionsLoading,
            agentConfig,
            selectedKB,
            setSelectedKB,
            selectedPersona,
            setSelectedPersona,
            loadSessions,
            loadSessionHistory,
            handleSend,
            handleDeleteSession,
            handleRenameSession,
            handleNewChat,
            clearState
        }}>
            {children}
        </AgentContext.Provider>
    );
};
