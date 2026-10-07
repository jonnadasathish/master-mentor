<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { SpeakingHistory } from '../../api/types'
import { shortDate } from '../../presentation/format'
import ErrorState from '../common/ErrorState.vue'
import Skeleton from '../common/Skeleton.vue'

/** Recent speaking practices: counts only, never transcripts, and always labelled measured or manual. */
const data = ref<SpeakingHistory | null>(null)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  error.value = null
  try {
    data.value = (await api.get<SpeakingHistory>('/communication/history', { limit: 8 })).data
  } catch (caught) {
    error.value = caught
  }
}
onMounted(load)
</script>

<template>
  <section
    class="history card"
    data-testid="speaking-history"
    aria-labelledby="speaking-history-title"
  >
    <h2 id="speaking-history-title">
      Recent speaking practice
    </h2>
    <Skeleton
      v-if="!data && !error"
      height="6rem"
    />
    <ErrorState
      v-else-if="!data"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <p
        v-if="!data.rows.length"
        class="muted"
        data-testid="speaking-history-empty"
      >
        No speaking practice yet. Open any communication skill below and try a spoken prompt; the first one takes about
        two minutes.
      </p>
      <ul
        v-else
        class="rows"
      >
        <li
          v-for="r in data.rows"
          :key="r.assessment_id"
        >
          <span class="when tabular">{{ shortDate(r.observed_on) }}</span>
          <RouterLink :to="{ name: 'skill', params: { key: r.skill } }">
            {{ r.skill_name }}
          </RouterLink>
          <span class="muted small">
            <template v-if="r.source === 'BROWSER'">
              Measured from a browser transcript · {{ r.word_count }} words in {{ r.duration_seconds }} s
              <template v-if="r.filler_per_100_words !== null">· {{ r.filler_per_100_words }} filler words per 100</template>
              <template v-if="r.timed">· timed</template>
            </template>
            <template v-else>
              Manual self-review (weaker evidence)<template v-if="r.duration_seconds"> · about {{ r.duration_seconds }} s</template>
            </template>
          </span>
        </li>
      </ul>
      <p class="muted small">
        {{ data.note }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.history { display: grid; gap: var(--s-3); padding: var(--s-5); }
.rows { display: grid; gap: var(--s-2); }
.rows li { display: grid; grid-template-columns: 4.5rem minmax(0, 1fr); gap: var(--s-1) var(--s-3); align-items: baseline; padding-block: var(--s-2); border-top: 1px solid var(--border); }
.rows li .muted { grid-column: 2; }
.when { color: var(--text-2); }
.small { font-size: var(--fs-sm); }
</style>
