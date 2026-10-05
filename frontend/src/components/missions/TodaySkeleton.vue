<script setup lang="ts">
import Skeleton from '../common/Skeleton.vue'
</script>

<template>
  <div
    class="page"
    data-testid="today-skeleton"
    aria-busy="true"
    aria-label="Loading your day"
  >
    <div class="stack">
      <Skeleton
        width="9rem"
        height="0.8rem"
      />
      <Skeleton
        width="22rem"
        height="2.2rem"
        radius="var(--r-md)"
      />
      <Skeleton
        width="14rem"
        height="1rem"
      />
    </div>
    <div class="cols">
      <div class="stack">
        <Skeleton
          height="6.5rem"
          radius="var(--r-lg)"
        />
        <Skeleton
          height="11rem"
          radius="var(--r-lg)"
        />
        <Skeleton
          height="11rem"
          radius="var(--r-lg)"
        />
      </div>
      <div class="stack">
        <Skeleton
          height="14rem"
          radius="var(--r-lg)"
        />
        <Skeleton
          height="8rem"
          radius="var(--r-lg)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.cols { display: grid; grid-template-columns: minmax(0, 1fr) 20rem; gap: var(--s-6); }
@media (max-width: 1279px) { .cols { grid-template-columns: minmax(0, 1fr); } }
</style>
