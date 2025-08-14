'use client'

import { Zap, Search, DollarSign, Settings, Users, Shield, LogOut, ChevronDown, Bell, Folder, Database, FileText, Download } from 'lucide-react'
import { useAuth } from '../contexts/auth-context'
import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'

interface HeaderProps {
  onDiscoverClick: () => void
  onRatesClick: () => void
  onDeviceManagementClick?: () => void
}

export function Header({ onDiscoverClick, onRatesClick, onDeviceManagementClick }: HeaderProps) {
  const { user, logout, hasPermission } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!user) {
    return null // Don't show header if not authenticated
  }

  return (
    <header className="bg-kasa-dark text-white border-b border-gray-800">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Zap className="h-8 w-8 text-kasa-primary" />
            <Link href="/" className="text-2xl font-bold hover:text-kasa-primary transition-colors">
              Kasa Monitor
            </Link>
          </div>
          
          <nav className="flex items-center space-x-4">
            {hasPermission('discover_devices') && (
              <button
                onClick={onDiscoverClick}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-kasa-secondary hover:bg-kasa-primary transition-colors"
              >
                <Search className="h-5 w-5" />
                <span>Discover Devices</span>
              </button>
            )}
            
            {hasPermission('view_rates') && (
              <button
                onClick={onRatesClick}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                <DollarSign className="h-5 w-5" />
                <span>Electricity Rates</span>
              </button>
            )}
            
            {onDeviceManagementClick && hasPermission('manage_devices') && (
              <button
                onClick={onDeviceManagementClick}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                <Settings className="h-5 w-5" />
                <span>Manage Devices</span>
              </button>
            )}

            {/* Admin Menu */}
            {user.role === 'admin' && (
              <div className="relative">
                <Link
                  href="/admin/users"
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 transition-colors"
                >
                  <Users className="h-5 w-5" />
                  <span>Admin</span>
                </Link>
              </div>
            )}

            {/* User Menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium">
                    {user.full_name?.charAt(0) || user.username.charAt(0)}
                  </span>
                </div>
                <span className="hidden sm:block">{user.full_name || user.username}</span>
                <ChevronDown className="h-4 w-4" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <p className="text-sm font-medium text-gray-900">{user.full_name || user.username}</p>
                    <p className="text-sm text-gray-500">{user.email}</p>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full mt-1 ${
                      user.role === 'admin' ? 'bg-red-100 text-red-800' :
                      user.role === 'operator' ? 'bg-blue-100 text-blue-800' :
                      user.role === 'viewer' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {user.role}
                    </span>
                  </div>

                  <div className="py-2">
                    {user.role === 'admin' && (
                      <>
                        <Link
                          href="/admin/users"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Users className="h-4 w-4 mr-3" />
                          User Management
                        </Link>
                        <Link
                          href="/admin/permissions"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Shield className="h-4 w-4 mr-3" />
                          Permissions
                        </Link>
                        <Link
                          href="/admin/system"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Settings className="h-4 w-4 mr-3" />
                          System Config
                        </Link>
                        <Link
                          href="/admin/alerts"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Bell className="h-4 w-4 mr-3" />
                          Alert Management
                        </Link>
                        <Link
                          href="/admin/device-groups"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Folder className="h-4 w-4 mr-3" />
                          Device Groups
                        </Link>
                        <Link
                          href="/admin/backup"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Database className="h-4 w-4 mr-3" />
                          Backup & Restore
                        </Link>
                        <Link
                          href="/admin/audit-logs"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <FileText className="h-4 w-4 mr-3" />
                          Audit Logs
                        </Link>
                        <hr className="my-2" />
                      </>
                    )}
                    <button
                      onClick={() => {
                        logout()
                        setShowUserMenu(false)
                      }}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <LogOut className="h-4 w-4 mr-3" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </nav>
        </div>
      </div>
    </header>
  )
}