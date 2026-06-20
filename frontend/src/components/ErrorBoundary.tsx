import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Component stack:', errorInfo.componentStack);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '40px',
          fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
          backgroundColor: '#fff3f0',
          margin: '20px',
          borderRadius: '8px',
          border: '1px solid #ffccc7',
        }}>
          <h2 style={{ color: '#cf1322', marginBottom: '16px' }}>
            ⚠️ 应用渲染出错
          </h2>
          <details open>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold', marginBottom: '12px' }}>
              错误详情 (点击展开/折叠)
            </summary>
            <pre style={{
              background: '#fff1f0',
              padding: '16px',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '13px',
              color: '#cf1322',
              border: '1px solid #ffa39e',
            }}>
              {this.state.error?.message}
              {'\n\n'}
              {this.state.error?.stack}
              {'\n\n--- Component Stack ---\n'}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '16px',
              padding: '8px 24px',
              background: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            🔄 刷新页面
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
