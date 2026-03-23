# OpenClaw VM Platform - UI Design System

## 🎨 设计原则

- **现代简洁**: 类似 Vercel、Linear、Stripe
- **专业化**: 企业级产品
- **科技感**: 虚拟化平台
- **响应式**: 支持桌面和移动端

---

## 🎨 配色方案

### 主色调
```css
--primary: #3B82F6;        /* 科技蓝 */
--primary-dark: #2563EB;   /* 深蓝 */
--primary-light: #60A5FA;  /* 浅蓝 */
```

### 辅助色
```css
--secondary: #8B5CF6;      /* 紫色 */
--accent: #06B6D4;         /* 青色 */
```

### 语义色
```css
--success: #10B981;        /* 绿色 */
--warning: #F59E0B;        /* 橙色 */
--error: #EF4444;          /* 红色 */
--info: #3B82F6;           /* 蓝色 */
```

### 灰度
```css
--gray-50: #F9FAFB;
--gray-100: #F3F4F6;
--gray-200: #E5E7EB;
--gray-300: #D1D5DB;
--gray-400: #9CA3AF;
--gray-500: #6B7280;
--gray-600: #4B5563;
--gray-700: #374151;
--gray-800: #1F2937;
--gray-900: #111827;
```

---

## 📝 字体

### 字体家族
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 字号
```css
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */
```

---

## 📐 间距

```css
--spacing-1: 0.25rem;    /* 4px */
--spacing-2: 0.5rem;     /* 8px */
--spacing-3: 0.75rem;    /* 12px */
--spacing-4: 1rem;       /* 16px */
--spacing-5: 1.25rem;    /* 20px */
--spacing-6: 1.5rem;     /* 24px */
--spacing-8: 2rem;       /* 32px */
--spacing-10: 2.5rem;    /* 40px */
--spacing-12: 3rem;      /* 48px */
```

---

## 🔲 圆角

```css
--rounded-sm: 0.25rem;   /* 4px */
--rounded: 0.375rem;     /* 6px */
--rounded-md: 0.5rem;    /* 8px */
--rounded-lg: 0.75rem;   /* 12px */
--rounded-xl: 1rem;      /* 16px */
--rounded-2xl: 1.5rem;   /* 24px */
--rounded-full: 9999px;
```

---

## 🌓 阴影

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
```

---

## 🧩 组件规范

### Button

**尺寸**:
- Small: h-8 px-3 text-sm
- Medium: h-10 px-4 text-base
- Large: h-12 px-6 text-lg

**样式**:
- Primary: bg-primary text-white hover:bg-primary-dark
- Secondary: bg-gray-100 text-gray-700 hover:bg-gray-200
- Danger: bg-error text-white hover:bg-red-600
- Ghost: bg-transparent text-gray-700 hover:bg-gray-100

### Card

```css
.card {
  bg-white;
  rounded-lg;
  shadow-md;
  border: 1px solid var(--gray-200);
  p-6;
}
```

### Badge

**状态颜色**:
- Running: bg-success/10 text-success
- Stopped: bg-gray-100 text-gray-600
- Error: bg-error/10 text-error
- Creating: bg-warning/10 text-warning

### Table

```css
.table-header {
  bg-gray-50;
  border-b: 2px solid var(--gray-200);
  text-gray-600;
  text-sm;
  font-medium;
}

.table-row {
  border-b: 1px solid var(--gray-100);
  hover:bg-gray-50;
}

.table-cell {
  py-4 px-6;
}
```

### Input

```css
.input {
  border: 1px solid var(--gray-300);
  rounded-md;
  px-4;
  py-2;
  focus:ring-2 focus:ring-primary focus:border-primary;
}
```

---

## 📱 响应式断点

```css
--breakpoint-sm: 640px;
--breakpoint-md: 768px;
--breakpoint-lg: 1024px;
--breakpoint-xl: 1280px;
--breakpoint-2xl: 1536px;
```

---

## 🎭 动画

```css
--transition-fast: 150ms ease;
--transition-base: 200ms ease;
--transition-slow: 300ms ease;
```

---

_设计系统 v1.0 - 2026-03-23_
