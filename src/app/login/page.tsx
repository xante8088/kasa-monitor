'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/auth-context';

export default function LoginPage() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    totp_code: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const loginData = requires2FA 
        ? formData 
        : { username: formData.username, password: formData.password };
        
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
      });

      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user);
      } else if (response.status === 403) {
        // Check if 2FA is required
        const errorData = await response.json();
        if (errorData.detail === '2FA verification required') {
          setRequires2FA(true);
          setError('');
        } else {
          setError(errorData.detail || 'Login failed');
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Login failed');
      }
    } catch (err) {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit} autoComplete="on">
          {!requires2FA ? (
            <div className="rounded-md shadow-sm -space-y-px">
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
                  <div className="flex-shrink-0">
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