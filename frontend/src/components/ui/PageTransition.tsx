import { useLocation } from 'react-router-dom';
import { clsx } from 'clsx';

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

export function PageTransition({ children, className }: PageTransitionProps) {
  const location = useLocation();

  return (
    <div
      key={location.pathname}
      className={clsx('animate-page-enter', className)}
    >
      {children}
    </div>
  );
}