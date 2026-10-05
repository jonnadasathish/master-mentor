<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../../api'
import Icon from '../common/Icon.vue'

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
    <Icon
      name="alert-triangle"
      :size="16"
    />
    <span><strong>Backup:</strong> {{ message }}</span>
  </p>
</template>

<style scoped>
.backup-warning { display: flex; align-items: flex-start; gap: var(--s-2); background: var(--medium-bg); color: var(--medium-fg); border: 1px solid var(--medium-bd); padding: var(--s-3) var(--s-4); border-radius: var(--r-md); margin: 0 0 var(--s-4); font-size: var(--fs-sm); }
.backup-warning :deep(svg) { margin-top: 0.15rem; }
</style>
