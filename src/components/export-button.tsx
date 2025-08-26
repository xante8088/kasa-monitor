'use client';

import React from 'react';
import { Download } from 'lucide-react';
import { useAuth } from '@/contexts/auth-context';

interface ExportButtonProps {
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
  showText?: boolean;
  title?: string;
  deviceName?: string;
}

export function ExportButton({ 
  onClick, 
  variant = 'primary', 
  size = 'md', 
  disabled = false,
  className = '',
  showText = true,
  title,
  deviceName
}: ExportButtonProps) {
  const { hasPermission } = useAuth();

  // Don't render if user lacks export permission
  if (!hasPermission('data.export')) {
    return null;
  }

  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses = {
    primary: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    outline: 'border border-green-600 text-green-600 bg-transparent hover:bg-green-50 focus:ring-green-500'
  };

  const sizeClasses = {
    sm: 'px-3 py-2 text-sm space-x-1',
    md: 'px-4 py-2 text-sm space-x-2',
    lg: 'px-6 py-3 text-base space-x-2'
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };

  const disabledClasses = disabled 
    ? 'opacity-50 cursor-not-allowed pointer-events-none' 
    : '';

  const buttonClasses = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabledClasses} ${className}`;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={buttonClasses}
      title={title || (deviceName ? `Export data for ${deviceName}` : "Export device data to various formats")}
    >
      <Download className={iconSizes[size]} />
      {showText && <span>{deviceName ? `Export ${deviceName}` : 'Export Data'}</span>}
    </button>
  );
}

// Specialized variants for different use cases
export function PrimaryExportButton(props: Omit<ExportButtonProps, 'variant'>) {
  return <ExportButton {...props} variant="primary" />;
}

export function SecondaryExportButton(props: Omit<ExportButtonProps, 'variant'>) {
  return <ExportButton {...props} variant="secondary" />;
}

export function OutlineExportButton(props: Omit<ExportButtonProps, 'variant'>) {
  return <ExportButton {...props} variant="outline" />;
}

export function CompactExportButton(props: Omit<ExportButtonProps, 'size' | 'showText'>) {
  return <ExportButton {...props} size="sm" showText={false} />;
}