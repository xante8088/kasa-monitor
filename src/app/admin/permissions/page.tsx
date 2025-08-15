'use client';

import React, { useState, useEffect } from 'react';
import { AppLayout } from '@/components/app-layout';

interface Permission {
  name: string;
  description: string;
  category: string;
}

interface RolePermissions {
  role: string;
  permissions: string[];
}

const PERMISSION_CATEGORIES = {
  'device_management': 'Device Management',
  'rate_management': 'Rate Management',
  'user_management': 'User Management',
  'system_config': 'System Configuration'
};

export default function PermissionsPage() {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [rolePermissions, setRolePermissions] = useState<RolePermissions[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const roles = ['admin', 'operator', 'viewer', 'guest'];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      console.log('Token retrieved:', token ? `${token.substring(0, 20)}...` : 'No token');
      
      // Fetch permissions
      const permissionsResponse = await fetch('/api/permissions', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log('Permissions response status:', permissionsResponse.status);
      if (permissionsResponse.ok) {
        const permissionsData = await permissionsResponse.json();
        console.log('Permissions data:', permissionsData);
        setPermissions(permissionsData);
      } else {
        const errorText = await permissionsResponse.text();
        console.error('Permissions fetch error:', errorText);
      }

      // Fetch role permissions
      const rolePermissionsResponse = await fetch('/api/roles/permissions', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      console.log('Role permissions response status:', rolePermissionsResponse.status);
      if (rolePermissionsResponse.ok) {
        const rolePermissionsData = await rolePermissionsResponse.json();
        console.log('Role permissions data:', rolePermissionsData);
        setRolePermissions(rolePermissionsData);
      } else {
        const errorText = await rolePermissionsResponse.text();
        console.error('Role permissions fetch error:', errorText);
      }
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Failed to load permissions data');
    } finally {
      setLoading(false);
    }
  };

  const hasPermission = (role: string, permission: string) => {
    const rolePerms = rolePermissions.find(rp => rp.role === role);
    return rolePerms?.permissions.includes(permission) || false;
  };

  const togglePermission = async (role: string, permission: string) => {
    setSaving(true);
    
    try {
      const token = localStorage.getItem('token');
      const hasCurrentPermission = hasPermission(role, permission);
      
      const response = await fetch(`/api/roles/${role}/permissions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          permission,
          action: hasCurrentPermission ? 'remove' : 'add'
        })
      });

      if (response.ok) {
        // Update local state
        setRolePermissions(prev => {
          const updated = prev.map(rp => {
            if (rp.role === role) {
              return {
                ...rp,
                permissions: hasCurrentPermission
                  ? rp.permissions.filter(p => p !== permission)
                  : [...rp.permissions, permission]
              };
            }
            return rp;
          });

          // If role doesn't exist, add it
          if (!updated.find(rp => rp.role === role)) {
            updated.push({
              role,
              permissions: [permission]
            });
          }

          return updated;
        });
      } else {
        setError('Failed to update permission');
      }
    } catch (err) {
      setError('Connection error');
    } finally {
      setSaving(false);
    }
  };

  const groupPermissionsByCategory = () => {
    const grouped: Record<string, Permission[]> = {};
    
    permissions.forEach(permission => {
      const category = permission.category || 'other';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(permission);
    });

    return grouped;
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-50 border-red-200 text-red-800';
      case 'operator': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'viewer': return 'bg-green-50 border-green-200 text-green-800';
      case 'guest': return 'bg-gray-50 border-gray-200 text-gray-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const groupedPermissions = groupPermissionsByCategory();

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Role & Permission Management</h1>
        <p className="text-gray-600 mt-1">Configure permissions for each user role</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {saving && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-blue-600">Saving changes...</p>
        </div>
      )}

      <div className="bg-white shadow-lg rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Permission
                </th>
                {roles.map(role => (
                  <th key={role} className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <span className={`inline-flex px-3 py-1 text-xs font-semibold rounded-full ${getRoleColor(role)}`}>
                      {role}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white">
              {Object.entries(groupedPermissions).map(([category, categoryPermissions], categoryIndex) => (
                <React.Fragment key={category}>
                  <tr className="bg-gray-100">
                    <td colSpan={roles.length + 1} className="px-6 py-3 text-sm font-semibold text-gray-900 uppercase tracking-wide">
                      {PERMISSION_CATEGORIES[category as keyof typeof PERMISSION_CATEGORIES] || category}
                    </td>
                  </tr>
                  {categoryPermissions.map((permission, permIndex) => (
                    <tr key={permission.name} className={permIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {permission.description}
                          </div>
                          <div className="text-sm text-gray-500">
                            {permission.name}
                          </div>
                        </div>
                      </td>
                      {roles.map(role => (
                        <td key={role} className="px-6 py-4 text-center">
                          <label className="inline-flex items-center">
                            <input
                              type="checkbox"
                              checked={hasPermission(role, permission.name)}
                              onChange={() => togglePermission(role, permission.name)}
                              disabled={saving}
                              className="form-checkbox h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                          </label>
                        </td>
                      ))}
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {permissions.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">🔐</div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No permissions configured</h3>
            <p className="text-gray-500">Permissions will appear here once the backend is configured.</p>
          </div>
        )}
      </div>

      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-4">Role Descriptions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium text-red-800">Administrator</h4>
            <p className="text-sm text-red-700">Full system access including user management, system configuration, and all device operations.</p>
          </div>
          <div>
            <h4 className="font-medium text-blue-800">Operator</h4>
            <p className="text-sm text-blue-700">Can control devices, view data, and manage rates but cannot manage users or system settings.</p>
          </div>
          <div>
            <h4 className="font-medium text-green-800">Viewer</h4>
            <p className="text-sm text-green-700">Read-only access to device data and rate information.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-800">Guest</h4>
            <p className="text-sm text-gray-700">Limited access to basic device information only.</p>
          </div>
        </div>
      </div>
      </div>
    </AppLayout>
  );
}