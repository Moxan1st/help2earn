'use client';

import { useState, useRef } from 'react';
import { Camera, X, Upload, Loader2 } from 'lucide-react';
import { useAccount } from 'wagmi';
import { api, Facility } from '@/services/api';
import toast from 'react-hot-toast';

interface CameraButtonProps {
  userLocation: { lat: number; lng: number } | null;
  walletAddress?: string;
  onSuccess: (facility: Facility) => void;
}

export function CameraButton({ userLocation, walletAddress, onSuccess }: CameraButtonProps) {
  const { isConnected } = useAccount();
  const [showModal, setShowModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!isConnected) {
      toast.error('Please connect your wallet first');
      return;
    }
    if (!userLocation) {
      toast.error('Unable to get your location');
      return;
    }
    setShowModal(true);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image too large (max 10MB)');
      return;
    }

    setSelectedImage(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleCapture = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleUpload = async () => {
    if (!selectedImage || !userLocation || !walletAddress) return;

    setUploading(true);
    try {
      const result = await api.uploadFacility(
        selectedImage,
        userLocation.lat,
        userLocation.lng,
        walletAddress
      );

      if (result.success && result.facility_id) {
        // Create facility object for map
        const newFacility: Facility = {
          id: result.facility_id,
          type: (result.facility_type || 'ramp') as 'ramp' | 'toilet' | 'elevator' | 'wheelchair',
          latitude: userLocation.lat,
          longitude: userLocation.lng,
          image_url: previewUrl || '',
          ai_analysis: result.condition || '',
          contributor_address: walletAddress,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        onSuccess(newFacility);
        toast.success(
          `Verified! You earned ${result.reward_amount} H2E tokens`,
          { duration: 5000 }
        );
        handleClose();
      } else {
        toast.error(result.reason || 'Verification failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    setShowModal(false);
    setSelectedImage(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  return (
    <>
      {/* Main camera button */}
      <button
        onClick={handleClick}
        className="camera-button-pulse bg-primary-600 hover:bg-primary-700 rounded-full p-5 shadow-xl transition-colors"
      >
        <Camera className="w-8 h-8 text-white" />
      </button>

      {/* Upload modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 modal-backdrop"
            onClick={handleClose}
          />

          {/* Modal content */}
          <div className="relative bg-white rounded-2xl shadow-xl max-w-sm w-full mx-4 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">Upload Facility</h2>
              <button
                onClick={handleClose}
                className="p-1 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              {/* Image preview or capture area */}
              {previewUrl ? (
                <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-gray-100 mb-4">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                  <button
                    onClick={() => {
                      setSelectedImage(null);
                      setPreviewUrl(null);
                    }}
                    className="absolute top-2 right-2 bg-black/50 rounded-full p-1"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={handleCapture}
                  className="aspect-[4/3] rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center cursor-pointer hover:border-primary-500 hover:bg-primary-50 transition-colors mb-4"
                >
                  <Camera className="w-12 h-12 text-gray-400 mb-2" />
                  <span className="text-sm text-gray-500">
                    Tap to take photo or select image
                  </span>
                </div>
              )}

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileSelect}
                className="hidden"
              />

              {/* Location info */}
              {userLocation && (
                <div className="text-sm text-gray-500 mb-4">
                  📍 Location: {userLocation.lat.toFixed(5)}, {userLocation.lng.toFixed(5)}
                </div>
              )}

              {/* Instructions */}
              <div className="bg-blue-50 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">
                  Take a clear photo of an accessibility facility (ramp, accessible toilet, elevator, or wheelchair station).
                  AI will verify and you'll receive tokens!
                </p>
              </div>

              {/* Upload button */}
              <button
                onClick={handleUpload}
                disabled={!selectedImage || uploading}
                className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload & Verify
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
