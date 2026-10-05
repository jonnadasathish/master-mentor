<script setup lang="ts">
/** Page title block: optional eyebrow, a strong title, a one-line description and an actions slot. */
defineProps<{ title: string; eyebrow?: string; description?: string }>()
</script>

<template>
  <header class="page-header">
    <div class="text">
      <p
        v-if="eyebrow"
        class="eyebrow"
      >
        {{ eyebrow }}
      </p>
      <h1>{{ title }}</h1>
      <p
        v-if="description"
        class="desc"
      >
        {{ description }}
      </p>
    </div>
    <div
      v-if="$slots.default"
      class="actions"
    >
      <slot />
    </div>
  </header>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-4); flex-wrap: wrap; }
.text { display: grid; gap: var(--s-1); min-width: 0; }
.desc { color: var(--text-2); max-width: 40rem; }
.actions { display: flex; gap: var(--s-2); flex-wrap: wrap; }
</style>
