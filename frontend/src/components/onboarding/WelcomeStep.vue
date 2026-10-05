<script setup lang="ts">
import Icon from '../common/Icon.vue'
</script>

<template>
  <div class="stack">
    <p class="lead">
      Master Mentor first learns what you already know. It will not force you through topics you've already
      demonstrated.
    </p>
    <ul class="points">
      <li>
        <Icon
          name="message"
          :size="18"
        />
        <div>
          <strong>Tell us about you</strong>
          <p class="muted">
            Your experience, your target and the time you have. A few minutes.
          </p>
        </div>
      </li>
      <li>
        <Icon
          name="crosshair"
          :size="18"
        />
        <div>
          <strong>Calibrate</strong>
          <p class="muted">
            Short real tasks measure where you are. What you say about yourself is never counted as proof.
          </p>
        </div>
      </li>
      <li>
        <Icon
          name="roadmap"
          :size="18"
        />
        <div>
          <strong>Get your personal roadmap</strong>
          <p class="muted">
            Built from what was measured, your target role and your date.
          </p>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.lead { font-size: var(--fs-lg); color: var(--text-2); max-width: 38rem; text-wrap: pretty; }
.points { display: grid; gap: var(--s-4); margin-top: var(--s-2); }
.points li { display: flex; gap: var(--s-4); align-items: flex-start; }
.points :deep(svg) { margin-top: 0.2rem; color: var(--accent); }
</style>
