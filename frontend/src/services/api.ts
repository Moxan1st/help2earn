/**
 * API service for Help2Earn backend communication
 */

import axios, { AxiosInstance } from 'axios';

// API base URL from environment or default to local
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for upload
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============ Types ============

export interface Facility {
  id: string;
  type: 'ramp' | 'toilet' | 'elevator' | 'wheelchair';
  latitude: number;
  longitude: number;
  image_url: string;
  ai_analysis?: string;
  contributor_address: string;
  distance?: number;
  created_at: string;
  updated_at: string;
}

export interface FacilityListResponse {
  facilities: Facility[];
  count: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  facility_id?: string;
  facility_type?: string;
  condition?: string;
  reward_amount?: number;
  tx_hash?: string;
  reason?: string;
}

export interface RewardRecord {
  id: string;
  facility_id: string;
  facility_type?: string;
  amount: number;
  tx_hash?: string;
  created_at: string;
}

export interface UserRewards {
  wallet_address: string;
  rewards: RewardRecord[];
  total_earned: number;
  contribution_count: number;
}

export interface HealthCheck {
  status: string;
  version: string;
  services: Record<string, boolean>;
}

// ============ API Functions ============

export const api = {
  /**
   * Check API health status
   */
  async healthCheck(): Promise<HealthCheck> {
    const response = await apiClient.get<HealthCheck>('/health');
    return response.data;
  },

  /**
   * Upload a new facility
   */
  async uploadFacility(
    image: File,
    latitude: number,
    longitude: number,
    walletAddress: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('image', image);
    formData.append('latitude', latitude.toString());
    formData.append('longitude', longitude.toString());
    formData.append('wallet_address', walletAddress);

    const response = await apiClient.post<UploadResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Get facilities near a location
   */
  async getFacilities(
    latitude: number,
    longitude: number,
    radius: number = 200,
    facilityType?: string
  ): Promise<FacilityListResponse> {
    const params: Record<string, string | number> = {
      latitude,
      longitude,
      radius,
    };

    if (facilityType) {
      params.facility_type = facilityType;
    }

    const response = await apiClient.get<FacilityListResponse>('/facilities', {
      params,
    });

    return response.data;
  },

  /**
   * Get a specific facility by ID
   */
  async getFacility(facilityId: string): Promise<Facility> {
    const response = await apiClient.get<Facility>(`/facilities/${facilityId}`);
    return response.data;
  },

  /**
   * Get rewards for a wallet address
   */
  async getRewards(walletAddress: string): Promise<UserRewards> {
    const response = await apiClient.get<UserRewards>(`/rewards/${walletAddress}`);
    return response.data;
  },

  /**
   * Get platform statistics
   */
  async getStats(): Promise<{
    total_facilities: number;
    total_rewards_distributed: number;
    unique_contributors: number;
    facilities_by_type: Record<string, number>;
  }> {
    const response = await apiClient.get('/stats');
    return response.data;
  },
};

// ============ Error Handling ============

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      const message = error.response.data?.error || error.response.data?.detail || 'Request failed';
      console.error('API Error:', message);
      throw new Error(message);
    } else if (error.request) {
      // No response received
      console.error('Network Error:', error.message);
      throw new Error('Network error. Please check your connection.');
    } else {
      // Request setup error
      console.error('Request Error:', error.message);
      throw error;
    }
  }
);

export default api;
