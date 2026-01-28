// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title RewardDistributor
 * @dev Distributes H2E token rewards for verified accessibility facilities
 *
 * This contract:
 * - Records verification hashes to prevent double-claiming
 * - Distributes rewards through the H2E token contract
 * - Tracks all reward distributions for transparency
 */

interface IHelp2EarnToken {
    function mint(address to, uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
}

contract RewardDistributor is Ownable, ReentrancyGuard {
    // Token contract reference
    IHelp2EarnToken public token;

    // Authorized backend addresses
    mapping(address => bool) public authorizedCallers;

    // Verification records (location hash => verified)
    mapping(bytes32 => bool) public verificationRecords;

    // Reward configuration
    uint256 public newFacilityReward = 50 * 10**18;     // 50 tokens for new
    uint256 public updateFacilityReward = 25 * 10**18;  // 25 tokens for update

    // Statistics
    uint256 public totalDistributed;
    uint256 public totalVerifications;

    // Events
    event RewardDistributed(
        address indexed user,
        bytes32 indexed locationHash,
        uint256 amount,
        uint256 timestamp,
        string facilityType
    );

    event CallerAuthorized(address indexed caller, bool authorized);
    event RewardAmountsUpdated(uint256 newFacilityReward, uint256 updateFacilityReward);

    /**
     * @dev Constructor
     * @param _token Address of the H2E token contract
     * @param initialOwner Address of the contract owner
     */
    constructor(address _token, address initialOwner) Ownable(initialOwner) {
        require(_token != address(0), "RewardDistributor: token is zero address");
        token = IHelp2EarnToken(_token);
        authorizedCallers[initialOwner] = true;
    }

    /**
     * @dev Modifier to restrict to authorized callers
     */
    modifier onlyAuthorized() {
        require(authorizedCallers[msg.sender], "RewardDistributor: caller not authorized");
        _;
    }

    /**
     * @dev Authorize or revoke a caller
     * @param caller Address to authorize/revoke
     * @param authorized Whether to authorize or revoke
     */
    function setAuthorizedCaller(address caller, bool authorized) external onlyOwner {
        authorizedCallers[caller] = authorized;
        emit CallerAuthorized(caller, authorized);
    }

    /**
     * @dev Update reward amounts
     * @param _newFacilityReward Reward for new facilities
     * @param _updateFacilityReward Reward for facility updates
     */
    function setRewardAmounts(
        uint256 _newFacilityReward,
        uint256 _updateFacilityReward
    ) external onlyOwner {
        newFacilityReward = _newFacilityReward;
        updateFacilityReward = _updateFacilityReward;
        emit RewardAmountsUpdated(_newFacilityReward, _updateFacilityReward);
    }

    /**
     * @dev Distribute reward for a verified facility
     * @param user User's wallet address
     * @param locationHash Unique hash of the facility location
     * @param amount Reward amount (must match configured amounts)
     */
    function distributeReward(
        address user,
        bytes32 locationHash,
        uint256 amount
    ) external onlyAuthorized nonReentrant {
        require(user != address(0), "RewardDistributor: user is zero address");
        require(!verificationRecords[locationHash], "RewardDistributor: already verified");
        require(
            amount == newFacilityReward || amount == updateFacilityReward,
            "RewardDistributor: invalid reward amount"
        );

        // Mark as verified
        verificationRecords[locationHash] = true;

        // Update statistics
        totalDistributed += amount;
        totalVerifications++;

        // Mint tokens to user
        token.mint(user, amount);

        emit RewardDistributed(user, locationHash, amount, block.timestamp, "");
    }

    /**
     * @dev Distribute reward with facility type
     * @param user User's wallet address
     * @param locationHash Unique hash of the facility location
     * @param amount Reward amount
     * @param facilityType Type of facility (ramp/toilet/elevator/wheelchair)
     */
    function distributeRewardWithType(
        address user,
        bytes32 locationHash,
        uint256 amount,
        string calldata facilityType
    ) external onlyAuthorized nonReentrant {
        require(user != address(0), "RewardDistributor: user is zero address");
        require(!verificationRecords[locationHash], "RewardDistributor: already verified");
        require(
            amount == newFacilityReward || amount == updateFacilityReward,
            "RewardDistributor: invalid reward amount"
        );

        // Mark as verified
        verificationRecords[locationHash] = true;

        // Update statistics
        totalDistributed += amount;
        totalVerifications++;

        // Mint tokens to user
        token.mint(user, amount);

        emit RewardDistributed(user, locationHash, amount, block.timestamp, facilityType);
    }

    /**
     * @dev Check if a location has been verified
     * @param locationHash Hash of the location
     * @return True if already verified
     */
    function isVerified(bytes32 locationHash) external view returns (bool) {
        return verificationRecords[locationHash];
    }

    /**
     * @dev Generate location hash (for client-side verification)
     * @param lat Latitude (as integer, multiplied by 10^5)
     * @param lng Longitude (as integer, multiplied by 10^5)
     * @param facilityType Type of facility
     * @return Location hash
     */
    function generateLocationHash(
        int256 lat,
        int256 lng,
        string calldata facilityType
    ) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(lat, ":", lng, ":", facilityType));
    }

    /**
     * @dev Get contract statistics
     * @return _totalDistributed Total tokens distributed
     * @return _totalVerifications Total number of verifications
     * @return _newReward Current new facility reward
     * @return _updateReward Current update facility reward
     */
    function getStats() external view returns (
        uint256 _totalDistributed,
        uint256 _totalVerifications,
        uint256 _newReward,
        uint256 _updateReward
    ) {
        return (
            totalDistributed,
            totalVerifications,
            newFacilityReward,
            updateFacilityReward
        );
    }

    /**
     * @dev Update token contract address (emergency use only)
     * @param _token New token contract address
     */
    function setTokenContract(address _token) external onlyOwner {
        require(_token != address(0), "RewardDistributor: token is zero address");
        token = IHelp2EarnToken(_token);
    }
}
