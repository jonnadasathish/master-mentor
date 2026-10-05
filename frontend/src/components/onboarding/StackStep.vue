<script setup lang="ts">
import { ref } from 'vue'
import { MAX_TECHNOLOGIES, toggleTechnology } from '../../practice/onboarding'
import { TECHNOLOGY_SUGGESTIONS } from '../../presentation/language'
import { useOnboardingStore } from '../../stores/onboarding'

const store = useOnboardingStore()
const other = ref('')

const isOn = (name: string) => store.draft.technologies.some((t) => t.toLowerCase() === name.toLowerCase())
function toggle(name: string): void {
  store.draft.technologies = toggleTechnology(store.draft.technologies, name)
}
function addOther(): void {
  if (!other.value.trim() || isOn(other.value)) {
    other.value = ''
    return
  }
  store.draft.technologies = toggleTechnology(store.draft.technologies, other.value)
  other.value = ''
}
const custom = () => store.draft.technologies.filter((t) => !TECHNOLOGY_SUGGESTIONS.some((s) => s.toLowerCase() === t.toLowerCase()))
</script>

<template>
  <div class="stack">
    <p class="muted">
      What do you use today? This is context only: using a technology doesn't earn any skill score. Skills are
      measured by tasks you complete.
    </p>
    <div
      class="chips"
      role="group"
      aria-label="Technologies you use"
    >
      <button
        v-for="t in TECHNOLOGY_SUGGESTIONS"
        :key="t"
        type="button"
        class="chip"
        :aria-pressed="isOn(t)"
        :data-testid="`ob-tech-${t}`"
        @click="toggle(t)"
      >
        {{ t }}
      </button>
      <button
        v-for="t in custom()"
        :key="t"
        type="button"
        class="chip"
        aria-pressed="true"
        :data-testid="`ob-tech-${t}`"
        @click="toggle(t)"
      >
        {{ t }}
      </button>
    </div>
    <form
      class="add"
      @submit.prevent="addOther"
    >
      <label>Something else?
        <input
          v-model="other"
          maxlength="40"
          placeholder="e.g. Kafka"
          data-testid="ob-tech-other"
          :disabled="store.draft.technologies.length >= MAX_TECHNOLOGIES"
        >
      </label>
      <button
        type="submit"
        class="btn btn-sm"
        data-testid="ob-tech-add"
      >
        Add
      </button>
    </form>
  </div>
</template>

<style scoped>
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { min-height: 2.4rem; padding: 0 var(--s-4); border-radius: 999px; border: 1px solid var(--border-strong); background: var(--surface); font: inherit; font-size: var(--fs-sm); font-weight: 560; color: var(--text); cursor: pointer; transition: background var(--t-fast) var(--ease); }
.chip:hover { background: var(--surface-2); }
.chip[aria-pressed='true'] { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-text); }
.add { display: flex; gap: var(--s-3); align-items: end; }
.add label { display: grid; gap: var(--s-1); font-weight: 560; color: var(--text); }
</style>
