import apiClient from './client';
import type { VM, Plan, CreateVMRequest } from '../types';

export const vmApi = {
  // 获取 VM 列表
  getVMList: async (): Promise<VM[]> => {
    const response = await apiClient.get<VM[]>('/vm/list');
    return response.data;
  },

  // 获取 VM 详情
  getVMDetail: async (vmId: string): Promise<VM> => {
    const response = await apiClient.get<VM>(`/vm/${vmId}`);
    return response.data;
  },

  // 创建 VM
  createVM: async (data: CreateVMRequest): Promise<VM> => {
    const response = await apiClient.post<VM>('/vm/create', data);
    return response.data;
  },

  // 启动 VM
  startVM: async (vmId: string): Promise<void> => {
    await apiClient.post(`/vm/${vmId}/start`);
  },

  // 停止 VM
  stopVM: async (vmId: string): Promise<void> => {
    await apiClient.post(`/vm/${vmId}/stop`);
  },

  // 删除 VM
  deleteVM: async (vmId: string): Promise<void> => {
    await apiClient.delete(`/vm/${vmId}`);
  },

  // 获取套餐列表
  getPlans: async (): Promise<Plan[]> => {
    const response = await apiClient.get<Plan[]>('/plans');
    return response.data;
  },
};
