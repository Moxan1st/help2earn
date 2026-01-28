'use client';

import { useEffect, useRef, useState } from 'react';
import { Facility } from '@/services/api';

// Facility type colors
const FACILITY_COLORS: Record<string, string> = {
  ramp: '#3B82F6',
  toilet: '#8B5CF6',
  elevator: '#F59E0B',
  wheelchair: '#10B981',
};

// Facility type icons (emoji)
const FACILITY_ICONS: Record<string, string> = {
  ramp: '♿',
  toilet: '🚻',
  elevator: '🛗',
  wheelchair: '🦽',
};

interface MapProps {
  center: { lat: number; lng: number };
  facilities: Facility[];
  onFacilityClick: (facility: Facility) => void;
}

export default function Map({ center, facilities, onFacilityClick }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const radiusCircleRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [leaflet, setLeaflet] = useState<any>(null);

  // Load Leaflet dynamically
  useEffect(() => {
    const loadLeaflet = async () => {
      const L = (await import('leaflet')).default;
      await import('leaflet/dist/leaflet.css');
      setLeaflet(L);
    };
    loadLeaflet();
  }, []);

  // Initialize map when Leaflet is loaded
  useEffect(() => {
    if (!leaflet || !mapContainer.current || mapRef.current) return;

    const L = leaflet;

    // Create map
    const map = L.map(mapContainer.current, {
      center: [center.lat, center.lng],
      zoom: 16,
      zoomControl: false,
    });
    mapRef.current = map;

    // Add zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(map);

    // Add 200m radius circle
    radiusCircleRef.current = L.circle([center.lat, center.lng], {
      radius: 200,
      color: '#22c55e',
      fillColor: '#22c55e',
      fillOpacity: 0.1,
      weight: 2,
      dashArray: '5, 5',
    }).addTo(map);

    // Add user location marker
    const userIcon = L.divIcon({
      className: 'user-location-marker',
      html: `<div style="
        width: 16px;
        height: 16px;
        background-color: #3B82F6;
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      "></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
    userMarkerRef.current = L.marker([center.lat, center.lng], { icon: userIcon }).addTo(map);

    // Try to get user's real location
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          map.setView([latitude, longitude], 16);
          userMarkerRef.current?.setLatLng([latitude, longitude]);
          radiusCircleRef.current?.setLatLng([latitude, longitude]);
        },
        (error) => {
          console.log('Geolocation error:', error.message);
        },
        { enableHighAccuracy: true }
      );
    }

    setMapLoaded(true);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [leaflet]);

  // Update center
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;

    mapRef.current.setView([center.lat, center.lng], 16);
    userMarkerRef.current?.setLatLng([center.lat, center.lng]);
    radiusCircleRef.current?.setLatLng([center.lat, center.lng]);
  }, [center, mapLoaded]);

  // Update facility markers
  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !leaflet) return;

    const L = leaflet;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Add new markers
    facilities.forEach((facility) => {
      const color = FACILITY_COLORS[facility.type] || '#6B7280';
      const icon = FACILITY_ICONS[facility.type] || '📍';

      const divIcon = L.divIcon({
        className: 'facility-marker',
        html: `<div style="
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background-color: ${color};
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          border: 2px solid white;
          cursor: pointer;
        ">${icon}</div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });

      const marker = L.marker([facility.latitude, facility.longitude], { icon: divIcon })
        .addTo(mapRef.current)
        .on('click', () => {
          onFacilityClick(facility);
        });

      markersRef.current.push(marker);
    });
  }, [facilities, mapLoaded, leaflet, onFacilityClick]);

  return (
    <div ref={mapContainer} className="w-full h-full" />
  );
}
