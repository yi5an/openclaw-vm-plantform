# OpenClaw VM Platform - 功能点清单

## 1. 核心功能模块

### 1.1 用户系统

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| 用户注册 | P0 | 邮箱注册 | JWT认证 + 邮箱验证 |
| 用户登录 | P0 | 邮箱/密码登录 | JWT Token |
| OAuth登录 | P1 | GitHub/Google登录 | OAuth 2.0 |
| 用户中心 | P0 | 个人信息管理 | RESTful API |
| 密码重置 | P1 | 邮箱验证码重置 | Redis缓存验证码 |

### 1.2 VM 管理

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| 创建VM | P0 | 选择套餐+配置 | 云API + SSH自动化 |
| VM列表 | P0 | 查看用户的VM | PostgreSQL查询 |
| VM详情 | P0 | 查看单个VM详情 | 包含状态、配置、使用量 |
| 启动VM | P0 | 启动已停止的VM | 云API + SSH |
| 停止VM | P0 | 停止运行中的VM | SSH + 云API |
| 删除VM | P0 | 删除VM | 云API + 数据清理 |
| VM续费 | P1 | 延长VM有效期 | 支付系统 |
| VM状态监控 | P1 | 实时状态 | Prometheus + WebSocket |

### 1.3 套餐管理

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| 套餐列表 | P0 | 展示所有套餐 | 静态配置 + 数据库 |
| 套餐详情 | P0 | 套餐包含的内容 | 对比表格 |
| 套餐升级 | P1 | 升级现有套餐 | 配额检查 + 差价计算 |
| 套餐降级 | P2 | 降级套餐 | 资源检查 + 退款 |

### 1.4 Agent 市场

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| Agent模板列表 | P0 | 预设模板展示 | 分类展示 + 搜索 |
| Agent详情 | P0 | 灵魂、人设、能力介绍 | Markdown文档 |
| 选择Agent | P0 | 创建VM时选择 | 多选 + 预览 |
| 自定义Agent | P1 | AI辅助创建 | LLM生成配置 |
| Agent导入导出 | P2 | 配置文件管理 | JSON/YAML |
| Agent评分 | P2 | 用户评分系统 | 数据库记录 |

### 1.5 渠道配置

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| Telegram配置 | P0 | Bot Token配置 | 向导 + 自动验证 |
| WhatsApp配置 | P1 | Business API配置 | 向导 + 验证 |
| WebChat配置 | P1 | 嵌入代码生成 | 自动生成JS代码 |
| API配置 | P1 | API Key管理 | 生成 + 权限控制 |
| 渠道状态 | P0 | 连接状态显示 | 健康检查 |
| 渠道测试 | P1 | 发送测试消息 | 模拟请求 |

### 1.6 计费系统

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| 订单创建 | P0 | 创建支付订单 | 数据库记录 |
| 支付集成 | P0 | 支付宝/微信 | 第三方支付API |
| 订单查询 | P0 | 查看订单状态 | 列表 + 详情 |
| Token统计 | P0 | 按VM统计Token | Redis实时 + DB持久化 |
| 账单生成 | P1 | 月度账单 | 定时任务 |
| 发票管理 | P2 | 开具发票 | 第三方服务 |

### 1.7 监控面板

| 功能点 | 优先级 | 描述 | 实现方案 |
|-------|--------|------|---------|
| VM监控 | P1 | CPU/内存/磁盘 | Prometheus + Grafana |
| Token使用 | P0 | Token消耗趋势 | 图表展示 |
| Agent活跃度 | P1 | 消息数量统计 | 数据库聚合 |
| 成本分析 | P1 | 费用明细 | 月度汇总 |
| 告警通知 | P2 | 异常告警 | 邮件/短信/Webhook |

---

## 2. 虚拟化支持

### 2.1 KVM（自建机房）

| 功能点 | 描述 | 实现方案 |
|-------|------|---------|
| 创建虚拟机 | 调用libvirt API | virsh命令封装 |
| 镜像管理 | QCOW2镜像 | 模板复制 |
| 网络配置 | 桥接网络 | XML配置 |
| 存储管理 | LVM/文件存储 | virsh pool |

**技术细节：**
```typescript
interface KVMProvider {
  // libvirt 连接
  connection: LibvirtConnection;
  
  // 创建VM
  async createVM(spec: VMSpec): Promise<VMInfo> {
    // 1. 复制模板镜像
    await this.copyImage(spec.template, spec.diskSize);
    
    // 2. 生成XML配置
    const xml = this.generateXML(spec);
    
    // 3. 定义并启动
    await this.connection.defineXML(xml);
    await this.connection.start(spec.name);
    
    // 4. 获取IP（DHCP）
    const ip = await this.waitForIP(spec.mac);
    return { ip, ... };
  }
}
```

### 2.2 OpenStack（大规模部署）

| 功能点 | 描述 | 实现方案 |
|-------|------|---------|
| 创建实例 | Nova API | REST调用 |
| 镜像管理 | Glance API | 镜像上传 |
| 网络管理 | Neutron API | 网络配置 |
| 存储管理 | Cinder API | 卷管理 |

**技术细节：**
```typescript
interface OpenStackProvider {
  // OpenStack SDK
  client: OpenStackClient;
  
  async createVM(spec: VMSpec): Promise<VMInfo> {
    // 1. 选择flavor
    const flavor = await this.client.getFlavor(spec.flavorId);
    
    // 2. 创建实例
    const server = await this.client.createServer({
      name: spec.name,
      flavor: flavor.id,
      image: spec.imageId,
      networks: [{ uuid: spec.networkId }],
      userData: this.generateInitScript(spec),
    });
    
    // 3. 等待活跃
    await this.waitForActive(server.id);
    
    // 4. 获取IP
    const ip = await this.getFloatingIP(server.id);
    return { ip, ... };
  }
}
```

### 2.3 云厂商API（阿里云）

| 功能点 | 描述 | 实现方案 |
|-------|------|---------|
| 创建实例 | ECS API | @alicloud/ecs |
| 镜像管理 | 自定义镜像 | 镜像共享 |
| 网络配置 | VPC/安全组 | API配置 |
| 自动化脚本 | Userdata | Shell脚本 |

**技术细节：**
```typescript
import ECS from '@alicloud/ecs';

interface AliyunProvider {
  client: ECS;
  
  async createVM(spec: VMSpec): Promise<VMInfo> {
    const result = await this.client.createInstance({
      RegionId: spec.region,
      ImageId: spec.imageId,
      InstanceType: spec.instanceType,
      SecurityGroupId: spec.securityGroupId,
      UserData: Buffer.from(this.generateInitScript(spec)).toString('base64'),
    });
    
    // 分配公网IP
    await this.client.allocatePublicIpAddress({
      InstanceId: result.InstanceId,
    });
    
    return {
      instanceId: result.InstanceId,
      ip: result.PublicIpAddress,
    };
  }
}
```

---

## 3. 镜像管理

### 3.1 镜像类型

| 镜像ID | 场景 | 包含Agent | 大小 |
|--------|------|----------|------|
| base | 基础 | 无 | 2GB |
| dev-starter | 开发起步 | coder | 3GB |
| dev-team | 开发团队 | coder, architect, tester | 4GB |
| support-basic | 客服基础 | support | 3GB |
| support-pro | 客服专业 | support, analyzer | 3.5GB |
| finance | 金融分析 | analyzer, reporter | 3.5GB |
| ops | 运维助手 | monitor, alerter | 3GB |

### 3.2 镜像构建流程

```bash
# 1. 基础镜像
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    nodejs npm docker.io git \
    && npm install -g openclaw

# 2. 场景镜像（dev-team）
COPY agents/coder /etc/openclaw/agents/
COPY agents/architect /etc/openclaw/agents/
COPY agents/tester /etc/openclaw/agents/

# 3. 打包
tar -czf openclaw-dev-team.tar.gz /

# 4. 上传到镜像仓库
# KVM: 上传到NFS
# OpenStack: 上传到Glance
# Aliyun: 导入为自定义镜像
```

---

## 4. Agent 配置方案

### 4.1 预设Agent模板

```yaml
# coder-agent.yaml
id: coder
name: 开发助手
category: development
description: 代码审查、Debug、重构建议

# 灵魂（SOUL.md）
soul: |
  你是一个专业的开发助手。
  擅长代码审查、Bug诊断、重构建议。
  语言简洁专业，注重代码质量。

# 人设（IDENTITY.md）
identity:
  name: Coder
  emoji: 💻
  role: 后端开发
  skills:
    - code-review
    - debugging
    - refactoring

# 模型配置
model:
  primary: deepseek/deepseek-reasoner
  fallback: zai/glm-5

# 工具配置
tools:
  - github
  - coding-agent
```

### 4.2 自定义Agent创建流程

```
1. 用户填写基本信息
   - 名称、用途描述、场景
   ↓
2. AI 生成配置
   - 分析需求 → 生成灵魂
   - 生成人设 → 生成Prompt
   - 推荐模型 → 推荐工具
   ↓
3. 用户预览和调整
   - 编辑各部分内容
   - 测试对话
   ↓
4. 保存并部署
   - 保存到数据库
   - SSH到VM配置
```

**AI生成示例：**
```typescript
async function generateAgentConfig(requirement: string): Promise<AgentConfig> {
  const prompt = `
用户需求: ${requirement}

请生成一个OpenClaw Agent的配置，包括：
1. soul（灵魂）- Agent的性格和行为准则
2. identity（人设）- 名称、emoji、角色
3. systemPrompt - 系统提示词
4. recommendedModel - 推荐的模型
5. skills - 需要的技能

以JSON格式返回。
  `;
  
  const config = await llm.chat(prompt);
  return JSON.parse(config);
}
```

---

## 5. Token 统计方案

### 5.1 统计架构

```
┌─────────────────────────────────────────────┐
│          User VM (OpenClaw Gateway)         │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Token Usage Middleware (Hook)       │   │
│  │ - 拦截所有LLM调用                   │   │
│  │ - 记录usage                         │   │
│  │ - 上报到平台                        │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓ HTTP
┌─────────────────────────────────────────────┐
│          Platform (Token Service)           │
│                                             │
│  1. 接收usage报告                           │
│  2. Redis实时累加                           │
│  3. 定时持久化到PostgreSQL                  │
│  4. 检查配额，超限则通知                    │
└─────────────────────────────────────────────┘
```

### 5.2 OpenClaw Hook 实现

```typescript
// 在OpenClaw Gateway中添加Hook
class TokenUsageHook {
  async afterLLMCall(context: LLMContext) {
    const usage = context.response.usage;
    
    // 上报到平台
    await fetch('https://platform.openclaw.ai/api/usage/report', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.vmToken}` },
      body: JSON.stringify({
        vmId: this.vmId,
        agentId: context.agentId,
        model: context.model,
        promptTokens: usage.prompt_tokens,
        completionTokens: usage.completion_tokens,
        timestamp: new Date(),
      }),
    });
  }
}

// 注册Hook
openclawGateway.registerHook('afterLLMCall', new TokenUsageHook());
```

### 5.3 平台统计服务

```typescript
class TokenUsageService {
  // 接收报告
  async reportUsage(usage: TokenUsage): Promise<void> {
    const key = `usage:${usage.vmId}:${this.getMonth()}`;
    
    // Redis累加
    await redis.multi()
      .incrby(`${key}:tokens`, usage.totalTokens)
      .incrby(`${key}:cost`, this.calculateCost(usage))
      .exec();
    
    // 检查配额
    await this.checkQuota(usage.vmId);
  }
  
  // 定时持久化
  @Cron('0 */5 * * * *') // 每5分钟
  async persistToDatabase(): Promise<void> {
    const vms = await this.getActiveVMs();
    
    for (const vm of vms) {
      const key = `usage:${vm.id}:${this.getMonth()}`;
      const data = await redis.hgetall(key);
      
      if (data) {
        await db.query(`
          INSERT INTO monthly_usage (vm_id, period, total_tokens, total_cost)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (vm_id, period) DO UPDATE
          SET total_tokens = $3, total_cost = $4
        `, [vm.id, this.getMonth(), data.tokens, data.cost]);
      }
    }
  }
  
  // 配额检查
  async checkQuota(vmId: string): Promise<void> {
    const vm = await this.getVM(vmId);
    const usage = await this.getCurrentUsage(vmId);
    const quota = await this.getQuota(vm.planId);
    
    if (usage.tokens >= quota.maxTokens) {
      // 通知用户
      await this.notifyUser(vm.userId, 'quota_exceeded', {
        used: usage.tokens,
        limit: quota.maxTokens,
      });
      
      // 可选：暂停服务
      // await this.suspendVM(vmId);
    }
  }
}
```

---

## 6. 渠道配置细节

### 6.1 Telegram 配置向导

```
步骤1: 创建Bot
┌────────────────────────────────────────┐
│ 1. 在Telegram中搜索 @BotFather          │
│ 2. 发送 /newbot                         │
│ 3. 按提示设置Bot名称                     │
│ 4. 复制Bot Token                        │
│                                        │
│ Bot Token: [________________]          │
│                                        │
│ [测试Token] [下一步]                    │
└────────────────────────────────────────┘

步骤2: 配置到VM
┌────────────────────────────────────────┐
│ 正在配置...                             │
│ ✓ Token验证成功                         │
│ ✓ Bot: @YourBot                        │
│ ✓ 连接到VM...                           │
│ ✓ 配置完成                              │
│                                        │
│ 你的Bot链接: https://t.me/YourBot      │
│ [打开Bot] [返回]                        │
└────────────────────────────────────────┘
```

**实现代码：**
```typescript
async function configureTelegram(vmId: string, botToken: string) {
  // 1. 验证Token
  const botInfo = await axios.get(`https://api.telegram.org/bot${botToken}/getMe`);
  if (!botInfo.data.ok) {
    throw new Error('Invalid bot token');
  }
  
  // 2. SSH到VM
  const ssh = await connectSSH(vmId);
  
  // 3. 配置OpenClaw
  await ssh.exec(`openclaw config set channels.telegram.botToken "${botToken}"`);
  await ssh.exec(`openclaw config set channels.telegram.webhookEnabled true`);
  
  // 4. 重启服务
  await ssh.exec('systemctl restart openclaw-gateway');
  
  // 5. 验证
  await sleep(5000);
  const status = await ssh.exec('systemctl is-active openclaw-gateway');
  if (status !== 'active') {
    throw new Error('Gateway failed to start');
  }
  
  // 6. 保存到数据库
  await db.query(`
    INSERT INTO channels (vm_id, type, config)
    VALUES ($1, 'telegram', $2)
  `, [vmId, { botToken, botUsername: botInfo.data.result.username }]);
  
  return {
    username: botInfo.data.result.username,
    link: `https://t.me/${botInfo.data.result.username}`,
  };
}
```

### 6.2 WhatsApp 配置

```
步骤1: WhatsApp Business API
┌────────────────────────────────────────┐
│ 需要先申请WhatsApp Business API        │
│                                        │
│ Phone Number: [________________]       │
│ API Key: [________________]            │
│                                        │
│ [测试连接] [下一步]                     │
└────────────────────────────────────────┘

步骤2: 验证
┌────────────────────────────────────────┐
│ 向你的WhatsApp号码发送测试消息...       │
│                                        │
│ ✓ 连接成功                              │
│ ✓ 测试消息已发送                        │
│                                        │
│ 请检查WhatsApp是否收到消息              │
│ [确认收到] [重新发送]                   │
└────────────────────────────────────────┘
```

### 6.3 WebChat 配置

```
步骤1: 生成嵌入代码
┌────────────────────────────────────────┐
│ WebChat已配置完成！                     │
│                                        │
│ 复制以下代码到你的网站：                │
│ ┌────────────────────────────────────┐ │
│ │ <script>                           │ │
│ │   window.OpenClawChat = {          │ │
│ │     vmId: 'xxx',                   │ │
│ │     theme: 'light'                 │ │
│ │   };                               │ │
│ │ </script>                          │ │
│ │ <script src="https://chat...">     │ │
│ │ </script>                          │ │
│ └────────────────────────────────────┘ │
│                                        │
│ [复制代码] [预览] [自定义样式]          │
└────────────────────────────────────────┘
```

---

## 7. 支付集成

### 7.1 支付宝

```typescript
import Alipay from 'alipay-sdk';

const alipay = new Alipay({
  appId: process.env.ALIPAY_APP_ID,
  privateKey: process.env.ALIPAY_PRIVATE_KEY,
  alipayPublicKey: process.env.ALIPAY_PUBLIC_KEY,
});

async function createPayment(order: Order): Promise<string> {
  const result = alipay.pageExec(
    alipaySdk.buildOrderParam({
      outTradeNo: order.id,
      totalAmount: order.amount,
      subject: `OpenClaw VM - ${order.planName}`,
      productCode: 'FAST_INSTANT_TRADE_PAY',
    })
  );
  
  return result; // 支付页面URL
}

// 回调处理
async function handleCallback(params: any): Promise<void> {
  const verified = alipay.verifyCallback(params);
  if (!verified) {
    throw new Error('Invalid callback');
  }
  
  const orderId = params.out_trade_no;
  const tradeStatus = params.trade_status;
  
  if (tradeStatus === 'TRADE_SUCCESS') {
    await activateOrder(orderId);
  }
}
```

### 7.2 微信支付

```typescript
import WxPay from 'wechatpay-node-v3';

const wxpay = new WxPay({
  appid: process.env.WECHAT_APP_ID,
  mchid: process.env.WECHAT_MCH_ID,
  serial_no: process.env.WECHAT_SERIAL_NO,
  privateKey: process.env.WECHAT_PRIVATE_KEY,
  apiv3_private_key: process.env.WECHAT_APIV3_KEY,
});

async function createPayment(order: Order): Promise<string> {
  const result = await wxpay.transactions_native({
    description: `OpenClaw VM - ${order.planName}`,
    out_trade_no: order.id,
    amount: {
      total: Math.round(order.amount * 100), // 分
      currency: 'CNY',
    },
    notify_url: 'https://platform.openclaw.ai/api/payment/wechat/callback',
  });
  
  return result.code_url; // 二维码URL
}
```

---

## 8. 监控告警

### 8.1 监控指标

| 指标 | 说明 | 告警阈值 |
|-----|------|---------|
| vm_cpu_usage | VM CPU使用率 | >80% 持续5分钟 |
| vm_memory_usage | VM内存使用率 | >90% 持续5分钟 |
| vm_disk_usage | VM磁盘使用率 | >85% |
| openclaw_gateway_status | Gateway服务状态 | 非active |
| token_usage_rate | Token使用速率 | 超过配额80% |
| api_error_rate | API错误率 | >5% |

### 8.2 告警通知

```typescript
class AlertService {
  async checkAndAlert(): Promise<void> {
    const vms = await this.getAllVMs();
    
    for (const vm of vms) {
      const metrics = await this.getMetrics(vm.id);
      
      // CPU告警
      if (metrics.cpuUsage > 80) {
        await this.sendAlert(vm.userId, {
          type: 'cpu_high',
          message: `VM ${vm.name} CPU使用率过高: ${metrics.cpuUsage}%`,
          severity: 'warning',
        });
      }
      
      // Gateway告警
      if (metrics.gatewayStatus !== 'active') {
        await this.sendAlert(vm.userId, {
          type: 'gateway_down',
          message: `VM ${vm.name} Gateway服务异常`,
          severity: 'critical',
        });
        
        // 尝试自动恢复
        await this.tryRecover(vm.id);
      }
    }
  }
  
  async tryRecover(vmId: string): Promise<void> {
    const ssh = await connectSSH(vmId);
    
    // 尝试重启
    await ssh.exec('systemctl restart openclaw-gateway');
    await sleep(10000);
    
    const status = await ssh.exec('systemctl is-active openclaw-gateway');
    if (status === 'active') {
      await this.sendAlert(vm.userId, {
        type: 'recovered',
        message: `VM ${vm.name} Gateway已自动恢复`,
        severity: 'info',
      });
    } else {
      // 需要人工介入
      await this.notifyOpsTeam(vmId);
    }
  }
}
```

---

## 9. 依赖关系

```
用户系统 (P0)
    ↓
VM管理 (P0) → 套餐管理 (P0)
    ↓
Agent市场 (P0)
    ↓
渠道配置 (P0) ← Telegram配置 (P0)
    ↓
计费系统 (P0) ← 支付集成 (P0)
    ↓
Token统计 (P0)
    ↓
监控面板 (P1)
```

---

## 10. MVP 功能范围

### 必须有（P0）
- ✅ 用户注册/登录
- ✅ 创建VM（单一云厂商）
- ✅ VM列表/详情/启动/停止
- ✅ 套餐选择
- ✅ Agent模板选择（3-5个）
- ✅ Telegram配置向导
- ✅ 支付宝支付
- ✅ Token统计

### 可选（P1）
- OAuth登录
- VM续费/升级
- 自定义Agent
- WhatsApp配置
- 监控面板

### 后期（P2）
- 微信支付
- WebChat
- 发票管理
- Agent评分

---

*文档版本: v1.0*
*创建日期: 2026-03-04*
