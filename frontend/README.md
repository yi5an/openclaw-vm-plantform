# OpenClaw VM Platform - Frontend

基于 React 18 + TypeScript + Vite + TailwindCSS 构建的虚拟机管理平台前端。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TailwindCSS** - 样式框架
- **React Router** - 路由管理
- **Axios** - HTTP 客户端

## 项目结构

```
src/
├── api/              # API 请求封装
│   ├── client.ts     # Axios 实例配置
│   ├── auth.ts       # 认证相关 API
│   └── vm.ts         # VM 管理 API
├── components/       # 组件库
│   ├── atoms/        # 原子组件（Button, Input, Card 等）
│   ├── molecules/    # 分子组件
│   ├── organisms/    # 有机体组件
│   └── templates/    # 模板组件（Layout 等）
├── pages/            # 页面组件
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── VMListPage.tsx
├── types/            # TypeScript 类型定义
├── hooks/            # 自定义 Hooks
├── lib/              # 工具函数
├── App.tsx           # 根组件
└── main.tsx          # 入口文件
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
VITE_API_BASE_URL=http://localhost:3000/api
```

## 功能模块

### ✅ 已完成

- [x] 项目脚手架搭建
- [x] 路由配置（React Router）
- [x] API 请求封装（Axios + 拦截器）
- [x] 基础 UI 组件（Button, Input, Card, StatusBadge）
- [x] 登录/注册页面
- [x] VM 管理页面（列表、启动/停止/删除）

### 🚧 开发中

- [ ] VM 创建页面（选择套餐）
- [ ] Agent 市场页面
- [ ] 渠道配置页面
- [ ] 计费和账单页面
- [ ] 监控面板

## 组件规范

### 命名规范

- 组件文件：PascalCase（如 `Button.tsx`）
- 组件名称：与文件名一致
- CSS 类名：使用 TailwindCSS，避免自定义类名

### 类型安全

- 所有组件必须定义 TypeScript 类型
- Props 必须有明确的类型定义
- 避免使用 `any`，优先使用具体类型

### 性能优化

- 使用 `React.memo` 避免不必要渲染
- 使用 `useCallback` 缓存回调函数
- 大列表使用虚拟滚动（待实现）

### 可访问性（a11y）

- 所有交互元素支持键盘导航
- 表单元素关联 label
- 图片提供 alt 属性
- 颜色对比度符合 WCAG 标准

## API 接口

### 认证相关

- `POST /api/auth/login` - 登录
- `POST /api/auth/register` - 注册
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/logout` - 退出登录

### VM 管理

- `GET /api/vm/list` - 获取 VM 列表
- `GET /api/vm/:vmId` - 获取 VM 详情
- `POST /api/vm/create` - 创建 VM
- `POST /api/vm/:vmId/start` - 启动 VM
- `POST /api/vm/:vmId/stop` - 停止 VM
- `DELETE /api/vm/:vmId` - 删除 VM

## 测试

```bash
npm run test
```

## 部署

```bash
npm run build
```

将 `dist` 目录部署到静态文件服务器即可。

## 注意事项

1. **认证流程**：使用 JWT Token，存储在 localStorage
2. **错误处理**：API 错误会统一在 axios 拦截器中处理
3. **路由保护**：未登录用户访问受保护路由会重定向到登录页
4. **响应式设计**：支持移动端和桌面端

---

**开发进度**: Milestone 1 - 架构就绪 ✅
**下一步**: 等待后端 API 就绪，开始集成测试
