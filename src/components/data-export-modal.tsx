'use client';

import React, { useState } from 'react';
import { X, Download, FileText, FileSpreadsheet, FilePlus } from 'lucide-react';

interface DataExportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DataExportModal({ isOpen, onClose }: DataExportModalProps) {
  const [exportType, setExportType] = useState('devices');
  const [format, setFormat] = useState('csv');
  const [dateRange, setDateRange] = useState('7days');
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        type: exportType,
        format: format,
        range: dateRange
      });

      const response = await fetch(`/api/export?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kasa-export-${exportType}-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        onClose();
      }
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Export Data</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Type
            </label>
            <select
              value={exportType}
              onChange={(e) => setExportType(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="devices">Devices</option>
              <option value="energy">Energy Consumption</option>
              <option value="costs">Cost Analysis</option>
              <option value="alerts">Alert History</option>
              <option value="audit">Audit Logs</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Format
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setFormat('csv')}
                className={`p-2 border rounded-md flex flex-col items-center ${
                  format === 'csv' ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
              >
                <FileText className="h-5 w-5 mb-1" />
                <span className="text-sm">CSV</span>
              </button>
              <button
                onClick={() => setFormat('xlsx')}
                className={`p-2 border rounded-md flex flex-col items-center ${
                  format === 'xlsx' ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
              >
                <FileSpreadsheet className="h-5 w-5 mb-1" />
                <span className="text-sm">Excel</span>
              </button>
              <button
                onClick={() => setFormat('pdf')}
                className={`p-2 border rounded-md flex flex-col items-center ${
                  format === 'pdf' ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
              >
                <FilePlus className="h-5 w-5 mb-1" />
                <span className="text-sm">PDF</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
              <option value="all">All Time</option>
            </select>
          </div>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
          >
            <Download className="h-4 w-4 mr-2" />
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  );
}