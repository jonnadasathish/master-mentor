<script setup lang="ts">
import { computed } from 'vue'
import { ApiError } from '../../api/client'
import { friendlyError } from '../../presentation/errors'
import Icon from './Icon.vue'

/** A calm error with a Retry action; technical details stay available but collapsed. */
const props = defineProps<{ error: unknown }>()
defineEmits<{ retry: [] }>()

const info = computed(() => friendlyError(props.error))
const technical = computed(() => {
  const e = props.error
  if (e instanceof ApiError) return `${e.code}${e.status ? ` (HTTP ${e.status})` : ''}: ${e.message}`
  return e instanceof Error ? e.message : String(e)
})
</script>

<template>
  <div
    class="error-state"
    role="alert"
    data-testid="error-state"
  >
    <span
      class="badge"
      aria-hidden="true"
    ><Icon
      name="alert-triangle"
      :size="20"
    /></span>
    <div class="body">
      <p class="title">
        {{ info.title }}
      </p>
      <p class="muted">
        {{ info.body }}
      </p>
      <div class="row">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          data-testid="retry"
          @click="$emit('retry')"
        >
          <Icon
            name="refresh"
            :size="14"
          /> Retry
        </button>
      </div>
      <details class="tech">
        <summary>Technical details</summary>
        <code>{{ technical }}</code>
      </details>
    </div>
  </div>
</template>

<style scoped>
.error-state { display: flex; gap: var(--s-4); padding: var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.badge { display: grid; place-items: center; flex: none; width: 2.6rem; height: 2.6rem; border-radius: 50%; background: var(--high-bg); color: var(--high-fg); }
.title { font-size: var(--fs-md); font-weight: 700; letter-spacing: -0.01em; }
.body { display: grid; gap: var(--s-2); min-width: 0; }
.tech { font-size: var(--fs-sm); color: var(--text-3); }
.tech summary { cursor: pointer; }
.tech code { display: block; margin-top: var(--s-1); font-family: var(--font-mono); font-size: var(--fs-xs); overflow-wrap: anywhere; }
</style>
