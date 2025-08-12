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
import { Header } from '@/components/header'
import { DiscoveryModal } from '@/components/discovery-modal'
import { ElectricityRatesModal } from '@/components/electricity-rates-modal'
import { DeviceManagementModal } from '@/components/device-management-modal'
import { CostSummary } from '@/components/cost-summary'

export default function Home() {
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [showDiscovery, setShowDiscovery] = useState(false)
  const [showRates, setShowRates] = useState(false)
  const [showDeviceManagement, setShowDeviceManagement] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <Header 
        onDiscoverClick={() => setShowDiscovery(true)}
        onRatesClick={() => setShowRates(true)}
        onDeviceManagementClick={() => setShowDeviceManagement(true)}
      />
      
      <main className="container mx-auto px-4 py-8">
        {selectedDevice ? (
          <DeviceDetail 
            deviceIp={selectedDevice}
            onBack={() => setSelectedDevice(null)}
          />
        ) : (
          <>
            <CostSummary />
            <DeviceGrid onDeviceSelect={setSelectedDevice} />
          </>
        )}
      </main>

      {showDiscovery && (
        <DiscoveryModal onClose={() => setShowDiscovery(false)} />
      )}
      
      {showRates && (
        <ElectricityRatesModal onClose={() => setShowRates(false)} />
      )}
      
      {showDeviceManagement && (
        <DeviceManagementModal 
          isOpen={showDeviceManagement}
          onClose={() => setShowDeviceManagement(false)} 
        />
      )}
    </div>
  )
}