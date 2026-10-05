<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { ApiError } from '../api/client'

/** Import a JSON export into an EMPTY database: preview (writes nothing) -> typed confirmation -> commit. */
interface Preview { ok: boolean; errors: string[]; warnings: string[]; counts: Record<string, number>; confirmation: string; exported_at: string | null }
const doc = ref<Record<string, unknown> | null>(null)
const preview = ref<Preview | null>(null)
const typed = ref('')
const result = ref('')
const error = ref('')

function readText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error ?? new Error('read failed'))
    reader.readAsText(file)
  })
}

async function onFile(event: Event): Promise<void> {
  error.value = ''
  result.value = ''
  preview.value = null
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    doc.value = JSON.parse(await readText(file)) as Record<string, unknown>
    preview.value = (await api.post<Preview>('/import/preview', doc.value)).data
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : `Not a valid JSON export (${String(caught)})`
  }
}

async function commit(): Promise<void> {
  if (!doc.value || !preview.value) return
  try {
    const data = (await api.post<{ inserted: Record<string, number> }>('/import/commit', { document: doc.value, confirm: typed.value })).data
    result.value = `Imported ${Object.values(data.inserted).reduce((a, b) => a + b, 0)} rows; derived state rebuilt.`
    preview.value = null
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}
</script>

<template>
  <section
    class="import"
    data-testid="import-panel"
  >
    <p>Restore a JSON export into an empty database (fresh install or after a dev reset). Existing history is never overwritten.</p>
    <label>Export file <input
      type="file"
      accept="application/json,.json"
      data-testid="import-file"
      @change="onFile"
    ></label>
    <template v-if="preview">
      <p v-if="preview.exported_at">
        Exported {{ preview.exported_at }}
      </p>
      <ul data-testid="import-counts">
        <li
          v-for="(n, table) in preview.counts"
          :key="table"
        >
          {{ table }}: {{ n }}
        </li>
      </ul>
      <ul
        v-if="preview.errors.length"
        role="alert"
        class="errors"
        data-testid="import-errors"
      >
        <li
          v-for="e in preview.errors"
          :key="e"
        >
          {{ e }}
        </li>
      </ul>
      <template v-else>
        <label>Type <code>{{ preview.confirmation }}</code> to import
          <input
            v-model="typed"
            data-testid="import-confirm"
          >
        </label>
        <button
          type="button"
          :disabled="typed !== preview.confirmation"
          data-testid="import-commit"
          @click="commit"
        >
          Import
        </button>
      </template>
    </template>
    <p
      v-if="result"
      role="status"
    >
      {{ result }}
    </p>
    <p
      v-if="error"
      role="alert"
      class="errors"
    >
      {{ error }}
    </p>
  </section>
</template>

<style scoped>
.import { display: flex; flex-direction: column; gap: 0.4rem; max-width: 40rem; }
label { display: flex; flex-direction: column; font-size: 0.85rem; }
.errors { color: #a11; }
</style>
