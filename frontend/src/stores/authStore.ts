import { create } from 'zustand';
import type { User } from '@/types/models';

const storedToken = localStorage.getItem('auth_token');
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
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: initialUser,
  token: storedToken,
  isAuthenticated: Boolean(initialUser && storedToken),
  login: (user, token) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_user', JSON.stringify(user));
    set({ user, token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    set({ user: null, token: null, isAuthenticated: false });
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
