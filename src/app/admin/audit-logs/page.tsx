'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FileText, Filter, Search, User, Shield, Settings, Activity, RefreshCw, Play, Pause, Download, ChevronDown } from 'lucide-react';
import { AppLayout } from '@/components/app-layout';
import { safeConsoleError, safeConsoleLog, safeFetch, safeStorage, createSafeApiUrl } from '@/lib/security-utils';

interface AuditLog {
  id: number;
  event_type: string;
  severity: string;
  user_id: number;
  username: string;
  ip_address: string;
  user_agent?: string;
  session_id?: string;
  resource_type?: string;
  resource_id?: string;
  action: string;
  details?: any;
  success: boolean;
  error_message?: string;
  timestamp: string;
  checksum: string;
}

type LogCategory = 'authentication' | 'devices' | 'users' | 'system' | 'security' | 'data' | 'api';
type LogSeverity = 'debug' | 'info' | 'warning' | 'error' | 'critical';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<LogCategory[]>([]);
  const [selectedSeverities, setSelectedSeverities] = useState<LogSeverity[]>([]);
  const [dateRange, setDateRange] = useState('7days');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshRate, setRefreshRate] = useState(30); // seconds
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  const [showSeverityDropdown, setShowSeverityDropdown] = useState(false);
  const categoryDropdownRef = useRef<HTMLDivElement>(null);
  const severityDropdownRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async (showRefreshIndicator = false) => {
    try {
      if (showRefreshIndicator) {
        setIsRefreshing(true);
      }
      const token = safeStorage.getItem('token');
      
      // Use safe API URL construction to prevent injection
      const apiParams = {
        page: currentPage.toString(),
        category: selectedCategories.length > 0 ? selectedCategories.join(',') : 'all',
        severity: selectedSeverities.length > 0 ? selectedSeverities.join(',') : 'all',
        range: dateRange,
        search: searchTerm
      };

      safeConsoleLog('Fetching audit logs with categories count', selectedCategories.length);

      const response = await safeFetch('/api/audit-logs', {
        params: apiParams,
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        safeConsoleLog('Received logs count', data.logs?.length || 0);
        setLogs(data.logs || []);
        setTotalPages(data.total_pages || 1);
      } else {
        safeConsoleError('Audit logs fetch failed', `Status: ${response.status}`);
      }
    } catch (error) {
      safeConsoleError('Failed to fetch audit logs', error);
    } finally {
      setLoading(false);
      if (showRefreshIndicator) {
        setIsRefreshing(false);
      }
    }
  }, [currentPage, selectedCategories, selectedSeverities, dateRange, searchTerm]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh && refreshRate > 0) {
      intervalRef.current = setInterval(() => {
        fetchLogs();
      }, refreshRate * 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshRate, fetchLogs]);

  // Click outside to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (categoryDropdownRef.current && !categoryDropdownRef.current.contains(event.target as Node)) {
        setShowCategoryDropdown(false);
      }
      if (severityDropdownRef.current && !severityDropdownRef.current.contains(event.target as Node)) {
        setShowSeverityDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getActionIcon = (action: string) => {
    if (action.includes('login') || action.includes('auth')) return <User className="h-4 w-4" />;
    if (action.includes('device')) return <Activity className="h-4 w-4" />;
    if (action.includes('user')) return <User className="h-4 w-4" />;
    if (action.includes('system') || action.includes('config')) return <Settings className="h-4 w-4" />;
    if (action.includes('security') || action.includes('permission')) return <Shield className="h-4 w-4" />;
    return <FileText className="h-4 w-4" />;
  };

  const getActionColor = (action: string, status: string) => {
    if (status === 'failure') return 'text-red-600 bg-red-50';
    if (action.includes('delete') || action.includes('remove')) return 'text-orange-600 bg-orange-50';
    if (action.includes('create') || action.includes('add')) return 'text-green-600 bg-green-50';
    if (action.includes('update') || action.includes('edit')) return 'text-blue-600 bg-blue-50';
    return 'text-gray-600 bg-gray-50';
  };

  const formatAction = (action: string) => {
    return action.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const handleManualRefresh = () => {
    fetchLogs(true);
  };

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  };

  const handleRefreshRateChange = (rate: number) => {
    setRefreshRate(rate);
  };

  const handleExportLogs = async () => {
    try {
      setIsExporting(true);
      setExportError(null);
      setExportSuccess(null);
      
      const token = safeStorage.getItem('token');
      const exportOptions = {
        format: 'csv',
        date_range: dateRange,
        category: selectedCategories.length > 0 ? selectedCategories.join(',') : null
      };

      const response = await fetch('/api/audit-logs/export', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(exportOptions)
      });

      if (response.ok) {
        // Get the filename from the response headers if available
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'audit_logs.csv';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="(.+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }

        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setExportSuccess(`Audit logs exported successfully as ${filename}`);
        
        // Clear success message after 5 seconds
        setTimeout(() => setExportSuccess(null), 5000);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Export failed' }));
        const errorMessage = errorData.detail || 'Failed to export audit logs';
        setExportError(errorMessage);
        // Clear error message after 10 seconds
        setTimeout(() => setExportError(null), 10000);
      }
    } catch (error) {
      safeConsoleError('Export error', error);
      const errorMessage = 'Network error occurred while exporting logs';
      setExportError(errorMessage);
      // Clear error message after 10 seconds
      setTimeout(() => setExportError(null), 10000);
    } finally {
      setIsExporting(false);
    }
  };

  const toggleCategory = (cat: LogCategory) => {
    setSelectedCategories(prev => {
      if (prev.includes(cat)) {
        return prev.filter(c => c !== cat);
      }
      return [...prev, cat];
    });
    setCurrentPage(1); // Reset to first page when filters change
  };

  const toggleSeverity = (sev: LogSeverity) => {
    setSelectedSeverities(prev => {
      if (prev.includes(sev)) {
        return prev.filter(s => s !== sev);
      }
      return [...prev, sev];
    });
    setCurrentPage(1); // Reset to first page when filters change
  };

  const categories: LogCategory[] = ['authentication', 'devices', 'users', 'system', 'security', 'data', 'api'];
  const severities: LogSeverity[] = ['debug', 'info', 'warning', 'error', 'critical'];

  const clearFilters = () => {
    setSelectedCategories([]);
    setSelectedSeverities([]);
    setSearchTerm('');
    setCurrentPage(1);
  };

  const hasActiveFilters = selectedCategories.length > 0 || selectedSeverities.length > 0 || searchTerm.length > 0;

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
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-600 mt-1">System activity and security audit trail</p>
      </div>

      {/* Export status messages */}
      {exportError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <Shield className="h-5 w-5 text-red-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Export Failed</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{exportError}</p>
              </div>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => setExportError(null)}
                  className="bg-red-50 text-red-800 text-sm px-3 py-2 rounded-md border border-red-200 hover:bg-red-100"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {exportSuccess && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <Download className="h-5 w-5 text-green-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Export Successful</h3>
              <div className="mt-2 text-sm text-green-700">
                <p>{exportSuccess}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 p-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
            <div className="flex-1 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search logs..."
                  className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              {/* Category filter with checkboxes */}
              <div className="relative" ref={categoryDropdownRef}>
                <button
                  onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                  className={`px-4 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 bg-white flex items-center space-x-2 ${
                    selectedCategories.length > 0 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-300'
                  }`}
                >
                  <span className={selectedCategories.length > 0 ? 'text-blue-700 font-medium' : ''}>
                    {selectedCategories.length === 0 
                      ? 'All Categories' 
                      : `${selectedCategories.length} categories`}
                  </span>
                  <ChevronDown className={`h-4 w-4 ${selectedCategories.length > 0 ? 'text-blue-600' : ''}`} />
                </button>
                {showCategoryDropdown && (
                  <div className="absolute z-10 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg">
                    {categories.map(cat => (
                      <label key={cat} className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedCategories.includes(cat)}
                          onChange={() => toggleCategory(cat)}
                          className="mr-2"
                        />
                        <span className="capitalize">{cat}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Severity filter with checkboxes */}
              <div className="relative" ref={severityDropdownRef}>
                <button
                  onClick={() => setShowSeverityDropdown(!showSeverityDropdown)}
                  className={`px-4 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 bg-white flex items-center space-x-2 ${
                    selectedSeverities.length > 0 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-300'
                  }`}
                >
                  <span className={selectedSeverities.length > 0 ? 'text-blue-700 font-medium' : ''}>
                    {selectedSeverities.length === 0 
                      ? 'All Levels' 
                      : `${selectedSeverities.length} levels`}
                  </span>
                  <ChevronDown className={`h-4 w-4 ${selectedSeverities.length > 0 ? 'text-blue-600' : ''}`} />
                </button>
                {showSeverityDropdown && (
                  <div className="absolute z-10 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg">
                    {severities.map(sev => (
                      <label key={sev} className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedSeverities.includes(sev)}
                          onChange={() => toggleSeverity(sev)}
                          className="mr-2"
                        />
                        <span className="capitalize">{sev}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="today">Today</option>
                <option value="7days">Last 7 Days</option>
                <option value="30days">Last 30 Days</option>
                <option value="90days">Last 90 Days</option>
                <option value="year">This Year</option>
              </select>
              
              {/* Clear Filters button */}
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="px-3 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 flex items-center text-sm"
                >
                  <Filter className="h-4 w-4 mr-1" />
                  Clear Filters
                </button>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {/* Auto-refresh controls */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={toggleAutoRefresh}
                  className={`px-3 py-2 rounded-md flex items-center text-sm ${
                    autoRefresh 
                      ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {autoRefresh ? (
                    <Pause className="h-4 w-4 mr-1" />
                  ) : (
                    <Play className="h-4 w-4 mr-1" />
                  )}
                  Auto-refresh
                </button>

                {autoRefresh && (
                  <select
                    value={refreshRate}
                    onChange={(e) => handleRefreshRateChange(Number(e.target.value))}
                    className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={5}>5s</option>
                    <option value={10}>10s</option>
                    <option value={30}>30s</option>
                    <option value={60}>1m</option>
                    <option value={300}>5m</option>
                  </select>
                )}
              </div>

              {/* Manual refresh button */}
              <button
                onClick={handleManualRefresh}
                disabled={isRefreshing}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center text-sm disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>

              {/* Export button */}
              <button 
                onClick={handleExportLogs}
                disabled={isExporting}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExporting ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                {isExporting ? 'Exporting...' : 'Export Logs'}
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  IP Address
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-500">No audit logs found</p>
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <User className="h-4 w-4 text-gray-600" />
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">{log.username}</p>
                          <p className="text-xs text-gray-500">ID: {log.user_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`p-1.5 rounded ${getActionColor(log.action, log.success ? 'success' : 'failure')}`}>
                          {getActionIcon(log.action)}
                        </div>
                        <span className="ml-2 text-sm text-gray-900">
                          {formatAction(log.action)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.resource_type || '-'}
                      {log.resource_id && (
                        <span className="text-gray-500"> #{log.resource_id}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.ip_address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        log.success 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {log.success ? 'success' : 'failure'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {log.details && (
                        <button 
                          onClick={() => {
                            setSelectedLog(log);
                            setShowDetailsModal(true);
                          }}
                          className="text-blue-600 hover:text-blue-700"
                        >
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing page <span className="font-medium">{currentPage}</span> of{' '}
                  <span className="font-medium">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Details Modal */}
      {showDetailsModal && selectedLog && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity">
              <div className="absolute inset-0 bg-gray-500 opacity-75" onClick={() => setShowDetailsModal(false)}></div>
            </div>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                      Audit Log Details
                    </h3>
                    
                    <div className="space-y-3">
                      <div>
                        <span className="font-medium text-gray-700">Timestamp:</span>
                        <p className="text-gray-600">{new Date(selectedLog.timestamp).toLocaleString()}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Event Type:</span>
                        <p className="text-gray-600">{selectedLog.event_type}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Severity:</span>
                        <p className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                          selectedLog.severity === 'info' ? 'bg-blue-100 text-blue-800' :
                          selectedLog.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                          selectedLog.severity === 'error' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {selectedLog.severity}
                        </p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">User:</span>
                        <p className="text-gray-600">{selectedLog.username} (ID: {selectedLog.user_id})</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">Action:</span>
                        <p className="text-gray-600">{selectedLog.action}</p>
                      </div>
                      
                      <div>
                        <span className="font-medium text-gray-700">IP Address:</span>
                        <p className="text-gray-600">{selectedLog.ip_address}</p>
                      </div>
                      
                      {selectedLog.user_agent && (
                        <div>
                          <span className="font-medium text-gray-700">User Agent:</span>
                          <p className="text-gray-600 text-sm break-words">{selectedLog.user_agent}</p>
                        </div>
                      )}
                      
                      <div>
                        <span className="font-medium text-gray-700">Status:</span>
                        <p className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                          selectedLog.success 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {selectedLog.success ? 'success' : 'failure'}
                        </p>
                      </div>
                      
                      {selectedLog.error_message && (
                        <div>
                          <span className="font-medium text-gray-700">Error:</span>
                          <p className="text-red-600">{selectedLog.error_message}</p>
                        </div>
                      )}
                      
                      {selectedLog.details && (
                        <div>
                          <span className="font-medium text-gray-700">Details:</span>
                          <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto mt-1">
                            {JSON.stringify(selectedLog.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={() => setShowDetailsModal(false)}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      </div>
    </AppLayout>
  );
}