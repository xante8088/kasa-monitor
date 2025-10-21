'use client';

import { useState, useEffect } from 'react';
import { AppLayout } from '@/components/app-layout';

interface SSLConfig {
  enabled: boolean;
  cert_path: string;
  key_path: string;
  force_https: boolean;
  port: number;
}

interface SSLFile {
  filename: string;
  path: string;
  size: number;
  modified: string;
  type: string;
}

interface CSRFormData {
  country: string;
  state: string;
  city: string;
  organization: string;
  organizational_unit: string;
  common_name: string;
  email: string;
  san_domains: string;
  key_size: number;
}

interface NetworkConfig {
  host: string;
  port: number;
  allowed_hosts: string[];
  local_only: boolean;
  cors_origins: string[];
}

interface ReverseProxyConfig {
  enabled: boolean;
  http_port: number;
  https_port: number;
  admin_port: number;
  server_name: string;
  force_https: boolean;
}

interface PluginSecurityConfig {
  require_signature: boolean;
  minimum_trust_level: string;
  allow_unsigned: boolean;
  verify_on_load: boolean;
  quarantine_invalid: boolean;
}

interface TrustedKey {
  name: string;
  trust_level: string;
}

interface SystemConfig {
  ssl: SSLConfig;
  network: NetworkConfig;
  reverse_proxy: ReverseProxyConfig;
  plugin_security: PluginSecurityConfig;
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
      force_https: false,
      port: 5273
    },
    network: {
      host: '0.0.0.0',
      port: 5272,
      allowed_hosts: [],
      local_only: false,
      cors_origins: []
    },
    reverse_proxy: {
      enabled: false,
      http_port: 8090,
      https_port: 8445,
      admin_port: 8446,
      server_name: 'localhost',
      force_https: true
    },
    plugin_security: {
      require_signature: false,
      minimum_trust_level: 'unsigned',
      allow_unsigned: true,
      verify_on_load: true,
      quarantine_invalid: true
    },
    database_path: 'kasa_monitor.db',
    influxdb_enabled: false,
    polling_interval: 30
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [sslFiles, setSslFiles] = useState<SSLFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [showCSRForm, setShowCSRForm] = useState(false);
  const [csrLoading, setCSRLoading] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [fileToDelete, setFileToDelete] = useState<string | null>(null);
  const [csrForm, setCSRForm] = useState<CSRFormData>({
    country: 'US',
    state: '',
    city: '',
    organization: '',
    organizational_unit: '',
    common_name: '',
    email: '',
    san_domains: '',
    key_size: 2048
  });
  const [trustedKeys, setTrustedKeys] = useState<TrustedKey[]>([]);
  const [showAddKeyForm, setShowAddKeyForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyData, setNewKeyData] = useState('');
  const [keyLoading, setKeyLoading] = useState(false);

  useEffect(() => {
    fetchConfig();
    fetchTrustedKeys();
    fetchPluginSecurityPolicies();
  }, []);

  useEffect(() => {
    if (config.ssl?.enabled) {
      fetchSSLFiles();
    }
  }, [config.ssl?.enabled]);

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
            force_https: data.ssl?.force_https ?? false,
            port: data.ssl?.port ?? 5273
          },
          network: {
            host: data.network?.host ?? '0.0.0.0',
            port: data.network?.port ?? 5272,
            allowed_hosts: data.network?.allowed_hosts ?? [],
            local_only: data.network?.local_only ?? false,
            cors_origins: data.network?.cors_origins ?? []
          },
          reverse_proxy: {
            enabled: data.reverse_proxy?.enabled ?? false,
            http_port: data.reverse_proxy?.http_port ?? 8090,
            https_port: data.reverse_proxy?.https_port ?? 8445,
            admin_port: data.reverse_proxy?.admin_port ?? 8446,
            server_name: data.reverse_proxy?.server_name ?? 'localhost',
            force_https: data.reverse_proxy?.force_https ?? true
          },
          plugin_security: {
            require_signature: data.plugin_security?.require_signature ?? false,
            minimum_trust_level: data.plugin_security?.minimum_trust_level ?? 'unsigned',
            allow_unsigned: data.plugin_security?.allow_unsigned ?? true,
            verify_on_load: data.plugin_security?.verify_on_load ?? true,
            quarantine_invalid: data.plugin_security?.quarantine_invalid ?? true
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
        setSuccess('Configuration saved successfully. All settings persist across container updates.');
        setTimeout(() => setSuccess(''), 5000);
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Failed to save configuration');
      }
    } catch (err) {
      setError('Connection error - please check your network connection and try again');
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

  // Helper function to check SSL configuration completeness
  const getSSLStatus = () => {
    const hasCert = config.ssl?.cert_path && config.ssl.cert_path.trim();
    const hasKey = config.ssl?.key_path && config.ssl.key_path.trim();
    const isEnabled = config.ssl?.enabled;
    
    return {
      hasCert,
      hasKey,
      isEnabled,
      isComplete: hasCert && hasKey,
      canAutoEnable: hasCert && hasKey && !isEnabled
    };
  };

  const uploadCertificate = async (type: 'cert' | 'key', file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    setSaving(true);
    setError('');
    setSuccess('');

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
        
        // Show enhanced success message about persistence and auto-enablement
        let successMsg = `${type === 'cert' ? 'SSL certificate' : 'SSL private key'} uploaded successfully and stored persistently.`;
        
        // Check if SSL was auto-enabled
        const otherType = type === 'cert' ? 'key' : 'cert';
        const otherPath = config.ssl?.[`${otherType}_path`];
        if (otherPath && otherPath.trim()) {
          successMsg += ` SSL has been automatically enabled since both certificate and private key are now present. Configuration persists across container updates.`;
          // Update SSL enabled status in the UI
          handleInputChange('ssl', 'enabled', true);
        } else {
          successMsg += ` Upload the ${type === 'cert' ? 'private key' : 'certificate'} to automatically enable SSL.`;
        }
        
        setSuccess(successMsg);
        
        // Refresh the configuration to get the latest database values
        setTimeout(() => fetchConfig(), 1000);
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || `Failed to upload ${type === 'cert' ? 'certificate' : 'private key'}`);
      }
    } catch (err) {
      setError('Upload failed - connection error');
    } finally {
      setSaving(false);
    }
  };

  const fetchSSLFiles = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ssl/files', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setSslFiles(data.files || []);
      } else {
        console.error('Failed to fetch SSL files');
        setError('Failed to load SSL files list');
      }
    } catch (err) {
      console.error('Error fetching SSL files:', err);
      setError('Network error while loading SSL files');
    }
  };

  const generateCSR = async () => {
    setCSRLoading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ssl/generate-csr', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...csrForm,
          san_domains: csrForm.san_domains ? csrForm.san_domains.split(',').map(s => s.trim()) : []
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(`CSR and private key generated successfully! Files: ${data.key_file}, ${data.csr_file}`);
        fetchSSLFiles();
        setShowCSRForm(false);
        setCSRForm({
          country: 'US',
          state: '',
          city: '',
          organization: '',
          organizational_unit: '',
          common_name: '',
          email: '',
          san_domains: '',
          key_size: 2048
        });
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate CSR');
      }
    } catch (err) {
      setError('Failed to generate CSR');
    } finally {
      setCSRLoading(false);
    }
  };

  const downloadFile = async (filename: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/ssl/download/${filename}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        setError('Failed to download file');
      }
    } catch (err) {
      setError('Download failed');
    }
  };

  const downloadMultiple = async () => {
    if (selectedFiles.length === 0) {
      setError('No files selected');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ssl/download-multiple', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filenames: selectedFiles })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ssl_files_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        setSelectedFiles([]);
      } else {
        setError('Failed to download files');
      }
    } catch (err) {
      setError('Download failed');
    }
  };

  const deleteFile = async (filename: string) => {
    if (deleteConfirmation.toLowerCase() !== 'delete') {
      setError('Type "delete" to confirm deletion');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/ssl/files/${filename}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: filename,
          confirmation: deleteConfirmation
        })
      });

      if (response.ok) {
        setSuccess(`File ${filename} deleted successfully`);
        fetchSSLFiles();
        setFileToDelete(null);
        setDeleteConfirmation('');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete file');
      }
    } catch (err) {
      setError('Delete failed');
    }
  };

  const toggleFileSelection = (filename: string) => {
    setSelectedFiles(prev => 
      prev.includes(filename) 
        ? prev.filter(f => f !== filename)
        : [...prev, filename]
    );
  };

  const fetchTrustedKeys = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/plugins/security/trusted-keys', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setTrustedKeys(data.trusted_keys || []);
      } else {
        console.error('Failed to fetch trusted keys');
      }
    } catch (err) {
      console.error('Error fetching trusted keys:', err);
    }
  };

  const fetchPluginSecurityPolicies = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/plugins/security/policies', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(prev => ({
          ...prev,
          plugin_security: {
            require_signature: data.require_signature ?? false,
            minimum_trust_level: data.minimum_trust_level ?? 'unsigned',
            allow_unsigned: data.allow_unsigned ?? true,
            verify_on_load: data.verify_on_load ?? true,
            quarantine_invalid: data.quarantine_invalid ?? true
          }
        }));
      }
    } catch (err) {
      console.error('Error fetching plugin security policies:', err);
    }
  };

  const updatePluginSecurityPolicies = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/plugins/security/policies', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config.plugin_security)
      });

      if (response.ok) {
        setSuccess('Plugin security policies updated successfully');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update plugin security policies');
      }
    } catch (err) {
      setError('Failed to update plugin security policies');
    }
  };

  const addTrustedKey = async () => {
    if (!newKeyName || !newKeyData) {
      setError('Key name and public key data are required');
      return;
    }

    setKeyLoading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/plugins/security/trusted-keys', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newKeyName,
          public_key: newKeyData
        })
      });

      if (response.ok) {
        setSuccess(`Trusted key '${newKeyName}' added successfully`);
        setNewKeyName('');
        setNewKeyData('');
        setShowAddKeyForm(false);
        fetchTrustedKeys();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to add trusted key');
      }
    } catch (err) {
      setError('Failed to add trusted key');
    } finally {
      setKeyLoading(false);
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">SSL/HTTPS Configuration</h2>
            <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
              Persistent across updates
            </div>
          </div>
          
          {/* SSL Status Display */}
          <div className="mb-6 p-4 rounded-lg border">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-gray-900">SSL Status</h3>
              <div className="flex items-center gap-2">
                <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                  getSSLStatus().isComplete && getSSLStatus().isEnabled
                    ? 'bg-green-100 text-green-800'
                    : getSSLStatus().isComplete
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {getSSLStatus().isComplete && getSSLStatus().isEnabled ? 'Active' : 
                   getSSLStatus().isComplete ? 'Ready' : 'Incomplete'}
                </span>
                {getSSLStatus().canAutoEnable && (
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    Auto-enable available
                  </span>
                )}
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-700">Certificate:</span>
                <div className="mt-1">
                  {config.ssl?.cert_path ? (
                    <div className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      <span className="font-mono text-gray-600 break-all">{config.ssl.cert_path}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400">○</span>
                      <span className="text-gray-500">No certificate uploaded</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div>
                <span className="font-medium text-gray-700">Private Key:</span>
                <div className="mt-1">
                  {config.ssl?.key_path ? (
                    <div className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      <span className="font-mono text-gray-600 break-all">{config.ssl.key_path}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400">○</span>
                      <span className="text-gray-500">No private key uploaded</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {config.ssl?.enabled && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-green-600">🔒</span>
                  <span className="text-sm text-green-800 font-medium">
                    SSL is enabled and configured. Certificates persist across container updates.
                  </span>
                </div>
                <div className="mt-2 text-xs text-green-700">
                  Your SSL certificates are stored persistently and will be automatically loaded when the application starts.
                </div>
              </div>
            )}
            
            {!config.ssl?.enabled && config.ssl?.cert_path && config.ssl?.key_path && (
              <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-blue-600">ℹ</span>
                  <span className="text-sm text-blue-800 font-medium">
                    SSL certificates are ready but SSL is disabled.
                  </span>
                </div>
                <div className="mt-2 text-xs text-blue-700">
                  Enable SSL below to start using HTTPS with your uploaded certificates.
                </div>
              </div>
            )}
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
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
              
              {config.ssl?.cert_path && config.ssl?.key_path && (
                <div className="text-xs text-green-600 flex items-center gap-1">
                  <span>✓</span>
                  <span>Auto-enabled when both cert & key present</span>
                </div>
              )}
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
                        placeholder="/app/ssl/certificate.crt (auto-populated after upload)"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                        readOnly={!!config.ssl?.cert_path}
                      />
                      <input
                        type="file"
                        accept=".crt,.pem,.cer"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadCertificate('cert', file);
                        }}
                        disabled={saving}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                      />
                      <p className="text-xs text-gray-500">
                        Upload your SSL certificate. Files are stored persistently and will be retained across container updates.
                      </p>
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
                        placeholder="/app/ssl/private.key (auto-populated after upload)"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                        readOnly={!!config.ssl?.key_path}
                      />
                      <input
                        type="file"
                        accept=".key,.pem"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadCertificate('key', file);
                        }}
                        disabled={saving}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                      />
                      <p className="text-xs text-gray-500">
                        Upload your SSL private key. Files are stored persistently with secure permissions (600) and retained across container updates.
                      </p>
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

                <div>
                  <label htmlFor="ssl_port" className="block text-sm font-medium text-gray-700">
                    HTTPS Port
                  </label>
                  <input
                    type="number"
                    id="ssl_port"
                    min="1"
                    max="65535"
                    value={config.ssl?.port ?? 5273}
                    onChange={(e) => handleInputChange('ssl', 'port', parseInt(e.target.value))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Port for HTTPS connections (default: 5273, standard: 443). This setting persists across container updates.
                  </p>
                </div>

                {/* CSR Generation Section */}
                <div className="border-t pt-4 mt-4">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-gray-900">Certificate Management</h3>
                    <button
                      onClick={() => setShowCSRForm(!showCSRForm)}
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                    >
                      {showCSRForm ? 'Cancel' : 'Generate CSR'}
                    </button>
                  </div>

                  {showCSRForm && (
                    <div className="bg-gray-50 p-4 rounded-lg mb-4">
                      <h4 className="text-md font-medium text-gray-900 mb-3">Certificate Signing Request (CSR) Generation</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Country Code (2 letters)
                          </label>
                          <input
                            type="text"
                            maxLength={2}
                            value={csrForm.country}
                            onChange={(e) => setCSRForm(prev => ({...prev, country: e.target.value.toUpperCase()}))}
                            placeholder="US"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            State/Province
                          </label>
                          <input
                            type="text"
                            value={csrForm.state}
                            onChange={(e) => setCSRForm(prev => ({...prev, state: e.target.value}))}
                            placeholder="California"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            City/Locality
                          </label>
                          <input
                            type="text"
                            value={csrForm.city}
                            onChange={(e) => setCSRForm(prev => ({...prev, city: e.target.value}))}
                            placeholder="San Francisco"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Organization
                          </label>
                          <input
                            type="text"
                            value={csrForm.organization}
                            onChange={(e) => setCSRForm(prev => ({...prev, organization: e.target.value}))}
                            placeholder="Your Company Name"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Organizational Unit (Optional)
                          </label>
                          <input
                            type="text"
                            value={csrForm.organizational_unit}
                            onChange={(e) => setCSRForm(prev => ({...prev, organizational_unit: e.target.value}))}
                            placeholder="IT Department"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Common Name (Domain)
                          </label>
                          <input
                            type="text"
                            value={csrForm.common_name}
                            onChange={(e) => setCSRForm(prev => ({...prev, common_name: e.target.value}))}
                            placeholder="example.com"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Email Address
                          </label>
                          <input
                            type="email"
                            value={csrForm.email}
                            onChange={(e) => setCSRForm(prev => ({...prev, email: e.target.value}))}
                            placeholder="admin@example.com"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Key Size
                          </label>
                          <select
                            value={csrForm.key_size}
                            onChange={(e) => setCSRForm(prev => ({...prev, key_size: parseInt(e.target.value)}))}
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          >
                            <option value={2048}>2048 bits</option>
                            <option value={3072}>3072 bits</option>
                            <option value={4096}>4096 bits</option>
                          </select>
                        </div>
                        <div className="md:col-span-2">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Subject Alternative Names (Optional)
                          </label>
                          <input
                            type="text"
                            value={csrForm.san_domains}
                            onChange={(e) => setCSRForm(prev => ({...prev, san_domains: e.target.value}))}
                            placeholder="www.example.com, api.example.com"
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          />
                          <p className="mt-1 text-xs text-gray-500">
                            Comma-separated list of additional domains
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 flex justify-end">
                        <button
                          onClick={generateCSR}
                          disabled={csrLoading || !csrForm.country || !csrForm.state || !csrForm.city || !csrForm.organization || !csrForm.common_name || !csrForm.email}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md font-medium disabled:opacity-50"
                        >
                          {csrLoading ? 'Generating...' : 'Generate CSR & Private Key'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* SSL Files Management */}
                  <div className="mt-4">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-md font-medium text-gray-900">SSL Files</h4>
                      <div className="flex gap-2">
                        <button
                          onClick={fetchSSLFiles}
                          className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm"
                        >
                          Refresh
                        </button>
                        {selectedFiles.length > 0 && (
                          <button
                            onClick={downloadMultiple}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                          >
                            Download Selected ({selectedFiles.length})
                          </button>
                        )}
                      </div>
                    </div>

                    {sslFiles.length === 0 ? (
                      <p className="text-gray-500 text-sm">No SSL files found in /app/ssl directory</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                <input
                                  type="checkbox"
                                  checked={selectedFiles.length === sslFiles.length}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedFiles(sslFiles.map(f => f.filename));
                                    } else {
                                      setSelectedFiles([]);
                                    }
                                  }}
                                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                File Name
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Type
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Size
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Modified
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {sslFiles.map((file) => (
                              <tr key={file.filename}>
                                <td className="px-3 py-2 whitespace-nowrap">
                                  <input
                                    type="checkbox"
                                    checked={selectedFiles.includes(file.filename)}
                                    onChange={() => toggleFileSelection(file.filename)}
                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                  />
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                                  {file.filename}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                  {file.type}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                  {(file.size / 1024).toFixed(1)} KB
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                  {new Date(file.modified).toLocaleString()}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => downloadFile(file.filename)}
                                      className="text-blue-600 hover:text-blue-900 text-xs"
                                    >
                                      Download
                                    </button>
                                    <button
                                      onClick={() => setFileToDelete(file.filename)}
                                      className="text-red-600 hover:text-red-900 text-xs"
                                    >
                                      Delete
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Delete Confirmation Modal */}
                  {fileToDelete && (
                    <div className="fixed inset-0 bg-gray-600/50 overflow-y-auto h-full w-full z-50">
                      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                        <div className="mt-3">
                          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.676-.833-2.46 0L3.354 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                          </div>
                          <div className="mt-2 px-7 py-3">
                            <h3 className="text-lg font-medium text-gray-900">Delete SSL File</h3>
                            <p className="mt-2 text-sm text-gray-500">
                              Are you sure you want to delete <strong>{fileToDelete}</strong>?
                              This action cannot be undone.
                            </p>
                            <div className="mt-3">
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Type "delete" to confirm:
                              </label>
                              <input
                                type="text"
                                value={deleteConfirmation}
                                onChange={(e) => setDeleteConfirmation(e.target.value)}
                                className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                                placeholder="delete"
                              />
                            </div>
                          </div>
                          <div className="flex justify-between px-4 py-3">
                            <button
                              onClick={() => {
                                setFileToDelete(null);
                                setDeleteConfirmation('');
                              }}
                              className="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md hover:bg-gray-700"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => deleteFile(fileToDelete)}
                              disabled={deleteConfirmation.toLowerCase() !== 'delete'}
                              className="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md hover:bg-red-700 disabled:opacity-50"
                            >
                              Delete File
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Reverse Proxy Configuration */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Reverse Proxy Configuration</h2>
          <p className="text-sm text-gray-600 mb-4">
            Configure nginx reverse proxy for production HTTPS access with enhanced security.
          </p>
          
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="reverse_proxy_enabled"
                checked={config.reverse_proxy?.enabled ?? false}
                onChange={(e) => handleInputChange('reverse_proxy', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="reverse_proxy_enabled" className="ml-2 text-sm text-gray-900">
                Enable Reverse Proxy
              </label>
            </div>

            {config.reverse_proxy?.enabled && (
              <>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-blue-800">
                        🚀 HTTPS Frontend Available!
                      </h3>
                      <div className="mt-2 text-sm text-blue-700">
                        <p>Access your secure frontend at:</p>
                        <div className="mt-2 font-mono bg-blue-100 px-2 py-1 rounded">
                          <strong>Main Interface:</strong> https://localhost:{config.reverse_proxy?.https_port ?? 8445}
                        </div>
                        <div className="mt-1 font-mono bg-blue-100 px-2 py-1 rounded">
                          <strong>Admin Interface:</strong> https://localhost:{config.reverse_proxy?.admin_port ?? 8446}/admin
                        </div>
                        <p className="mt-2 text-xs">
                          HTTP requests to port {config.reverse_proxy?.http_port ?? 8090} will be automatically redirected to HTTPS.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="proxy_http_port" className="block text-sm font-medium text-gray-700">
                      HTTP Port (Redirect)
                    </label>
                    <input
                      type="number"
                      id="proxy_http_port"
                      min="1024"
                      max="65535"
                      value={config.reverse_proxy?.http_port ?? 8090}
                      onChange={(e) => handleInputChange('reverse_proxy', 'http_port', parseInt(e.target.value))}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Port for HTTP (auto-redirects to HTTPS)
                    </p>
                  </div>

                  <div>
                    <label htmlFor="proxy_https_port" className="block text-sm font-medium text-gray-700">
                      HTTPS Port (Main)
                    </label>
                    <input
                      type="number"
                      id="proxy_https_port"
                      min="1024"
                      max="65535"
                      value={config.reverse_proxy?.https_port ?? 8445}
                      onChange={(e) => handleInputChange('reverse_proxy', 'https_port', parseInt(e.target.value))}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Main HTTPS port for web interface
                    </p>
                  </div>

                  <div>
                    <label htmlFor="proxy_admin_port" className="block text-sm font-medium text-gray-700">
                      Admin HTTPS Port
                    </label>
                    <input
                      type="number"
                      id="proxy_admin_port"
                      min="1024"
                      max="65535"
                      value={config.reverse_proxy?.admin_port ?? 8446}
                      onChange={(e) => handleInputChange('reverse_proxy', 'admin_port', parseInt(e.target.value))}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Dedicated admin interface port
                    </p>
                  </div>
                </div>

                <div>
                  <label htmlFor="proxy_server_name" className="block text-sm font-medium text-gray-700">
                    Server Name
                  </label>
                  <input
                    type="text"
                    id="proxy_server_name"
                    value={config.reverse_proxy?.server_name ?? 'localhost'}
                    onChange={(e) => handleInputChange('reverse_proxy', 'server_name', e.target.value)}
                    placeholder="localhost, example.com, or your domain"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Domain name or hostname for the server (should match SSL certificate)
                  </p>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="proxy_force_https"
                    checked={config.reverse_proxy?.force_https ?? true}
                    onChange={(e) => handleInputChange('reverse_proxy', 'force_https', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="proxy_force_https" className="ml-2 text-sm text-gray-900">
                    Force HTTPS (recommended)
                  </label>
                  <p className="ml-2 text-xs text-gray-500">
                    Automatically redirect all HTTP requests to HTTPS
                  </p>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-800">
                        Configuration Requirements
                      </h3>
                      <div className="mt-2 text-sm text-yellow-700">
                        <ul className="list-disc list-inside space-y-1">
                          <li>SSL certificates must be configured and valid</li>
                          <li>Nginx must be installed and running</li>
                          <li>Ensure ports are not already in use</li>
                          <li>Server name should match your SSL certificate</li>
                        </ul>
                      </div>
                    </div>
                  </div>
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
                  value={config.network?.port ?? 5272}
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

        {/* Database Management */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Database Management</h2>
          <p className="text-sm text-gray-600 mb-4">
            Manage your device readings and historical data
          </p>

          <div className="space-y-4">
            <div className="border-t pt-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-red-800">
                      Clear All Device Readings
                    </h3>
                    <div className="mt-2 text-sm text-red-700">
                      <p>This action will permanently delete:</p>
                      <ul className="list-disc list-inside mt-2 space-y-1">
                        <li>All device sensor readings</li>
                        <li>All historical energy data</li>
                        <li>All calculated costs</li>
                        <li>InfluxDB time-series data (if configured)</li>
                      </ul>
                      <p className="mt-3 font-semibold">This will preserve:</p>
                      <ul className="list-disc list-inside mt-2 space-y-1">
                        <li>Device information and configuration</li>
                        <li>Electricity rates</li>
                        <li>User accounts and settings</li>
                        <li>System configuration</li>
                      </ul>
                    </div>
                    <div className="mt-4">
                      <button
                        onClick={async () => {
                          if (!confirm('Are you sure you want to clear ALL device readings? This action cannot be undone!')) {
                            return;
                          }

                          const confirmation = prompt('Type "CLEAR ALL DATA" to confirm:');
                          if (confirmation !== 'CLEAR ALL DATA') {
                            setError('Confirmation text did not match. Operation cancelled.');
                            return;
                          }

                          setSaving(true);
                          setError('');
                          setSuccess('');

                          try {
                            const token = localStorage.getItem('token');
                            if (!token) {
                              setError('Not authenticated. Please log in again.');
                              setSaving(false);
                              return;
                            }

                            const response = await fetch('/api/readings/clear', {
                              method: 'POST',
                              headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                              }
                            });

                            if (response.ok) {
                              const data = await response.json();
                              setSuccess(`Successfully cleared ${data.details.readings_deleted} device readings and ${data.details.costs_deleted} cost records. ${data.details.influxdb_cleared ? 'InfluxDB data also cleared.' : ''}`);
                            } else if (response.status === 401) {
                              setError('Authentication failed. Your session may have expired. Please log out and log in again.');
                            } else {
                              const errorData = await response.json().catch(() => ({}));
                              setError(errorData.detail || errorData.message || 'Failed to clear device readings');
                            }
                          } catch (err) {
                            setError('Connection error while clearing readings');
                          } finally {
                            setSaving(false);
                          }
                        }}
                        disabled={saving}
                        className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
                      >
                        {saving ? 'Clearing...' : 'Clear All Readings'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Plugin Security Configuration */}
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Plugin Security Configuration</h2>
          <p className="text-sm text-gray-600 mb-4">
            Configure security policies for plugin installation and execution. These settings control how plugins are verified and trusted.
          </p>
          
          <div className="space-y-6">
            {/* Security Policies */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Security Policies</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="require_signature"
                    checked={config.plugin_security?.require_signature ?? false}
                    onChange={(e) => handleInputChange('plugin_security', 'require_signature', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="require_signature" className="ml-2 text-sm text-gray-900">
                    Require digital signatures for all plugins
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="allow_unsigned"
                    checked={config.plugin_security?.allow_unsigned ?? true}
                    onChange={(e) => handleInputChange('plugin_security', 'allow_unsigned', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="allow_unsigned" className="ml-2 text-sm text-gray-900">
                    Allow unsigned plugins (development mode)
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="verify_on_load"
                    checked={config.plugin_security?.verify_on_load ?? true}
                    onChange={(e) => handleInputChange('plugin_security', 'verify_on_load', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="verify_on_load" className="ml-2 text-sm text-gray-900">
                    Verify signatures when loading plugins
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="quarantine_invalid"
                    checked={config.plugin_security?.quarantine_invalid ?? true}
                    onChange={(e) => handleInputChange('plugin_security', 'quarantine_invalid', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="quarantine_invalid" className="ml-2 text-sm text-gray-900">
                    Quarantine plugins with invalid signatures
                  </label>
                </div>

                <div>
                  <label htmlFor="minimum_trust_level" className="block text-sm font-medium text-gray-700 mb-2">
                    Minimum Trust Level
                  </label>
                  <select
                    id="minimum_trust_level"
                    value={config.plugin_security?.minimum_trust_level ?? 'unsigned'}
                    onChange={(e) => handleInputChange('plugin_security', 'minimum_trust_level', e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="unsigned">Unsigned (least restrictive)</option>
                    <option value="community">Community</option>
                    <option value="verified">Verified</option>
                    <option value="official">Official (most restrictive)</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    Only plugins with this trust level or higher will be allowed
                  </p>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={updatePluginSecurityPolicies}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                  >
                    Update Security Policies
                  </button>
                </div>
              </div>
            </div>

            {/* Trusted Keys Management */}
            <div className="border-t pt-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">Trusted Signing Keys</h3>
                <div className="flex gap-2">
                  <button
                    onClick={fetchTrustedKeys}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm"
                  >
                    Refresh
                  </button>
                  <button
                    onClick={() => setShowAddKeyForm(!showAddKeyForm)}
                    className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm"
                  >
                    {showAddKeyForm ? 'Cancel' : 'Add Key'}
                  </button>
                </div>
              </div>

              {showAddKeyForm && (
                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                  <h4 className="text-md font-medium text-gray-900 mb-3">Add Trusted Signing Key</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Key Name
                      </label>
                      <input
                        type="text"
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        placeholder="verified_developer_name or official_kasa_monitor"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Use 'official_*' for official keys, 'verified_*' for verified developers, or any other name for community keys
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Public Key (PEM format)
                      </label>
                      <textarea
                        value={newKeyData}
                        onChange={(e) => setNewKeyData(e.target.value)}
                        rows={8}
                        placeholder="-----BEGIN PUBLIC KEY-----&#10;MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...&#10;-----END PUBLIC KEY-----"
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        onClick={addTrustedKey}
                        disabled={keyLoading || !newKeyName || !newKeyData}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium disabled:opacity-50"
                      >
                        {keyLoading ? 'Adding...' : 'Add Trusted Key'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Trusted Keys List */}
              <div>
                {trustedKeys.length === 0 ? (
                  <p className="text-gray-500 text-sm">No trusted keys configured</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Key Name
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Trust Level
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {trustedKeys.map((key) => (
                          <tr key={key.name}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {key.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                key.trust_level === 'official' ? 'bg-blue-100 text-blue-800' :
                                key.trust_level === 'verified' ? 'bg-green-100 text-green-800' :
                                'bg-yellow-100 text-yellow-800'
                              }`}>
                                {key.trust_level}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                Active
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Security Info */}
              <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-blue-800">
                      Plugin Security Information
                    </h3>
                    <div className="mt-2 text-sm text-blue-700">
                      <ul className="list-disc list-inside space-y-1">
                        <li><strong>Official keys:</strong> Use prefix 'official_' for maximum trust</li>
                        <li><strong>Verified keys:</strong> Use prefix 'verified_' for verified developers</li>
                        <li><strong>Community keys:</strong> Any other name for community contributors</li>
                        <li><strong>Trust levels:</strong> Higher levels include all lower levels (official &gt; verified &gt; community &gt; unsigned)</li>
                        <li><strong>CLI tool:</strong> Use <code>tools/plugin_signer.py</code> to generate keys and sign plugins</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* SSL Persistence Information */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                SSL Certificate Persistence
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc list-inside space-y-1">
                  <li><strong>Persistent Storage:</strong> SSL certificates are stored in persistent volumes and survive container updates</li>
                  <li><strong>Database Integration:</strong> Certificate paths are stored in the database and automatically loaded on startup</li>
                  <li><strong>Auto-Enablement:</strong> SSL is automatically enabled when both certificate and private key are present</li>
                  <li><strong>Secure Permissions:</strong> Private keys are automatically secured with 600 permissions</li>
                  <li><strong>Container Updates:</strong> Your SSL configuration persists across Docker container updates and restarts</li>
                </ul>
              </div>
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
    </AppLayout>
  );
}