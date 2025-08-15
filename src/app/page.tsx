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

export default function Home() {
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)

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
            <CostSummary />
            <DeviceGrid onDeviceSelect={setSelectedDevice} />
          </>
        )}
      </main>
    </AppLayout>
  )
}