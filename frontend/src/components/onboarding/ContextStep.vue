<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { SelfReportClaim } from '../../api/types'
import { claimsOf, toggleClaim } from '../../practice/onboarding'
import { COMPONENT_LABEL, SELF_REPORT_CLAIMS } from '../../presentation/language'
import { useCatalogTreeStore } from '../../stores/data'
import { useOnboardingStore } from '../../stores/onboarding'
import Skeleton from '../common/Skeleton.vue'

const store = useOnboardingStore()
const tree = useCatalogTreeStore()
const open = ref<Set<string>>(new Set())
const sections = computed(() => (tree.data ?? []).map((c) => ({ ...c, label: COMPONENT_LABEL[c.component] ?? c.component })))
const total = computed(() => Object.values(store.draft.claims).reduce((n, l) => n + l.length, 0))

function toggle(claim: SelfReportClaim, group: string): void {
  store.draft.claims = toggleClaim(store.draft.claims, claim, group)
}
function flip(component: string): void {
  const next = new Set(open.value)
  if (next.has(component)) next.delete(component)
  else next.add(component)
  open.value = next
}
onMounted(async () => {
  await tree.ensure()
  if (tree.data?.length) open.value = new Set([tree.data[0]!.component])
})
</script>

<template>
  <div class="stack">
    <p
      class="notice"
      data-testid="ob-self-report-notice"
    >
      <strong>Self-reported context — not yet verified.</strong>
      These answers help you see the difference between what you believe and what is measured. They don't count as
      proof of skill and never change a score. Everything here is optional.
    </p>
    <Skeleton
      v-if="!tree.data"
      height="12rem"
      radius="var(--r-lg)"
    />
    <div
      v-for="c in sections"
      :key="c.component"
      class="component"
    >
      <button
        type="button"
        class="head"
        :aria-expanded="open.has(c.component)"
        @click="flip(c.component)"
      >
        <span>{{ c.label }}</span>
        <span class="muted tabular">{{ c.groups.length }} topics</span>
      </button>
      <ul v-if="open.has(c.component)">
        <li
          v-for="g in c.groups"
          :key="g.key"
        >
          <span class="name">{{ g.name }}</span>
          <span
            class="claims"
            role="group"
            :aria-label="`How you see ${g.name}`"
          >
            <button
              v-for="claim in SELF_REPORT_CLAIMS"
              :key="claim.key"
              type="button"
              class="claim"
              :aria-pressed="claimsOf(store.draft.claims, g.key).includes(claim.key)"
              :title="claim.hint"
              :data-testid="`ob-claim-${claim.key}-${g.key}`"
              @click="toggle(claim.key, g.key)"
            >
              {{ claim.label }}
            </button>
          </span>
        </li>
      </ul>
    </div>
    <p class="muted small tabular">
      {{ total }} {{ total === 1 ? 'answer' : 'answers' }} so far
    </p>
  </div>
</template>

<style scoped>
.notice { padding: var(--s-3) var(--s-4); background: var(--medium-bg); color: var(--text); border: 1px dashed var(--medium-bd); border-radius: var(--r-md); font-size: var(--fs-sm); }
.component { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); overflow: hidden; }
.head { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: var(--s-3) var(--s-4); background: none; border: 0; font: inherit; font-weight: 650; cursor: pointer; text-align: left; }
.head:hover { background: var(--surface-2); }
li { display: grid; gap: var(--s-2); padding: var(--s-3) var(--s-4); border-top: 1px solid var(--border); }
.name { font-size: var(--fs-sm); font-weight: 560; }
.claims { display: flex; flex-wrap: wrap; gap: var(--s-1); }
.claim { padding: 0.2rem 0.65rem; border-radius: 999px; border: 1px dashed var(--border-strong); background: var(--surface); font: inherit; font-size: var(--fs-xs); font-weight: 560; color: var(--text-2); cursor: pointer; }
.claim:hover { background: var(--surface-2); }
.claim[aria-pressed='true'] { border-style: solid; background: var(--medium-bg); border-color: var(--medium-fg); color: var(--medium-fg); }
.small { font-size: var(--fs-sm); }
</style>
