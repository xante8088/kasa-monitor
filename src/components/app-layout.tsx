'use client';

import { useState } from 'react';
import { Header } from './header';
import { DiscoveryModal } from './discovery-modal';
import { ElectricityRatesModal } from './electricity-rates-modal';
import { DeviceManagementModal } from './device-management-modal';
import { DataExportModal } from './data-export-modal';
import { useAuth } from '@/contexts/auth-context';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { getShortVersion } from '@/lib/version';

interface AppLayoutProps {
  children: React.ReactNode;
  showCostSummary?: boolean;
}

export function AppLayout({ children, showCostSummary = false }: AppLayoutProps) {
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false);
  const [showRatesModal, setShowRatesModal] = useState(false);
  const [showDeviceManagementModal, setShowDeviceManagementModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!user) {
      router.push('/login');
    }
  }, [user, router]);

  if (!user) {
    return null; // Don't render anything while redirecting
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        onDiscoverClick={() => setShowDiscoveryModal(true)}
        onRatesClick={() => setShowRatesModal(true)}
        onDeviceManagementClick={() => setShowDeviceManagementModal(true)}
        onExportClick={() => setShowExportModal(true)}
      />
      
      <main className="pb-8">
        {children}
      </main>
      
      {/* Footer with version */}
      <footer className="fixed bottom-0 right-0 p-2">
        <div className="text-xs text-gray-400">
          {getShortVersion()}
        </div>
      </footer>

      {showDiscoveryModal && (
        <DiscoveryModal
          onClose={() => setShowDiscoveryModal(false)}
        />
      )}

      {showRatesModal && (
        <ElectricityRatesModal
          onClose={() => setShowRatesModal(false)}
        />
      )}

      {showDeviceManagementModal && (
        <DeviceManagementModal
          isOpen={showDeviceManagementModal}
          onClose={() => setShowDeviceManagementModal(false)}
        />
      )}

      {showExportModal && (
        <DataExportModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  );
}