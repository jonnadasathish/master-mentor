import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError } from '../api/client'

export interface ReportedError {
  id: number
  code: string
  message: string
  source: string
}

/** Central place where every unexpected UI/API error lands (shown by ErrorBanner). */
export const useErrorStore = defineStore('errors', () => {
  const errors = ref<ReportedError[]>([])
  let nextId = 1

  function report(error: unknown, source: string): ReportedError {
    const entry: ReportedError =
      error instanceof ApiError
        ? { id: nextId++, code: error.code, message: error.message, source }
        : { id: nextId++, code: 'UI_ERROR', message: error instanceof Error ? error.message : String(error), source }
    errors.value = [...errors.value.slice(-4), entry] // keep the last 5
    return entry
  }

  function dismiss(id: number): void {
    errors.value = errors.value.filter((entry) => entry.id !== id)
  }

  return { errors, report, dismiss }
})
