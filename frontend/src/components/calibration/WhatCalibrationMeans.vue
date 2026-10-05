<script setup lang="ts">
import Icon from '../common/Icon.vue'

/** A short, steady explanation of what calibration is and is not. */
</script>

<template>
  <section
    class="means card-quiet"
    aria-labelledby="means-title"
    data-testid="what-calibration-means"
  >
    <h2
      id="means-title"
      class="eyebrow"
    >
      What calibration does
    </h2>
    <ul>
      <li>
        <Icon
          name="target"
          :size="16"
        /> It measures what you can do today. Every task becomes evidence.
      </li>
      <li>
        <Icon
          name="roadmap"
          :size="16"
        /> Your personal roadmap is built from that evidence, your target role and your date.
      </li>
      <li>
        <Icon
          name="zap"
          :size="16"
        /> There is no pass or fail. An honest miss shows where to start.
      </li>
    </ul>
  </section>
</template>

<style scoped>
.means { display: grid; gap: var(--s-3); }
ul { display: grid; gap: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); }
li { display: flex; gap: var(--s-2); align-items: flex-start; }
li :deep(svg) { margin-top: 0.15rem; color: var(--calibration-fg); flex: none; }
</style>
