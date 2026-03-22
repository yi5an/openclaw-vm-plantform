import apiClient from './client';
import type { LoginRequest, RegisterRequest, AuthResponse, User } from '../types';

export const authApi = {
  // 用户登录
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    // 使用 form-data 格式（后端要求）
    const formData = new URLSearchParams();
    formData.append('username', data.email); // 后端字段名是 username
    formData.append('password', data.password);

    const response = await apiClient.post<{ access_token: string }>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    // 保存 token
    const token = response.data.access_token;
    localStorage.setItem('auth_token', token);

    // 获取用户信息
    const userResponse = await apiClient.get<User>('/users/me');

    return {
      token,
      user: userResponse.data
    };
  },

  // 用户注册
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/register', data);
    return response.data;
  },

  // 获取当前用户信息
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  },

  // 退出登录
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
  },
};
