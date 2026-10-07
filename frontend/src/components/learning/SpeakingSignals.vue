<script setup lang="ts">
import { computed } from 'vue'
import type { SpeakingResult } from '../../api/types'
import { RATING_LABEL } from '../../presentation/learning'

/**
 * The measurable signals of one speaking practice, as the server computed them (D-087). Signals, not a grade:
 * nothing here judges grammar, pronunciation, accent or confidence.
 */
const props = defineProps<{ speaking: SpeakingResult }>()

const CRITERION_LABEL: Record<string, string> = {
  length: 'Length',
  duration: 'Duration',
  fillers: 'Filler words',
  structure: 'Structure phrases',
  vocabulary: 'Target phrases',
  repetition: 'Repeated phrases',
}
const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`
const list = (pairs: [string, number][]) => pairs.map(([w, n]) => `${w} ×${n}`).join(', ')

const lines = computed(() => {
  const s = props.speaking
  if (s.source === 'MANUAL') {
    return [
      s.duration_seconds ? `About ${plural(s.duration_seconds, 'second')} of practice (your own estimate).` : 'No speech was measured.',
    ]
  }
  const out = [
    `${plural(s.word_count, 'word')} in ${plural(s.duration_seconds, 'second')}${s.words_per_minute !== null ? ` (about ${s.words_per_minute} words per minute)` : ''}.`,
  ]
  out.push(
    s.filler_count
      ? `${plural(s.filler_count, 'filler word')}: ${list(s.fillers)}. Browsers often drop "um" and "uh", so this can be an undercount.`
      : 'No filler words found. Browsers often drop "um" and "uh", so this can be an undercount.',
  )
  if (s.structure_markers.length) out.push(`Structure phrases used: ${s.structure_markers.join(', ')}.`)
  const total = s.vocabulary_used.length + s.vocabulary_missing.length
  if (total) {
    out.push(
      `Included ${s.vocabulary_used.length} of ${plural(total, 'target phrase')}${s.vocabulary_used.length ? `: ${s.vocabulary_used.join(', ')}` : ''}.${s.vocabulary_missing.length ? ` Not used: ${s.vocabulary_missing.join(', ')}.` : ''}`,
    )
  }
  if (s.repeated_phrases.length) out.push(`Repeated three or more times: ${list(s.repeated_phrases)}.`)
  return out
})
const criteria = computed(() => Object.entries(props.speaking.criteria))
</script>

<template>
  <section
    class="signals"
    data-testid="speaking-signals"
    aria-label="Speaking signals"
  >
    <ul class="lines">
      <li
        v-for="line in lines"
        :key="line"
      >
        {{ line }}
      </li>
    </ul>
    <ul
      v-if="criteria.length"
      class="chips"
      aria-label="Measured criteria"
    >
      <li
        v-for="[key, rating] in criteria"
        :key="key"
        class="chip"
        :class="`r${rating}`"
      >
        {{ CRITERION_LABEL[key] ?? key }}: {{ RATING_LABEL[rating] }}
      </li>
    </ul>
    <p class="muted small">
      {{ speaking.evidence_note }}
    </p>
  </section>
</template>

<style scoped>
.signals { display: grid; gap: var(--s-3); padding: var(--s-4); border: 1px solid var(--border); border-radius: var(--r-lg); background: var(--surface); }
.lines { display: grid; gap: var(--s-2); list-style: disc; padding-left: var(--s-5); line-height: 1.5; }
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { padding: 0.2rem 0.6rem; border-radius: var(--r-md); font-size: var(--fs-sm); font-weight: 600; background: var(--surface-3); color: var(--text-2); }
.chip.r2 { background: var(--healthy-bg); color: var(--healthy-fg); }
.chip.r1 { background: var(--surface-3); }
.chip.r0 { background: var(--high-bg); color: var(--high-fg); }
.small { font-size: var(--fs-sm); }
</style>
