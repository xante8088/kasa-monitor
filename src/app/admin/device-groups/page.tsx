'use client';

import React, { useState, useEffect } from 'react';
import { Folder, Plus, Trash2, Edit, Power, Zap, ChevronRight } from 'lucide-react';

interface DeviceGroup {
  id: number;
  name: string;
  description: string;
  devices: string[];
  parent_id?: number;
  children?: DeviceGroup[];
  total_power: number;
  device_count: number;
  created_at: string;
}

interface Device {
  id: string;
  name: string;
  model: string;
  is_on: boolean;
  current_power: number;
}

export default function DeviceGroupsPage() {
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<DeviceGroup | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<DeviceGroup | null>(null);

  useEffect(() => {
    fetchGroups();
    fetchDevices();
  }, []);

  const fetchGroups = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/device-groups', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setGroups(organizeHierarchy(data));
      }
    } catch (error) {
      console.error('Failed to fetch device groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDevices = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/devices', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  };

  const organizeHierarchy = (groups: DeviceGroup[]): DeviceGroup[] => {
    const map = new Map<number, DeviceGroup>();
    const roots: DeviceGroup[] = [];
    
    groups.forEach(group => {
      map.set(group.id, { ...group, children: [] });
    });
    
    groups.forEach(group => {
      if (group.parent_id) {
        const parent = map.get(group.parent_id);
        if (parent) {
          parent.children = parent.children || [];
          parent.children.push(map.get(group.id)!);
        }
      } else {
        roots.push(map.get(group.id)!);
      }
    });
    
    return roots;
  };

  const controlGroup = async (groupId: number, action: 'on' | 'off') => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/device-groups/${groupId}/control`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      });
      fetchGroups();
    } catch (error) {
      console.error('Failed to control group:', error);
    }
  };

  const deleteGroup = async (groupId: number) => {
    if (!confirm('Are you sure you want to delete this group?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/device-groups/${groupId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchGroups();
    } catch (error) {
      console.error('Failed to delete group:', error);
    }
  };

  const createGroup = async (groupData: any) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/device-groups', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(groupData)
      });
      
      if (response.ok) {
        fetchGroups();
        setShowCreateModal(false);
      }
    } catch (error) {
      console.error('Failed to create group:', error);
    }
  };

  const updateGroup = async (groupId: number, groupData: any) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/device-groups/${groupId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(groupData)
      });
      
      if (response.ok) {
        fetchGroups();
        setEditingGroup(null);
      }
    } catch (error) {
      console.error('Failed to update group:', error);
    }
  };

  const GroupCard = ({ group, level = 0 }: { group: DeviceGroup; level?: number }) => {
    const [expanded, setExpanded] = useState(false);
    
    return (
      <div className={`${level > 0 ? 'ml-8' : ''}`}>
        <div className="border border-gray-200 rounded-lg p-4 mb-3 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div className="flex items-start flex-1">
              {group.children && group.children.length > 0 && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="mr-2 mt-1 text-gray-500 hover:text-gray-700"
                >
                  <ChevronRight
                    className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
                  />
                </button>
              )}
              <div className="flex-1">
                <div className="flex items-center">
                  <Folder className="h-5 w-5 text-blue-500 mr-2" />
                  <h3 className="text-lg font-medium text-gray-900">{group.name}</h3>
                  <span className="ml-3 px-2 py-1 text-xs bg-gray-100 rounded-full">
                    {group.device_count} devices
                  </span>
                </div>
                {group.description && (
                  <p className="mt-1 text-sm text-gray-600">{group.description}</p>
                )}
                <div className="mt-2 flex items-center space-x-4 text-sm">
                  <div className="flex items-center text-gray-500">
                    <Zap className="h-4 w-4 mr-1" />
                    <span>{group.total_power.toFixed(1)}W</span>
                  </div>
                  <span className="text-gray-400">
                    Created {new Date(group.created_at).toLocaleDateString()}
                  </span>
                </div>
                {group.devices.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {group.devices.slice(0, 5).map((deviceId) => {
                      const device = devices.find(d => d.id === deviceId);
                      return device ? (
                        <span
                          key={deviceId}
                          className={`px-2 py-1 text-xs rounded ${
                            device.is_on ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {device.name}
                        </span>
                      ) : null;
                    })}
                    {group.devices.length > 5 && (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                        +{group.devices.length - 5} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2 ml-4">
              <button
                onClick={() => controlGroup(group.id, 'on')}
                className="p-2 text-green-600 hover:bg-green-50 rounded"
                title="Turn all on"
              >
                <Power className="h-4 w-4" />
              </button>
              <button
                onClick={() => controlGroup(group.id, 'off')}
                className="p-2 text-red-600 hover:bg-red-50 rounded"
                title="Turn all off"
              >
                <Power className="h-4 w-4" />
              </button>
              <button
                onClick={() => setEditingGroup(group)}
                className="p-2 text-gray-500 hover:text-blue-600"
              >
                <Edit className="h-4 w-4" />
              </button>
              <button
                onClick={() => deleteGroup(group.id)}
                className="p-2 text-gray-500 hover:text-red-600"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        {expanded && group.children && (
          <div className="mt-2">
            {group.children.map((child) => (
              <GroupCard key={child.id} group={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Device Groups</h1>
          <p className="text-gray-600 mt-1">Organize and control devices in groups</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Group
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {groups.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <Folder className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No device groups created yet</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-4 text-blue-600 hover:text-blue-700"
              >
                Create your first group
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {groups.map((group) => (
                <GroupCard key={group.id} group={group} />
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Group Statistics</h3>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Total Groups</p>
                <p className="text-2xl font-semibold text-gray-900">{groups.length}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Grouped Devices</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {groups.reduce((sum, g) => sum + g.device_count, 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Power Usage</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {groups.reduce((sum, g) => sum + g.total_power, 0).toFixed(1)}W
                </p>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Quick Actions</h4>
              <div className="space-y-2">
                <button className="w-full text-left px-3 py-2 text-sm bg-green-50 text-green-700 rounded hover:bg-green-100">
                  Turn All Groups On
                </button>
                <button className="w-full text-left px-3 py-2 text-sm bg-red-50 text-red-700 rounded hover:bg-red-100">
                  Turn All Groups Off
                </button>
                <button className="w-full text-left px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded hover:bg-blue-100">
                  Export Group Report
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Create/Edit Group Modal */}
      {(showCreateModal || editingGroup) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {editingGroup ? 'Edit Group' : 'Create New Group'}
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                
                // Get selected devices from checkboxes
                const selectedDevices: string[] = [];
                const checkboxes = e.currentTarget.querySelectorAll('input[name="device"]:checked');
                checkboxes.forEach((checkbox: any) => {
                  selectedDevices.push(checkbox.value);
                });
                
                const groupData = {
                  name: formData.get('name'),
                  description: formData.get('description'),
                  devices: selectedDevices,
                  parent_id: formData.get('parent_id') ? parseInt(formData.get('parent_id') as string) : null
                };
                
                if (editingGroup) {
                  updateGroup(editingGroup.id, groupData);
                } else {
                  createGroup(groupData);
                }
              }}
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Group Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    defaultValue={editingGroup?.name}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter group name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    name="description"
                    defaultValue={editingGroup?.description}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter group description (optional)"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Parent Group (Optional)
                  </label>
                  <select
                    name="parent_id"
                    defaultValue={editingGroup?.parent_id || ''}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">No Parent (Root Group)</option>
                    {groups.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select Devices
                  </label>
                  <div className="border border-gray-300 rounded-md p-2 max-h-40 overflow-y-auto">
                    {devices.length === 0 ? (
                      <p className="text-sm text-gray-500">No devices available</p>
                    ) : (
                      devices.map((device) => (
                        <label key={device.id} className="flex items-center p-1 hover:bg-gray-50">
                          <input
                            type="checkbox"
                            name="device"
                            value={device.id}
                            defaultChecked={editingGroup?.devices.includes(device.id)}
                            className="mr-2"
                          />
                          <span className="text-sm">{device.name} - {device.model}</span>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              </div>
              
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingGroup(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editingGroup ? 'Update' : 'Create'} Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}