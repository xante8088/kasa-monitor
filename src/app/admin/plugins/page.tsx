'use client';

import { useState, useEffect } from 'react';
import { Plus, Search, Filter, Download, Upload, Settings as SettingsIcon, Power, Trash2, RefreshCw } from 'lucide-react';
import PluginConfigModal from '../../../components/plugin-config-modal';
import PluginUploadModal from '../../../components/plugin-upload-modal';
import { safeConsoleError, safeStorage } from '@/lib/security-utils';

interface Plugin {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  plugin_type: 'device' | 'integration' | 'analytics' | 'automation' | 'utility';
  state: 'discovered' | 'loaded' | 'initialized' | 'running' | 'error' | 'disabled';
  enabled: boolean;
  main_class: string;
  dependencies?: string[];
  python_dependencies?: string[];
  permissions?: string[];
  config_schema?: any;
  hooks?: string[];
  api_version: string;
  min_app_version?: string;
  max_app_version?: string;
  homepage?: string;
  license?: string;
  icon?: string;
  error_message?: string;
  last_updated?: string;
}

interface PluginMetrics {
  enabled_count: number;
  running_count: number;
  error_count: number;
  total_count: number;
}

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [metrics, setMetrics] = useState<PluginMetrics>({
    enabled_count: 0,
    running_count: 0,
    error_count: 0,
    total_count: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterState, setFilterState] = useState<string>('all');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);

  useEffect(() => {
    fetchPlugins();
  }, []);

  const fetchPlugins = async () => {
    try {
      setLoading(true);
      const token = safeStorage.getItem('token');
      
      const [pluginsResponse, metricsResponse] = await Promise.all([
        fetch('/api/plugins', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }),
        fetch('/api/plugins/metrics', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      ]);

      if (pluginsResponse.ok) {
        const pluginsData = await pluginsResponse.json();
        setPlugins(pluginsData);
      } else {
        setError('Failed to fetch plugins');
      }

      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }
    } catch (err) {
      safeConsoleError('Error fetching plugins', err);
      setError('Failed to fetch plugins');
    } finally {
      setLoading(false);
    }
  };

  const togglePlugin = async (pluginId: string, enabled: boolean) => {
    try {
      const token = safeStorage.getItem('token');
      const response = await fetch(`/api/plugins/${pluginId}/${enabled ? 'enable' : 'disable'}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchPlugins(); // Refresh the list
      } else {
        setError(`Failed to ${enabled ? 'enable' : 'disable'} plugin`);
      }
    } catch (err) {
      safeConsoleError('Error toggling plugin', err);
      setError(`Failed to ${enabled ? 'enable' : 'disable'} plugin`);
    }
  };

  const reloadPlugin = async (pluginId: string) => {
    try {
      const token = safeStorage.getItem('token');
      const response = await fetch(`/api/plugins/${pluginId}/reload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchPlugins(); // Refresh the list
      } else {
        setError('Failed to reload plugin');
      }
    } catch (err) {
      safeConsoleError('Error reloading plugin', err);
      setError('Failed to reload plugin');
    }
  };

  const deletePlugin = async (pluginId: string) => {
    if (!confirm('Are you sure you want to delete this plugin? This action cannot be undone.')) {
      return;
    }

    try {
      const token = safeStorage.getItem('token');
      const response = await fetch(`/api/plugins/${pluginId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchPlugins(); // Refresh the list
      } else {
        setError('Failed to delete plugin');
      }
    } catch (err) {
      safeConsoleError('Error deleting plugin', err);
      setError('Failed to delete plugin');
    }
  };

  const openConfigModal = (plugin: Plugin) => {
    setSelectedPlugin(plugin);
    setShowConfigModal(true);
  };

  const closeConfigModal = () => {
    setShowConfigModal(false);
    setSelectedPlugin(null);
  };

  const handleConfigUpdate = (pluginId: string, config: any) => {
    // Optionally refresh the plugin list to get updated state
    fetchPlugins();
  };

  const getPluginTypeColor = (type: string) => {
    switch (type) {
      case 'device': return 'bg-blue-100 text-blue-800';
      case 'integration': return 'bg-green-100 text-green-800';
      case 'analytics': return 'bg-purple-100 text-purple-800';
      case 'automation': return 'bg-orange-100 text-orange-800';
      case 'utility': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'running': return 'bg-green-100 text-green-800';
      case 'initialized': return 'bg-blue-100 text-blue-800';
      case 'loaded': return 'bg-yellow-100 text-yellow-800';
      case 'discovered': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'disabled': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'running': return '🟢';
      case 'initialized': return '🔵';
      case 'loaded': return '🟡';
      case 'discovered': return '⚪';
      case 'error': return '🔴';
      case 'disabled': return '⚫';
      default: return '⚪';
    }
  };

  const filteredPlugins = plugins.filter(plugin => {
    const matchesSearch = plugin.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         plugin.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         plugin.author.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = filterType === 'all' || plugin.plugin_type === filterType;
    const matchesState = filterState === 'all' || plugin.state === filterState;
    
    return matchesSearch && matchesType && matchesState;
  });

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-red-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading plugins...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Plugin Management</h1>
        <p className="mt-2 text-gray-600">
          Manage system plugins to extend Kasa Monitor functionality
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                <span className="text-white text-sm font-medium">{metrics.total_count}</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Plugins</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.total_count}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                <span className="text-white text-sm font-medium">{metrics.running_count}</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Running</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.running_count}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                <span className="text-white text-sm font-medium">{metrics.enabled_count}</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Enabled</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.enabled_count}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                <span className="text-white text-sm font-medium">{metrics.error_count}</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Errors</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.error_count}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
          <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search plugins..."
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-red-500 focus:border-red-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Type Filter */}
            <select
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-red-500 focus:border-red-500"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="all">All Types</option>
              <option value="device">Device</option>
              <option value="integration">Integration</option>
              <option value="analytics">Analytics</option>
              <option value="automation">Automation</option>
              <option value="utility">Utility</option>
            </select>

            {/* State Filter */}
            <select
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-red-500 focus:border-red-500"
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
            >
              <option value="all">All States</option>
              <option value="running">Running</option>
              <option value="initialized">Initialized</option>
              <option value="loaded">Loaded</option>
              <option value="discovered">Discovered</option>
              <option value="error">Error</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <Upload className="h-4 w-4 mr-2" />
              Install Plugin
            </button>
            <button
              onClick={fetchPlugins}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Plugin Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredPlugins.map((plugin) => (
          <div key={plugin.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
            <div className="p-6">
              {/* Plugin Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
                    {plugin.icon ? (
                      <span className="text-lg">{plugin.icon}</span>
                    ) : (
                      <span className="text-white font-semibold text-sm">
                        {plugin.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{plugin.name}</h3>
                    <p className="text-sm text-gray-500">v{plugin.version} by {plugin.author}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="text-lg">{getStateIcon(plugin.state)}</span>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStateColor(plugin.state)}`}>
                    {plugin.state}
                  </span>
                </div>
              </div>

              {/* Plugin Description */}
              <p className="text-gray-600 text-sm mb-4">{plugin.description}</p>

              {/* Plugin Type and Info */}
              <div className="flex items-center space-x-2 mb-4">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPluginTypeColor(plugin.plugin_type)}`}>
                  {plugin.plugin_type}
                </span>
                {plugin.permissions && plugin.permissions.length > 0 && (
                  <span className="text-xs text-gray-500">
                    {plugin.permissions.length} permission{plugin.permissions.length !== 1 ? 's' : ''}
                  </span>
                )}
                {plugin.hooks && plugin.hooks.length > 0 && (
                  <span className="text-xs text-gray-500">
                    {plugin.hooks.length} hook{plugin.hooks.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>

              {/* Error Message */}
              {plugin.error_message && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-700">{plugin.error_message}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => togglePlugin(plugin.id, !plugin.enabled)}
                    className={`inline-flex items-center px-3 py-1 text-xs font-medium rounded-full ${
                      plugin.enabled
                        ? 'bg-green-100 text-green-800 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                    }`}
                  >
                    <Power className="h-3 w-3 mr-1" />
                    {plugin.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  
                  {plugin.state === 'error' && (
                    <button
                      onClick={() => reloadPlugin(plugin.id)}
                      className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800"
                    >
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Retry
                    </button>
                  )}
                </div>

                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => openConfigModal(plugin)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Configure Plugin"
                  >
                    <SettingsIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => deletePlugin(plugin.id)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete Plugin"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredPlugins.length === 0 && !loading && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">🧩</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No plugins found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm || filterType !== 'all' || filterState !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Install your first plugin to get started'}
          </p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Install Plugin
          </button>
        </div>
      )}

      {/* Plugin Upload Modal */}
      <PluginUploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={fetchPlugins}
      />

      {/* Plugin Configuration Modal */}
      {selectedPlugin && (
        <PluginConfigModal
          plugin={selectedPlugin}
          isOpen={showConfigModal}
          onClose={closeConfigModal}
          onConfigUpdate={handleConfigUpdate}
        />
      )}
    </div>
  );
}