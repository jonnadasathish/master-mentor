<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { stateFromGapStatus, type PrepareCategory } from '../../presentation/language'
import type { CategorySummary } from '../../presentation/prepare'
import Icon from '../common/Icon.vue'
import ProgressBar from '../common/ProgressBar.vue'
import StatusPill from '../common/StatusPill.vue'

/** One preparation area on the Prepare hub: score against target, the active gap and the next action. */
const props = defineProps<{ category: PrepareCategory; summary: CategorySummary; to: RouteLocationRaw }>()
const measured = computed(() => props.summary.assessedPct !== null && props.summary.assessedPct > 0)
</script>

<template>
  <RouterLink
    :to="to"
    class="category"
    :data-testid="`category-${category.slug}`"
  >
    <div class="head">
      <span
        class="icon"
        aria-hidden="true"
      ><Icon
        :name="category.icon"
        :size="20"
      /></span>
      <h2>{{ category.label }}</h2>
      <Icon
        class="go"
        name="chevron-right"
        :size="18"
      />
    </div>

    <template v-if="measured">
      <p class="score tabular">
        <strong>{{ summary.score }}</strong><span class="of"> / {{ summary.target }}</span>
        <span class="muted small"> needed</span>
      </p>
      <ProgressBar
        :value="summary.score"
        :max="summary.target"
        :label="`${category.label} score against the level you're aiming for`"
        :tone="summary.score !== null && summary.target !== null && summary.score >= summary.target ? 'healthy' : 'accent'"
      />
    </template>
    <p
      v-else
      class="score muted"
    >
      Not measured yet
    </p>

    <p
      v-if="summary.topGap"
      class="gap"
    >
      <StatusPill
        :state="stateFromGapStatus(summary.topGap.gap!.status)"
        quiet
      />
      <span class="gap-name">{{ summary.topGap.name }}</span>
    </p>
    <p
      v-if="summary.nextLabel"
      class="next"
    >
      <span class="label">Next</span> {{ summary.nextLabel }}
    </p>
    <p
      v-else
      class="next muted"
    >
      <span class="label">Next</span> Nothing urgent here
    </p>
  </RouterLink>
</template>

<style scoped>
.category {
  min-width: 0; display: grid; gap: var(--s-3); align-content: start; padding: var(--s-5); background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); box-shadow: var(--shadow-sm); color: inherit; text-decoration: none;
  transition: box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease), transform var(--t-base) var(--ease);
}
.category:hover { box-shadow: var(--shadow-md); border-color: var(--border-strong); transform: translateY(-1px); text-decoration: none; }
.head { display: flex; align-items: center; gap: var(--s-3); }
.icon { display: grid; place-items: center; width: 2.2rem; height: 2.2rem; border-radius: var(--r-md); background: var(--accent-soft); color: var(--accent-text); }
h2 { flex: 1; font-size: var(--fs-lg); }
.go { color: var(--text-3); }
.score { font-size: var(--fs-xl); letter-spacing: -0.02em; }
.score strong { font-weight: 700; }
.of { font-size: var(--fs-md); color: var(--text-3); }
.small { font-size: var(--fs-sm); }
.gap { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-sm); min-width: 0; }
.gap-name { flex: 1; font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.next { font-size: var(--fs-sm); color: var(--text-2); }
.label { font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); margin-right: var(--s-1); }
</style>
