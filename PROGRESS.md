# Help2Earn 项目进度

## 已完成 ✅

### 1. 数据库 (Supabase)
- **连接字符串**: `postgresql://postgres:***@db.ljedvdsnkdrsdcgmgdwv.supabase.co:5432/postgres`
- **已创建表**: `facilities`, `rewards`
- **PostGIS**: 已启用

### 2. 智能合约 (Sepolia Testnet)
- **Help2EarnToken**: `0x491c88aBE3FE07dFD13e379dE44D427bA94CE4C9`
- **RewardDistributor**: `0xDf929aD0C7f32B9E3cce6B86dEaD2ff1522EF0A4`
- **Minter**: 已设置为 RewardDistributor
- **部署钱包**: `0xBc5c983a05c889efA3bCa353012C96DdDa439e78`

### 3. Google Cloud Storage
- **Project ID**: `gen-lang-client-0334796697`
- **Bucket**: `help2earn-images-2026-1-28`
- **Service Account Key**: `backend/gen-lang-client-0334796697-2371a9854738.json`

### 4. API Keys
- **Gemini API**: 已配置在 `.env`
- **Alchemy RPC**: `https://eth-sepolia.g.alchemy.com/v2/fkVlNh_pydNsyP9cKFg39`

### 5. 代码
- **后端**: FastAPI + SpoonOS React Agent (完成)
- **前端**: Next.js + Mapbox + RainbowKit (完成)
- **合约**: ERC-20 Token + RewardDistributor (已部署)

---

## 下次继续 📋

### 启动后端
```bash
cd /home/moxan_sigs/help2earn/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 启动前端
```bash
cd /home/moxan_sigs/help2earn/frontend
npm install
npm run dev
```

### 前端还需要配置
创建 `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=你的walletconnect_project_id
```
> 地图已改用 OpenStreetMap (Leaflet)，无需 Mapbox Token

---

## 项目结构
```
help2earn/
├── backend/
│   ├── main.py                 # API 入口
│   ├── agent/                  # SpoonOS Agent
│   ├── skills/                 # Vision/Database/Blockchain/Storage
│   ├── .env                    # 环境变量 (已配置)
│   └── requirements.txt
├── frontend/
│   ├── src/app/               # Next.js 页面
│   ├── src/components/        # React 组件
│   └── package.json
├── contracts/
│   ├── contracts/             # Solidity 源码
│   └── scripts/               # 部署脚本
└── database/
    └── init.sql               # 数据库 schema
```

---

## 有用的链接
- Etherscan Token: https://sepolia.etherscan.io/address/0x491c88aBE3FE07dFD13e379dE44D427bA94CE4C9
- Etherscan Distributor: https://sepolia.etherscan.io/address/0xDf929aD0C7f32B9E3cce6B86dEaD2ff1522EF0A4
- Supabase Dashboard: https://supabase.com/dashboard
- GCP Console: https://console.cloud.google.com

---

*最后更新: 2025-01-28*

---

## 2026-01-28 20:50 进度更新

### 已完成的修改 ✅

1. **地图改用 OpenStreetMap (Leaflet)**
   - 移除了 Mapbox 依赖，不再需要 Mapbox Token
   - 修改了 `frontend/src/components/Map.tsx` 使用动态导入 Leaflet
   - 更新了 `frontend/package.json`，用 `leaflet` 替换 `mapbox-gl`

2. **前端 .env.local 已配置**
   - `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=aee869aa0978e405d41e101c6701e839`

3. **后端依赖已安装**
   - 创建了虚拟环境 `backend/venv`
   - 移除了不存在的 `spoon-ai` 依赖
   - 重写了 `agent/help2earn_agent.py` 直接调用 skills

4. **修复了 UI z-index 问题**
   - 地图加载后按钮不再被遮挡
   - 更新了 `page.tsx` 中的 z-index 为 `z-[100]`

5. **添加了模拟模式**
   - 在 `skills/vision/skill.py` 添加了 `MOCK_VISION` 环境变量
   - 当 Gemini API 不可用时，返回模拟数据用于测试

6. **修复了数据库连接**
   - URL 编码了密码中的特殊字符 `[]` → `%5B%5D`
   - 添加了 SSL 支持

### 当前问题 ❌

1. **Clash Verge TUN 模式劫持所有流量**
   - 数据库连接被 Clash 拦截，无法连接 Supabase
   - DNS 解析返回 Clash 的假 IP `198.18.x.x`
   - **解决方案**: 关闭 Clash TUN 模式，或在 Clash 配置中添加绕过规则

2. **Gemini API 地区限制**
   - 中国大陆无法直接访问 Gemini API
   - 已启用 `MOCK_VISION=true` 作为临时方案
   - **解决方案**: 配置代理让后端能访问 Gemini，或改用其他 AI 服务

3. **GCS 上传失败**
   - Bucket 启用了 uniform bucket-level access，导致 ACL 操作失败
   - **解决方案**: 修改 storage skill 代码或 bucket 设置

### 下次继续需要做的 📋

1. **关闭 Clash Verge 或配置绕过规则**
   ```yaml
   # 在 Clash 配置的 rules 最前面添加:
   - DOMAIN-SUFFIX,supabase.co,DIRECT
   - DOMAIN-SUFFIX,googleapis.com,DIRECT
   ```

2. **检查 Supabase 项目状态**
   - 登录 https://supabase.com/dashboard
   - 如果项目被暂停，点击 "Restore project"

3. **启动服务的命令**
   ```bash
   # 后端 (在 backend 目录)
   source venv/bin/activate
   MOCK_VISION=true uvicorn main:app --reload --port 8000

   # 前端 (在 frontend 目录)
   npm run dev
   ```

4. **测试数据库连接**
   ```bash
   cd /home/moxan_sigs/help2earn/backend
   source venv/bin/activate
   python3 -c "
   import psycopg2
   conn = psycopg2.connect(
       host='db.ljedvdsnkdrsdcgmgdwv.supabase.co',
       port=5432, database='postgres', user='postgres',
       password='[Moxan2026**]', sslmode='require'
   )
   print('Connected!')
   conn.close()
   "
   ```

### 后端 .env 当前配置
```
DATABASE_URL=postgresql://postgres:%5BMoxan2026**%5D@db.ljedvdsnkdrsdcgmgdwv.supabase.co:5432/postgres?sslmode=require
MOCK_VISION=true
# 其他配置保持不变
```

---

*更新时间: 2026-01-28 20:50*

---

## 2026-01-29 Mock 替换计划

### Mock 模块状态

| 模块 | 环境变量 | Mock 实现 | 真实服务 |
|------|---------|----------|----------|
| Storage | `MOCK_STORAGE` | 本地文件系统 | GCS Bucket |
| Database | `MOCK_DATABASE` | 内存数据 | Supabase PostgreSQL |
| Blockchain | `MOCK_BLOCKCHAIN` | 模拟 Web3 | Sepolia 合约 |
| Vision | `MOCK_VISION` | 随机结果 | Gemini API |

### 已完成的代码修改 ✅

1. **Storage skill 修复** (`backend/skills/storage/skill.py`)
   - 移除了 `blob.make_public()` 调用（与 uniform bucket-level access 不兼容）
   - 改用直接构造公共 URL: `https://storage.googleapis.com/{bucket}/{blob}`

2. **Vision skill 添加代理支持** (`backend/skills/vision/skill.py`)
   - 添加了 `HTTPS_PROXY` 和 `HTTP_PROXY` 环境变量支持
   - 支持通过代理访问 Gemini API

3. **创建 env.example 模板** (`backend/env.example`)
   - 包含所有 Mock 开关说明
   - 包含所有服务配置项

### 切换到真实实现的步骤

#### 1. Storage (GCS)
```bash
# 在 .env 中设置
MOCK_STORAGE=false
GCS_PROJECT_ID=gen-lang-client-0334796697
GCS_BUCKET_NAME=help2earn-images-2026-1-28
GOOGLE_APPLICATION_CREDENTIALS=gen-lang-client-0334796697-2371a9854738.json
```

确保 GCS Bucket 权限配置：
- 在 GCP Console 添加 `allUsers` 具有 `Storage Object Viewer` 角色
- 或使用签名 URL（代码中已有 `get_image_url` 函数支持）

#### 2. Database (Supabase)
```bash
# 解决网络问题：在 Clash 配置中添加绕过规则
# rules:
#   - DOMAIN-SUFFIX,supabase.co,DIRECT
#   - DOMAIN-SUFFIX,supabase.net,DIRECT

# 在 .env 中设置
MOCK_DATABASE=false
DATABASE_URL=postgresql://postgres:%5BMoxan2026**%5D@db.ljedvdsnkdrsdcgmgdwv.supabase.co:5432/postgres?sslmode=require
```

#### 3. Blockchain (Sepolia)
```bash
# 在 .env 中设置
MOCK_BLOCKCHAIN=false
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/fkVlNh_pydNsyP9cKFg39
TOKEN_CONTRACT_ADDRESS=0x491c88aBE3FE07dFD13e379dE44D427bA94CE4C9
DISTRIBUTOR_CONTRACT_ADDRESS=0xDf929aD0C7f32B9E3cce6B86dEaD2ff1522EF0A4
MINTER_PRIVATE_KEY=<你的部署钱包私钥>
```

#### 4. Vision (Gemini)
```bash
# 在 .env 中设置
MOCK_VISION=false
GEMINI_API_KEY=<你的 Gemini API Key>
HTTPS_PROXY=http://127.0.0.1:7890  # Clash 代理端口
```

### 验证命令

```bash
# 测试数据库连接
nc -zv db.ljedvdsnkdrsdcgmgdwv.supabase.co 5432

# 启动后端
cd /home/web3_moxpc0/help2earn/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# 启动前端
cd /home/web3_moxpc0/help2earn/frontend
npm run dev
```

*更新时间: 2026-01-29*

---

## 2026-01-29 01:30 Mock 替换完成

### 全部模块已切换到真实实现 ✅

| 模块 | 环境变量 | 真实服务 | 状态 |
|------|---------|---------|------|
| Database | `MOCK_DATABASE=false` | Supabase (Session Pooler) | ✅ |
| Storage | `MOCK_STORAGE=false` | GCS Bucket | ✅ |
| Blockchain | `MOCK_BLOCKCHAIN=false` | Sepolia Testnet | ✅ |
| Vision | `MOCK_VISION=false` | Gemini API | ✅ |

### 关键配置变更

1. **数据库连接改用 Session Pooler**（解决 IPv6 问题）
   ```
   postgresql://postgres.ljedvdsnkdrsdcgmgdwv:***@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
   ```

2. **Storage skill 修复** - 移除 `make_public()` 调用

3. **Vision skill 添加代理支持** - 支持 `HTTPS_PROXY` 环境变量

4. **Database skill 添加 dotenv 加载** - 确保环境变量正确读取

5. **修复 UUID 转字符串** - `get_user_rewards` 中 UUID 类型转换

### 当前 .env 配置
```bash
# Mock 全部关闭
MOCK_DATABASE=false
MOCK_STORAGE=false
MOCK_BLOCKCHAIN=false
MOCK_VISION=false

# Database (Session Pooler)
DATABASE_URL=postgresql://postgres.ljedvdsnkdrsdcgmgdwv:***@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require

# Storage
GCS_PROJECT_ID=gen-lang-client-0334796697
GCS_BUCKET_NAME=help2earn-images-2026-1-28
GOOGLE_APPLICATION_CREDENTIALS=gen-lang-client-0334796697-fb33522868e1.json

# Blockchain
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/fkVlNh_pydNsyP9cKFg39
TOKEN_CONTRACT_ADDRESS=0x491c88aBE3FE07dFD13e379dE44D427bA94CE4C9
DISTRIBUTOR_CONTRACT_ADDRESS=0xDf929aD0C7f32B9E3cce6B86dEaD2ff1522EF0A4
MINTER_PRIVATE_KEY=***

# Vision
GEMINI_API_KEY=***
HTTPS_PROXY=http://127.0.0.1:7890
```

*更新时间: 2026-01-29 01:30*

---

## 2026-01-29 02:30 部署完成 & 待办任务

### 部署状态 ✅

| 服务 | 平台 | URL | 状态 |
|------|------|-----|------|
| 前端 | Vercel | 已部署 | Live |
| 后端 | Render | `https://help2earn-api.onrender.com` | Live |

### 最新修复
- Vision skill: 添加 `genai.configure(api_key=...)` 配置 Gemini API Key
- 前端 TypeScript: facility_type 类型断言
- 前端: Leaflet CSS 导入 ts-ignore

### 待修复问题

1. ~~**UI - Facility Types 标尺**~~ ✅ 已修复
   - 使用自定义 SVG 图标替换 emoji
   - 统一字体样式，改善颜色对比度
   - 移动到左上角 Logo 下方

2. ~~**地图不显示已上传的 Facility**~~ ✅ 已修复
   - 修复了 `query_facilities_nearby` 中缺少 `WHERE` 关键字的 SQL 语法错误
   - 图标大小 36px，不随地图缩放变化（Leaflet divIcon 正常行为）

3. ~~**上链行为确认**~~ ✅ 已修复
   - 修改 agent 使用 `distribute_reward_with_hash` 通过 RewardDistributor 发放奖励
   - 生成 location hash 用于链上防重复提交
   - 添加了 fallback 到直接 mint（如果 distributor 失败）

4. **照片真实性验证系统（新功能规划）**
   - AI 判断真实性
   - 真实 → 双倍代币
   - 虚假 → 扣除代币 + 禁止上传
   - 其他用户质疑机制
   - 考虑引入区块链预言机

*更新时间: 2026-01-29 02:30*
