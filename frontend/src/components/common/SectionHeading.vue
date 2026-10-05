<script setup lang="ts">
/** A quiet uppercase section label with an optional right-aligned link/action. */
defineProps<{ title: string; id?: string }>()
</script>

<template>
  <div class="section-heading">
    <h2
      :id="id"
      class="eyebrow"
    >
      {{ title }}
    </h2>
    <div
      v-if="$slots.default"
      class="aside"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: var(--s-3); margin-bottom: var(--s-3); }
.eyebrow { margin: 0; font-size: var(--fs-xs); letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-3); font-weight: 650; }
.aside { font-size: var(--fs-sm); }
</style>
