<script setup lang="ts">
import { onMounted } from 'vue'
import { api } from '../api'
import { useCatalogStore } from '../stores/catalog'

/** Internal verification page for the loaded catalog (Slice 2). Not the final Skills experience. */
const catalog = useCatalogStore()
onMounted(() => catalog.fetchAll(api))

function select(key: string): void {
  catalog.selectSkill(api, key)
}
</script>

<template>
  <section class="catalog">
    <h1>Catalog (internal verification)</h1>
    <p v-if="catalog.loading">
      Loading…
    </p>
    <p
      v-else-if="catalog.error"
      role="alert"
      data-testid="catalog-error"
    >
      {{ catalog.error.code }}: {{ catalog.error.message }}
    </p>

    <template v-if="catalog.summary">
      <h2>Summary</h2>
      <dl data-testid="catalog-summary">
        <dt>Catalog version</dt>
        <dd>{{ catalog.summary.versions.catalog_version }}</dd>
        <dt>Loaded at (UTC)</dt>
        <dd>{{ catalog.summary.loaded_at }}</dd>
        <dt>Skills</dt>
        <dd data-testid="skill-count">
          {{ catalog.summary.counts.skills }}
        </dd>
        <dt>Prerequisites</dt>
        <dd>{{ catalog.summary.counts.skill_prerequisites }}</dd>
        <dt>Problems</dt>
        <dd data-testid="problem-count">
          {{ catalog.summary.counts.problems }}
        </dd>
        <dt>Mission templates</dt>
        <dd>{{ catalog.summary.counts.mission_templates }}</dd>
        <dt>Roadmap milestones</dt>
        <dd>{{ catalog.summary.counts.roadmap_milestones }}</dd>
      </dl>
      <details>
        <summary>Component versions and file fingerprints</summary>
        <ul>
          <li
            v-for="(value, name) in catalog.summary.versions"
            :key="name"
          >
            {{ name }}: <code>{{ value }}</code>
          </li>
        </ul>
      </details>
    </template>

    <template v-if="catalog.profile">
      <h2>Role profile</h2>
      <p data-testid="profile-name">
        {{ catalog.profile.name }} ({{ catalog.profile.seniority }}): {{ catalog.profile.required_skill_count }}
        required skills, {{ catalog.profile.critical_skills.length }} critical
      </p>
      <table>
        <thead>
          <tr>
            <th>Component</th><th>Weight</th><th>Gate</th><th>Stretch</th><th>Track</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in catalog.profile.config.components"
            :key="c.key"
          >
            <td>{{ c.name }}</td><td>{{ c.weight }}</td><td>{{ c.gate }}</td><td>{{ c.stretch }}</td><td>{{ c.track }}</td>
          </tr>
        </tbody>
      </table>
      <p>
        Tiers: <span
          v-for="(n, tier) in catalog.profile.tier_counts"
          :key="tier"
        >{{ tier }}={{ n }} </span>
      </p>
    </template>

    <div class="columns">
      <div>
        <h2>Skill tree</h2>
        <details
          v-for="component in catalog.tree"
          :key="component.component"
          data-testid="tree-component"
        >
          <summary>{{ component.component }}</summary>
          <details
            v-for="group in component.groups"
            :key="group.key"
          >
            <summary>{{ group.name }} ({{ group.skills.length }})</summary>
            <button
              v-for="key in group.skills"
              :key="key"
              type="button"
              class="skill"
              @click="select(key)"
            >
              {{ key }}
            </button>
          </details>
        </details>
      </div>
      <div
        v-if="catalog.selected"
        data-testid="skill-detail"
      >
        <h2>{{ catalog.selected.key }}</h2>
        <p>
          {{ catalog.selected.name }} · {{ catalog.selected.tier }} · target {{ catalog.selected.target_score }} ·
          floor {{ catalog.selected.floor_score }} · milestone {{ catalog.selected.milestone?.key ?? '—' }}
        </p>
        <h3>Prerequisites</h3>
        <ul>
          <li
            v-for="p in catalog.selected.prerequisites"
            :key="p.key"
          >
            <button
              type="button"
              class="link"
              @click="select(p.key)"
            >
              {{ p.key }}
            </button> ≥ {{ p.min_score }}
          </li>
          <li v-if="!catalog.selected.prerequisites.length">
            none (root skill)
          </li>
        </ul>
        <h3>Dependents</h3>
        <ul>
          <li
            v-for="d in catalog.selected.dependents"
            :key="d.key"
          >
            <button
              type="button"
              class="link"
              @click="select(d.key)"
            >
              {{ d.key }}
            </button> (needs ≥ {{ d.min_score }})
          </li>
        </ul>
      </div>
    </div>

    <template v-if="catalog.roadmap">
      <h2>Roadmap</h2>
      <div
        v-for="track in catalog.roadmap.tracks"
        :key="track.track"
        data-testid="roadmap-track"
      >
        <h3>{{ track.track }}</h3>
        <ol>
          <li
            v-for="m in track.milestones"
            :key="m.key"
          >
            {{ m.key }} {{ m.name }} ({{ m.skills.length }} skills)
          </li>
        </ol>
      </div>
      <p>Baseline battery: {{ catalog.roadmap.baseline_items.length }} items, {{ catalog.roadmap.baseline_total_minutes }} min</p>
    </template>
  </section>
</template>

<style scoped>
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.skill { display: inline-block; margin: 0.15rem; font-size: 0.85rem; }
.link { background: none; border: none; color: #2a55b0; cursor: pointer; padding: 0; text-decoration: underline; }
table { border-collapse: collapse; }
td, th { border: 1px solid #ddd; padding: 0.2rem 0.5rem; text-align: left; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; }
@media (max-width: 640px) { .columns { grid-template-columns: 1fr; } }
</style>
