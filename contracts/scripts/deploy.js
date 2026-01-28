const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await hre.ethers.provider.getBalance(deployer.address)).toString());

  // Deploy Help2EarnToken
  console.log("\n1. Deploying Help2EarnToken...");
  const Token = await hre.ethers.getContractFactory("Help2EarnToken");
  const token = await Token.deploy(deployer.address);
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log("Help2EarnToken deployed to:", tokenAddress);

  // Deploy RewardDistributor
  console.log("\n2. Deploying RewardDistributor...");
  const Distributor = await hre.ethers.getContractFactory("RewardDistributor");
  const distributor = await Distributor.deploy(tokenAddress, deployer.address);
  await distributor.waitForDeployment();
  const distributorAddress = await distributor.getAddress();
  console.log("RewardDistributor deployed to:", distributorAddress);

  // Set distributor as minter
  console.log("\n3. Setting RewardDistributor as token minter...");
  const setMinterTx = await token.setMinter(distributorAddress);
  await setMinterTx.wait();
  console.log("Minter set successfully!");

  // Summary
  console.log("\n" + "=".repeat(50));
  console.log("DEPLOYMENT COMPLETE!");
  console.log("=".repeat(50));
  console.log("TOKEN_CONTRACT_ADDRESS=" + tokenAddress);
  console.log("DISTRIBUTOR_CONTRACT_ADDRESS=" + distributorAddress);
  console.log("=".repeat(50));
  console.log("\nUpdate your .env file with these addresses!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
