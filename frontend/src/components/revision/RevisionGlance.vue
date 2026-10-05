<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Today } from '../../api/types'
import { formatMinutes, plural } from '../../presentation/format'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'

/** What is waiting for review today. Counts and minutes are the server's. */
defineProps<{ revisions: Today['revisions'] }>()
</script>

<template>
  <section
    class="glance card-quiet"
    aria-labelledby="glance-title"
    data-testid="revision-glance"
  >
    <h2
      id="glance-title"
      class="eyebrow"
    >
      Revision
    </h2>
    <template v-if="revisions.due + revisions.overdue > 0">
      <p class="lead">
        {{ plural(revisions.due + revisions.overdue, 'review') }} waiting
      </p>
      <p class="pills">
        <StatusPill
          v-if="revisions.overdue"
          state="overdue"
          :label="`${revisions.overdue} overdue`"
        />
        <StatusPill
          v-if="revisions.due"
          state="due"
          :label="`${revisions.due} due today`"
        />
      </p>
      <p class="muted">
        About {{ formatMinutes(revisions.backlog_minutes) }} in total.
      </p>
    </template>
    <p
      v-else
      class="lead clear"
    >
      <Icon
        name="check-circle"
        :size="16"
      /> You're clear for today.
    </p>
    <RouterLink
      :to="{ name: 'revision' }"
      class="more"
    >
      Open revision
      <Icon
        name="arrow-right"
        :size="14"
      />
    </RouterLink>
  </section>
</template>

<style scoped>
.glance { display: grid; gap: var(--s-2); }
.lead { font-weight: 650; font-size: var(--fs-md); }
.clear { display: flex; align-items: center; gap: var(--s-2); color: var(--healthy-fg); }
.pills { display: flex; gap: var(--s-2); flex-wrap: wrap; }
.more { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); font-weight: 600; }
</style>
