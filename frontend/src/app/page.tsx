'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useAccount } from 'wagmi';
import { WalletButton } from '@/components/WalletButton';
import { CameraButton } from '@/components/CameraButton';
import { FacilityDetail } from '@/components/FacilityDetail';
import { RewardsPanel } from '@/components/RewardsPanel';
import { api, Facility } from '@/services/api';
import { MapPin, Trophy, Info } from 'lucide-react';
import toast from 'react-hot-toast';

// Dynamically import Map component to avoid SSR issues with Mapbox
const Map = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-100">
      <div className="text-gray-500">Loading map...</div>
    </div>
  ),
});

export default function Home() {
  const { address, isConnected } = useAccount();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [showRewards, setShowRewards] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [loading, setLoading] = useState(false);

  // Get user location on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => {
          console.error('Geolocation error:', error);
          // Default to a central location (Shanghai)
          setUserLocation({ lat: 31.2304, lng: 121.4737 });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        }
      );
    }
  }, []);

  // Fetch facilities when location changes
  useEffect(() => {
    if (userLocation) {
      fetchFacilities();
    }
  }, [userLocation]);

  const fetchFacilities = async () => {
    if (!userLocation) return;

    setLoading(true);
    try {
      const data = await api.getFacilities(userLocation.lat, userLocation.lng, 500);
      setFacilities(data.facilities);
    } catch (error) {
      console.error('Failed to fetch facilities:', error);
      toast.error('Failed to load nearby facilities');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = (facility: Facility) => {
    setFacilities((prev) => [facility, ...prev]);
    toast.success('Facility verified! Reward sent to your wallet.');
  };

  const handleFacilityClick = (facility: Facility) => {
    setSelectedFacility(facility);
  };

  return (
    <main className="relative w-full h-screen overflow-hidden">
      {/* Map takes full screen */}
      <div className="absolute inset-0">
        {userLocation && (
          <Map
            center={userLocation}
            facilities={facilities}
            onFacilityClick={handleFacilityClick}
          />
        )}
      </div>

      {/* Header overlay */}
      <header className="absolute top-0 left-0 right-0 z-[100] p-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2 bg-white/90 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg">
            <MapPin className="w-5 h-5 text-primary-600" />
            <span className="font-bold text-gray-800">Help2Earn</span>
          </div>

          {/* Wallet Button */}
          <WalletButton />
        </div>
      </header>

      {/* Bottom action bar */}
      <div className="absolute bottom-0 left-0 right-0 z-[100] p-4 pb-8">
        <div className="flex items-center justify-center gap-4">
          {/* Rewards button */}
          {isConnected && (
            <button
              onClick={() => setShowRewards(true)}
              className="bg-white/90 backdrop-blur-sm rounded-full p-3 shadow-lg hover:bg-white transition-colors"
            >
              <Trophy className="w-6 h-6 text-amber-500" />
            </button>
          )}

          {/* Camera button (main action) */}
          <CameraButton
            userLocation={userLocation}
            walletAddress={address}
            onSuccess={handleUploadSuccess}
          />

          {/* Info button */}
          <button
            onClick={() => toast('Help2Earn: Upload accessibility facility photos to earn tokens!')}
            className="bg-white/90 backdrop-blur-sm rounded-full p-3 shadow-lg hover:bg-white transition-colors"
          >
            <Info className="w-6 h-6 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Facility type legend */}
      <div className="absolute bottom-28 left-4 z-[100] bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-lg">
        <div className="text-xs font-medium text-gray-500 mb-2">Facility Types</div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <div className="w-5 h-5 rounded-full bg-[#3B82F6] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="white">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z" />
              </svg>
            </div>
            <span>Ramp 坡道</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <div className="w-5 h-5 rounded-full bg-[#8B5CF6] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="white">
                <path d="M9 4v1H4v14h2v-6h12v6h2V5h-5V4c0-.55-.45-1-1-1H10c-.55 0-1 .45-1 1zm6 3H9V6h6v1z" />
              </svg>
            </div>
            <span>Toilet 无障碍厕所</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <div className="w-5 h-5 rounded-full bg-[#F59E0B] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="white">
                <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 7H8.5L12 7l3.5 3H12v5h-1v-5z" />
              </svg>
            </div>
            <span>Elevator 电梯</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <div className="w-5 h-5 rounded-full bg-[#10B981] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="white">
                <path d="M12 2c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm9 7h-6v13h-2v-6h-3v6H8V9H2V7h17v2z" />
              </svg>
            </div>
            <span>Wheelchair 轮椅</span>
          </div>
        </div>
      </div>

      {/* Facility detail modal */}
      {selectedFacility && (
        <FacilityDetail
          facility={selectedFacility}
          onClose={() => setSelectedFacility(null)}
        />
      )}

      {/* Rewards panel */}
      {showRewards && address && (
        <RewardsPanel
          walletAddress={address}
          onClose={() => setShowRewards(false)}
        />
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 z-[200] bg-black/20 flex items-center justify-center">
          <div className="bg-white rounded-lg p-4 shadow-xl">
            <div className="spinner w-8 h-8 border-primary-600" />
          </div>
        </div>
      )}
    </main>
  );
}
