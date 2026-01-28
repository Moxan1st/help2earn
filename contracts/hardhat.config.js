require("@nomicfoundation/hardhat-toolbox");

const SEPOLIA_RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/fkVlNh_pydNsyP9cKFg39";
const PRIVATE_KEY = "362ed7fab66af581bda007a87ccfc69c0f43a9b7c8654ed813d9a176cffcd034";

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    sepolia: {
      url: SEPOLIA_RPC_URL,
      accounts: [PRIVATE_KEY],
      chainId: 11155111
    }
  }
};
