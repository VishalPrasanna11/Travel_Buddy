import React from 'react'
import ReactDOM from 'react-dom/client'
import './global.css'
import { BrowserRouter as Router } from "react-router-dom"
import AppRouter from './AppRouter'
import Auth0ProviderWithPopup from './auth/Auth0ProviderwithPopUp'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { ErrorBoundary } from './components/system/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
        <Router>
          <QueryClientProvider client={queryClient}>
            <Auth0ProviderWithPopup>
              <AppRouter />
              <Toaster
                visibleToasts={1}
                position="top-center"
                toastOptions={{
                  classNames: {
                    toast: 'rounded-xl border border-border bg-background text-foreground shadow-overlay font-sans',
                    description: 'text-muted-foreground',
                    error: 'border-red/30 bg-danger-tint',
                    success: 'border-leaf-green/40 bg-success-tint',
                  },
                }}
              />
            </Auth0ProviderWithPopup>
          </QueryClientProvider>
        </Router>
    </ErrorBoundary>
  </React.StrictMode>
)
