<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { ContentSummary } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import { CONTENT_TYPE_ICON, CONTENT_TYPE_LABEL } from '../../presentation/learning'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'

/** Learning items as a compact list: type, title, minutes, timed, and the learner's own progress. */
defineProps<{ items: ContentSummary[]; testid?: string }>()
</script>

<template>
  <ul
    class="content-list card-quiet divided"
    :data-testid="testid ?? 'content-list'"
  >
    <li
      v-for="c in items"
      :key="c.key"
    >
      <span
        class="type"
        aria-hidden="true"
      ><Icon
        :name="CONTENT_TYPE_ICON[c.type]"
        :size="16"
      /></span>
      <span class="main">
        <RouterLink
          :to="{ name: 'learn', params: { key: c.key } }"
          class="title"
          :data-testid="`content-${c.key}`"
        >{{ c.title }}</RouterLink>
        <span class="muted small">{{ CONTENT_TYPE_LABEL[c.type] }} · {{ formatMinutes(c.minutes) }}<template v-if="c.time_limit_seconds"> · timed option</template><template v-if="c.difficulty"> · {{ c.difficulty.toLowerCase() }}</template></span>
      </span>
      <StatusPill
        v-if="c.progress?.passed"
        state="completed"
        :label="c.spoken ? 'Practised' : c.progress.best_points !== null ? `${c.progress.best_points}` : 'Done'"
        quiet
      />
      <StatusPill
        v-else-if="c.progress && c.progress.best_points !== null"
        state="medium"
        :label="c.spoken ? 'Practised' : `Best ${c.progress.best_points}`"
        quiet
      />
      <StatusPill
        v-else-if="c.progress"
        state="completed"
        label="Studied"
        quiet
      />
    </li>
  </ul>
</template>

<style scoped>
.content-list li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.type { display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: var(--r-md); background: var(--accent-soft); color: var(--accent-text); flex: none; }
.main { display: grid; flex: 1; min-width: 0; }
.title { font-weight: 600; }
.small { font-size: var(--fs-sm); }
</style>
