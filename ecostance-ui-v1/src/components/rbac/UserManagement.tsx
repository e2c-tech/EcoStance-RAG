import { useState, useEffect } from 'react';
import { tenantUsersAPI, tenantRolesAPI } from '../../services/api';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Users, UserPlus, Edit, Trash2, Search, AlertCircle, Check, Shield } from 'lucide-react';

interface Role {
    id: string;
    name: string;
    description?: string;
}

interface User {
    id: string;
    email: string;
    full_name: string;
    role?: { // API returns single role object or null
        id: string;
        name: string;
    };
    is_active: boolean;
    created_at: string;
}

export default function UserManagement() {
    const [users, setUsers] = useState<User[]>([]);
    const [roles, setRoles] = useState<Role[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    // Modal states
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [formData, setFormData] = useState({
        emails: '',
        role_id: '',
        is_active: true,
        full_name: '' // Only for edit mode
    });

    useEffect(() => {
        loadUsers();
        loadRoles();
    }, []);

    const loadUsers = async () => {
        try {
            const data = await tenantUsersAPI.list();
            console.log('🔍 Raw users data:', data);

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
        } catch (err: any) {
            console.error('❌ Failed to load users:', err);
            setError(err.message || 'Failed to load users');
            setUsers([]);
        }
    };

    const loadRoles = async () => {
        try {
            const data = await tenantRolesAPI.list();
            console.log('🔍 Raw roles data:', data);

            let rolesArray: Role[] = [];
            if (Array.isArray(data)) {
                rolesArray = data;
            } else if (data && typeof data === 'object') {
                // Check common property names for lists
                if ('roles' in data && Array.isArray((data as any).roles)) {
                    rolesArray = (data as any).roles;
                } else if ('data' in data && Array.isArray((data as any).data)) {
                    rolesArray = (data as any).data;
                } else if ('items' in data && Array.isArray((data as any).items)) {
                    rolesArray = (data as any).items;
                } else if ('results' in data && Array.isArray((data as any).results)) {
                    rolesArray = (data as any).results;
                } else {
                    console.warn('⚠️ Unexpected roles response format:', data);
                }
            }
            setRoles(rolesArray);
        } catch (err: any) {
            console.error('❌ Failed to load roles:', err);
        }
    };

    const handleInviteUsers = async () => {
        if (!formData.emails.trim() || !formData.role_id) return;

        // Parse emails from textarea (split by comma, space, newline)
        const emailList = formData.emails
            .split(/[\s,]+/)
            .map(e => e.trim())
            .filter(e => e && e.includes('@')); // Basic validation

        if (emailList.length === 0) {
            setError('Please enter at least one valid email address.');
            return;
        }

        try {
            setLoading(true);
            setError('');

            const result: any = await tenantUsersAPI.inviteBulk({
                emails: emailList,
                role_id: formData.role_id
            });

            await loadUsers();

            // Construct success message
            const successCount = result.successful ? result.successful.length : 0;
            const failedCount = result.failed ? result.failed.length : 0;

            if (successCount > 0) {
                console.log('✅ Successful invitations:', result.successful);
            }

            let msg = `Invited ${successCount} user(s) successfully.`;
            if (failedCount > 0) {
                msg += ` Failed to invite ${failedCount} user(s). Check console for details.`;
                console.warn('Failed invitations:', result.failed);
            }

            setSuccess(msg);
            resetForm();
        } catch (err: any) {
            setError(err.message || 'Failed to invite users');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateUser = async () => {
        if (!editingUser) return;

        try {
            setLoading(true);
            setError('');
            await tenantUsersAPI.update(editingUser.id, {
                full_name: formData.full_name,
                is_active: formData.is_active,
                role_id: formData.role_id
            });
            await loadUsers();
            setSuccess('User updated successfully');
            resetForm();
        } catch (err: any) {
            setError(err.message || 'Failed to update user');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteUser = async (userId: string, userEmail: string) => {
        if (!confirm(`Are you sure you want to remove ${userEmail}? This action cannot be undone.`)) return;

        try {
            setLoading(true);
            setError('');
            await tenantUsersAPI.remove(userId);
            await loadUsers();
            setSuccess('User removed successfully');
        } catch (err: any) {
            // If user is already gone (404), treat as success and refresh
            const errorMsg = (err.message || '').toLowerCase();
            if (errorMsg.includes('user not found') || errorMsg.includes('not found')) {
                await loadUsers();
                setSuccess('User entry cleared (already deleted)');
            } else {
                setError(err.message || 'Failed to remove user');
            }
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setShowModal(false);
        setEditingUser(null);
        setFormData({
            emails: '',
            role_id: '',
            is_active: true,
            full_name: ''
        });
        setTimeout(() => {
            setSuccess('');
            setError('');
        }, 5000);
    };

    const openEditModal = (user: User) => {
        setEditingUser(user);
        setFormData({
            emails: user.email, // Use this field for display in edit (read-only)
            full_name: user.full_name || '',
            role_id: user.role?.id || '',
            is_active: user.is_active
        });
        setShowModal(true);
    };

    const filteredUsers = Array.isArray(users) ? users.filter(user =>
        user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (user.full_name || '').toLowerCase().includes(searchTerm.toLowerCase())
    ) : [];

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    return (
        <div className="space-y-6">
            {error && (
                <div className="p-4 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
                    <p className="text-error">{error}</p>
                </div>
            )}

            {success && (
                <div className="p-4 bg-success/10 border border-success/20 rounded-lg flex items-start gap-2">
                    <Check className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                    <p className="text-success">{success}</p>
                </div>
            )}

            <Card className="p-6 bg-surface border-border">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-lg font-semibold text-text flex items-center gap-2">
                            <Users className="w-5 h-5 text-primary" />
                            User Management
                        </h2>
                        <p className="text-sm text-text-secondary mt-1">
                            Invite and manage users in your organization
                        </p>
                    </div>
                    <Button onClick={() => setShowModal(true)}>
                        <UserPlus className="w-4 h-4 mr-2" />
                        Invite Users
                    </Button>
                </div>

                {/* Search */}
                <div className="mb-6">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                        <input
                            type="text"
                            placeholder="Search users by email or name..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                        />
                    </div>
                </div>

                {/* Users List */}
                <div className="space-y-3">
                    {filteredUsers.map((user) => (
                        <div key={user.id} className="p-4 border border-border rounded-lg bg-background">
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h3 className="font-medium text-text">{user.email}</h3>
                                        {user.full_name && (
                                            <span className="text-sm text-text-secondary">({user.full_name})</span>
                                        )}
                                        {!user.is_active && (
                                            <span className="px-2 py-0.5 text-xs bg-warning/10 text-warning border border-warning/20 rounded">
                                                Inactive
                                            </span>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-4 text-xs text-text-secondary mt-2">
                                        <span className="flex items-center gap-1">
                                            <Shield className="w-3 h-3" />
                                            {user.role ? user.role.name : 'No Active Role'}
                                        </span>
                                        <span>Added {formatDate(user.created_at)}</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => openEditModal(user)}
                                    >
                                        <Edit className="w-4 h-4" />
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleDeleteUser(user.id, user.email)}
                                        className="text-error hover:text-error/80"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ))}
                    {filteredUsers.length === 0 && (
                        <div className="text-center py-8">
                            <Users className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                            <p className="text-text-secondary">
                                {searchTerm ? 'No users found matching your search' : 'No users found'}
                            </p>
                        </div>
                    )}
                </div>
            </Card>

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-surface border border-border rounded-lg p-6 w-full max-w-md mx-4">
                        <h3 className="text-lg font-semibold text-text mb-4">
                            {editingUser ? 'Edit User' : 'Invite New Users'}
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-1">
                                    {editingUser ? 'Email Address' : 'Email Addresses (Bulk)'} *
                                </label>
                                {editingUser ? (
                                    <input
                                        type="email"
                                        value={formData.emails}
                                        disabled
                                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text opacity-50 cursor-not-allowed"
                                    />
                                ) : (
                                    <>
                                        <textarea
                                            value={formData.emails}
                                            onChange={(e) => setFormData(prev => ({ ...prev, emails: e.target.value }))}
                                            className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text focus:border-primary focus:outline-none min-h-[100px]"
                                            placeholder="colleague1@example.com, colleague2@example.com&#10;colleague3@example.com"
                                        />
                                        <p className="text-xs text-text-secondary mt-1">
                                            Enter multiple emails separated by commas, spaces, or new lines.
                                        </p>
                                    </>
                                )}
                            </div>

                            {editingUser && (
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-1">
                                        Full Name
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.full_name}
                                        onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text focus:border-primary focus:outline-none"
                                        placeholder="e.g. John Doe"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-1">
                                    Role *
                                </label>
                                <select
                                    value={formData.role_id}
                                    onChange={(e) => setFormData(prev => ({ ...prev, role_id: e.target.value }))}
                                    className="w-full px-3 py-2 border border-border rounded-lg bg-background text-text focus:border-primary focus:outline-none"
                                >
                                    <option value="">Select a role...</option>
                                    {roles.length === 0 ? (
                                        <option disabled>No roles found</option>
                                    ) : (
                                        roles.map(role => (
                                            <option key={role.id} value={role.id}>
                                                {role.name}
                                            </option>
                                        ))
                                    )}
                                </select>
                                <p className="text-xs text-text-secondary mt-1">
                                    Assigning a role grants specific permissions to {editingUser ? 'this user' : 'these users'}.
                                </p>
                            </div>

                            {editingUser && (
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="is_active"
                                        checked={formData.is_active}
                                        onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                                        className="w-4 h-4 accent-primary"
                                    />
                                    <label htmlFor="is_active" className="text-sm text-text">Active Account</label>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-2 mt-6">
                            <Button
                                variant="outline"
                                onClick={resetForm}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={editingUser ? handleUpdateUser : handleInviteUsers}
                                disabled={loading || !formData.emails || !formData.role_id}
                            >
                                {editingUser ? 'Save Changes' : (loading ? 'Sending Invites...' : 'Send Invites')}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
