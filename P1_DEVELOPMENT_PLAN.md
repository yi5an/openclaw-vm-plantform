# OpenClaw VM Platform - P1 开发计划

**创建时间**: 2026-03-22 22:18
**目标**: 完成 P1 核心功能开发

---

## 📋 P1 功能清单

### 1. Agent 管理 API (优先级: P1-高)

**负责人**: @coder
**预计时间**: 2-3 天

#### 功能点
- [ ] 创建 Agent（选择模板、配置模型）
- [ ] Agent 列表（按 VM 过滤）
- [ ] Agent 详情（包含使用统计）
- [ ] 更新 Agent 配置
- [ ] 启动/停止 Agent
- [ ] 删除 Agent
- [ ] 验证自定义 Token

#### API 端点
```
POST   /api/v1/agents                 # 创建 Agent
GET    /api/v1/agents                 # Agent 列表
GET    /api/v1/agents/{id}            # Agent 详情
PATCH  /api/v1/agents/{id}            # 更新 Agent
POST   /api/v1/agents/{id}/start      # 启动 Agent
POST   /api/v1/agents/{id}/stop       # 停止 Agent
DELETE /api/v1/agents/{id}            # 删除 Agent
POST   /api/v1/agents/validate-token  # 验证 Token
```

#### 数据模型
- ✅ 已完成（agents, agent_templates 表）

#### 测试要求
- 单元测试覆盖率 > 80%
- 集成测试完整流程

---

### 2. 渠道配置 API (优先级: P1-高)

**负责人**: @coder
**预计时间**: 2-3 天

#### 功能点
- [ ] 飞书渠道配置
- [ ] Telegram 渠道配置
- [ ] 渠道列表
- [ ] 渠道状态检查
- [ ] 测试消息发送
- [ ] 删除渠道

#### API 端点
```
POST   /api/v1/channels/feishu        # 配置飞书
POST   /api/v1/channels/telegram      # 配置 Telegram
GET    /api/v1/channels               # 渠道列表
GET    /api/v1/channels/{id}/status   # 渠道状态
POST   /api/v1/channels/{id}/test     # 测试消息
DELETE /api/v1/channels/{id}          # 删除渠道
```

#### 数据模型
- ✅ 已完成（channels 表）

---

### 3. 计费系统 (优先级: P1-中)

**负责人**: @coder
**预计时间**: 2 天

#### 功能点
- [ ] Token 使用记录
- [ ] 余额变动日志
- [ ] 使用统计（按 Agent 分组）
- [ ] 订单管理
- [ ] 余额查询

#### API 端点
```
GET    /api/v1/billing/usage          # 使用记录
GET    /api/v1/billing/stats          # 使用统计
GET    /api/v1/billing/orders         # 订单列表
GET    /api/v1/billing/balance        # 余额查询
```

#### 数据模型
- ✅ 已完成（orders, token_usage, user_balance_log 表）

---

### 4. Libvirt 集成 (优先级: P1-高)

**负责人**: @coder + @devopser
**预计时间**: 3-4 天

#### 功能点
- [ ] 虚拟机创建（qcow2 + cloud-init）
- [ ] 虚拟机启停
- [ ] 虚拟机删除
- [ ] SSH 自动化部署
- [ ] OpenClaw 自动安装
- [ ] 健康检查

#### 技术实现
- 使用 `libvirt-python` 库
- cloud-init 配置网络和 SSH
- Ansible 自动化部署

#### 文档参考
- `docs/vm-provisioning.md`
- `docs/openclaw-deployment.md`

---

## 📅 开发时间表

### Week 1 (3月22日 - 3月28日)

| 日期 | 任务 | 负责人 |
|------|------|--------|
| 3月22日 | P0 测试完成 + 文档 | Tester + Doc-writer |
| 3月23日 | Agent API 开发 | Coder |
| 3月24日 | Agent API 测试 + 渠道 API 开发 | Tester + Coder |
| 3月25日 | 渠道 API 完成 + 测试 | Coder + Tester |
| 3月26日 | 计费系统开发 | Coder |
| 3月27日 | Libvirt 集成（基础）| Coder + Devopser |
| 3月28日 | Libvirt 集成（部署）| Coder + Devopser |

### Week 2 (3月29日 - 4月4日)

| 日期 | 任务 | 负责人 |
|------|------|--------|
| 3月29日 | P1 集成测试 | Tester |
| 3月30日 | Bug 修复 | Coder |
| 3月31日 | 前端 P1 功能开发 | Frontenddev |
| 4月1日 | 前端 P1 功能开发 | Frontenddev |
| 4月2日 | 前后端集成测试 | Tester |
| 4月3日 | 文档完善 | Doc-writer |
| 4月4日 | 发布 v0.2.0-beta | Team |

---

## 📊 验收标准

### P1 完成标准

1. ✅ 所有 API 端点实现完成
2. ✅ 单元测试覆盖率 > 80%
3. ✅ 集成测试通过
4. ✅ API 文档完整
5. ✅ 用户手册更新
6. ✅ 部署文档验证

### 发布标准

1. ✅ P0 + P1 功能完整
2. ✅ 所有测试通过
3. ✅ 文档完整
4. ✅ 前后端集成成功
5. ✅ Demo 演示通过

---

## 🚀 启动 P1 开发

**等待 P0 测试和文档完成后启动**:
- [ ] Tester 完成 P0 最终测试报告
- [ ] Doc-writer 完成基础文档
- [ ] 启动 Coder 开始 Agent API 开发

---

_最后更新: 2026-03-22 22:18_
