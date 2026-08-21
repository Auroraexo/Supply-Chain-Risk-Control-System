import { create } from 'zustand';

interface ProgressState {
  loading: boolean;
  progress: number;
  start: () => void;
  done: () => void;
  set: (n: number) => void;
}

export const useProgressStore = create<ProgressState>((set, get) => {
  let timer: ReturnType<typeof setInterval> | null = null;
  let hideTimer: ReturnType<typeof setTimeout> | null = null;

  return {
    loading: false,
    progress: 0,

    start: () => {
      if (timer) clearInterval(timer);
      if (hideTimer) clearTimeout(hideTimer);
      set({ loading: true, progress: 0 });

      // 模拟进度增长：快速到 40%，然后缓慢增长到 90%
      timer = setInterval(() => {
        const { progress } = get();
        if (progress < 40) {
          set({ progress: progress + Math.random() * 15 + 5 });
        } else if (progress < 90) {
          set({ progress: progress + Math.random() * 3 + 0.5 });
        } else {
          if (timer) clearInterval(timer);
        }
      }, 200);
    },

    done: () => {
      if (timer) clearInterval(timer);
      set({ progress: 100 });
      hideTimer = setTimeout(() => {
        set({ loading: false, progress: 0 });
      }, 300);
    },

    set: (n: number) => {
      set({ progress: Math.min(n, 100) });
    },
  };
});