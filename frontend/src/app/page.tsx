'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useAccount } from 'wagmi';
import { WalletButton } from '@/components/WalletButton';
import { CameraButton } from '@/components/CameraButton';
import { FacilityDetail } from '@/components/FacilityDetail';
import { RewardsPanel } from '@/components/RewardsPanel';
import { api, Facility } from '@/services/api';
import { MapPin, Trophy, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import { RampIcon, ToiletIcon, ElevatorIcon, WheelchairIcon } from '@/icons';

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

  const fetchFacilities = async (lat?: number, lng?: number, radius?: number) => {
    const queryLat = lat ?? userLocation?.lat;
    const queryLng = lng ?? userLocation?.lng;
    if (!queryLat || !queryLng) return;

    setLoading(true);
    try {
      // Use provided radius or default 500m, cap at 5000m (API limit)
      const queryRadius = Math.min(radius ?? 500, 5000);
      const data = await api.getFacilities(queryLat, queryLng, queryRadius);
      setFacilities(data.facilities);
    } catch (error) {
      console.error('Failed to fetch facilities:', error);
      toast.error('Failed to load nearby facilities');
    } finally {
      setLoading(false);
    }
  };

  // Debounce timer for view changes
  const viewChangeTimer = useRef<NodeJS.Timeout | null>(null);

  // Handle map view changes (pan/zoom) with debounce
  const handleViewChange = useCallback((newCenter: { lat: number; lng: number }, radius: number) => {
    // Clear previous timer
    if (viewChangeTimer.current) {
      clearTimeout(viewChangeTimer.current);
    }
    // Debounce: wait 500ms after last view change before fetching
    viewChangeTimer.current = setTimeout(() => {
      fetchFacilities(newCenter.lat, newCenter.lng, radius);
    }, 500);
  }, []);

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
            onViewChange={handleViewChange}
          />
        )}
      </div>

      {/* Header overlay */}
      <header className="absolute top-0 left-0 right-0 z-[100] p-4">
        <div className="flex items-start justify-between">
          {/* Left side: Logo + Facility Types */}
          <div className="flex flex-col gap-2">
            {/* Logo */}
            <div className="flex items-center gap-2 bg-white/90 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg">
              <MapPin className="w-5 h-5 text-primary-600" />
              <span className="font-semibold text-sm text-gray-800">Help2Earn</span>
            </div>

            {/* Facility type legend */}
            <div className="bg-white/90 backdrop-blur-sm rounded-xl p-3 shadow-lg">
              <div className="text-sm font-semibold text-gray-800 mb-2">Facility Types</div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <div className="w-6 h-6 rounded-full bg-[#3B82F6] flex items-center justify-center">
                    <RampIcon className="w-4 h-4" fill="white" />
                  </div>
                  <span>Ramp 坡道</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <div className="w-6 h-6 rounded-full bg-[#8B5CF6] flex items-center justify-center">
                    <ToiletIcon className="w-4 h-4" fill="white" />
                  </div>
                  <span>Toilet 无障碍厕所</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <div className="w-6 h-6 rounded-full bg-[#F59E0B] flex items-center justify-center">
                    <ElevatorIcon className="w-4 h-4" fill="white" />
                  </div>
                  <span>Elevator 电梯</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <div className="w-6 h-6 rounded-full bg-[#10B981] flex items-center justify-center">
                    <WheelchairIcon className="w-4 h-4" fill="white" />
                  </div>
                  <span>Wheelchair 轮椅</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right side: Wallet + Rewards */}
          <div className="flex flex-col items-end gap-2">
            <WalletButton />
            {isConnected && (
              <button
                onClick={() => setShowRewards(true)}
                className="flex items-center gap-2 bg-white/90 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg hover:bg-white transition-colors"
              >
                <Trophy className="w-4 h-4 text-amber-500" />
                <span className="font-semibold text-sm text-gray-800">My Rewards</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Bottom action bar */}
      <div className="absolute bottom-0 left-0 right-0 z-[100] p-4 pb-8">
        <div className="flex items-center justify-center gap-4">
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
