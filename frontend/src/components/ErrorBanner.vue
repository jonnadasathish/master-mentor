<script setup lang="ts">
import { useErrorStore } from '../stores/errors'

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
      <strong>{{ entry.code }}</strong> {{ entry.message }}
      <button
        type="button"
        aria-label="Dismiss error"
        @click="errorStore.dismiss(entry.id)"
      >
        ×
      </button>
    </li>
  </ul>
</template>
