import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, Menu, Moon, Search, Sun, X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/hooks/useTheme';

const routeLabels: Array<[string, string]> = [
  ['/dashboard', '风险态势'], ['/raw-data', '数据中心'], ['/analysis', '风险分析'],
  ['/decisions', '决策审批'], ['/rules', '规则策略'], ['/settings', '系统管理'],
];

export function Header() {
  const { setMobileOpen } = useSidebarStore();
  const { user } = useAuthStore();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const pageLabel = routeLabels.find(([path]) => location.pathname.startsWith(path))?.[1] || '风险控制中心';

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    navigate(`/analysis?q=${encodeURIComponent(value)}`);
    setSearchOpen(false);
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg-primary/90 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between gap-3 px-4 sm:px-5 lg:px-7">
        <div className="flex min-w-0 items-center gap-3">
          <button onClick={() => setMobileOpen(true)} aria-label="打开导航菜单" className="rounded-btn p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary lg:hidden"><Menu size={20}/></button>
          <div className="hidden sm:block"><p className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-muted">Supply Chain Risk Control</p><p className="text-body font-semibold text-text-primary">{pageLabel}</p></div>
        </div>

        <div className="flex items-center gap-1.5">
          <form onSubmit={handleSearch} className={`${searchOpen ? 'flex' : 'hidden'} absolute inset-x-3 top-2 z-30 h-12 items-center rounded-card border border-accent-blue bg-bg-secondary px-3 shadow-card-hover sm:static sm:flex sm:h-9 sm:w-64 sm:border-border sm:bg-bg-secondary sm:shadow-none`}>
            <Search size={15} className="flex-none text-text-muted"/><input autoFocus={searchOpen} value={query} onChange={e => setQuery(e.target.value)} type="search" placeholder="搜索请求 ID、风险事件..." aria-label="全局搜索" className="min-w-0 flex-1 bg-transparent px-2 text-caption text-text-primary outline-none placeholder:text-text-muted"/><button type="button" className="p-1 text-text-muted sm:hidden" onClick={() => setSearchOpen(false)} aria-label="关闭搜索"><X size={17}/></button>
          </form>
          <button onClick={() => setSearchOpen(true)} aria-label="打开搜索" className="rounded-btn p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary sm:hidden"><Search size={18}/></button>
          <button onClick={toggleTheme} aria-label={theme === 'dark' ? '切换浅色主题' : '切换深色主题'} className="rounded-btn p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary">{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</button>
          <div className="relative">
            <button onClick={() => setNotificationsOpen(v => !v)} aria-label="通知" aria-expanded={notificationsOpen} className="relative rounded-btn p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"><Bell size={18}/><span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full border-2 border-bg-primary bg-risk-critical"/></button>
            {notificationsOpen && <div className="absolute right-0 top-11 w-80 rounded-card border border-border bg-bg-secondary p-4 shadow-card-hover"><div className="flex items-center justify-between"><p className="text-body font-semibold text-text-primary">通知中心</p><button className="text-caption text-accent-blue" onClick={() => navigate('/analysis')}>查看风险队列</button></div><div className="mt-4 rounded-btn bg-bg-tertiary/50 p-4 text-center"><p className="text-caption font-medium text-text-primary">暂无未读通知</p><p className="mt-1 text-[12px] text-text-muted">新的重大风险和审批任务会在这里提示</p></div></div>}
          </div>
          {user && <div className="ml-1 flex items-center gap-2 border-l border-border pl-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-blue text-caption font-bold text-white">{user.username[0].toUpperCase()}</div><div className="hidden md:block"><p className="max-w-28 truncate text-caption font-semibold text-text-primary">{user.username}</p><p className="text-[11px] text-text-muted">{user.role}</p></div></div>}
        </div>
      </div>
    </header>
  );
}
