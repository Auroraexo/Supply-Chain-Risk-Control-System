import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';
import { Skeleton } from '@/components/ui/Skeleton';

export function ProtectedRoute() {
  const login = useAuthStore((state) => state.login);
  const clearSession = useAuthStore((state) => state.clearSession);
  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);
  const location = useLocation();

  useEffect(() => {
    let active = true;
    authService.getMe().then(res => {
      if (!active) return;
      login(res.data);
      setValid(true);
    }).catch(() => {
      if (!active) return;
      clearSession();
      setValid(false);
    }).finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, [clearSession, login]);

  if (checking) return <div className="space-y-4 p-6"><Skeleton className="h-10 w-72"/><Skeleton className="h-72 w-full"/></div>;

  if (!valid) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
