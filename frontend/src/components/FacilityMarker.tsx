'use client';

import { Facility } from '@/services/api';

// Facility type icons (using SVG for better map rendering)
const FACILITY_ICONS: Record<string, JSX.Element> = {
  ramp: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z" />
    </svg>
  ),
  toilet: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M9 4v1H4v14h2v-6h12v6h2V5h-5V4c0-.55-.45-1-1-1H10c-.55 0-1 .45-1 1zm6 3H9V6h6v1z" />
    </svg>
  ),
  elevator: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 7H8.5L12 7l3.5 3H12v5h-1v-5z" />
    </svg>
  ),
  wheelchair: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M12 2c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm9 7h-6v13h-2v-6h-3v6H8V9H2V7h17v2z" />
    </svg>
  ),
};

// Facility type colors
const FACILITY_COLORS: Record<string, string> = {
  ramp: '#3B82F6',
  toilet: '#8B5CF6',
  elevator: '#F59E0B',
  wheelchair: '#10B981',
};

interface FacilityMarkerProps {
  facility: Facility;
  onClick: () => void;
}

export function FacilityMarker({ facility, onClick }: FacilityMarkerProps) {
  const color = FACILITY_COLORS[facility.type] || '#6B7280';
  const icon = FACILITY_ICONS[facility.type];

  return (
    <button
      onClick={onClick}
      className="facility-marker relative flex items-center justify-center"
      style={{
        width: '36px',
        height: '36px',
        backgroundColor: color,
        borderRadius: '50%',
        border: '2px solid white',
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        color: 'white',
        cursor: 'pointer',
        transition: 'transform 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      {icon}

      {/* Pulse animation for recent facilities */}
      {isRecent(facility.created_at) && (
        <span
          className="absolute inset-0 rounded-full animate-ping"
          style={{
            backgroundColor: color,
            opacity: 0.4,
          }}
        />
      )}
    </button>
  );
}

// Check if facility was added in the last hour
function isRecent(dateStr: string): boolean {
  const created = new Date(dateStr);
  const now = new Date();
  const hourAgo = new Date(now.getTime() - 60 * 60 * 1000);
  return created > hourAgo;
}

// Marker cluster component for when many facilities are close together
interface MarkerClusterProps {
  count: number;
  onClick: () => void;
}

export function MarkerCluster({ count, onClick }: MarkerClusterProps) {
  // Determine size based on count
  const size = count < 10 ? 40 : count < 100 ? 48 : 56;

  return (
    <button
      onClick={onClick}
      className="marker-cluster flex items-center justify-center"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: '#22c55e',
        borderRadius: '50%',
        border: '3px solid white',
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        color: 'white',
        fontWeight: 'bold',
        fontSize: count < 10 ? '14px' : count < 100 ? '12px' : '10px',
        cursor: 'pointer',
        transition: 'transform 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      {count}
    </button>
  );
}
