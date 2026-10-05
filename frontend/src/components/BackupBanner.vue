<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

/** Warns when the last database backup is missing or older than the configured age (D-075). */
const message = ref('')

onMounted(async () => {
  try {
    const status = (await api.get<{ warning: boolean; message: string }>('/system/backup-status')).data
    if (status.warning) message.value = status.message
  } catch {
    // Status is advisory; the error store already shows API failures elsewhere.
  }
})
</script>

<template>
  <p
    v-if="message"
    class="backup-warning"
    role="alert"
    data-testid="backup-warning"
  >
    ⚠ Backup: {{ message }}
  </p>
</template>

<style scoped>
.backup-warning { background: #fff1d6; border: 1px solid #c77700; padding: 0.4rem 0.75rem; border-radius: 6px; margin: 0 0 1rem; }
</style>
