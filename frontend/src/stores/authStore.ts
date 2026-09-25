import { create } from 'zustand';
import type { User } from '@/types/models';

localStorage.removeItem('auth_token'); // Credentials now live in HttpOnly cookies.
const storedUser = localStorage.getItem('auth_user');

function readStoredUser(): User | null {
  if (!storedUser) return null;
  try {
    return JSON.parse(storedUser) as User;
  } catch {
    localStorage.removeItem('auth_user');
    return null;
  }
}

const initialUser = readStoredUser();

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
  clearSession: () => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: initialUser,
  // The cached user is display-only. Authentication must be confirmed by the
  // HttpOnly session cookie through /auth/me before protected routes render.
  isAuthenticated: false,
  login: (user) => {
    localStorage.setItem('auth_user', JSON.stringify(user));
    set({ user, isAuthenticated: true });
  },
  clearSession: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    set({ user: null, isAuthenticated: false });
  },
  logout: () => {
    void fetch(`${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/logout`, { method: 'POST', credentials: 'include' });
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    set({ user: null, isAuthenticated: false });
  },
  updateUser: (updates) =>
    set((state) => ({
      user: state.user
        ? (() => {
            const user = { ...state.user, ...updates };
            localStorage.setItem('auth_user', JSON.stringify(user));
            return user;
          })()
        : null,
    })),
}));
