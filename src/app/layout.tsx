import React from 'react';
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'
import { AuthCheck } from '@/components/auth-check'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Kasa Monitor',
  description: 'Monitor and track your Kasa smart devices',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <AuthCheck>
            {children}
          </AuthCheck>
        </Providers>
      </body>
    </html>
  )
}