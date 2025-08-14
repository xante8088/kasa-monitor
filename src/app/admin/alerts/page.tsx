'use client';

import React, { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, Edit, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

interface Alert {
  id: number;
  name: string;
  type: string;
  threshold: number;
  condition: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  device_id?: string;
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

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'rules' | 'history'>('rules');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);

  useEffect(() => {
    fetchAlerts();
    fetchAlertHistory();
  }, []);

  const fetchAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/alerts', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlertHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/alerts/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAlertHistory(data);
      }
    } catch (error) {
      console.error('Failed to fetch alert history:', error);
    }
  };

  const toggleAlert = async (alertId: number, enabled: boolean) => {
    try {
      const token = localStorage.getItem('token');
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
      console.error('Failed to toggle alert:', error);
    }
  };

  const deleteAlert = async (alertId: number) => {
    if (!confirm('Are you sure you want to delete this alert?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAlerts();
    } catch (error) {
      console.error('Failed to delete alert:', error);
    }
  };

  const acknowledgeAlert = async (historyId: number) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/alerts/history/${historyId}/acknowledge`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAlertHistory();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
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
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Alert Management</h1>
          <p className="text-gray-600 mt-1">Configure alerts and view alert history</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
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
                  onClick={() => setShowCreateModal(true)}
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
                          onClick={() => setEditingAlert(alert)}
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
    </div>
  );
}