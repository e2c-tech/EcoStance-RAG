import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { tenantUsersAPI, tenantRolesAPI, rbacAPI } from '../services/api';
import { useAuth } from './AuthContext.v2';

export interface Role {
    id: string;
    name: string;
    description?: string;
    permissions?: string[];
    user_count?: number;
    is_active?: boolean;
    created_at?: string;
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    role?: {
        id: string;
        name: string;
    };
    is_active: boolean;
    created_at: string;
}

export interface Permission {
    id: string;
    name: string;
    description: string;
    category: string;
}

export interface PermissionCategory {
    category: string;
    permissions: Permission[];
}

interface RBACContextType {
    users: User[];
    roles: Role[];
    permissions: PermissionCategory[];
    isLoading: boolean;
    error: string | null;
    fetchUsers: (force?: boolean) => Promise<void>;
    fetchRoles: (force?: boolean) => Promise<void>;
    fetchPermissions: (force?: boolean) => Promise<void>;
    refreshAll: () => Promise<void>;
}

const RBACContext = createContext<RBACContextType | undefined>(undefined);

export const RBACProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { user } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissions, setPermissions] = useState<PermissionCategory[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loadedStates, setLoadedStates] = useState({
        users: false,
        roles: false,
        permissions: false
    });

    // Clear state when tenant changes
    useEffect(() => {
        setUsers([]);
        setRoles([]);
        setPermissions([]);
        setLoadedStates({ users: false, roles: false, permissions: false });
        setError(null);
    }, [user?.tenantId]);

    const fetchUsers = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.users && !force && users.length > 0) return;

        try {
            setIsLoading(true);
            const data = await tenantUsersAPI.list();
            let usersArray: User[] = [];
            if (Array.isArray(data)) {
                usersArray = data;
            } else if (data && typeof data === 'object') {
                if ('users' in data && Array.isArray((data as any).users)) {
                    usersArray = (data as any).users;
                } else if ('data' in data && Array.isArray((data as any).data)) {
                    usersArray = (data as any).data;
                }
            }
            setUsers(usersArray);
            setLoadedStates(prev => ({ ...prev, users: true }));
        } catch (err: any) {
            setError(err.message || 'Failed to load users');
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.users, users.length]);

    const fetchRoles = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.roles && !force && roles.length > 0) return;

        try {
            setIsLoading(true);
            const data = await tenantRolesAPI.list();
            let rolesArray: Role[] = [];
            if (Array.isArray(data)) {
                rolesArray = data;
            } else if (data && typeof data === 'object') {
                if ('roles' in data && Array.isArray((data as any).roles)) {
                    rolesArray = (data as any).roles;
                } else if ('data' in data && Array.isArray((data as any).data)) {
                    rolesArray = (data as any).data;
                } else if ('items' in data && Array.isArray((data as any).items)) {
                    rolesArray = (data as any).items;
                } else if ('results' in data && Array.isArray((data as any).results)) {
                    rolesArray = (data as any).results;
                }
            }
            setRoles(rolesArray);
            setLoadedStates(prev => ({ ...prev, roles: true }));
        } catch (err: any) {
            console.error('Failed to load roles:', err);
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.roles, roles.length]);

    const fetchPermissions = useCallback(async (force = false) => {
        if (!user?.tenantId) return;
        if (loadedStates.permissions && !force && permissions.length > 0) return;

        try {
            setIsLoading(true);
            const data = await rbacAPI.permissions.getCategories();
            let permissionsArray: PermissionCategory[] = [];
            if (Array.isArray(data)) {
                permissionsArray = data;
            } else if (data && typeof data === 'object' && 'categories' in data && Array.isArray((data as any).categories)) {
                permissionsArray = (data as any).categories;
            } else if (data && typeof data === 'object' && 'data' in data && Array.isArray((data as any).data)) {
                permissionsArray = (data as any).data;
            }
            setPermissions(permissionsArray);
            setLoadedStates(prev => ({ ...prev, permissions: true }));
        } catch (err: any) {
            console.error('Failed to load permissions:', err);
        } finally {
            setIsLoading(false);
        }
    }, [user?.tenantId, loadedStates.permissions, permissions.length]);

    const refreshAll = useCallback(async () => {
        await Promise.all([
            fetchUsers(true),
            fetchRoles(true),
            fetchPermissions(true)
        ]);
    }, [fetchUsers, fetchRoles, fetchPermissions]);

    return (
        <RBACContext.Provider value={{
            users,
            roles,
            permissions,
            isLoading,
            error,
            fetchUsers,
            fetchRoles,
            fetchPermissions,
            refreshAll
        }}>
            {children}
        </RBACContext.Provider>
    );
};

export const useRBAC = () => {
    const context = useContext(RBACContext);
    if (context === undefined) {
        throw new Error('useRBAC must be used within an RBACProvider');
    }
    return context;
};
