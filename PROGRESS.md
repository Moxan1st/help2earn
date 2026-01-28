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
