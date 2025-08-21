'use client';

import { useState, useRef } from 'react';
import { X, Upload, File, AlertTriangle, CheckCircle, RefreshCw, Package } from 'lucide-react';
import { safeConsoleError, safeStorage } from '@/lib/security-utils';

interface PluginUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

interface UploadProgress {
  step: 'upload' | 'validation' | 'installation' | 'complete';
  message: string;
  progress: number;
}

export default function PluginUploadModal({ isOpen, onClose, onUploadSuccess }: PluginUploadModalProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    if (!uploading) {
      setSelectedFile(null);
      setError('');
      setSuccess(false);
      setUploadProgress(null);
      onClose();
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file: File) => {
    setError('');
    setSuccess(false);
    setUploadProgress(null);

    // Validate file type
    if (!file.name.endsWith('.zip')) {
      setError('Please select a ZIP file containing the plugin');
      return;
    }

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }

    setSelectedFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const uploadPlugin = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError('');
      setSuccess(false);

      // Step 1: Upload
      setUploadProgress({
        step: 'upload',
        message: 'Uploading plugin file...',
        progress: 20
      });

      const formData = new FormData();
      formData.append('file', selectedFile);

      const token = safeStorage.getItem('token');
      const response = await fetch('/api/plugins/install', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      // Step 2: Validation
      setUploadProgress({
        step: 'validation',
        message: 'Validating plugin...',
        progress: 50
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload plugin');
      }

      // Step 3: Installation
      setUploadProgress({
        step: 'installation',
        message: 'Installing plugin...',
        progress: 80
      });

      const result = await response.json();

      // Step 4: Complete
      setUploadProgress({
        step: 'complete',
        message: `Plugin "${result.name}" installed successfully!`,
        progress: 100
      });

      setSuccess(true);
      setTimeout(() => {
        onUploadSuccess();
        handleClose();
      }, 2000);

    } catch (err: any) {
      safeConsoleError('Error uploading plugin', err);
      setError(err.message || 'Failed to upload plugin');
      setUploadProgress(null);
    } finally {
      setUploading(false);
    }
  };

  const getStepIcon = (step: string) => {
    switch (step) {
      case 'upload': return <Upload className="h-5 w-5" />;
      case 'validation': return <File className="h-5 w-5" />;
      case 'installation': return <Package className="h-5 w-5" />;
      case 'complete': return <CheckCircle className="h-5 w-5" />;
      default: return <RefreshCw className="h-5 w-5" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">Install Plugin</h3>
              <p className="text-sm text-gray-500">Upload a plugin ZIP file</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={uploading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="mt-6">
          {!uploadProgress ? (
            <>
              {/* File Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 ${
                  dragActive
                    ? 'border-red-400 bg-red-50'
                    : selectedFile
                    ? 'border-green-400 bg-green-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={handleFileInputChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={uploading}
                />

                <div className="text-center">
                  {selectedFile ? (
                    <div className="space-y-2">
                      <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
                      <div className="text-sm">
                        <p className="font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-gray-500">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="text-sm">
                        <p className="font-medium text-gray-900">
                          Drop your plugin ZIP file here
                        </p>
                        <p className="text-gray-500">or click to browse</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* File Requirements */}
              <div className="mt-4 text-xs text-gray-500">
                <p className="font-medium mb-2">Requirements:</p>
                <ul className="space-y-1">
                  <li>• ZIP file containing plugin code</li>
                  <li>• Must include manifest.json file</li>
                  <li>• Maximum file size: 50MB</li>
                  <li>• Valid plugin structure</li>
                </ul>
              </div>
            </>
          ) : (
            /* Upload Progress */
            <div className="space-y-4">
              <div className="text-center">
                <div className="flex items-center justify-center mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                    {uploadProgress.step === 'complete' ? (
                      <CheckCircle className="h-6 w-6 text-green-600" />
                    ) : (
                      <RefreshCw className="h-6 w-6 text-red-600 animate-spin" />
                    )}
                  </div>
                </div>
                <p className="text-sm font-medium text-gray-900 mb-2">
                  {uploadProgress.message}
                </p>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-red-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress.progress}%` }}
                ></div>
              </div>

              {/* Progress Steps */}
              <div className="flex justify-between text-xs text-gray-500">
                {['upload', 'validation', 'installation', 'complete'].map((step, index) => (
                  <div
                    key={step}
                    className={`flex items-center space-x-1 ${
                      uploadProgress.step === step
                        ? 'text-red-600 font-medium'
                        : index < ['upload', 'validation', 'installation', 'complete'].indexOf(uploadProgress.step)
                        ? 'text-green-600'
                        : 'text-gray-400'
                    }`}
                  >
                    {getStepIcon(step)}
                    <span className="capitalize">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex">
                <AlertTriangle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Success Display */}
          {success && (
            <div className="mt-4 bg-green-50 border border-green-200 rounded-md p-3">
              <div className="flex">
                <CheckCircle className="h-5 w-5 text-green-400" />
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    Plugin installed successfully! The page will refresh automatically.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 mt-6 pt-6 border-t border-gray-200">
          <button
            onClick={handleClose}
            disabled={uploading}
            className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Cancel'}
          </button>
          {selectedFile && !uploadProgress && (
            <button
              onClick={uploadPlugin}
              disabled={uploading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
            >
              <Upload className="h-4 w-4 mr-2" />
              Install Plugin
            </button>
          )}
        </div>
      </div>
    </div>
  );
}