<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { MockKit } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import { ROUND_LABEL, stateFromGapStatus } from '../../presentation/language'
import SectionHeading from '../common/SectionHeading.vue'
import StatusPill from '../common/StatusPill.vue'
import ContentList from './ContentList.vue'

/**
 * Rehearsal material for every round of the loop: timed prompts from the library, the skills the round should probe
 * first (the gap engine's order). Log the result with the mock form; weaknesses flow back into gaps and revision.
 */
const kits = ref<MockKit[]>([])
const failed = ref(false)
const selected = ref<string | null>(null)
const kit = computed(() => kits.value.find((k) => k.round === selected.value) ?? kits.value[0] ?? null)

onMounted(async () => {
  try {
    kits.value = (await api.get<MockKit[]>('/learning/mock-kits')).data
  } catch {
    failed.value = true
  }
})
</script>

<template>
  <section
    v-if="!failed && kits.length"
    class="kits"
    aria-labelledby="mock-kits"
    data-testid="mock-kits"
  >
    <SectionHeading
      id="mock-kits"
      title="Rehearse a round"
    />
    <div
      class="tabs"
      role="tablist"
      aria-label="Interview rounds"
    >
      <button
        v-for="k in kits"
        :key="k.round"
        type="button"
        class="tab"
        role="tab"
        :aria-selected="kit?.round === k.round"
        :data-testid="`kit-${k.round}`"
        @click="selected = k.round"
      >
        {{ ROUND_LABEL[k.round_type] ?? k.round_type }}<template v-if="k.round.endsWith('_2')">
          (2)
        </template>
      </button>
    </div>
    <div
      v-if="kit"
      class="kit card-quiet"
      role="tabpanel"
    >
      <p class="muted small">
        A {{ formatMinutes(kit.minutes) }} round. Set a timer, answer aloud, then score each prompt honestly.
      </p>
      <p
        v-if="kit.focus_skills.length"
        class="focus"
      >
        <span class="small">Probe first:</span>
        <RouterLink
          v-for="s in kit.focus_skills"
          :key="s.key"
          :to="{ name: 'skill', params: { key: s.key } }"
          class="focus-skill"
        >
          {{ s.name }}
          <StatusPill
            :state="stateFromGapStatus(s.status)"
            quiet
          />
        </RouterLink>
      </p>
      <ContentList
        v-if="kit.items.length"
        :items="kit.items"
        :testid="`kit-items-${kit.round}`"
      />
      <p
        v-else
        class="muted small"
      >
        No timed prompts for this round in the library yet.
      </p>
    </div>
  </section>
</template>

<style scoped>
.kits { display: grid; gap: var(--s-3); }
.kit { display: grid; gap: var(--s-3); }
.focus { display: flex; flex-wrap: wrap; gap: var(--s-2); align-items: center; }
.focus-skill { display: inline-flex; gap: var(--s-1); align-items: center; font-weight: 600; font-size: var(--fs-sm); }
.small { font-size: var(--fs-sm); }
</style>
