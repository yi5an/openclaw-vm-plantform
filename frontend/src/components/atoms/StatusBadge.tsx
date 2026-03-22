import React from 'react';

interface StatusBadgeProps {
  status: 'running' | 'stopped' | 'creating' | 'error' | 'active' | 'inactive';
  className?: string;
}

/**
 * StatusBadge 组件
 * 显示 VM 状态的徽章
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
}) => {
  const statusConfig = {
    running: { label: '运行中', color: 'bg-green-100 text-green-800' },
    stopped: { label: '已停止', color: 'bg-gray-100 text-gray-800' },
    creating: { label: '创建中', color: 'bg-blue-100 text-blue-800' },
    error: { label: '错误', color: 'bg-red-100 text-red-800' },
    active: { label: '活跃', color: 'bg-green-100 text-green-800' },
    inactive: { label: '未激活', color: 'bg-gray-100 text-gray-800' },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}
    >
      {config.label}
    </span>
  );
};
