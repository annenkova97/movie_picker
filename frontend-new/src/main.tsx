import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GoogleOAuthProvider } from '@react-oauth/google';
import * as Sentry from '@sentry/react';
import './styles/global.css';
import App from './App';
import { AuthProvider } from './auth';
import { ErrorBoundary } from './components/ErrorBoundary';

// Sentry: включается только когда в сборку передан VITE_SENTRY_DSN.
const sentryDsn = (import.meta.env.VITE_SENTRY_DSN as string | undefined) || '';
if (sentryDsn) {
  Sentry.init({ dsn: sentryDsn, sendDefaultPii: false });
}

const qc = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) || '';

const Root = (
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

ReactDOM.createRoot(document.getElementById('root')!).render(
  googleClientId ? (
    <GoogleOAuthProvider clientId={googleClientId}>{Root}</GoogleOAuthProvider>
  ) : (
    Root
  ),
);
