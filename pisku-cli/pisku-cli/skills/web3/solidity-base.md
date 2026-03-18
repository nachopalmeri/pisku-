# Solidity + Base Network — Smart Contract Patterns

## Purpose
Context for writing and deploying smart contracts on Base (Coinbase L2, EVM-compatible). Use when project involves Solidity contracts, Hardhat/Foundry, or Web3 interactions.

## Base Network Info
- Mainnet RPC: `https://mainnet.base.org`
- Testnet (Sepolia): `https://sepolia.base.org`
- Chain ID Mainnet: 8453
- Chain ID Testnet: 84532
- Block explorer: https://basescan.org
- Native token: ETH

## Contract Structure (Hardhat)
```
contracts/
├── MyContract.sol
├── interfaces/IMyContract.sol
└── libraries/MyLib.sol
hardhat.config.ts
scripts/deploy.ts
test/MyContract.test.ts
```

## Solidity Patterns
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract MyContract is Ownable, ReentrancyGuard {
    // Events first
    event Deposited(address indexed user, uint256 amount);
    
    // State variables
    mapping(address => uint256) private _balances;
    
    // Modifiers
    modifier validAmount(uint256 amount) {
        require(amount > 0, "Amount must be positive");
        _;
    }
    
    constructor(address initialOwner) Ownable(initialOwner) {}
    
    // External > Public for gas efficiency
    function deposit() external payable nonReentrant validAmount(msg.value) {
        _balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }
    
    function withdraw(uint256 amount) external nonReentrant {
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        _balances[msg.sender] -= amount;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
```

## Security Checklist
- ✅ ReentrancyGuard on state-changing payable functions
- ✅ Check-Effects-Interactions pattern
- ✅ Use `call()` not `transfer()` for ETH sends
- ✅ Validate all inputs with `require()`
- ✅ Events for all state changes
- ❌ Never use `tx.origin` for auth (use `msg.sender`)
- ❌ Never use `block.timestamp` for randomness

## Hardhat Config for Base
```typescript
import { HardhatUserConfig } from "hardhat/config";

const config: HardhatUserConfig = {
  solidity: "0.8.20",
  networks: {
    base: {
      url: "https://mainnet.base.org",
      accounts: [process.env.PRIVATE_KEY!],
      chainId: 8453,
    },
    "base-sepolia": {
      url: "https://sepolia.base.org",
      accounts: [process.env.PRIVATE_KEY!],
      chainId: 84532,
    },
  },
  etherscan: {
    apiKey: { base: process.env.BASESCAN_API_KEY! },
    customChains: [{ network: "base", chainId: 8453, urls: { apiURL: "https://api.basescan.org/api", browserURL: "https://basescan.org" } }],
  },
};
export default config;
```

## Deploy Script
```typescript
import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  const Contract = await ethers.getContractFactory("MyContract");
  const contract = await Contract.deploy(deployer.address);
  await contract.waitForDeployment();
  console.log("Deployed to:", await contract.getAddress());
}
main().catch(console.error);
```

## ethers.js v6 Patterns (Frontend)
```typescript
const provider = new ethers.BrowserProvider(window.ethereum);
const signer = await provider.getSigner();
const contract = new ethers.Contract(ADDRESS, ABI, signer);
const tx = await contract.deposit({ value: ethers.parseEther("0.01") });
await tx.wait();
```
