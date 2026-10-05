<script setup lang="ts">
import { onMounted } from 'vue'
import { api } from '../api'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
onMounted(() => system.fetchHealth(api))
</script>

<template>
  <section>
    <h1>System status</h1>
    <p v-if="system.loading">
      Checking…
    </p>
    <dl
      v-else-if="system.health"
      data-testid="health"
    >
      <dt>Database</dt>
      <dd>{{ system.health.db }}</dd>
      <dt>Ruleset</dt>
      <dd>{{ system.health.ruleset_version }}</dd>
      <dt>Seed</dt>
      <dd>{{ system.health.seed_version ?? 'not loaded (Slice 2)' }}</dd>
    </dl>
    <p
      v-else-if="system.error"
      role="alert"
      data-testid="health-error"
    >
      {{ system.error.code }}: {{ system.error.message }}
    </p>
    <button
      type="button"
      @click="system.fetchHealth(api)"
    >
      Check again
    </button>
  </section>
</template>
