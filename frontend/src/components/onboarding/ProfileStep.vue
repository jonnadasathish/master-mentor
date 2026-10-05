<script setup lang="ts">
import { useOnboardingStore } from '../../stores/onboarding'

const store = useOnboardingStore()
</script>

<template>
  <div class="stack">
    <p class="muted">
      This is context for you and for the mentor. It is not a test and it doesn't change any score.
    </p>
    <div class="fields">
      <label class="wide">What should we call you?
        <input
          v-model="store.draft.name"
          maxlength="100"
          autocomplete="given-name"
          data-testid="ob-name"
        >
      </label>
      <label>Years of professional software development
        <input
          v-model.number="store.draft.years"
          type="number"
          min="0"
          max="60"
          data-testid="ob-years"
        >
      </label>
      <label>Current role <span class="muted">(optional)</span>
        <input
          v-model="store.draft.currentRole"
          maxlength="100"
          placeholder="e.g. Backend Engineer"
          data-testid="ob-current-role"
        >
      </label>
      <label>Previous role <span class="muted">(optional)</span>
        <input
          v-model="store.draft.previousRole"
          maxlength="100"
          data-testid="ob-previous-role"
        >
      </label>
    </div>
  </div>
</template>

<style scoped>
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-4); }
label { display: grid; gap: var(--s-1); font-weight: 560; color: var(--text); }
.wide { grid-column: 1 / -1; }
input { width: 100%; }
@media (max-width: 767px) { .fields { grid-template-columns: 1fr; } }
</style>
