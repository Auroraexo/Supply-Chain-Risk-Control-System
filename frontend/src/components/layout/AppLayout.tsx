import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '@/components/ui/Toast';
import { useSidebarStore } from '@/stores/sidebarStore';
import { clsx } from 'clsx';

export function AppLayout() {
  const { collapsed } = useSidebarStore();

  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar />
      <div
        className={clsx(
          'transition-all duration-300',
          'lg:ml-16',
          !collapsed && 'lg:ml-60'
        )}
      >
        <Header />
        <main className="p-4 lg:p-6 max-w-[1400px] mx-auto">
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}