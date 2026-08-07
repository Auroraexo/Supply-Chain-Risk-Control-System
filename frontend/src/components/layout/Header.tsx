import { Menu, Bell, Search } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useAuthStore } from '@/stores/authStore';

export function Header() {
  const { setMobileOpen } = useSidebarStore();
  const { user } = useAuthStore();

  const roleLabels: Record<string, string> = {
    admin: '系统管理员',
    analyst: '风险分析师',
    decider: '决策者',
  };

  return (
    <header className="sticky top-0 z-20 bg-bg-primary/80 backdrop-blur-md border-b border-border">
      <div className="flex items-center justify-between h-14 px-4 lg:px-6">
        {/* Left */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden text-text-secondary hover:text-text-primary transition-colors"
          >
            <Menu size={20} />
          </button>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-input bg-bg-tertiary/50 border border-border">
            <Search size={14} className="text-text-muted" />
            <input
              type="text"
              placeholder="搜索..."
              className="bg-transparent text-body text-text-primary placeholder:text-text-muted outline-none w-40"
            />
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          <button className="relative p-2 rounded-btn text-text-secondary hover:text-text-primary hover:bg-bg-tertiary/50 transition-colors">
            <Bell size={18} />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-risk-critical animate-pulse-dot" />
          </button>
          {user && (
            <div className="flex items-center gap-2 pl-2 border-l border-border">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-caption font-medium text-white">
                {user.username[0].toUpperCase()}
              </div>
              <div className="hidden sm:block">
                <p className="text-caption text-text-primary font-medium">{user.username}</p>
                <p className="text-caption text-text-muted">{roleLabels[user.role] || user.role}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}