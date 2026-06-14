import React from 'react';
import * as Sentry from '@sentry/react';

interface State {
  error: Error | null;
}

/**
 * Глобальный error boundary: вместо «белого экрана» при упавшем рендере —
 * понятный fallback с кнопкой перезагрузки. Ошибка улетает в Sentry, если
 * он инициализирован (без DSN captureException — безопасный no-op).
 */
export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div
        style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 14,
          padding: 24, textAlign: 'center',
          fontFamily: 'var(--font-body, system-ui)',
          color: 'var(--color-cream, #e9d9a7)',
        }}
      >
        <div style={{ fontSize: 40 }} aria-hidden>🎬</div>
        <div style={{ fontSize: 18, fontWeight: 700 }}>Что-то сломалось</div>
        <div style={{ fontSize: 14, opacity: 0.7, maxWidth: 360 }}>
          Мы уже знаем об ошибке. Попробуй перезагрузить страницу — обычно помогает.
        </div>
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: 6, padding: '10px 22px', borderRadius: 999,
            border: '1px solid var(--color-gold, #c9a84c)',
            background: 'transparent', color: 'var(--color-gold, #c9a84c)',
            fontSize: 14, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Перезагрузить
        </button>
      </div>
    );
  }
}
