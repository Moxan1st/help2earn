const hre = require("hardhat");

async function main() {
  const tokenAddress = "0x491c88aBE3FE07dFD13e379dE44D427bA94CE4C9";
  const distributorAddress = "0xDf929aD0C7f32B9E3cce6B86dEaD2ff1522EF0A4";

  console.log("Setting RewardDistributor as token minter...");

  const Token = await hre.ethers.getContractFactory("Help2EarnToken");
  const token = Token.attach(tokenAddress);

  // Check current minter
  const currentMinter = await token.minter();
  console.log("Current minter:", currentMinter);

  if (currentMinter.toLowerCase() === distributorAddress.toLowerCase()) {
    console.log("Minter already set correctly!");
    return;
  }

  // Set new minter
  const tx = await token.setMinter(distributorAddress);
  console.log("Transaction hash:", tx.hash);
  await tx.wait();
  console.log("Minter set successfully!");

  // Verify
  const newMinter = await token.minter();
  console.log("New minter:", newMinter);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
