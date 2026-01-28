# Help2Earn 技术方案设计

## 项目概述
Help2Earn 是一个基于 DePIN 的无障碍设施数据收集平台。用户通过拍照上传无障碍设施获得代币奖励，同时为轮椅使用者等群体提供精准的无障碍信息服务。

**黑客松要求**：项目基于 SpoonOS 构建，使用 React Agent 承担核心业务功能。

---

## 技术选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | Next.js 14 + PWA | SSR + 离线支持，可添加到手机主屏 |
| 地图 | Mapbox GL JS | 支持自定义图标、聚合、中国地图 |
| 后端 | **FastAPI + SpoonOS** | Python 后端，深度集成 SpoonOS |
| Agent | **SpoonOS React Agent** | 核心业务流程由 Agent 驱动 |
| 数据库 | PostgreSQL + PostGIS | 支持地理位置查询 |
| AI验证 | Gemini Vision (通过 SpoonOS) | 多模态图片识别 |
| 区块链 | Ethereum Sepolia (测试网) | ERC-20 代币 + 智能合约 |
| 钱包 | wagmi + viem + RainbowKit | 前端钱包连接 |
| 存储 | Cloudflare R2 / AWS S3 | 图片存储 |

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户设备 (Next.js PWA)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 地图视图  │  │ 拍照上传  │  │ 设施详情  │  │ 钱包 (RainbowKit)│ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FastAPI + SpoonOS 后端 (核心)                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              SpoonOS React Agent (核心驱动)                 │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │ │
│  │  │ Vision Skill │ │ Database Skill│ │ Blockchain Skill  │  │ │
│  │  │ 图片识别验证  │ │ 设施数据CRUD  │ │ 代币发放/查询     │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              Anti-Fraud Skill (防刷检测)              │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ POST /upload │  │ GET /facilities│ │ GET /rewards          │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│  Gemini Vision   │ │ PostgreSQL+PostGIS│ │  Ethereum Sepolia    │
│  (SpoonOS 调用)   │ │ 设施数据存储       │ │  ERC-20 代币合约     │
└──────────────────┘ └──────────────────┘ └──────────────────────┘
```

---

## 核心模块设计

### 1. SpoonOS React Agent (核心 - 满足黑客松要求)

```python
# backend/agent/help2earn_agent.py
from spoon_ai.agents import SpoonReactSkill
from spoon_ai.chat import ChatBot

class Help2EarnAgent:
    """
    核心 React Agent，承担完整业务流程：
    - 图片验证 (Vision Skill)
    - 防刷检测 (Anti-Fraud Skill)
    - 数据库操作 (Database Skill)
    - 代币发放 (Blockchain Skill)
    """

    def __init__(self):
        self.agent = SpoonReactSkill(
            llm=ChatBot(llm_provider="google", model_name="gemini-pro-vision"),
            skill_paths=[
                "./skills/vision",      # 图片识别
                "./skills/database",    # 数据库操作
                "./skills/blockchain",  # 区块链交易
                "./skills/anti_fraud"   # 防刷检测
            ],
            scripts_enabled=True
        )

    async def process_upload(self, image: bytes, lat: float, lng: float, wallet: str):
        """Agent 自主完成整个上传验证流程"""
        result = await self.agent.run(f"""
        你是 Help2Earn 的验证 Agent，请按以下步骤处理用户上传：

        1. [Vision] 分析图片，判断是否为无障碍设施
           - 如果不是 → 返回 {{"success": false, "reason": "非无障碍设施"}}
           - 如果是 → 识别类型(ramp/toilet/elevator/wheelchair)和状况

        2. [Anti-Fraud] 检查坐标 ({lat}, {lng}) 的同类型设施记录
           - 15天内有记录 → 返回 {{"success": false, "reason": "重复提交"}}
           - 15天前有记录 → 标记为"更新"，奖励 25 Token
           - 无记录 → 标记为"新增"，奖励 50 Token

        3. [Database] 存储设施数据到数据库

        4. [Blockchain] 向钱包 {wallet} 发放代币奖励

        5. 返回完整结果
        """, image=image)

        return result
```

**为什么满足黑客松要求**：
- ✅ 基于 SpoonOS 构建（使用 SpoonReactSkill）
- ✅ 使用 React Agent 体系
- ✅ Agent 承担核心功能（验证、防刷、存储、发币全流程）
- ✅ 非边缘调用，是业务核心驱动

---

### 2. Skills 定义 (Agent 的能力模块)

#### 2.1 Vision Skill (图片识别)
```python
# backend/skills/vision/skill.py
@skill("analyze_image")
async def analyze_image(image: bytes) -> dict:
    """使用 Gemini Vision 分析图片"""
    # 调用 Gemini API 识别无障碍设施
    return {
        "is_valid": True,
        "facility_type": "ramp",
        "condition": "坡度小于5度，路面平整",
        "confidence": 0.95
    }
```

#### 2.2 Database Skill (数据库操作)
```python
# backend/skills/database/skill.py
@skill("save_facility")
async def save_facility(data: dict) -> str:
    """保存设施到 PostgreSQL"""
    # INSERT INTO facilities ...
    return facility_id

@skill("check_existing")
async def check_existing(lat: float, lng: float, type: str) -> dict:
    """查询是否存在同类型设施"""
    # SELECT * FROM facilities WHERE ...
    return {"exists": True, "last_updated": "2024-01-01"}
```

#### 2.3 Blockchain Skill (代币发放)
```python
# backend/skills/blockchain/skill.py
@skill("send_reward")
async def send_reward(wallet: str, amount: int) -> str:
    """调用智能合约发放代币"""
    # 使用 web3.py 调用合约
    return tx_hash
```

#### 2.4 Anti-Fraud Skill (防刷检测)
```python
# backend/skills/anti_fraud/skill.py
@skill("check_fraud")
async def check_fraud(lat: float, lng: float, type: str) -> dict:
    """检查是否为刷单行为"""
    # 15天规则检查
    return {
        "is_fraud": False,
        "reward_amount": 50,  # 或 25 (更新)
        "reason": "new_facility"
    }
```

---

### 3. FastAPI 后端

```python
# backend/main.py
from fastapi import FastAPI
from agent.help2earn_agent import Help2EarnAgent

app = FastAPI()
agent = Help2EarnAgent()

@app.post("/upload")
async def upload_facility(
    image: UploadFile,
    latitude: float,
    longitude: float,
    wallet_address: str
):
    """上传设施 - 由 SpoonOS Agent 处理全流程"""
    result = await agent.process_upload(
        image=await image.read(),
        lat=latitude,
        lng=longitude,
        wallet=wallet_address
    )
    return result

@app.get("/facilities")
async def get_facilities(lat: float, lng: float, radius: int = 200):
    """查询附近设施"""
    result = await agent.agent.run(f"""
    查询坐标 ({lat}, {lng}) 半径 {radius}m 内的所有无障碍设施
    """)
    return result

@app.get("/rewards/{wallet}")
async def get_rewards(wallet: str):
    """查询用户奖励记录"""
    result = await agent.agent.run(f"""
    查询钱包 {wallet} 的所有奖励记录
    """)
    return result
```

---

### 4. 前端模块 (Next.js PWA)

#### 4.1 地图视图 ("看" 功能)
```
文件: frontend/src/app/page.tsx, frontend/src/components/Map.tsx

功能:
- 显示用户当前位置 200m 半径内的无障碍设施
- 设施类型图标: 坡道、无障碍厕所、电梯、轮椅借用处
- 图标聚合: 密集区域显示大图标，点击展开
- 点击小图标查看详情图片和 AI 分析结果
```

#### 4.2 拍照上传 ("帮" 功能)
```
文件: frontend/src/components/CameraButton.tsx

流程:
1. 用户点击拍照按钮
2. 获取 GPS 坐标 (navigator.geolocation)
3. 调用相机拍照或选择图片
4. 上传到 FastAPI 后端 (由 SpoonOS Agent 处理)
5. 显示验证结果和奖励
```

#### 4.3 钱包集成
```
文件: frontend/src/providers/Web3Provider.tsx

功能:
- RainbowKit 钱包连接 (MetaMask, WalletConnect 等)
- 显示代币余额
- 交易历史记录
```

### 4. 智能合约

#### 4.1 ERC-20 代币合约
```solidity
// contracts/Help2EarnToken.sol
contract Help2EarnToken is ERC20 {
    address public minter; // 后端服务地址

    function mint(address to, uint256 amount) external onlyMinter {
        _mint(to, amount);
    }
}
```

#### 4.2 奖励分发合约
```solidity
// contracts/RewardDistributor.sol
contract RewardDistributor {
    // 记录每次验证的哈希值 (防篡改)
    mapping(bytes32 => bool) public verificationRecords;

    event RewardDistributed(
        address indexed user,
        bytes32 locationHash,
        uint256 amount,
        uint256 timestamp
    );

    function distributeReward(
        address user,
        bytes32 locationHash,
        uint256 amount
    ) external onlyAuthorized {
        require(!verificationRecords[locationHash], "Already verified");
        verificationRecords[locationHash] = true;
        token.mint(user, amount);
        emit RewardDistributed(user, locationHash, amount, block.timestamp);
    }
}
```

---

## 数据库设计

```sql
-- 无障碍设施表
CREATE TABLE facilities (
    id UUID PRIMARY KEY,
    type VARCHAR(20) NOT NULL, -- ramp, toilet, elevator, wheelchair
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    image_url TEXT NOT NULL,
    ai_analysis TEXT,
    contributor_address VARCHAR(42),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 空间索引
CREATE INDEX idx_facilities_location ON facilities USING GIST(location);

-- 奖励记录表
CREATE TABLE rewards (
    id UUID PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    facility_id UUID REFERENCES facilities(id),
    amount INTEGER NOT NULL,
    tx_hash VARCHAR(66),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 目录结构

```
help2earn/
├── backend/                       # FastAPI + SpoonOS 后端
│   ├── main.py                   # FastAPI 入口
│   ├── agent/
│   │   └── help2earn_agent.py    # SpoonOS React Agent (核心)
│   ├── skills/                   # Agent Skills
│   │   ├── vision/
│   │   │   └── skill.py          # 图片识别 Skill
│   │   ├── database/
│   │   │   └── skill.py          # 数据库操作 Skill
│   │   ├── blockchain/
│   │   │   └── skill.py          # 区块链交易 Skill
│   │   └── anti_fraud/
│   │       └── skill.py          # 防刷检测 Skill
│   ├── models/
│   │   └── schemas.py            # Pydantic 数据模型
│   └── requirements.txt          # Python 依赖
│
├── frontend/                      # Next.js PWA 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # 主页(地图)
│   │   │   └── layout.tsx        # 布局
│   │   ├── components/
│   │   │   ├── Map.tsx           # 地图组件
│   │   │   ├── CameraButton.tsx  # 拍照按钮
│   │   │   ├── FacilityMarker.tsx# 设施标记
│   │   │   └── WalletButton.tsx  # 钱包连接
│   │   ├── services/
│   │   │   └── api.ts            # 后端 API 调用
│   │   └── providers/
│   │       └── Web3Provider.tsx  # Web3 上下文
│   └── public/
│       └── icons/                # 设施图标
│
├── contracts/                     # Solidity 智能合约
│   ├── Help2EarnToken.sol        # ERC-20 代币
│   └── RewardDistributor.sol     # 奖励分发
│
└── database/
    └── init.sql                  # PostgreSQL 初始化脚本
```

---

## 关键文件清单

| 文件路径 | 用途 |
|----------|------|
| `backend/agent/help2earn_agent.py` | **SpoonOS React Agent 核心** |
| `backend/skills/vision/skill.py` | Gemini 图片识别 Skill |
| `backend/skills/blockchain/skill.py` | 代币发放 Skill |
| `backend/main.py` | FastAPI 入口 |
| `frontend/src/app/page.tsx` | 前端主页 |
| `frontend/src/components/Map.tsx` | Mapbox 地图组件 |
| `contracts/Help2EarnToken.sol` | ERC-20 代币合约 |

---

## 验证方案

1. **SpoonOS Agent 测试**
   - 启动 FastAPI: `uvicorn backend.main:app --reload`
   - 测试 Agent 能否正确调用各 Skill
   - 验证完整业务流程

2. **本地开发测试**
   - 前端: `cd frontend && npm run dev`
   - 后端: `cd backend && uvicorn main:app --reload`
   - 使用 Sepolia 测试网测试代币转账

3. **AI 验证测试**
   - 准备测试图片集(坡道、厕所、电梯、无关图片)
   - 验证 Gemini + SpoonOS Vision Skill 识别准确率

4. **智能合约测试**
   - Hardhat 本地测试
   - Sepolia 测试网部署验证

5. **端到端测试**
   - 完整流程: 拍照 → SpoonOS Agent 处理 → 数据入库 → 代币到账

---

## 已确认事项

| 事项 | 决定 |
|------|------|
| SpoonOS 集成 | ✅ 全 Python 后端，深度集成 React Agent |
| 代币经济 | ⏳ 暂用测试代币，后续设计 |
| 部署环境 | ✅ 前端 Vercel，后端待定 (Railway/Render) |
| 黑客松要求 | ✅ 满足 SpoonOS + React Agent 核心使用要求 |
