import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VMListPage } from './pages/VMListPage';
import { ProtectedRoute } from './components/templates/ProtectedRoute';

/**
 * App 组件
 * 路由配置和根组件
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        {/* 受保护路由 */}
        <Route
          path="/vms"
          element={
            <ProtectedRoute>
              <VMListPage />
            </ProtectedRoute>
          }
        />
        
        {/* 默认重定向 */}
        <Route path="/" element={<Navigate to="/vms" replace />} />
        <Route path="*" element={<Navigate to="/vms" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
