import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '@/components/ui/Toast';
import { TopProgressBar } from '@/components/ui/TopProgressBar';
import { PageTransition } from '@/components/ui/PageTransition';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { useSidebarStore } from '@/stores/sidebarStore';
import { clsx } from 'clsx';

export function AppLayout() {
  const { collapsed } = useSidebarStore();

  return (
    <div className="min-h-screen bg-bg-primary">
      <TopProgressBar />
      <Sidebar />
      <div
        className={clsx(
          'transition-all duration-300',
          'lg:ml-16',
          !collapsed && 'lg:ml-60'
        )}
      >
        <Header />
        <main className="mx-auto w-full max-w-[1600px] p-4 sm:p-5 lg:p-7">
          <ErrorBoundary>
            <PageTransition>
              <Outlet />
            </PageTransition>
          </ErrorBoundary>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
