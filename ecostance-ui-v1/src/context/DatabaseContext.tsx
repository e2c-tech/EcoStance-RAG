import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { databaseAPI } from '../services/api';
import { useAuth } from './AuthContext.v2';

interface Connection {
    name: string;
    type: string;
    host: string;
    database: string;
    username: string;
}

interface DatabaseSchema {
    tables: Array<{
        name: string;
        columns: Array<{
            name: string;
            type: string;
        }>;
    }>;
}

interface DatabaseContextType {
    connections: Connection[];
    selectedConnection: string;
    isConnected: boolean;
    schema: DatabaseSchema | null;
    isLoading: boolean;
    error: string | null;
    fetchConnections: (force?: boolean) => Promise<void>;
    connect: (connectionName: string) => Promise<void>;
    disconnect: () => void;
    setIsConnected: (connected: boolean) => void;
    setSelectedConnection: (name: string) => void;
    setSchema: (schema: DatabaseSchema | null) => void;
    loadSchema: () => Promise<void>;
}

const DatabaseContext = createContext<DatabaseContextType | undefined>(undefined);

export const DatabaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [connections, setConnections] = useState<Connection[]>([]);
    const [selectedConnection, setSelectedConnection] = useState<string>('');
    const [isConnected, setIsConnected] = useState(false);
    const [schema, setSchema] = useState<DatabaseSchema | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);
    const { user } = useAuth();

    // Clear state when user or tenant changes
    useEffect(() => {
        setConnections([]);
        setSelectedConnection('');
        setIsConnected(false);
        setSchema(null);
        setHasLoaded(false);
        setError(null);
    }, [user?.tenantId]);

    const fetchConnections = useCallback(async (force = false) => {
        if (hasLoaded && !force && connections.length > 0) {
            return;
        }

        try {
            setIsLoading(true);
            setError(null);
            const data = await databaseAPI.listConnections() as Connection[];
            if (Array.isArray(data)) {
                setConnections(data);
                setHasLoaded(true);
            }
        } catch (err: any) {
            console.error('Failed to load connections:', err);
            setError(err.message || 'Failed to load connections');
        } finally {
            setIsLoading(false);
        }
    }, [hasLoaded, connections.length]);

    const connect = useCallback(async (connectionName: string) => {
        try {
            setIsLoading(true);
            setError(null);
            const conn = await databaseAPI.loadConnection(connectionName) as any;

            let dbUri: string;
            if (conn.db_uri) {
                dbUri = conn.db_uri;
            } else if (conn.type === 'sqlite') {
                dbUri = conn.db_path || conn.database;
            } else {
                dbUri = `${conn.type}://${conn.username}:${conn.password}@${conn.host}:${conn.port}/${conn.database}`;
            }

            await databaseAPI.connect(dbUri);
            setIsConnected(true);
            setSelectedConnection(connectionName);

            // Try to load schema
            try {
                const schemaData = await databaseAPI.getSchema() as any;
                setSchema(schemaData);
            } catch (schemaErr) {
                console.warn('Failed to load schema during connect:', schemaErr);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to connect to database');
            throw err;
        } finally {
            setIsLoading(false);
        }
    }, []);

    const disconnect = useCallback(() => {
        setIsConnected(false);
        setSelectedConnection('');
        setSchema(null);
    }, []);

    const loadSchema = useCallback(async () => {
        try {
            const schemaData = await databaseAPI.getSchema() as any;
            setSchema(schemaData);
        } catch (err: any) {
            console.warn('Failed to load schema:', err);
        }
    }, []);

    return (
        <DatabaseContext.Provider value={{
            connections,
            selectedConnection,
            isConnected,
            schema,
            isLoading,
            error,
            fetchConnections,
            connect,
            disconnect,
            setIsConnected,
            setSelectedConnection,
            setSchema,
            loadSchema
        }}>
            {children}
        </DatabaseContext.Provider>
    );
};

export const useDatabase = () => {
    const context = useContext(DatabaseContext);
    if (context === undefined) {
        throw new Error('useDatabase must find its way into a DatabaseProvider');
    }
    return context;
};
