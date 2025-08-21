'use client'

import React, { useState, useEffect } from 'react'
import { AppLayout } from '@/components/app-layout'
import { useAuth } from '@/contexts/auth-context'
import { User, Mail, Shield, Trash2, Save, AlertTriangle, CheckCircle, X } from 'lucide-react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { safeConsoleError, safeStorage } from '@/lib/security-utils'

export default function ProfilePage() {
  const { user, logout } = useAuth()
  const router = useRouter()
  
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  const [twoFAEnabled, setTwoFAEnabled] = useState(false)
  const [twoFAQRCode, setTwoFAQRCode] = useState('')
  const [twoFAToken, setTwoFAToken] = useState('')
  const [showTwoFASetup, setShowTwoFASetup] = useState(false)
  
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '')
      setEmail(user.email || '')
      // Check if 2FA is enabled for this user
      checkTwoFAStatus()
    }
  }, [user])

  const checkTwoFAStatus = async () => {
    try {
      const token = safeStorage.getItem('token')
      const response = await axios.get('/api/auth/2fa/status', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTwoFAEnabled(response.data.enabled)
    } catch (error) {
      safeConsoleError('Failed to check 2FA status', error)
    }
  }

  const handleUpdateProfile = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const updates: any = {}
      
      if (fullName !== user?.full_name) updates.full_name = fullName
      if (email !== user?.email) updates.email = email
      
      if (Object.keys(updates).length === 0) {
        setMessage({ type: 'error', text: 'No changes to save' })
        return
      }
      
      const response = await axios.put('/api/auth/profile', updates, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setMessage({ type: 'success', text: 'Profile updated successfully' })
      // Update user context if needed
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update profile' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' })
      return
    }
    
    if (newPassword.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters long' })
      return
    }
    
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const response = await axios.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setMessage({ type: 'success', text: 'Password changed successfully' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to change password' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleEnable2FA = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const response = await axios.post('/api/auth/2fa/setup', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setTwoFAQRCode(response.data.qr_code)
      setShowTwoFASetup(true)
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to setup 2FA' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleVerify2FA = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const response = await axios.post('/api/auth/2fa/verify', {
        token: twoFAToken
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setTwoFAEnabled(true)
      setShowTwoFASetup(false)
      setTwoFAToken('')
      setMessage({ type: 'success', text: '2FA enabled successfully' })
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Invalid verification code' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDisable2FA = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const response = await axios.post('/api/auth/2fa/disable', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setTwoFAEnabled(false)
      setMessage({ type: 'success', text: '2FA disabled successfully' })
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to disable 2FA' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE MY ACCOUNT') {
      setMessage({ type: 'error', text: 'Please type the confirmation text exactly' })
      return
    }
    
    try {
      setLoading(true)
      setMessage(null)
      
      const token = safeStorage.getItem('token')
      const response = await axios.delete('/api/auth/account', {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      // Log out and redirect to login
      logout()
      router.push('/login')
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to delete account' 
      })
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Please log in to view your profile</p>
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Profile Settings</h1>
        
        {message && (
          <div className={`mb-6 p-4 rounded-lg flex items-center ${
            message.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            {message.type === 'success' ? (
              <CheckCircle className="h-5 w-5 mr-2" />
            ) : (
              <AlertTriangle className="h-5 w-5 mr-2" />
            )}
            {message.text}
          </div>
        )}

        {/* Basic Information */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <User className="h-5 w-5 mr-2" />
            Basic Information
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username (cannot be changed)
              </label>
              <input
                type="text"
                value={user.username}
                disabled
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter your full name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter your email"
              />
            </div>
            
            <button
              onClick={handleUpdateProfile}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </button>
          </div>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Shield className="h-5 w-5 mr-2" />
            Change Password
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Password
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <button
              onClick={handleChangePassword}
              disabled={loading || !currentPassword || !newPassword || !confirmPassword}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
            >
              <Shield className="h-4 w-4 mr-2" />
              Change Password
            </button>
          </div>
        </div>

        {/* Two-Factor Authentication */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Shield className="h-5 w-5 mr-2" />
            Two-Factor Authentication
          </h2>
          
          {!twoFAEnabled ? (
            <div>
              <p className="text-gray-600 mb-4">
                Add an extra layer of security to your account by enabling two-factor authentication.
              </p>
              <button
                onClick={handleEnable2FA}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                Enable 2FA
              </button>
            </div>
          ) : (
            <div>
              <p className="text-green-600 mb-4 flex items-center">
                <CheckCircle className="h-5 w-5 mr-2" />
                Two-factor authentication is enabled
              </p>
              <button
                onClick={handleDisable2FA}
                disabled={loading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                Disable 2FA
              </button>
            </div>
          )}
          
          {showTwoFASetup && (
            <div className="mt-6 p-4 border border-gray-200 rounded-lg">
              <h3 className="font-semibold mb-3">Setup Two-Factor Authentication</h3>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600 mb-4">
                <li>Scan the QR code with your authenticator app</li>
                <li>Enter the 6-digit code from your app below</li>
                <li>Click Verify to complete setup</li>
              </ol>
              
              {twoFAQRCode && (
                <div className="mb-4 flex justify-center">
                  <div className="p-4 bg-white border-2 border-gray-300 rounded-lg">
                    <img src={twoFAQRCode} alt="2FA QR Code" className="w-48 h-48" />
                  </div>
                </div>
              )}
              
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={twoFAToken}
                  onChange={(e) => setTwoFAToken(e.target.value)}
                  placeholder="Enter 6-digit code"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  maxLength={6}
                />
                <button
                  onClick={handleVerify2FA}
                  disabled={loading || twoFAToken.length !== 6}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  Verify
                </button>
                <button
                  onClick={() => {
                    setShowTwoFASetup(false)
                    setTwoFAToken('')
                  }}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Delete Account */}
        <div className="bg-white rounded-lg shadow-md p-6 border-2 border-red-200">
          <h2 className="text-xl font-semibold mb-4 flex items-center text-red-600">
            <AlertTriangle className="h-5 w-5 mr-2" />
            Danger Zone
          </h2>
          
          {!showDeleteConfirm ? (
            <div>
              <p className="text-gray-600 mb-4">
                Once you delete your account, there is no going back. Please be certain.
              </p>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete My Account
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-red-50 border border-red-300 rounded-lg">
                <p className="text-red-800 font-semibold mb-2">
                  Are you absolutely sure?
                </p>
                <p className="text-sm text-red-700">
                  This action cannot be undone. This will permanently delete your account
                  and remove all of your data from our servers.
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type <span className="font-mono font-bold">DELETE MY ACCOUNT</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  className="w-full px-3 py-2 border border-red-300 rounded-md focus:ring-red-500 focus:border-red-500"
                />
              </div>
              
              <div className="flex space-x-2">
                <button
                  onClick={handleDeleteAccount}
                  disabled={loading || deleteConfirmText !== 'DELETE MY ACCOUNT'}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Account
                </button>
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false)
                    setDeleteConfirmText('')
                  }}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}