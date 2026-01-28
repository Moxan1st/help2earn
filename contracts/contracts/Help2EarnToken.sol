// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title Help2EarnToken (H2E)
 * @dev ERC-20 token for Help2Earn platform rewards
 *
 * Token is minted by authorized minters (backend service) when users
 * successfully verify accessibility facilities.
 */
contract Help2EarnToken is ERC20, Ownable {
    // Address authorized to mint tokens (backend service)
    address public minter;

    // Maximum supply cap (100 million tokens)
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10**18;

    // Events
    event MinterChanged(address indexed previousMinter, address indexed newMinter);
    event TokensMinted(address indexed to, uint256 amount, string reason);

    /**
     * @dev Constructor initializes the token with name and symbol
     * @param initialOwner Address of the contract owner
     */
    constructor(address initialOwner) ERC20("Help2Earn Token", "H2E") Ownable(initialOwner) {
        minter = initialOwner;
    }

    /**
     * @dev Modifier to restrict minting to authorized minter
     */
    modifier onlyMinter() {
        require(msg.sender == minter, "Help2EarnToken: caller is not the minter");
        _;
    }

    /**
     * @dev Set a new minter address
     * @param newMinter Address of the new minter
     */
    function setMinter(address newMinter) external onlyOwner {
        require(newMinter != address(0), "Help2EarnToken: new minter is zero address");
        address oldMinter = minter;
        minter = newMinter;
        emit MinterChanged(oldMinter, newMinter);
    }

    /**
     * @dev Mint tokens to a recipient
     * @param to Recipient address
     * @param amount Amount of tokens to mint (in wei)
     */
    function mint(address to, uint256 amount) external onlyMinter {
        require(to != address(0), "Help2EarnToken: mint to zero address");
        require(totalSupply() + amount <= MAX_SUPPLY, "Help2EarnToken: max supply exceeded");
        _mint(to, amount);
        emit TokensMinted(to, amount, "facility_verification");
    }

    /**
     * @dev Mint tokens with a custom reason
     * @param to Recipient address
     * @param amount Amount of tokens to mint
     * @param reason Reason for minting (e.g., "new_facility", "facility_update")
     */
    function mintWithReason(address to, uint256 amount, string calldata reason) external onlyMinter {
        require(to != address(0), "Help2EarnToken: mint to zero address");
        require(totalSupply() + amount <= MAX_SUPPLY, "Help2EarnToken: max supply exceeded");
        _mint(to, amount);
        emit TokensMinted(to, amount, reason);
    }

    /**
     * @dev Burn tokens from caller's balance
     * @param amount Amount of tokens to burn
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }

    /**
     * @dev Get the remaining mintable supply
     * @return Amount of tokens that can still be minted
     */
    function remainingSupply() external view returns (uint256) {
        return MAX_SUPPLY - totalSupply();
    }
}
