'use client';

import React, { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, Edit, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { AppLayout } from '@/components/app-layout';
import { safeConsoleError, safeStorage } from '@/lib/security-utils';

interface Alert {
  id: number;
  name: string;
  type: string;
  threshold: number;
  condition: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  device_ips?: string[];
  notification_channels: string[];
  created_at: string;
  triggered_count: number;
  last_triggered?: string;
}

interface AlertHistory {
  id: number;
  alert_id: number;
  alert_name: string;
  triggered_at: string;
  severity: string;
  message: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
}

interface Device {
  ip: string;
  alias?: string;
  model?: string;
  device_type?: string;
  is_on?: boolean;
  mac?: string;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'rules' | 'history'>('rules');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchAlerts();
    fetchAlertHistory();
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const token = safeStorage.getItem('token');
      const response = await fetch('/api/devices', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
      }
    } catch (error) {
      safeConsoleError('Failed to fetch devices', error);
    }
  };

  const fetchAlerts = async () => {
    try {
      const token = safeStorage.getItem('token');
      const response = await fetch('/api/alerts', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      safeConsoleError('Failed to fetch alerts', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlertHistory = async () => {
    try {
      const token = safeStorage.getItem('token');
      const response = await fetch('/api/alerts/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAlertHistory(data);
      }
    } catch (error) {
      safeConsoleError('Failed to fetch alert history', error);
    }
  };

  const toggleAlert = async (alertId: number, enabled: boolean) => {
    try {
      const token = safeStorage.getItem('token');
      await fetch(`/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enabled })
      });
      fetchAlerts();
    } catch (error) {
      safeConsoleError('Failed to toggle alert', error);
    }
  };

  const deleteAlert = async (alertId: number) => {
    if (!confirm('Are you sure you want to delete this alert?')) return;
    
    try {
      const token = safeStorage.getItem('token');
      await fetch(`/api/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAlerts();
    } catch (error) {
      safeConsoleError('Failed to delete alert', error);
    }
  };

  const acknowledgeAlert = async (historyId: number) => {
    try {
      const token = safeStorage.getItem('token');
      await fetch(`/api/alerts/history/${historyId}/acknowledge`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAlertHistory();
    } catch (error) {
      safeConsoleError('Failed to acknowledge alert', error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50';
      case 'high': return 'text-orange-600 bg-orange-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <XCircle className="h-4 w-4" />;
      case 'high': return <AlertTriangle className="h-4 w-4" />;
      default: return <Bell className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Alert Management</h1>
          <p className="text-gray-600 mt-1">Configure alerts and view alert history</p>
        </div>
        <button
          onClick={() => {
            setShowCreateModal(true);
            setSelectedDevices(new Set());
            setSelectedChannels(new Set());
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Alert
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('rules')}
              className={`py-2 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'rules'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Alert Rules ({alerts.length})
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`py-2 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Alert History ({alertHistory.filter(a => !a.acknowledged).length} unacknowledged)
            </button>
          </nav>
        </div>

        {activeTab === 'rules' ? (
          <div className="p-6">
            {alerts.length === 0 ? (
              <div className="text-center py-8">
                <Bell className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No alert rules configured</p>
                <button
                  onClick={() => {
                    setShowCreateModal(true);
                    setSelectedDevices(new Set());
                    setSelectedChannels(new Set());
                  }}
                  className="mt-4 text-blue-600 hover:text-blue-700"
                >
                  Create your first alert
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {alerts.map((alert) => (
                  <div key={alert.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center">
                          <h3 className="text-lg font-medium text-gray-900">{alert.name}</h3>
                          <span className={`ml-3 px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(alert.severity)}`}>
                            {alert.severity}
                          </span>
                          {alert.enabled ? (
                            <span className="ml-2 px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                              Active
                            </span>
                          ) : (
                            <span className="ml-2 px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600">
                              Disabled
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-gray-600">
                          Triggers when {alert.type} {alert.condition} {alert.threshold}
                        </p>
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                          <span>Triggered {alert.triggered_count} times</span>
                          {alert.last_triggered && (
                            <span className="ml-4">
                              Last: {new Date(alert.last_triggered).toLocaleString()}
                            </span>
                          )}
                        </div>
                        <div className="mt-2">
                          <span className="text-sm text-gray-500">Notifications: </span>
                          {alert.notification_channels.map((channel, idx) => (
                            <span key={idx} className="ml-1 px-2 py-1 text-xs bg-gray-100 rounded">
                              {channel}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 ml-4">
                        <button
                          onClick={() => toggleAlert(alert.id, !alert.enabled)}
                          className="p-2 text-gray-500 hover:text-gray-700"
                        >
                          <input
                            type="checkbox"
                            checked={alert.enabled}
                            onChange={() => {}}
                            className="h-4 w-4 text-blue-600 rounded"
                          />
                        </button>
                        <button
                          onClick={() => {
                            setEditingAlert(alert);
                            // Set selected devices and channels for editing
                            setSelectedDevices(new Set(alert.device_ips || []));
                            setSelectedChannels(new Set(alert.notification_channels || []));
                          }}
                          className="p-2 text-gray-500 hover:text-blue-600"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteAlert(alert.id)}
                          className="p-2 text-gray-500 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="p-6">
            {alertHistory.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No alerts triggered yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {alertHistory.map((item) => (
                  <div
                    key={item.id}
                    className={`border rounded-lg p-4 ${
                      item.acknowledged ? 'bg-gray-50 border-gray-200' : 'bg-white border-orange-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start">
                        <div className={`p-2 rounded-full ${getSeverityColor(item.severity)}`}>
                          {getSeverityIcon(item.severity)}
                        </div>
                        <div className="ml-4">
                          <h4 className="font-medium text-gray-900">{item.alert_name}</h4>
                          <p className="text-sm text-gray-600 mt-1">{item.message}</p>
                          <p className="text-xs text-gray-500 mt-2">
                            {new Date(item.triggered_at).toLocaleString()}
                          </p>
                          {item.acknowledged && (
                            <p className="text-xs text-green-600 mt-1">
                              ✓ Acknowledged by {item.acknowledged_by} at{' '}
                              {new Date(item.acknowledged_at!).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                      {!item.acknowledged && (
                        <button
                          onClick={() => acknowledgeAlert(item.id)}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                          Acknowledge
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create/Edit Alert Modal */}
      {(showCreateModal || editingAlert) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingAlert ? 'Edit Alert' : 'Create New Alert'}
            </h2>
            
            <form onSubmit={async (e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              const alertData = {
                name: formData.get('name'),
                type: formData.get('type'),
                threshold: parseFloat(formData.get('threshold') as string),
                condition: formData.get('condition'),
                severity: formData.get('severity'),
                device_ips: Array.from(selectedDevices),
                notification_channels: Array.from(selectedChannels),
                enabled: formData.get('enabled') === 'on'
              };

              try {
                const token = safeStorage.getItem('token');
                const response = await fetch(
                  editingAlert ? `/api/alerts/${editingAlert.id}` : '/api/alerts',
                  {
                    method: editingAlert ? 'PUT' : 'POST',
                    headers: {
                      'Authorization': `Bearer ${token}`,
                      'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(alertData)
                  }
                );

                if (response.ok) {
                  setShowCreateModal(false);
                  setEditingAlert(null);
                  setSelectedDevices(new Set());
                  setSelectedChannels(new Set());
                  fetchAlerts();
                }
              } catch (error) {
                safeConsoleError('Failed to save alert', error);
              }
            }}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Alert Name
                  </label>
                  <input
                    name="name"
                    type="text"
                    required
                    defaultValue={editingAlert?.name}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., High Power Usage Alert"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Metric Type
                    </label>
                    <select
                      name="type"
                      defaultValue={editingAlert?.type || 'power'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="power">Power Usage (W)</option>
                      <option value="energy">Energy (kWh)</option>
                      <option value="cost">Cost ($)</option>
                      <option value="uptime">Uptime (%)</option>
                      <option value="temperature">Temperature (°C)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Condition
                    </label>
                    <select
                      name="condition"
                      defaultValue={editingAlert?.condition || 'greater_than'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="greater_than">Greater than</option>
                      <option value="less_than">Less than</option>
                      <option value="equals">Equals</option>
                      <option value="not_equals">Not equals</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Threshold Value
                    </label>
                    <input
                      name="threshold"
                      type="number"
                      step="0.01"
                      required
                      defaultValue={editingAlert?.threshold}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., 1000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Severity
                    </label>
                    <select
                      name="severity"
                      defaultValue={editingAlert?.severity || 'medium'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Devices (Select devices to monitor)
                  </label>
                  <div className="border border-gray-300 rounded-md p-3 max-h-40 overflow-y-auto">
                    {devices.length === 0 ? (
                      <p className="text-sm text-gray-500">No devices available</p>
                    ) : (
                      <div className="space-y-2">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={devices.length > 0 && selectedDevices.size === devices.length}
                            onChange={(e) => {
                              if (e.target.checked) {
                                // Select all devices
                                const allDeviceIps = new Set(devices.map(d => d.ip));
                                setSelectedDevices(allDeviceIps);
                              } else {
                                // Deselect all devices
                                setSelectedDevices(new Set());
                              }
                            }}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-700 font-medium">All Devices</span>
                        </label>
                        <div className="border-t pt-2 mt-2">
                          {devices.map((device) => (
                            <label key={device.ip} className="flex items-center py-1">
                              <input
                                type="checkbox"
                                checked={selectedDevices.has(device.ip)}
                                onChange={(e) => {
                                  const newSelected = new Set(selectedDevices);
                                  if (e.target.checked) {
                                    newSelected.add(device.ip);
                                  } else {
                                    newSelected.delete(device.ip);
                                  }
                                  setSelectedDevices(newSelected);
                                }}
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                              />
                              <span className="ml-2 text-sm text-gray-700">
                                {device.alias || `${device.ip} (${device.mac})`}
                                {device.model && <span className="text-gray-500 ml-1">({device.model})</span>}
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notification Channels
                  </label>
                  <div className="border border-gray-300 rounded-md p-3">
                    <div className="space-y-2">
                      {['email', 'sms', 'webhook', 'slack', 'discord', 'push'].map((channel) => (
                        <label key={channel} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={selectedChannels.has(channel)}
                            onChange={(e) => {
                              const newChannels = new Set(selectedChannels);
                              if (e.target.checked) {
                                newChannels.add(channel);
                              } else {
                                newChannels.delete(channel);
                              }
                              setSelectedChannels(newChannels);
                            }}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-700 capitalize">{channel}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-center">
                  <input
                    name="enabled"
                    type="checkbox"
                    defaultChecked={editingAlert?.enabled ?? true}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 text-sm text-gray-700">
                    Enable this alert immediately
                  </label>
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingAlert(null);
                    setSelectedDevices(new Set());
                    setSelectedChannels(new Set());
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editingAlert ? 'Update' : 'Create'} Alert
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </div>
    </AppLayout>
  );
}