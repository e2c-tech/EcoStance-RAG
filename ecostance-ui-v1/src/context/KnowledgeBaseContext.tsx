import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { knowledgeBaseAPI } from '../services/api';
import { KnowledgeBaseDetails } from '../services/api.types';
import { useAuth } from './AuthContext.v2';

interface KnowledgeBase {
    id: string;
    name: string;
    documentCount: number;
    totalVectors: number;
    lastUpdated: Date;
    sizeGB: number;
    status: 'Ready' | 'Processing' | 'Error';
}

interface KnowledgeBaseContextType {
    knowledgeBases: KnowledgeBase[];
    isLoading: boolean;
    error: Error | null;
    fetchKnowledgeBases: (force?: boolean) => Promise<void>;
    deleteKB: (kbId: string) => Promise<void>;
    addKB: (kb: KnowledgeBase) => void;
}

const KnowledgeBaseContext = createContext<KnowledgeBaseContextType | undefined>(undefined);

export const KnowledgeBaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);
    const { user } = useAuth();

    // Clear data when tenant changes
    useEffect(() => {
        setKnowledgeBases([]);
        setHasLoaded(false);
        setError(null);
    }, [user?.tenantId]);

    const fetchKnowledgeBases = useCallback(async (force = false) => {
        // If already loaded and not forcing, don't fetch again
        if (hasLoaded && !force && knowledgeBases.length > 0) {
            return;
        }

        try {
            setIsLoading(true);
            setError(null);

            const response = await knowledgeBaseAPI.list(force);

            if (response && Array.isArray(response)) {
                const detailedKBs = await Promise.all(
                    response.map(async (kb: any) => {
                        const kbName = typeof kb === 'string' ? kb : (kb.name || kb.id);
                        try {
                            const details = await knowledgeBaseAPI.getDetails(kbName, force) as KnowledgeBaseDetails;
                            return {
                                id: kbName,
                                name: kbName,
                                documentCount: details.files_count || 0,
                                totalVectors: details.vectors_count || details.total_points || 0,
                                lastUpdated: new Date(),
                                sizeGB: 0,
                                status: 'Ready' as const,
                            } as KnowledgeBase;
                        } catch (err) {
                            return {
                                id: kbName,
                                name: kbName,
                                documentCount: 0,
                                totalVectors: 0,
                                lastUpdated: new Date(),
                                sizeGB: 0,
                                status: 'Ready' as const,
                            } as KnowledgeBase;
                        }
                    })
                );
                setKnowledgeBases(detailedKBs);
                setHasLoaded(true);
            }
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch knowledge bases'));
        } finally {
            setIsLoading(false);
        }
    }, [hasLoaded, knowledgeBases.length]);

    const removeKB = useCallback(async (kbId: string) => {
        try {
            await knowledgeBaseAPI.delete(kbId);
            setKnowledgeBases(prev => prev.filter(kb => kb.id !== kbId));
        } catch (err) {
            throw err;
        }
    }, []);

    const addKB = useCallback((kb: KnowledgeBase) => {
        setKnowledgeBases(prev => [...prev, kb]);
    }, []);

    return (
        <KnowledgeBaseContext.Provider value={{
            knowledgeBases,
            isLoading,
            error,
            fetchKnowledgeBases,
            deleteKB: removeKB,
            addKB
        }}>
            {children}
        </KnowledgeBaseContext.Provider>
    );
};

export const useKnowledgeBases = () => {
    const context = useContext(KnowledgeBaseContext);
    if (context === undefined) {
        throw new Error('useKnowledgeBases must be used within a KnowledgeBaseProvider');
    }
    return context;
};
