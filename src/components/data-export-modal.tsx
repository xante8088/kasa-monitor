'use client';

import React, { useState, useEffect } from 'react';
import { X, Download, FileText, FileSpreadsheet, Database, Code, Calendar, Settings, Eye, Clock, CheckSquare } from 'lucide-react';
import { safeConsoleError, safeStorage } from '@/lib/security-utils';

interface Device {
  id: string;
  name: string;
  record_count: number;
  first_record: string;
  last_record: string;
}

interface Metric {
  id: string;
  name: string;
  description: string;
}

interface ExportFormat {
  name: string;
  extension: string;
  mime_type: string;
}

interface DataExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedDevices?: string[];
  modalTitle?: string;
  deviceContext?: {
    deviceId: string;
    deviceName: string;
  };
}

export function DataExportModal({ 
  isOpen, 
  onClose, 
  preselectedDevices = [],
  modalTitle,
  deviceContext
}: DataExportModalProps) {
  const [step, setStep] = useState(1); // 1: devices, 2: settings, 3: preview, 4: export
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [availableDevices, setAvailableDevices] = useState<Device[]>([]);
  const [availableMetrics, setAvailableMetrics] = useState<Metric[]>([]);
  const [availableFormats, setAvailableFormats] = useState<Record<string, ExportFormat>>({});
  
  // Export settings
  const [format, setFormat] = useState('csv');
  const [dateRange, setDateRange] = useState('7days');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [aggregation, setAggregation] = useState('raw');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['power', 'energy']);
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [compression, setCompression] = useState('none');
  
  // State
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [quickExportInProgress, setQuickExportInProgress] = useState<string | null>(null);

  // Load data on modal open and handle pre-selection
  useEffect(() => {
    if (isOpen) {
      loadDevices();
      loadMetrics();
      loadFormats();
      
      // Pre-select devices if provided
      if (preselectedDevices.length > 0) {
        setSelectedDevices(preselectedDevices);
      }
    }
  }, [isOpen, preselectedDevices]);

  const loadDevices = async () => {
    try {
      const token = safeStorage.getItem('token');
      // Use the standard devices endpoint
      const response = await fetch('/api/devices', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const devices = await response.json();
        // Transform to export format
        const exportDevices = devices.map((device: any) => ({
          id: device.ip,
          name: device.alias || device.model,
          type: device.device_type
        }));
        setAvailableDevices(exportDevices);
      }
    } catch (error) {
      safeConsoleError('Failed to load devices', error);
      // Provide empty fallback
      setAvailableDevices([]);
    }
  };

  const loadMetrics = async () => {
    // Use predefined metrics since there's no dedicated endpoint
    const defaultMetrics = [
      { id: 'power', name: 'Power (W)', unit: 'W' },
      { id: 'voltage', name: 'Voltage (V)', unit: 'V' },
      { id: 'current', name: 'Current (A)', unit: 'A' },
      { id: 'energy', name: 'Energy (kWh)', unit: 'kWh' },
      { id: 'cost', name: 'Cost ($)', unit: '$' },
      { id: 'uptime', name: 'Uptime', unit: 'hours' },
      { id: 'on_time', name: 'On Time', unit: 'hours' }
    ];
    setAvailableMetrics(defaultMetrics);
  };

  const loadFormats = async () => {
    // Use predefined formats since there's no dedicated endpoint
    const defaultFormats = [
      { id: 'csv', name: 'CSV', extension: '.csv', icon: 'FileText' },
      { id: 'json', name: 'JSON', extension: '.json', icon: 'Code' },
      { id: 'excel', name: 'Excel', extension: '.xlsx', icon: 'FileSpreadsheet' }
    ];
    setAvailableFormats(defaultFormats);
  };

  const getDateRange = () => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    if (dateRange === 'custom') {
      return { start: customStartDate, end: customEndDate };
    }
    
    let startDate = new Date();
    switch (dateRange) {
      case 'today':
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case '7days':
        startDate.setDate(now.getDate() - 7);
        break;
      case '30days':
        startDate.setDate(now.getDate() - 30);
        break;
      case '90days':
        startDate.setDate(now.getDate() - 90);
        break;
      case 'year':
        startDate = new Date(now.getFullYear(), 0, 1);
        break;
      default:
        startDate.setDate(now.getDate() - 7);
    }
    
    return {
      start: startDate.toISOString().split('T')[0] + 'T00:00:00Z',
      end: now.toISOString()
    };
  };

  const loadPreview = async () => {
    if (selectedDevices.length === 0) return;
    
    setPreviewLoading(true);
    setError('');
    
    try {
      const token = safeStorage.getItem('token');
      const range = getDateRange();
      
      // Since there's no preview endpoint, create a simple preview
      const previewInfo = {
        devices: selectedDevices.length,
        metrics: selectedMetrics.length,
        dateRange: `${range.start} to ${range.end}`,
        format: format,
        aggregation: aggregation
      };
      
      // Set preview data directly
      const preview = [
        `Devices: ${selectedDevices.length} selected`,
        `Metrics: ${selectedMetrics.join(', ') || 'All metrics'}`,
        `Date range: ${previewInfo.dateRange}`,
        `Format: ${previewInfo.format.toUpperCase()}`,
        `Aggregation: ${aggregation}`
      ];
      setPreviewData(preview);
    } catch (error) {
      setError('Failed to load preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    setError('');
    
    try {
      const token = safeStorage.getItem('token');
      const range = getDateRange();
      
      // Determine which export endpoint to use based on selected metrics
      const hasEnergyMetrics = selectedMetrics.some(m => 
        ['energy', 'cost', 'power'].includes(m)
      );
      
      const endpoint = hasEnergyMetrics ? '/api/export/energy' : '/api/export/devices';
      
      // Build request params as query string (backend expects query params)
      const params = new URLSearchParams();
      params.append('format', format === 'excel' ? 'excel' : 'csv');
      
      if (hasEnergyMetrics) {
        // Energy export endpoint parameters
        if (selectedDevices.length === 1) {
          params.append('device_ip', selectedDevices[0]);
        }
        params.append('start_date', range.start);
        params.append('end_date', range.end);
      } else {
        // Device export endpoint parameters
        params.append('include_energy', String(hasEnergyMetrics));
      }

      const response = await fetch(`${endpoint}?${params}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        // Backend returns the file directly, not JSON
        const blob = await response.blob();
        
        // Determine filename based on format
        const extension = format === 'excel' ? '.xlsx' : '.csv';
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = `kasa-export-${timestamp}${extension}`;
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        // Show success message and close modal
        setError(''); // Clear any previous errors
        onClose();
      } else {
        // Handle error responses
        let errorMessage = 'Export failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        
        if (response.status === 403) {
          setError('You do not have permission to export data. Please contact your administrator.');
        } else if (response.status === 429) {
          setError('Export rate limit exceeded. Please wait before trying again.');
        } else if (response.status === 401) {
          setError('Authentication expired. Please log in again.');
        } else {
          setError(`${errorMessage} (Error ${response.status})`);
        }
      }
    } catch (error) {
      setError('Export failed');
    } finally {
      setIsExporting(false);
    }
  };
  
  // Quick export functions for device context
  const handleQuickExport = async (preset: '24h' | '7d' | '30d') => {
    if (!deviceContext || selectedDevices.length === 0) return;
    
    setQuickExportInProgress(preset);
    setError('');
    
    try {
      const token = safeStorage.getItem('token');
      const now = new Date();
      let startDate = new Date();
      
      switch (preset) {
        case '24h':
          startDate.setDate(now.getDate() - 1);
          break;
        case '7d':
          startDate.setDate(now.getDate() - 7);
          break;
        case '30d':
          startDate.setDate(now.getDate() - 30);
          break;
      }
      
      const exportRequest = {
        devices: selectedDevices,
        date_range: {
          start: startDate.toISOString(),
          end: now.toISOString()
        },
        format: 'csv',
        aggregation: 'raw',
        metrics: ['power', 'energy'],
        options: {
          include_metadata: true
        }
      };
      
      const response = await fetch('/api/exports/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(exportRequest)
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.status === 'completed') {
          const downloadResponse = await fetch(result.download_url, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          if (downloadResponse.ok) {
            const blob = await downloadResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename || `${deviceContext.deviceName}_${preset}_export.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            onClose();
          } else {
            setError('Failed to download export file. Please try again.');
          }
        } else {
          setError('Export started. Check export history for progress.');
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Quick export failed');
      }
    } catch (error) {
      setError('Quick export failed');
    } finally {
      setQuickExportInProgress(null);
    }
  };
  
  const generateDeviceFilename = (deviceName: string, dateRange: string) => {
    const cleanName = deviceName.replace(/[^a-zA-Z0-9]/g, '_');
    const timestamp = new Date().toISOString().split('T')[0];
    return `${cleanName}_${dateRange}_${timestamp}`;
  };

  const handleDeviceToggle = (deviceId: string) => {
    setSelectedDevices(prev => 
      prev.includes(deviceId)
        ? prev.filter(id => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const handleMetricToggle = (metricId: string) => {
    setSelectedMetrics(prev => 
      prev.includes(metricId)
        ? prev.filter(id => id !== metricId)
        : [...prev, metricId]
    );
  };

  const resetModal = () => {
    setStep(1);
    setSelectedDevices(preselectedDevices.length > 0 ? preselectedDevices : []);
    setFormat('csv');
    setDateRange('7days');
    setAggregation('raw');
    setSelectedMetrics(['power', 'energy']);
    setError('');
    setPreviewData([]);
  };

  if (!isOpen) return null;

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Select Devices</h3>
              {deviceContext ? (
                <div className="mb-4">
                  <p className="text-sm text-gray-600 mb-3">
                    Exporting data for <span className="font-medium">{deviceContext.deviceName}</span>. 
                    You can select additional devices if needed.
                  </p>
                  
                  {/* Quick Export Options for Device Context */}
                  <div className="quick-export-section border rounded-lg p-4">
                    <h4 className="text-sm font-medium text-blue-900 mb-2">Quick Export Options</h4>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleQuickExport('24h')}
                        disabled={quickExportInProgress !== null}
                        className="quick-export-button px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                      >
                        {quickExportInProgress === '24h' ? (
                          <div className="animate-spin h-3 w-3 border border-white border-t-transparent rounded-full" />
                        ) : null}
                        <span>Last 24 Hours</span>
                      </button>
                      <button
                        onClick={() => handleQuickExport('7d')}
                        disabled={quickExportInProgress !== null}
                        className="quick-export-button px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                      >
                        {quickExportInProgress === '7d' ? (
                          <div className="animate-spin h-3 w-3 border border-white border-t-transparent rounded-full" />
                        ) : null}
                        <span>Last 7 Days</span>
                      </button>
                      <button
                        onClick={() => handleQuickExport('30d')}
                        disabled={quickExportInProgress !== null}
                        className="quick-export-button px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                      >
                        {quickExportInProgress === '30d' ? (
                          <div className="animate-spin h-3 w-3 border border-white border-t-transparent rounded-full" />
                        ) : null}
                        <span>Last 30 Days</span>
                      </button>
                    </div>
                    <p className="text-xs text-blue-700 mt-2">Quick exports use CSV format with all available metrics</p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-600 mb-4">Choose which devices to export data from</p>
              )}
              
              {availableDevices.length === 0 ? (
                <p className="text-gray-500 text-sm">No devices with data available</p>
              ) : (
                <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
                  {availableDevices.map((device) => (
                    <label key={device.id} className="flex items-center p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0">
                      <input
                        type="checkbox"
                        checked={selectedDevices.includes(device.id)}
                        onChange={() => handleDeviceToggle(device.id)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div className="ml-3 flex-1">
                        <div className="text-sm font-medium text-gray-900">{device.name}</div>
                        <div className="text-xs text-gray-500">
                          {device.record_count} records • {new Date(device.first_record).toLocaleDateString()} - {new Date(device.last_record).toLocaleDateString()}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
              
              <div className="mt-3 flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {selectedDevices.length} device{selectedDevices.length !== 1 ? 's' : ''} selected
                </span>
                <div className="space-x-2">
                  <button
                    onClick={() => setSelectedDevices(availableDevices.map(d => d.id))}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Select All
                  </button>
                  <button
                    onClick={() => setSelectedDevices([])}
                    className="text-xs text-gray-600 hover:text-gray-800"
                  >
                    Clear All
                  </button>
                </div>
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Export Settings</h3>
            </div>

            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="inline h-4 w-4 mr-1" />
                Date Range
              </label>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="today">Today</option>
                <option value="7days">Last 7 Days</option>
                <option value="30days">Last 30 Days</option>
                <option value="90days">Last 90 Days</option>
                <option value="year">This Year</option>
                <option value="custom">Custom Range</option>
              </select>
              
              {dateRange === 'custom' && (
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => setCustomStartDate(e.target.value)}
                      className="w-full p-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">End Date</label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => setCustomEndDate(e.target.value)}
                      className="w-full p-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Format Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FileText className="inline h-4 w-4 mr-1" />
                Export Format
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(availableFormats).map(([key, formatInfo]) => (
                  <button
                    key={key}
                    onClick={() => setFormat(key)}
                    className={`p-3 border rounded-md flex flex-col items-center ${
                      format === key ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                    }`}
                  >
                    {key === 'csv' && <FileText className="h-5 w-5 mb-1" />}
                    {key === 'excel' && <FileSpreadsheet className="h-5 w-5 mb-1" />}
                    {key === 'json' && <Code className="h-5 w-5 mb-1" />}
                    {key === 'sqlite' && <Database className="h-5 w-5 mb-1" />}
                    <span className="text-sm font-medium">{formatInfo.name}</span>
                    <span className="text-xs text-gray-500">.{formatInfo.extension}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Aggregation Level */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Clock className="inline h-4 w-4 mr-1" />
                Data Aggregation
              </label>
              <select
                value={aggregation}
                onChange={(e) => setAggregation(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="raw">Raw Data (all records)</option>
                <option value="hourly">Hourly Aggregation</option>
                <option value="daily">Daily Aggregation</option>
              </select>
            </div>

            {/* Metrics Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <CheckSquare className="inline h-4 w-4 mr-1" />
                Metrics to Include
              </label>
              <div className="space-y-2">
                {availableMetrics.map((metric) => (
                  <label key={metric.id} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedMetrics.includes(metric.id)}
                      onChange={() => handleMetricToggle(metric.id)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <div className="ml-2">
                      <span className="text-sm font-medium text-gray-900">{metric.name}</span>
                      <p className="text-xs text-gray-500">{metric.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Additional Options */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Settings className="inline h-4 w-4 mr-1" />
                Additional Options
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={includeMetadata}
                    onChange={(e) => setIncludeMetadata(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-900">Include metadata and headers</span>
                </label>
                
                <div>
                  <label className="block text-sm text-gray-700 mt-2 mb-1">Compression</label>
                  <select
                    value={compression}
                    onChange={(e) => setCompression(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="none">No compression</option>
                    <option value="zip">ZIP compression</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Preview Export</h3>
              <p className="text-sm text-gray-600 mb-4">Review your export settings and preview the data</p>
            </div>

            {/* Export Summary */}
            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Export Summary</h4>
              <div className="text-sm text-gray-600 space-y-1">
                <div>Devices: {selectedDevices.length} selected{deviceContext && selectedDevices.includes(deviceContext.deviceId) ? ` (including ${deviceContext.deviceName})` : ''}</div>
                <div>Format: {availableFormats[format]?.name} (.{availableFormats[format]?.extension})</div>
                <div>Date Range: {dateRange === 'custom' ? `${customStartDate} to ${customEndDate}` : dateRange}</div>
                <div>Aggregation: {aggregation}</div>
                <div>Metrics: {selectedMetrics.join(', ')}</div>
              </div>
            </div>

            {/* Data Preview */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-900">Data Preview</h4>
                <button
                  onClick={loadPreview}
                  disabled={previewLoading || selectedDevices.length === 0}
                  className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                >
                  <Eye className="inline h-4 w-4 mr-1" />
                  {previewLoading ? 'Loading...' : 'Load Preview'}
                </button>
              </div>
              
              {previewData.length > 0 ? (
                <div className="max-h-40 overflow-auto border border-gray-200 rounded-md">
                  <table className="min-w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {Object.keys(previewData[0] || {}).map((key) => (
                          <th key={key} className="px-2 py-1 text-left font-medium text-gray-900">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.slice(0, 5).map((row, index) => (
                        <tr key={index} className="border-t border-gray-200">
                          {Object.values(row).map((value: any, colIndex) => (
                            <td key={colIndex} className="px-2 py-1 text-gray-900">
                              {typeof value === 'number' ? value.toFixed(2) : String(value)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="border border-gray-200 rounded-md p-4 text-center text-gray-500 text-sm">
                  Click "Load Preview" to see a sample of your data
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const getStepTitle = () => {
    if (modalTitle) {
      return modalTitle;
    }
    
    if (deviceContext) {
      switch (step) {
        case 1: return `Export Data - ${deviceContext.deviceName}`;
        case 2: return `Configure Export - ${deviceContext.deviceName}`;
        case 3: return `Preview & Export - ${deviceContext.deviceName}`;
        default: return `Export Data - ${deviceContext.deviceName}`;
      }
    }
    
    switch (step) {
      case 1: return 'Select Devices';
      case 2: return 'Configure Export';
      case 3: return 'Preview & Export';
      default: return 'Export Data';
    }
  };

  const canProceedToNextStep = () => {
    switch (step) {
      case 1: return selectedDevices.length > 0;
      case 2: return selectedMetrics.length > 0 && format;
      case 3: return true;
      default: return false;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-xl font-semibold">{getStepTitle()}</h2>
            <div className="flex items-center mt-2">
              {[1, 2, 3].map((stepNum) => (
                <div key={stepNum} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    stepNum === step ? 'bg-blue-600 text-white' :
                    stepNum < step ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'
                  }`}>
                    {stepNum < step ? <CheckSquare className="h-4 w-4" /> : stepNum}
                  </div>
                  {stepNum < 3 && <div className={`w-12 h-1 mx-2 ${stepNum < step ? 'bg-green-600' : 'bg-gray-200'}`} />}
                </div>
              ))}
            </div>
          </div>
          <button 
            onClick={() => { resetModal(); onClose(); }} 
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Step Content */}
        <div className="mb-6">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <div>
            {step > 1 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Previous
              </button>
            )}
          </div>
          
          <div className="space-x-3">
            <button
              onClick={() => { resetModal(); onClose(); }}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            
            {step < 3 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canProceedToNextStep()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleExport}
                disabled={isExporting || selectedDevices.length === 0}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center"
              >
                <Download className="h-4 w-4 mr-2" />
                {isExporting ? 'Exporting...' : 'Export Data'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}