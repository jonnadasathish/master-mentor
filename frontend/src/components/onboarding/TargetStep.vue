<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RoleOption } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import { weeklyMinutes } from '../../practice/onboarding'
import { useOnboardingStore } from '../../stores/onboarding'
import Icon from '../common/Icon.vue'

const props = defineProps<{ roles: RoleOption[] }>()
const store = useOnboardingStore()
const custom = ref(false)
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const total = computed(() => weeklyMinutes(store.draft.budgets))
const role = computed(() => props.roles.find((r) => r.profile_key === store.draft.roleKey) ?? props.roles[0] ?? null)
</script>

<template>
  <div class="stack">
    <fieldset>
      <legend>What are you preparing for?</legend>
      <div
        v-for="r in roles"
        :key="r.profile_key"
        class="role"
        :class="{ chosen: r.profile_key === role?.profile_key }"
        data-testid="ob-role"
      >
        <Icon
          name="target"
          :size="20"
        />
        <div>
          <strong>{{ r.name }}</strong>
          <p class="muted">
            {{ r.seniority }} · an internal benchmark Master Mentor measures you against. It is not a claim about any
            particular company.
          </p>
        </div>
      </div>
    </fieldset>

    <label>Target interview date <span class="muted">(optional)</span>
      <input
        v-model="store.draft.targetDate"
        type="date"
        data-testid="ob-target-date"
      >
      <small class="muted">A date lets the mentor plan the phases of your preparation. You can change it any time.</small>
    </label>

    <fieldset>
      <legend>How much time can you give?</legend>
      <p class="hours">
        <strong class="tabular">{{ formatMinutes(total) }}</strong> a week
        <span class="muted">· Mon–Fri {{ store.draft.budgets[0] }} min, Sat–Sun {{ store.draft.budgets[5] }} min</span>
      </p>
      <button
        type="button"
        class="link-btn"
        :aria-expanded="custom"
        data-testid="ob-customize"
        @click="custom = !custom"
      >
        {{ custom ? 'Hide the days' : 'Choose minutes for each day (set a day to 0 to rest)' }}
      </button>
      <div
        v-if="custom"
        class="days"
      >
        <label
          v-for="(d, i) in DAYS"
          :key="d"
        >{{ d }}
          <input
            v-model.number="store.draft.budgets[i]"
            type="number"
            min="0"
            max="600"
            :data-testid="`ob-budget-${i}`"
          >
        </label>
      </div>
    </fieldset>

    <label>Target company profile <span class="muted">(optional)</span>
      <input
        v-model="store.draft.companyProfile"
        maxlength="120"
        placeholder="e.g. product company, fast-paced startup"
        data-testid="ob-company"
      >
      <small class="muted">Kept as a note for you. It doesn't change the plan.</small>
    </label>
  </div>
</template>

<style scoped>
fieldset { display: grid; gap: var(--s-3); }
legend { font-weight: 650; margin-bottom: var(--s-2); color: var(--text); }
label { display: grid; gap: var(--s-1); font-weight: 560; color: var(--text); }
label input[type='date'] { width: fit-content; }
.role { display: flex; gap: var(--s-3); align-items: flex-start; padding: var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); background: var(--surface); }
.role.chosen { border-color: var(--accent); background: var(--accent-soft); box-shadow: 0 0 0 2px var(--accent-soft); }
.role :deep(svg) { margin-top: 0.15rem; color: var(--accent); }
.hours { font-size: var(--fs-lg); }
.days { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: var(--s-2); }
.days input { width: 100%; }
small { font-weight: 400; }
@media (max-width: 767px) { .days { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
</style>
