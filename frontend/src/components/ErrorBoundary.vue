<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'
import { useErrorStore } from '../stores/errors'

/** Catches render/lifecycle errors from child views so one broken page never blanks the shell. */
const failed = ref(false)
const errorStore = useErrorStore()

onErrorCaptured((error) => {
  failed.value = true
  errorStore.report(error, 'component')
  return false // handled: stop propagation to app.config.errorHandler
})

function retry(): void {
  failed.value = false
}
</script>

<template>
  <div
    v-if="failed"
    role="alert"
    data-testid="error-fallback"
  >
    <p>This page failed to render.</p>
    <button
      type="button"
      @click="retry"
    >
      Try again
    </button>
  </div>
  <slot v-else />
</template>
