// API 响应通用格式
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 用户相关类型
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  createdAt: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}

// VM 相关类型
export interface VM {
  id: string;
  userId: string;
  name: string;
  status: 'running' | 'stopped' | 'creating' | 'error';
  planId: string;
  planName: string;
  cpu: number;
  memory: number;
  disk: number;
  ip?: string;
  createdAt: string;
  expiredAt: string;
}

export interface Plan {
  id: string;
  name: string;
  description: string;
  price: number;
  cpu: number;
  memory: number;
  disk: number;
  maxAgents: number;
  maxChannels: number;
}

export interface CreateVMRequest {
  planId: string;
  name?: string;
}

// Agent 相关类型
export interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
}

export interface AgentConfig {
  agentId: string;
  enabled: boolean;
  config?: Record<string, any>;
}

// 渠道相关类型
export interface Channel {
  id: string;
  vmId: string;
  type: 'telegram' | 'whatsapp' | 'feishu';
  config: Record<string, any>;
  status: 'active' | 'inactive';
}

// 计费相关类型
export interface TokenUsage {
  vmId: string;
  agentId: string;
  tokens: number;
  cost: number;
  timestamp: string;
}

export interface Order {
  id: string;
  userId: string;
  planId: string;
  amount: number;
  status: 'pending' | 'paid' | 'failed';
  createdAt: string;
}
