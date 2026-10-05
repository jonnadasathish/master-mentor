import type { App } from 'vue'
import { useErrorStore } from './stores/errors'

/**
 * Error-handling strategy:
 *  1. ErrorBoundary catches render/lifecycle errors of the current page (shell stays usable).
 *  2. app.config.errorHandler catches anything that escapes component boundaries.
 *  3. unhandledrejection catches failed promises outside components.
 * All three report to the error store, which ErrorBanner renders. API failures arrive as ApiError
 * carrying the server's error-envelope code.
 */
export function installGlobalErrorHandling(app: App, target: Window = window): void {
  const errorStore = useErrorStore()
  app.config.errorHandler = (error) => {
    errorStore.report(error, 'vue')
    console.error(error)
  }
  target.addEventListener('unhandledrejection', (event) => {
    errorStore.report(event.reason, 'promise')
  })
}
