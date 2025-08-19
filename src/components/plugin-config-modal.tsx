'use client';

import { useState, useEffect } from 'react';
import { X, Save, RefreshCw, AlertTriangle, CheckCircle, Settings, Info } from 'lucide-react';

interface Plugin {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  plugin_type: string;
  state: string;
  enabled: boolean;
  config_schema?: any;
  current_config?: any;
  permissions?: string[];
  hooks?: string[];
  error_message?: string;
}

interface PluginConfigModalProps {
  plugin: Plugin;
  isOpen: boolean;
  onClose: () => void;
  onConfigUpdate: (pluginId: string, config: any) => void;
}

export default function PluginConfigModal({ plugin, isOpen, onClose, onConfigUpdate }: PluginConfigModalProps) {
  const [config, setConfig] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'config' | 'info' | 'status'>('config');

  useEffect(() => {
    if (isOpen && plugin) {
      fetchPluginConfig();
    }
  }, [isOpen, plugin]);

  const fetchPluginConfig = async () => {
    try {
      setLoading(true);
      setError('');
      
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/plugins/${plugin.id}/config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data.config || {});
      } else {
        setError('Failed to fetch plugin configuration');
      }
    } catch (err) {
      console.error('Error fetching plugin config:', err);
      setError('Failed to fetch plugin configuration');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      const response = await fetch(`/api/plugins/${plugin.id}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ config })
      });

      if (response.ok) {
        setSuccess('Configuration saved successfully');
        onConfigUpdate(plugin.id, config);
        setTimeout(() => setSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to save configuration');
      }
    } catch (err) {
      console.error('Error saving plugin config:', err);
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = () => {
    if (confirm('Are you sure you want to reset to default configuration?')) {
      const defaultConfig = generateDefaultConfig(plugin.config_schema);
      setConfig(defaultConfig);
    }
  };

  const generateDefaultConfig = (schema: any): any => {
    if (!schema || !schema.properties) return {};
    
    const defaultConfig: any = {};
    Object.entries(schema.properties).forEach(([key, property]: [string, any]) => {
      if (property.default !== undefined) {
        defaultConfig[key] = property.default;
      } else if (property.type === 'string') {
        defaultConfig[key] = '';
      } else if (property.type === 'number' || property.type === 'integer') {
        defaultConfig[key] = 0;
      } else if (property.type === 'boolean') {
        defaultConfig[key] = false;
      } else if (property.type === 'array') {
        defaultConfig[key] = [];
      } else if (property.type === 'object') {
        defaultConfig[key] = {};
      }
    });
    return defaultConfig;
  };

  const renderConfigField = (key: string, property: any, value: any) => {
    const updateValue = (newValue: any) => {
      setConfig(prev => ({ ...prev, [key]: newValue }));
    };

    const fieldId = `config-${key}`;

    switch (property.type) {
      case 'string':
        if (property.enum) {
          return (
            <select
              id={fieldId}
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
              value={value || ''}
              onChange={(e) => updateValue(e.target.value)}
            >
              <option value="">Select...</option>
              {property.enum.map((option: string) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          );
        } else if (property.format === 'password') {
          return (
            <input
              id={fieldId}
              type="password"
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
              value={value || ''}
              onChange={(e) => updateValue(e.target.value)}
              placeholder={property.placeholder || ''}
            />
          );
        } else if (property.format === 'textarea') {
          return (
            <textarea
              id={fieldId}
              rows={3}
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
              value={value || ''}
              onChange={(e) => updateValue(e.target.value)}
              placeholder={property.placeholder || ''}
            />
          );
        } else {
          return (
            <input
              id={fieldId}
              type="text"
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
              value={value || ''}
              onChange={(e) => updateValue(e.target.value)}
              placeholder={property.placeholder || ''}
            />
          );
        }

      case 'number':
      case 'integer':
        return (
          <input
            id={fieldId}
            type="number"
            step={property.type === 'integer' ? 1 : 'any'}
            min={property.minimum}
            max={property.maximum}
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
            value={value || ''}
            onChange={(e) => updateValue(property.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value))}
          />
        );

      case 'boolean':
        return (
          <div className="mt-1">
            <label className="flex items-center">
              <input
                id={fieldId}
                type="checkbox"
                className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                checked={value || false}
                onChange={(e) => updateValue(e.target.checked)}
              />
              <span className="ml-2 text-sm text-gray-700">
                {property.description || `Enable ${key}`}
              </span>
            </label>
          </div>
        );

      case 'array':
        return (
          <div className="mt-1">
            <textarea
              id={fieldId}
              rows={3}
              className="block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
              value={Array.isArray(value) ? value.join('\\n') : ''}
              onChange={(e) => updateValue(e.target.value.split('\\n').filter(item => item.trim()))}
              placeholder="Enter one item per line"
            />
            <p className="mt-1 text-xs text-gray-500">Enter one item per line</p>
          </div>
        );

      default:
        return (
          <input
            id={fieldId}
            type="text"
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-red-500 focus:border-red-500"
            value={JSON.stringify(value) || ''}
            onChange={(e) => {
              try {
                updateValue(JSON.parse(e.target.value));
              } catch {
                // Keep as string if invalid JSON
              }
            }}
            placeholder="JSON value"
          />
        );
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-4 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
              <Settings className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">{plugin.name}</h3>
              <p className="text-sm text-gray-500">Plugin Configuration</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mt-4 mb-6 border-b border-gray-200">
          {['config', 'info', 'status'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg ${
                activeTab === tab
                  ? 'bg-red-50 text-red-700 border-b-2 border-red-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'config' && 'Configuration'}
              {tab === 'info' && 'Information'}
              {tab === 'status' && 'Status'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="max-h-96 overflow-y-auto">
          {/* Configuration Tab */}
          {activeTab === 'config' && (
            <div>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
                  <span className="ml-2 text-gray-600">Loading configuration...</span>
                </div>
              ) : plugin.config_schema && plugin.config_schema.properties ? (
                <div className="space-y-6">
                  {Object.entries(plugin.config_schema.properties).map(([key, property]: [string, any]) => (
                    <div key={key}>
                      <label htmlFor={`config-${key}`} className="block text-sm font-medium text-gray-700">
                        {property.title || key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
                        {plugin.config_schema.required?.includes(key) && (
                          <span className="text-red-500 ml-1">*</span>
                        )}
                      </label>
                      {property.description && (
                        <p className="text-xs text-gray-500 mt-1">{property.description}</p>
                      )}
                      {renderConfigField(key, property, config[key])}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Info className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-600">This plugin has no configurable options.</p>
                </div>
              )}
            </div>
          )}

          {/* Information Tab */}
          {activeTab === 'info' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Plugin Details</h4>
                  <dl className="space-y-2">
                    <div>
                      <dt className="text-xs font-medium text-gray-500">ID</dt>
                      <dd className="text-sm text-gray-900 font-mono">{plugin.id}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-gray-500">Version</dt>
                      <dd className="text-sm text-gray-900">{plugin.version}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-gray-500">Author</dt>
                      <dd className="text-sm text-gray-900">{plugin.author}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-gray-500">Type</dt>
                      <dd className="text-sm text-gray-900 capitalize">{plugin.plugin_type}</dd>
                    </div>
                  </dl>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Capabilities</h4>
                  <dl className="space-y-2">
                    <div>
                      <dt className="text-xs font-medium text-gray-500">Permissions</dt>
                      <dd className="text-sm text-gray-900">
                        {plugin.permissions && plugin.permissions.length > 0 ? (
                          <ul className="text-xs space-y-1">
                            {plugin.permissions.map((perm, index) => (
                              <li key={index} className="font-mono bg-gray-100 px-2 py-1 rounded">
                                {perm}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          'None'
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-gray-500">Hooks</dt>
                      <dd className="text-sm text-gray-900">
                        {plugin.hooks && plugin.hooks.length > 0 ? (
                          <ul className="text-xs space-y-1">
                            {plugin.hooks.map((hook, index) => (
                              <li key={index} className="font-mono bg-gray-100 px-2 py-1 rounded">
                                {hook}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          'None'
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">Description</h4>
                <p className="text-sm text-gray-600">{plugin.description}</p>
              </div>
            </div>
          )}

          {/* Status Tab */}
          {activeTab === 'status' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">Current Status</h4>
                <div className="flex items-center space-x-2 mb-4">
                  <div className={`w-3 h-3 rounded-full ${
                    plugin.state === 'running' ? 'bg-green-500' :
                    plugin.state === 'error' ? 'bg-red-500' :
                    plugin.state === 'initialized' ? 'bg-blue-500' :
                    'bg-gray-500'
                  }`}></div>
                  <span className="text-sm font-medium capitalize">{plugin.state}</span>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    plugin.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {plugin.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>

              {plugin.error_message && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <div className="flex">
                    <AlertTriangle className="h-5 w-5 text-red-400" />
                    <div className="ml-3">
                      <h4 className="text-sm font-medium text-red-800">Error</h4>
                      <p className="text-sm text-red-700 mt-1">{plugin.error_message}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-6 border-t border-gray-200 mt-6">
          <div>
            {error && (
              <div className="flex items-center text-red-600 text-sm">
                <AlertTriangle className="h-4 w-4 mr-1" />
                {error}
              </div>
            )}
            {success && (
              <div className="flex items-center text-green-600 text-sm">
                <CheckCircle className="h-4 w-4 mr-1" />
                {success}
              </div>
            )}
          </div>

          <div className="flex space-x-3">
            {activeTab === 'config' && plugin.config_schema && (
              <>
                <button
                  onClick={resetConfig}
                  className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  disabled={saving}
                >
                  Reset
                </button>
                <button
                  onClick={saveConfig}
                  disabled={saving}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                >
                  {saving ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Configuration
                    </>
                  )}
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}