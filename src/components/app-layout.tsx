'use client';

import { useState } from 'react';
import { Header } from './header';
import { DiscoveryModal } from './discovery-modal';
import { ElectricityRatesModal } from './electricity-rates-modal';
import { DeviceManagementModal } from './device-management-modal';
import { useAuth } from '@/contexts/auth-context';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface AppLayoutProps {
  children: React.ReactNode;
  showCostSummary?: boolean;
}

export function AppLayout({ children, showCostSummary = false }: AppLayoutProps) {
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false);
  const [showRatesModal, setShowRatesModal] = useState(false);
  const [showDeviceManagementModal, setShowDeviceManagementModal] = useState(false);
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
      />
      
      <main className="pb-8">
        {children}
      </main>

      {showDiscoveryModal && (
        <DiscoveryModal
          isOpen={showDiscoveryModal}
          onClose={() => setShowDiscoveryModal(false)}
        />
      )}

      {showRatesModal && (
        <ElectricityRatesModal
          isOpen={showRatesModal}
          onClose={() => setShowRatesModal(false)}
        />
      )}

      {showDeviceManagementModal && (
        <DeviceManagementModal
          isOpen={showDeviceManagementModal}
          onClose={() => setShowDeviceManagementModal(false)}
        />
      )}
    </div>
  );
}