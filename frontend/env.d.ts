/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base path of the backend API (default "/api/v1", proxied by Vite in development). */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}
