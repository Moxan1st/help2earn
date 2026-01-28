'use client';

import { useState, useEffect } from 'react';
import { X, Trophy, ExternalLink, Loader2 } from 'lucide-react';
import { api, UserRewards, RewardRecord } from '@/services/api';

// Facility type colors
const FACILITY_COLORS: Record<string, string> = {
  ramp: 'bg-blue-500',
  toilet: 'bg-purple-500',
  elevator: 'bg-amber-500',
  wheelchair: 'bg-emerald-500',
};

interface RewardsPanelProps {
  walletAddress: string;
  onClose: () => void;
}

export function RewardsPanel({ walletAddress, onClose }: RewardsPanelProps) {
  const [rewards, setRewards] = useState<UserRewards | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRewards();
  }, [walletAddress]);

  const fetchRewards = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRewards(walletAddress);
      setRewards(data);
    } catch (err) {
      console.error('Failed to fetch rewards:', err);
      setError('Failed to load rewards');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const shortenTxHash = (hash: string) => {
    return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 modal-backdrop"
        onClick={onClose}
      />

      {/* Panel content */}
      <div className="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md sm:mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold">My Rewards</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 px-4">
              <p className="text-gray-500 mb-4">{error}</p>
              <button
                onClick={fetchRewards}
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg"
              >
                Retry
              </button>
            </div>
          ) : rewards ? (
            <>
              {/* Summary */}
              <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500">Total Earned</div>
                    <div className="text-2xl font-bold text-amber-600">
                      {rewards.total_earned} <span className="text-sm">H2E</span>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500">Contributions</div>
                    <div className="text-2xl font-bold text-primary-600">
                      {rewards.contribution_count}
                    </div>
                  </div>
                </div>
              </div>

              {/* Rewards list */}
              <div className="p-4">
                <h3 className="text-sm font-medium text-gray-500 mb-3">
                  Recent Rewards
                </h3>

                {rewards.rewards.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No rewards yet. Upload accessibility facilities to earn tokens!
                  </div>
                ) : (
                  <div className="space-y-3">
                    {rewards.rewards.map((reward: RewardRecord) => (
                      <div
                        key={reward.id}
                        className="bg-gray-50 rounded-lg p-3 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-10 h-10 rounded-full ${
                              FACILITY_COLORS[reward.facility_type || 'ramp']
                            } flex items-center justify-center text-white font-bold`}
                          >
                            +{reward.amount}
                          </div>
                          <div>
                            <div className="font-medium text-sm">
                              {reward.facility_type
                                ? reward.facility_type.charAt(0).toUpperCase() +
                                  reward.facility_type.slice(1)
                                : 'Facility'}{' '}
                              Verified
                            </div>
                            <div className="text-xs text-gray-500">
                              {formatDate(reward.created_at)}
                            </div>
                          </div>
                        </div>

                        {reward.tx_hash && (
                          <a
                            href={`https://sepolia.etherscan.io/tx/${reward.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 p-1"
                            title="View transaction"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <div className="text-xs text-gray-500 text-center">
            H2E tokens are on Sepolia testnet
          </div>
        </div>
      </div>
    </div>
  );
}
