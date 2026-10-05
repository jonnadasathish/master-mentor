<script setup lang="ts">
import { friendlyFromCode } from '../../presentation/errors'
import { useErrorStore } from '../../stores/errors'
import Icon from './Icon.vue'

/** Unexpected errors (render failures, failed writes) as calm, dismissible notices. */
const errorStore = useErrorStore()
</script>

<template>
  <ul
    v-if="errorStore.errors.length"
    class="error-banner"
    aria-live="polite"
  >
    <li
      v-for="entry in errorStore.errors"
      :key="entry.id"
      role="alert"
    >
      <Icon
        name="alert-triangle"
        :size="16"
      />
      <div class="text">
        <strong>{{ friendlyFromCode(entry.code).title }}</strong>
        <details>
          <summary>Technical details</summary>
          <code>{{ entry.code }} · {{ entry.source }} · {{ entry.message }}</code>
        </details>
      </div>
      <button
        type="button"
        class="btn btn-ghost btn-sm"
        aria-label="Dismiss"
        @click="errorStore.dismiss(entry.id)"
      >
        <Icon
          name="x"
          :size="14"
        />
      </button>
    </li>
  </ul>
</template>

<style scoped>
.error-banner { display: grid; gap: var(--s-2); margin-bottom: var(--s-4); }
li { display: flex; align-items: flex-start; gap: var(--s-3); background: var(--high-bg); color: var(--high-fg); border: 1px solid var(--high-bd); border-radius: var(--r-md); padding: var(--s-3) var(--s-4); }
.text { flex: 1; min-width: 0; display: grid; gap: var(--s-1); }
details { font-size: var(--fs-sm); color: var(--text-2); }
summary { cursor: pointer; }
code { font-family: var(--font-mono); font-size: var(--fs-xs); overflow-wrap: anywhere; display: block; }
</style>
