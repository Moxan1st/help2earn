'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';

export function WalletButton() {
  return (
    <ConnectButton.Custom>
      {({
        account,
        chain,
        openAccountModal,
        openChainModal,
        openConnectModal,
        mounted,
      }) => {
        const ready = mounted;
        const connected = ready && account && chain;

        return (
          <div
            {...(!ready && {
              'aria-hidden': true,
              style: {
                opacity: 0,
                pointerEvents: 'none',
                userSelect: 'none',
              },
            })}
          >
            {(() => {
              if (!connected) {
                return (
                  <button
                    onClick={openConnectModal}
                    className="bg-primary-600 hover:bg-primary-700 text-white font-semibold text-sm px-4 py-2 rounded-full shadow-lg transition-colors"
                  >
                    Connect Wallet
                  </button>
                );
              }

              if (chain.unsupported) {
                return (
                  <button
                    onClick={openChainModal}
                    className="bg-red-500 hover:bg-red-600 text-white font-semibold text-sm px-4 py-2 rounded-full shadow-lg transition-colors"
                  >
                    Wrong Network
                  </button>
                );
              }

              return (
                <button
                  onClick={openAccountModal}
                  className="bg-white/90 backdrop-blur-sm hover:bg-white text-gray-800 font-semibold text-sm px-4 py-2 rounded-full shadow-lg transition-colors flex items-center gap-2"
                >
                  {chain.hasIcon && chain.iconUrl && (
                    <img
                      src={chain.iconUrl}
                      alt={chain.name ?? 'Chain'}
                      className="w-4 h-4 rounded-full"
                    />
                  )}
                  <span className="hidden sm:inline">
                    {account.displayName}
                  </span>
                  <span className="sm:hidden">
                    {account.address.slice(0, 6)}...{account.address.slice(-4)}
                  </span>
                </button>
              );
            })()}
          </div>
        );
      }}
    </ConnectButton.Custom>
  );
}
