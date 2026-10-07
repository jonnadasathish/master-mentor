<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { CommunicationReadiness } from '../../api/types'
import ErrorState from '../common/ErrorState.vue'
import Skeleton from '../common/Skeleton.vue'

/**
 * Communication Readiness (D-087): a separate, read-only view. It is not part of Overall Readiness and changes no
 * gate. Every sentence about evidence comes from the server so self-report is never shown as a measurement.
 */
const data = ref<CommunicationReadiness | null>(null)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  error.value = null
  try {
    data.value = (await api.get<CommunicationReadiness>('/communication/readiness')).data
  } catch (caught) {
    error.value = caught
  }
}
onMounted(load)
</script>

<template>
  <section
    class="readiness card"
    data-testid="communication-readiness"
    aria-labelledby="comm-ready-title"
  >
    <h2 id="comm-ready-title">
      Communication Readiness
    </h2>
    <Skeleton
      v-if="!data && !error"
      height="10rem"
    />
    <ErrorState
      v-else-if="!data"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <ul class="areas">
        <li
          v-for="a in data.areas"
          :key="a.key"
          class="area"
          :data-testid="`comm-area-${a.key}`"
        >
          <div class="top">
            <strong>{{ a.title }}</strong>
            <span
              class="status"
              :class="`s-${a.status.toLowerCase()}`"
            >{{ a.status_label }}</span>
          </div>
          <p class="summary">
            {{ a.summary }}
          </p>
          <p
            v-if="a.self_report"
            class="muted small self-report"
          >
            {{ a.self_report }}
          </p>
          <details v-if="a.skills.length">
            <summary class="small">
              Skills in this area ({{ a.skills_with_evidence }} of {{ a.skills_total }} practised)
            </summary>
            <ul class="skills">
              <li
                v-for="s in a.skills"
                :key="s.key"
              >
                <RouterLink :to="{ name: 'skill', params: { key: s.key } }">
                  {{ s.name }}
                </RouterLink>
                <span class="muted small">
                  <template v-if="s.measured + s.manual + s.other === 0">
                    {{ s.self_reported ? ' · self-reported only' : ' · not measured yet' }}
                  </template>
                  <template v-else>
                    · {{ s.measured }} measured, {{ s.manual }} manual<template v-if="s.other">, {{ s.other }} other</template>
                  </template>
                </span>
              </li>
            </ul>
          </details>
        </li>
      </ul>
      <p class="muted small note">
        {{ data.note }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.readiness { display: grid; gap: var(--s-4); padding: var(--s-5); }
.areas { display: grid; gap: var(--s-3); grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); }
.area { display: grid; gap: var(--s-2); padding: var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); align-content: start; }
.top { display: flex; justify-content: space-between; gap: var(--s-2); align-items: baseline; flex-wrap: wrap; }
.status { font-size: var(--fs-sm); font-weight: 650; padding: 0.1rem 0.5rem; border-radius: var(--r-md); background: var(--surface-3); color: var(--text-2); }
.s-working { background: var(--healthy-bg); color: var(--healthy-fg); }
.s-strong { background: var(--healthy-bg); color: var(--healthy-fg); }
.s-developing { background: var(--high-bg); color: var(--high-fg); }
.summary { line-height: 1.5; }
.skills { display: grid; gap: var(--s-1); padding-top: var(--s-2); }
details summary { cursor: pointer; color: var(--accent-text); font-weight: 600; }
.small { font-size: var(--fs-sm); }
</style>
