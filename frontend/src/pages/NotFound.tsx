import { useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-accent-blue/10 flex items-center justify-center mb-6">
        <Compass size={32} className="text-accent-blue" />
      </div>
      <p className="text-display font-mono text-text-muted">404</p>
      <h1 className="text-h2 text-text-primary mt-2">页面不存在</h1>
      <p className="text-body text-text-secondary mt-2">您访问的页面不存在或已被移动</p>
      <Button className="mt-6" onClick={() => navigate('/dashboard')}>
        返回仪表盘
      </Button>
    </div>
  );
}
