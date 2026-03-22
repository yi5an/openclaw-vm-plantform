import React, { useState, useEffect } from 'react';
import { Button } from '../components/atoms/Button';
import { Card } from '../components/atoms/Card';
import { StatusBadge } from '../components/atoms/StatusBadge';
import { MainLayout } from '../components/templates/MainLayout';
import { vmApi } from '../api/vm';
import type { VM } from '../types';

/**
 * VM 管理页面
 * 显示用户的虚拟机列表，支持启动/停止/删除操作
 */
export const VMListPage: React.FC = () => {
  const [vms, setVMs] = useState<VM[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadVMs();
  }, []);

  const loadVMs = async () => {
    try {
      setLoading(true);
      const data = await vmApi.getVMList();
      setVMs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 VM 列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (vmId: string) => {
    try {
      await vmApi.startVM(vmId);
      await loadVMs();
    } catch (err) {
      alert(err instanceof Error ? err.message : '启动失败');
    }
  };

  const handleStop = async (vmId: string) => {
    if (!confirm('确定要停止这个虚拟机吗？')) return;
    
    try {
      await vmApi.stopVM(vmId);
      await loadVMs();
    } catch (err) {
      alert(err instanceof Error ? err.message : '停止失败');
    }
  };

  const handleDelete = async (vmId: string) => {
    if (!confirm('确定要删除这个虚拟机吗？此操作不可恢复。')) return;
    
    try {
      await vmApi.deleteVM(vmId);
      await loadVMs();
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败');
    }
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">加载中...</div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="px-4 py-6 sm:px-0">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">我的虚拟机</h1>
          <Button onClick={() => alert('创建 VM 功能开发中...')}>
            创建虚拟机
          </Button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {vms.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">您还没有创建虚拟机</p>
              <Button onClick={() => alert('创建 VM 功能开发中...')}>
                创建第一个虚拟机
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {vms.map(vm => (
              <Card key={vm.id}>
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{vm.name}</h3>
                      <p className="text-sm text-gray-500">{vm.planName}</p>
                    </div>
                    <StatusBadge status={vm.status} />
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">CPU:</span>
                      <span className="font-medium">{vm.cpu} 核</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">内存:</span>
                      <span className="font-medium">{vm.memory} GB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">磁盘:</span>
                      <span className="font-medium">{vm.disk} GB</span>
                    </div>
                    {vm.ip && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">IP:</span>
                        <span className="font-medium">{vm.ip}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex space-x-2 pt-4 border-t">
                    {vm.status === 'stopped' && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleStart(vm.id)}
                        className="flex-1"
                      >
                        启动
                      </Button>
                    )}
                    {vm.status === 'running' && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStop(vm.id)}
                        className="flex-1"
                      >
                        停止
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDelete(vm.id)}
                      className="flex-1"
                    >
                      删除
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
};
