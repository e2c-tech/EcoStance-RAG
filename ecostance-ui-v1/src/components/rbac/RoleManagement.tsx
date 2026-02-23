import { useState, useEffect } from 'react';
import { rbacAPI } from '../../services/api';
import { useRBAC, Role } from '../../context/RBACContext';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Users, Shield, Plus, Edit, Trash2, AlertCircle, Check } from 'lucide-react';


export default function RoleManagement() {
  const {
    roles,
    permissions,
    fetchRoles,
    fetchPermissions
  } = useRBAC();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [] as string[],
  });

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, [fetchRoles, fetchPermissions]);


  const handleCreateRole = async () => {
    if (!formData.name.trim()) return;
    try {
      setLoading(true);
      setError('');
      // Filter out any null/undefined values that might have crept into the state
      const dirtyPermissions = formData.permissions;
      const cleanPermissions = dirtyPermissions.filter(p => p && typeof p === 'string');

      await rbacAPI.roles.create({
        ...formData,
        permissions: cleanPermissions
      });
      await fetchRoles(true);
      setSuccess('Role created successfully');
      resetForm();
    } catch (err: any) {
      setError(err.message || 'Failed to create role');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateRole = async () => {
    if (!editingRole || !formData.name.trim()) return;
    try {
      setLoading(true);
      setError('');
      // Filter out any null/undefined values that might have crept into the state
      const dirtyPermissions = formData.permissions;
      const cleanPermissions = dirtyPermissions.filter(p => p && typeof p === 'string');

      await rbacAPI.roles.update(editingRole.id, {
        ...formData,
        permissions: cleanPermissions
      });
      await fetchRoles(true);
      setSuccess('Role updated successfully');
      resetForm();
    } catch (err: any) {
      setError(err.message || 'Failed to update role');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRole = async (roleId: string, roleName: string) => {
    if (!confirm(`Delete role "${roleName}"? This action cannot be undone and will remove this role from all users.`)) return;
    try {
      await rbacAPI.roles.delete(roleId);
      await fetchRoles(true);
      setSuccess('Role deleted successfully');
    } catch (err: any) {
      setError(err.message || 'Failed to delete role');
    }
  };

  const resetForm = () => {
    setFormData({ name: '', description: '', permissions: [] });
    setShowCreateForm(false);
    setEditingRole(null);
  };

  const startEdit = (role: Role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      description: role.description || '',
      permissions: role.permissions || [],
    });
    setShowCreateForm(true);
  };

  const togglePermission = (permissionId: string) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permissionId)
        ? prev.permissions.filter(p => p !== permissionId)
        : [...prev.permissions, permissionId],
    }));
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
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
              <Shield className="w-5 h-5 text-primary" />
              Role Management
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Create and manage custom roles with specific permissions for your organization
            </p>
          </div>
          <Button onClick={() => setShowCreateForm(true)} disabled={showCreateForm}>
            <Plus className="w-4 h-4 mr-2" />
            Create Role
          </Button>
        </div>

        {/* Create/Edit Role Form */}
        {showCreateForm && (
          <div className="mb-6 p-4 bg-background rounded-lg border border-border">
            <h3 className="text-md font-medium text-text mb-4">
              {editingRole ? 'Edit Role' : 'Create New Role'}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Role Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-border rounded-lg bg-surface text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                  placeholder="e.g., Content Manager"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 border border-border rounded-lg bg-surface text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                  placeholder="Describe what this role can do..."
                  rows={2}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-3">
                  Permissions
                </label>
                <div className="space-y-4 max-h-64 overflow-y-auto">
                  {Array.isArray(permissions) && permissions.map((category) => (
                    <div key={category.category} className="border border-border rounded-lg p-3">
                      <h4 className="font-medium text-text mb-2 capitalize">
                        {(category.category || 'Uncategorized').replace(/_/g, ' ')}
                      </h4>
                      <div className="space-y-2">
                        {Array.isArray(category.permissions) && category.permissions.map((permission) => (
                          <label key={permission.id || permission.name} className="flex items-start gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.permissions.includes(permission.id || permission.name)}
                              onChange={() => togglePermission(permission.id || permission.name)}
                              className="mt-0.5 w-4 h-4 accent-primary"
                            />
                            <div>
                              <div className="text-sm font-medium text-text">{permission.name}</div>
                              <div className="text-xs text-text-secondary">{permission.description}</div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  onClick={editingRole ? handleUpdateRole : handleCreateRole}
                  disabled={loading || !formData.name.trim() || formData.permissions.length === 0}
                >
                  {editingRole ? 'Update Role' : 'Create Role'}
                </Button>
                <Button variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Roles List */}
        <div className="space-y-3">
          {Array.isArray(roles) && roles.map((role) => (
            <div key={role.id} className="flex items-center justify-between p-4 border border-border rounded-lg bg-background">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-medium text-text">{role.name}</h3>
                  {!role.is_active && (
                    <span className="px-2 py-0.5 text-xs bg-warning/10 text-warning border border-warning/20 rounded">
                      Inactive
                    </span>
                  )}
                </div>
                {role.description && (
                  <p className="text-sm text-text-secondary mb-2">{role.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {role.user_count || 0} users
                  </span>
                  <span className="flex items-center gap-1">
                    <Shield className="w-3 h-3" />
                    {role.permissions?.length || 0} permissions
                  </span>
                  <span>Created {formatDate(role.created_at)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => startEdit(role)}
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDeleteRole(role.id, role.name)}
                  className="text-error hover:text-error/80"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
          {Array.isArray(roles) && roles.length === 0 && (
            <div className="text-center py-8">
              <Shield className="w-12 h-12 text-text-secondary mx-auto mb-3" />
              <p className="text-text-secondary">No custom roles created yet</p>
              <p className="text-sm text-text-secondary">Create your first role to get started</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}