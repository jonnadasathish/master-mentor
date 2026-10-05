<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'
import { useErrorStore } from '../../stores/errors'
import Icon from './Icon.vue'

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
    class="fallback"
    role="alert"
    data-testid="error-fallback"
  >
    <Icon
      name="alert-triangle"
      :size="22"
    />
    <p class="title">
      This page couldn't be shown.
    </p>
    <p class="muted">
      The rest of Master Mentor is still working.
    </p>
    <button
      type="button"
      class="btn btn-primary btn-sm"
      @click="retry"
    >
      Try again
    </button>
  </div>
  <slot v-else />
</template>

<style scoped>
.fallback { display: grid; justify-items: center; gap: var(--s-2); padding: var(--s-7) var(--s-4); text-align: center; color: var(--high-fg); }
.fallback .title { color: var(--text); font-weight: 700; }
.fallback p { color: var(--text); }
.fallback p { color: var(--text-3); }
</style>
