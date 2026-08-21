import { useProgressStore } from '@/stores/progressStore';

export function TopProgressBar() {
  const { loading, progress } = useProgressStore();

  if (!loading) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-0.5">
      <div
        className="h-full bg-gradient-to-r from-accent-blue via-accent-cyan to-accent-purple transition-all duration-200 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}