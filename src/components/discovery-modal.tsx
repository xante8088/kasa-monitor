'use client'

import { useState } from 'react'
import { X, Search, User, Lock } from 'lucide-react'
import axios from 'axios'
import { useQueryClient } from '@tanstack/react-query'

interface DiscoveryModalProps {
  onClose: () => void
}

export function DiscoveryModal({ onClose }: DiscoveryModalProps) {
  const [discovering, setDiscovering] = useState(false)
  const [useAuth, setUseAuth] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const handleDiscover = async () => {
    setDiscovering(true)
    setResult(null)
    
    try {
      const credentials = useAuth && username && password 
        ? { username, password }
        : undefined
      
      // Get auth token from localStorage
      const token = localStorage.getItem('token')
      
      const response = await axios.post('/api/discover', credentials, {
        headers: {
          Authorization: token ? `Bearer ${token}` : ''
        }
      })
      const count = response.data.discovered
      
      setResult(`Successfully discovered ${count} device${count !== 1 ? 's' : ''}!`)
      
      // Invalidate devices query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      
      // Auto-close after success
      setTimeout(onClose, 2000)
    } catch (error) {
      setResult('Failed to discover devices. Please check your network connection.')
    } finally {
      setDiscovering(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Discover Kasa Devices</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="space-y-4">
          <p className="text-gray-600">
            Search for Kasa smart devices on your network. This may take a few seconds.
          </p>

          <div className="space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={useAuth}
                onChange={(e) => setUseAuth(e.target.checked)}
                className="rounded"
              />
              <span>Use TP-Link Cloud credentials</span>
            </label>

            {useAuth && (
              <div className="space-y-3 pl-6">
                <div>
                  <label className="flex items-center space-x-2 text-sm text-gray-600 mb-1">
                    <User className="h-4 w-4" />
                    <span>Username</span>
                  </label>
                  <input
                    type="email"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                  />
                </div>
                
                <div>
                  <label className="flex items-center space-x-2 text-sm text-gray-600 mb-1">
                    <Lock className="h-4 w-4" />
                    <span>Password</span>
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                  />
                </div>
              </div>
            )}
          </div>

          {result && (
            <div className={`p-3 rounded-lg ${
              result.includes('Successfully') 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'
            }`}>
              {result}
            </div>
          )}

          <button
            onClick={handleDiscover}
            disabled={discovering}
            className={`
              w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg
              font-medium transition-colors
              ${discovering 
                ? 'bg-gray-300 cursor-not-allowed' 
                : 'bg-kasa-primary hover:bg-kasa-secondary text-white'}
            `}
          >
            <Search className="h-5 w-5" />
            <span>{discovering ? 'Discovering...' : 'Discover Devices'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}