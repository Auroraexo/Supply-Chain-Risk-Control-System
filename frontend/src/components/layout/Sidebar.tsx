import { memo, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard, Database, Search, Scale, GitBranch, Settings,
  ChevronLeft, ChevronRight, LogOut, Shield,
} from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useAuthStore } from '@/stores/authStore';

interface NavItem {
  label: string;
  icon: React.ReactNode;
  path: string;
  roles?: string[];
}

const mainNav: NavItem[] = [
  { label: '仪表盘', icon: <LayoutDashboard size={20} />, path: '/dashboard' },
  { label: '原始数据', icon: <Database size={20} />, path: '/raw-data' },
  { label: '风险分析', icon: <Search size={20} />, path: '/analysis' },
  { label: '决策管理', icon: <Scale size={20} />, path: '/decisions' },
  { label: '规则引擎', icon: <GitBranch size={20} />, path: '/rules', roles: ['admin', 'decider'] },
];

const bottomNav: NavItem[] = [
  { label: '系统设置', icon: <Settings size={20} />, path: '/settings/llm', roles: ['admin'] },
];

/** 导航项按钮 — 组件化避免父组件重渲染时重建子树 */
const NavButton = memo(function NavButton({
  item,
  active,
  collapsed,
  disabled,
  onClick,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      disabled={disabled}
      className={clsx(
        'w-full flex items-center gap-3 px-3 py-2.5 rounded-btn transition-all duration-200 select-none',
        active
          ? 'bg-accent-blue/15 text-accent-blue shadow-glow-blue'
          : 'text-text-secondary hover:bg-bg-tertiary/50 hover:text-text-primary',
        disabled && 'opacity-40 cursor-not-allowed',
        collapsed && 'justify-center'
      )}
    >
      {item.icon}
      {!collapsed && <span className="text-body font-medium">{item.label}</span>}
    </button>
  );
});

/** 桌面端侧边栏内容 — 独立组件 + React.memo 避免 AppLayout 重渲染时闪烁 */
const SidebarContent = memo(function SidebarContent({
  collapsed,
  isMobile,
  onNavClick,
  onCloseMobile,
}: {
  collapsed: boolean;
  isMobile: boolean;
  onNavClick: (item: NavItem) => void;
  onCloseMobile: () => void;
}) {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = useCallback(
    (path: string) => {
      if (path === '/dashboard') return location.pathname === '/dashboard';
      return location.pathname.startsWith(path);
    },
    [location.pathname]
  );

  const handleNavClick = useCallback(
    (item: NavItem) => {
      if (item.roles && user && !item.roles.includes(user.role)) return;
      onNavClick(item);
    },
    [user, onNavClick]
  );

  const handleLogout = useCallback(() => {
    logout();
    navigate('/login');
  }, [logout, navigate]);

  return (
    <div
      className="flex flex-col h-full"
      onClick={isMobile ? (e) => e.stopPropagation() : undefined}
    >
      {/* Logo */}
      <div className={clsx('flex items-center gap-2 px-4 py-5 border-b border-border', collapsed && 'justify-center')}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center flex-shrink-0">
          <Shield size={18} className="text-white" />
        </div>
        {!collapsed && <span className="text-h3 font-semibold text-text-primary whitespace-nowrap">SCRS</span>}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {mainNav.map((item) => (
          <NavButton
            key={item.path}
            item={item}
            active={isActive(item.path)}
            collapsed={collapsed}
            disabled={!!(item.roles && user && !item.roles.includes(user.role))}
            onClick={() => handleNavClick(item)}
          />
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="px-2 pb-2 space-y-1 border-t border-border pt-2">
        {bottomNav.map((item) => (
          <NavButton
            key={item.path}
            item={item}
            active={isActive(item.path)}
            collapsed={collapsed}
            disabled={!!(item.roles && user && !item.roles.includes(user.role))}
            onClick={() => handleNavClick(item)}
          />
        ))}
        <button
          onClick={handleLogout}
          title={collapsed ? '退出' : undefined}
          className={clsx(
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-btn text-text-secondary hover:bg-risk-critical/10 hover:text-risk-critical transition-all duration-200 select-none',
            collapsed && 'justify-center'
          )}
        >
          <LogOut size={20} />
          {!collapsed && <span className="text-body font-medium">退出登录</span>}
        </button>
      </div>
    </div>
  );
});

export function Sidebar() {
  const { collapsed, mobileOpen, toggleCollapsed, setMobileOpen } = useSidebarStore();
  const navigate = useNavigate();

  const handleNavClick = useCallback(
    (item: NavItem) => {
      if (mobileOpen) {
        // 移动端：先关闭侧边栏（等待动画），再导航
        setMobileOpen(false);
        setTimeout(() => {
          navigate(item.path);
        }, 300);
      } else {
        // 桌面端：直接导航
        navigate(item.path);
      }
    },
    [mobileOpen, setMobileOpen, navigate]
  );

  const handleCloseMobile = useCallback(() => {
    setMobileOpen(false);
  }, [setMobileOpen]);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={clsx(
          'hidden lg:flex flex-col fixed top-0 left-0 h-screen bg-bg-secondary border-r border-border z-30',
          'transition-all duration-300 will-change-[width]',
          collapsed ? 'w-16' : 'w-60'
        )}
      >
        <SidebarContent
          collapsed={collapsed}
          isMobile={false}
          onNavClick={handleNavClick}
          onCloseMobile={handleCloseMobile}
        />
        {/* Collapse Toggle (Desktop) */}
        <div className="px-2 pb-3 mt-auto">
          <button
            onClick={toggleCollapsed}
            className="w-full flex items-center justify-center py-2 rounded-btn text-text-muted hover:text-text-primary hover:bg-bg-tertiary/50 transition-all duration-200"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-30">
          {/* 遮罩层 */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
            onClick={handleCloseMobile}
          />
          {/* 侧边栏 — stopPropagation 防止点击事件冒泡到遮罩层 */}
          <aside
            className="absolute top-0 left-0 h-screen w-60 bg-bg-secondary border-r border-border animate-slide-in-right"
            onClick={(e) => e.stopPropagation()}
          >
            <SidebarContent
              collapsed={false}
              isMobile={true}
              onNavClick={handleNavClick}
              onCloseMobile={handleCloseMobile}
            />
          </aside>
        </div>
      )}
    </>
  );
}