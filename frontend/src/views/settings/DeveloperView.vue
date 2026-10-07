<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { CatalogSummary } from '../../api/types'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import SectionHeading from '../../components/common/SectionHeading.vue'
import { useSystemStore } from '../../stores/system'

/** The technical corner: health, versions, backups and developer procedures. Not part of the daily experience. */
const system = useSystemStore()
const catalog = ref<CatalogSummary | null>(null)
const backup = ref<Record<string, unknown> | null>(null)
const ok = computed(() => system.health?.db === 'ok')

async function load(): Promise<void> {
  await system.fetchHealth(api)
  try {
    catalog.value = (await api.get<CatalogSummary>('/catalog')).data
  } catch {
    catalog.value = null
  }
  try {
    backup.value = (await api.get<Record<string, unknown>>('/system/backup-status')).data
  } catch {
    backup.value = null
  }
}
onMounted(load)
</script>

<template>
  <div class="page page-narrow">
    <RouterLink
      :to="{ name: 'settings' }"
      class="back"
    >
      <Icon
        name="arrow-left"
        :size="14"
      /> Settings
    </RouterLink>
    <PageHeader
      eyebrow="Settings"
      title="Developer / System"
      description="Technical details for developers. Nothing here is needed for your daily preparation."
    />

    <ErrorState
      v-if="system.error"
      :error="system.error"
      @retry="load"
    />

    <section class="card">
      <h2>System health</h2>
      <dl
        v-if="system.health"
        class="facts"
        data-testid="health"
      >
        <div><dt>Database</dt><dd>{{ ok ? 'Connected' : system.health.db }}</dd></div>
        <div><dt>Ruleset version</dt><dd>{{ system.health.ruleset_version }}</dd></div>
        <div><dt>Catalog (seed) version</dt><dd>{{ system.health.seed_version ?? 'not loaded' }}</dd></div>
      </dl>
      <p
        v-else-if="system.loading"
        class="muted"
      >
        Checking…
      </p>
      <button
        type="button"
        class="btn btn-sm"
        @click="load"
      >
        Check again
      </button>
    </section>

    <section class="card">
      <h2>Backups</h2>
      <dl
        v-if="backup"
        class="facts"
        data-testid="backup-facts"
      >
        <div><dt>Latest backup</dt><dd>{{ backup.latest_file ?? 'none' }}</dd></div>
        <div><dt>Taken at (UTC)</dt><dd>{{ backup.taken_at ?? '—' }}</dd></div>
        <div><dt>Age</dt><dd>{{ backup.age_hours ?? '—' }} h</dd></div>
      </dl>
      <p class="muted small">
        Take a backup now with <code>make backup</code>; check that it restores with <code>make backup-verify</code>.
      </p>
    </section>

    <section
      v-if="catalog"
      class="card"
    >
      <h2>Skill catalog</h2>
      <dl class="facts">
        <div><dt>Skills</dt><dd>{{ catalog.counts.skills }}</dd></div>
        <div><dt>Problems</dt><dd>{{ catalog.counts.problems }}</dd></div>
        <div><dt>Loaded at (UTC)</dt><dd>{{ catalog.loaded_at }}</dd></div>
      </dl>
      <RouterLink
        :to="{ name: 'catalog' }"
        class="btn btn-sm"
        data-testid="catalog-link"
      >
        Open catalog verification
      </RouterLink>
      <RouterLink
        :to="{ name: 'coverage' }"
        class="btn btn-sm"
        data-testid="coverage-link"
      >
        Content coverage report
      </RouterLink>
    </section>

    <section class="card">
      <h2>Developer procedures</h2>
      <SectionHeading title="Reset preparation data" />
      <p class="small">
        Clears all preparation history and keeps the catalog, your goal and settings. A backup is taken first. It never runs
        automatically and needs an explicit confirmation:
      </p>
      <pre>make dev-reset CONFIRM=RESET-PREP-DATA</pre>
      <p class="muted small">
        Run it from the project folder. It refuses to run outside the development environment.
      </p>
    </section>
  </div>
</template>

<style scoped>
.back { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); width: fit-content; }
.card { display: grid; gap: var(--s-3); align-content: start; }
.facts { display: grid; gap: var(--s-3); }
.facts div { display: flex; justify-content: space-between; gap: var(--s-4); padding-bottom: var(--s-2); border-bottom: 1px solid var(--border); }
.facts dt { color: var(--text-3); }
.facts dd { font-family: var(--font-mono); font-size: var(--fs-sm); overflow-wrap: anywhere; text-align: right; }
.small { font-size: var(--fs-sm); }
pre { margin: 0; padding: var(--s-3) var(--s-4); background: var(--surface-3); border-radius: var(--r-md); font-family: var(--font-mono); font-size: var(--fs-sm); overflow-x: auto; }
code { font-family: var(--font-mono); background: var(--surface-3); padding: 0.1rem 0.35rem; border-radius: var(--r-sm); }
</style>
