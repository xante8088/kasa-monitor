/**
 * Kasa Monitor - Main Application Page
 * Copyright (C) 2025 Kasa Monitor Contributors
 *
 * This file is part of Kasa Monitor.
 *
 * Kasa Monitor is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Kasa Monitor is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
 */

'use client'

import { useState } from 'react'
import { DeviceGrid } from '@/components/device-grid'
import { DeviceDetail } from '@/components/device-detail'
import { CostSummary } from '@/components/cost-summary'
import { AppLayout } from '@/components/app-layout'
import { PrimaryExportButton } from '@/components/export-button'
import { DataExportModal } from '@/components/data-export-modal'
import { useAuth } from '@/contexts/auth-context'

export default function Home() {
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [showExportModal, setShowExportModal] = useState(false)
  const { hasPermission } = useAuth()

  return (
    <AppLayout showCostSummary={true}>
      <main className="container mx-auto px-4 py-8">
        {selectedDevice ? (
          <DeviceDetail 
            deviceIp={selectedDevice}
            onBack={() => setSelectedDevice(null)}
          />
        ) : (
          <>
            <div className="flex justify-between items-center mb-6">
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              {hasPermission('data.export') && (
                <PrimaryExportButton
                  onClick={() => setShowExportModal(true)}
                  size="lg"
                />
              )}
            </div>
            <CostSummary />
            <DeviceGrid onDeviceSelect={setSelectedDevice} />
          </>
        )}
      </main>
      
      {showExportModal && (
        <DataExportModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </AppLayout>
  )
}