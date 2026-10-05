<script setup lang="ts">
/** A code listing with its language. Plain text only: nothing is evaluated or highlighted as HTML. */
defineProps<{ code: string; language?: string; explanation?: string }>()
</script>

<template>
  <figure class="code">
    <figcaption
      v-if="language && language !== 'text'"
      class="lang"
    >
      {{ language }}
    </figcaption>
    <pre tabindex="0"><code>{{ code }}</code></pre>
    <p
      v-if="explanation"
      class="explain"
    >
      {{ explanation }}
    </p>
  </figure>
</template>

<style scoped>
.code { margin: 0; display: grid; gap: var(--s-2); min-width: 0; }
.lang { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
pre {
  margin: 0; padding: var(--s-4); background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-md);
  overflow-x: auto; font-family: var(--font-mono); font-size: var(--fs-sm); line-height: 1.55; color: var(--text);
  overflow-wrap: normal; white-space: pre;
}
pre:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.explain { font-size: var(--fs-sm); color: var(--text-2); }
</style>
