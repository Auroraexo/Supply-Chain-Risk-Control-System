import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center p-12 text-center">
          <AlertTriangle size={48} className="text-risk-critical mb-4 opacity-60" />
          <h2 className="text-h2 text-text-primary mb-2">页面渲染异常</h2>
          <p className="text-body text-text-secondary mb-4 max-w-md">
            {this.state.error?.message || '页面组件发生未知错误'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 rounded-btn bg-accent-blue text-white text-body font-medium hover:bg-accent-blue/80 transition-colors"
          >
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}