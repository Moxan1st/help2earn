'use client';

import { useState } from 'react';
import { X, MapPin, Clock, User } from 'lucide-react';
import { Facility } from '@/services/api';

// Parse AI analysis JSON
const parseAiAnalysis = (analysis: string | undefined): { condition?: string; details?: string } => {
  if (!analysis) return {};
  try {
    const parsed = JSON.parse(analysis);
    return {
      condition: parsed.condition,
      details: parsed.details ? JSON.stringify(parsed.details, null, 2) : undefined
    };
  } catch {
    return { condition: analysis };
  }
};

// Facility type display names
const FACILITY_NAMES: Record<string, { en: string; zh: string }> = {
  ramp: { en: 'Wheelchair Ramp', zh: '无障碍坡道' },
  toilet: { en: 'Accessible Toilet', zh: '无障碍厕所' },
  elevator: { en: 'Accessible Elevator', zh: '无障碍电梯' },
  wheelchair: { en: 'Wheelchair Station', zh: '轮椅借用处' },
};

// Facility type colors
const FACILITY_COLORS: Record<string, string> = {
  ramp: 'bg-blue-500',
  toilet: 'bg-purple-500',
  elevator: 'bg-amber-500',
  wheelchair: 'bg-emerald-500',
};

interface FacilityDetailProps {
  facility: Facility;
  onClose: () => void;
}

export function FacilityDetail({ facility, onClose }: FacilityDetailProps) {
  const [imageError, setImageError] = useState(false);
  const facilityName = FACILITY_NAMES[facility.type] || { en: 'Unknown', zh: '未知' };
  const facilityColor = FACILITY_COLORS[facility.type] || 'bg-gray-500';
  const aiAnalysis = parseAiAnalysis(facility.ai_analysis);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 modal-backdrop"
        onClick={onClose}
      />

      {/* Modal content */}
      <div className="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md sm:mx-4 max-h-[80vh] overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 bg-black/30 hover:bg-black/50 rounded-full p-1 transition-colors"
        >
          <X className="w-5 h-5 text-white" />
        </button>

        {/* Image */}
        <div className="relative aspect-video bg-gray-200">
          {facility.image_url && !imageError ? (
            <img
              src={facility.image_url}
              alt={facilityName.en}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              {imageError ? 'Failed to load image' : 'No image available'}
            </div>
          )}

          {/* Type badge */}
          <div className={`absolute bottom-3 left-3 ${facilityColor} text-white px-3 py-1 rounded-full text-sm font-medium`}>
            {facilityName.zh}
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Title */}
          <h2 className="text-xl font-bold">{facilityName.en}</h2>

          {/* AI Analysis */}
          {aiAnalysis.condition && (
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs font-medium text-gray-500 mb-1">AI Analysis</div>
              <p className="text-sm text-gray-700">{aiAnalysis.condition}</p>
            </div>
          )}

          {/* Details */}
          <div className="space-y-2">
            {/* Location */}
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MapPin className="w-4 h-4" />
              <span>
                {facility.latitude.toFixed(5)}, {facility.longitude.toFixed(5)}
              </span>
            </div>

            {/* Date */}
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Clock className="w-4 h-4" />
              <span>Added {formatDate(facility.created_at)}</span>
            </div>

            {/* Contributor */}
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <User className="w-4 h-4" />
              <span>Contributor: {formatAddress(facility.contributor_address)}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={() => {
                // Open in Google Maps
                const url = `https://www.google.com/maps/search/?api=1&query=${facility.latitude},${facility.longitude}`;
                window.open(url, '_blank');
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg transition-colors"
            >
              Navigate
            </button>
            <button
              onClick={onClose}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
