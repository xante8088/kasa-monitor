'use client';

import { useState, useEffect } from 'react';

interface SSLConfig {
  enabled: boolean;
  cert_path: string;
  key_path: string;
  force_https: boolean;
}

interface NetworkConfig {
  host: string;
  port: number;
  allowed_hosts: string[];
  local_only: boolean;
  cors_origins: string[];
}

interface SystemConfig {
  ssl: SSLConfig;
  network: NetworkConfig;
  database_path: string;
  influxdb_enabled: boolean;
  polling_interval: number;
}

export default function SystemConfigPage() {
  const [config, setConfig] = useState<SystemConfig>({
    ssl: {
      enabled: false,
      cert_path: '',
      key_path: '',
      force_https: false
    },
    network: {
      host: '0.0.0.0',
      port: 8000,
      allowed_hosts: [],
      local_only: false,
      cors_origins: []
    },
    database_path: 'kasa_monitor.db',
    influxdb_enabled: false,
    polling_interval: 30
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/system/config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        // Merge with defaults to ensure all nested properties exist
        const mergedConfig: SystemConfig = {
          ssl: {
            enabled: data.ssl?.enabled ?? false,
            cert_path: data.ssl?.cert_path ?? '',
            key_path: data.ssl?.key_path ?? '',
            force_https: data.ssl?.force_https ?? false
          },
          network: {
            host: data.network?.host ?? '0.0.0.0',
            port: data.network?.port ?? 8000,
            allowed_hosts: data.network?.allowed_hosts ?? [],
            local_only: data.network?.local_only ?? false,
            cors_origins: data.network?.cors_origins ?? []
          },
          database_path: data.database_path ?? 'kasa_monitor.db',
          influxdb_enabled: data.influxdb_enabled ?? false,
          polling_interval: data.polling_interval ?? 30
        };
        setConfig(mergedConfig);
      } else {
        setError('Failed to load system configuration');
      }
    } catch (err) {
      setError('Connection error');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/system/config', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      });

      if (response.ok) {
        setSuccess('Configuration saved successfully');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to save configuration');
      }
    } catch (err) {
      setError('Connection error');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (section: string, field: string, value: any) => {
    setConfig(prev => {
      const sectionKey = section as keyof SystemConfig;
      const currentSection = prev[sectionKey];
      
      // Handle nested objects (ssl and network)
      if (typeof currentSection === 'object' && currentSection !== null) {
        return {
          ...prev,
          [section]: {
            ...currentSection,
            [field]: value
          }
        };
      }
      
      // Handle primitive values
      return {
        ...prev,
        [section]: value
      };
    });
  };

  const handleArrayInputChange = (section: string, field: string, value: string) => {
    const array = value.split(',').map(item => item.trim()).filter(item => item);
    handleInputChange(section, field, array);
  };

  const uploadCertificate = async (type: 'cert' | 'key', file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/system/ssl/upload-${type}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        const field = type === 'cert' ? 'cert_path' : 'key_path';
        handleInputChange('ssl', field, data.path);
        setSuccess(`${type === 'cert' ? 'Certificate' : 'Private key'} uploaded successfully`);
      } else {
        setError(`Failed to upload ${type === 'cert' ? 'certificate' : 'private key'}`);
      }
    } catch (err) {
      setError('Upload failed');
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Configuration</h1>
          <p className="text-gray-600 mt-1">Configure SSL, network settings, and system parameters</p>
        </div>
        <button
          onClick={saveConfig}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <p className="text-green-600">{success}</p>
        </div>
      )}

      <div className="space-y-8">
        {/* SSL Configuration */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">SSL/HTTPS Configuration</h2>
          
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="ssl_enabled"
                checked={config.ssl?.enabled ?? false}
                onChange={(e) => handleInputChange('ssl', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="ssl_enabled" className="ml-2 text-sm text-gray-900">
                Enable SSL/HTTPS
              </label>
            </div>

            {config.ssl?.enabled && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      SSL Certificate
                    </label>
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={config.ssl?.cert_path ?? ''}
                        onChange={(e) => handleInputChange('ssl', 'cert_path', e.target.value)}
                        placeholder="/path/to/certificate.crt"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                      <input
                        type="file"
                        accept=".crt,.pem,.cer"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadCertificate('cert', file);
                        }}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Private Key
                    </label>
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={config.ssl?.key_path ?? ''}
                        onChange={(e) => handleInputChange('ssl', 'key_path', e.target.value)}
                        placeholder="/path/to/private.key"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                      <input
                        type="file"
                        accept=".key,.pem"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadCertificate('key', file);
                        }}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="force_https"
                    checked={config.ssl?.force_https ?? false}
                    onChange={(e) => handleInputChange('ssl', 'force_https', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="force_https" className="ml-2 text-sm text-gray-900">
                    Force HTTPS (redirect HTTP to HTTPS)
                  </label>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Network Configuration */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Network Configuration</h2>
          
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="host" className="block text-sm font-medium text-gray-700">
                  Host Address
                </label>
                <input
                  type="text"
                  id="host"
                  value={config.network?.host ?? '0.0.0.0'}
                  onChange={(e) => handleInputChange('network', 'host', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Use 0.0.0.0 to allow all interfaces, 127.0.0.1 for localhost only
                </p>
              </div>

              <div>
                <label htmlFor="port" className="block text-sm font-medium text-gray-700">
                  Port
                </label>
                <input
                  type="number"
                  id="port"
                  value={config.network?.port ?? 8000}
                  onChange={(e) => handleInputChange('network', 'port', parseInt(e.target.value))}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="local_only"
                checked={config.network?.local_only ?? false}
                onChange={(e) => handleInputChange('network', 'local_only', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="local_only" className="ml-2 text-sm text-gray-900">
                Local network access only (restrict to private IP ranges)
              </label>
            </div>

            <div>
              <label htmlFor="allowed_hosts" className="block text-sm font-medium text-gray-700">
                Allowed Hosts
              </label>
              <input
                type="text"
                id="allowed_hosts"
                value={(config.network?.allowed_hosts ?? []).join(', ')}
                onChange={(e) => handleArrayInputChange('network', 'allowed_hosts', e.target.value)}
                placeholder="example.com, *.mydomain.com, 192.168.1.0/24"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Comma-separated list of allowed hostnames, IPs, or CIDR ranges
              </p>
            </div>

            <div>
              <label htmlFor="cors_origins" className="block text-sm font-medium text-gray-700">
                CORS Origins
              </label>
              <input
                type="text"
                id="cors_origins"
                value={(config.network?.cors_origins ?? []).join(', ')}
                onChange={(e) => handleArrayInputChange('network', 'cors_origins', e.target.value)}
                placeholder="https://example.com, http://localhost:3000"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Comma-separated list of allowed CORS origins
              </p>
            </div>
          </div>
        </div>

        {/* System Settings */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">System Settings</h2>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="database_path" className="block text-sm font-medium text-gray-700">
                Database Path
              </label>
              <input
                type="text"
                id="database_path"
                value={config.database_path ?? 'kasa_monitor.db'}
                onChange={(e) => setConfig(prev => ({ ...prev, database_path: e.target.value }))}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label htmlFor="polling_interval" className="block text-sm font-medium text-gray-700">
                Device Polling Interval (seconds)
              </label>
              <input
                type="number"
                id="polling_interval"
                min="5"
                max="300"
                value={config.polling_interval ?? 30}
                onChange={(e) => setConfig(prev => ({ ...prev, polling_interval: parseInt(e.target.value) }))}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                How often to poll devices for new data (5-300 seconds)
              </p>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="influxdb_enabled"
                checked={config.influxdb_enabled ?? false}
                onChange={(e) => setConfig(prev => ({ ...prev, influxdb_enabled: e.target.checked }))}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="influxdb_enabled" className="ml-2 text-sm text-gray-900">
                Enable InfluxDB for time-series data
              </label>
            </div>
          </div>
        </div>

        {/* Security Warning */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Security Considerations
              </h3>
              <div className="mt-2 text-sm text-yellow-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>Always use HTTPS in production environments</li>
                  <li>Restrict network access using allowed hosts and local-only settings</li>
                  <li>Keep SSL certificates up to date and secure</li>
                  <li>Use strong passwords and enable multi-factor authentication when possible</li>
                  <li>Regularly update the application and dependencies</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}