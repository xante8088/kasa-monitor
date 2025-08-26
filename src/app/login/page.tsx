'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/auth-context';
import { apiClient } from '@/lib/api-client';

export default function LoginPage() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    totp_code: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  // Extract URL parameters
  const returnUrl = searchParams.get('returnUrl');
  const sessionExpired = searchParams.get('sessionExpired') === 'true';
  const authRequired = searchParams.get('authRequired') === 'true';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const loginData = requires2FA 
        ? formData 
        : { username: formData.username, password: formData.password };
        
      const data = await apiClient.post('/api/auth/login', loginData, { requiresAuth: false });
      
      // Login successful
      login(data.access_token, data.user, data.refresh_token);
    } catch (err: any) {
      // Handle different types of errors
      if (err.status === 403) {
        // Check if 2FA is required
        if (err.data?.detail === '2FA verification required') {
          setRequires2FA(true);
          setError('');
        } else {
          setError(err.data?.detail || 'Login failed');
        }
      } else if (err.status === 401) {
        setError('Invalid username or password');
      } else if (err.status === 429) {
        setError('Too many login attempts. Please try again later.');
      } else {
        setError(err.message || 'Connection error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Set session messages based on URL parameters
  useEffect(() => {
    if (sessionExpired) {
      setSessionMessage('Your session has expired. Please log in again.');
    } else if (authRequired) {
      setSessionMessage('Please log in to access this feature.');
    } else if (returnUrl) {
      setSessionMessage('Please log in to continue.');
    }
  }, [sessionExpired, authRequired, returnUrl]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center bg-blue-600 rounded-lg">
            <span className="text-white text-2xl">⚡</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Kasa Monitor
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to your account
          </p>
          
          {/* Session/Auth Messages */}
          {sessionMessage && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <div className="shrink-0">
                  <svg className="h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-blue-800">{sessionMessage}</p>
                  {returnUrl && (
                    <p className="text-xs text-blue-600 mt-1">
                      You'll be redirected to {decodeURIComponent(returnUrl)} after login.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit} autoComplete="on">
          {!requires2FA ? (
            <div className="rounded-md shadow-xs -space-y-px">
              <div>
                <label htmlFor="username" className="sr-only">
                  Username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder="Username"
                  value={formData.username}
                  onChange={handleInputChange}
                />
              </div>
              <div>
                <label htmlFor="password" className="sr-only">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder="Password"
                  value={formData.password}
                  onChange={handleInputChange}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center">
                  <div className="shrink-0">
                    <svg className="h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-blue-800">
                      Two-Factor Authentication Required
                    </h3>
                    <div className="mt-1 text-sm text-blue-700">
                      Authenticating as <span className="font-semibold">{formData.username}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Enter verification code
                </label>
                <p className="text-sm text-gray-600 mb-3">
                  Enter the 6-digit code from your authenticator app
                </p>
                <input
                  id="totp_code"
                  name="totp_code"
                  type="text"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  autoFocus
                  className="block w-full px-4 py-3 text-center text-lg font-mono border border-gray-300 placeholder-gray-400 text-gray-900 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="000000"
                  value={formData.totp_code}
                  onChange={handleInputChange}
                />
              </div>
              
              <button
                type="button"
                onClick={() => {
                  setRequires2FA(false);
                  setFormData(prev => ({ ...prev, totp_code: '' }));
                  setError('');
                }}
                className="w-full text-sm text-blue-600 hover:text-blue-500"
              >
                ← Back to login
              </button>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading || (requires2FA && formData.totp_code.length !== 6)}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                {loading ? (
                  <svg className="h-5 w-5 text-blue-300 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-blue-300 group-hover:text-blue-200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                  </svg>
                )}
              </span>
              {loading ? (requires2FA ? 'Verifying...' : 'Signing in...') : (requires2FA ? 'Verify Code' : 'Sign in')}
            </button>
          </div>

          <div className="text-center">
            <Link 
              href="/setup"
              className="text-blue-600 hover:text-blue-500 text-sm"
            >
              First time setup? Create admin account
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}