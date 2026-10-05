<script setup lang="ts">
import type { Rating } from '../../api/types'
import { RATING_LABEL } from '../../presentation/learning'

/** Missed / Partly / Fully as a labelled radio group (keyboard and screen-reader friendly). */
defineProps<{ name: string; label: string; modelValue: Rating | undefined }>()
const emit = defineEmits<{ 'update:modelValue': [value: Rating] }>()
const VALUES: Rating[] = [0, 1, 2]
</script>

<template>
  <fieldset
    class="rating"
    :data-testid="`rate-${name}`"
  >
    <legend class="sr-only">
      {{ label }}
    </legend>
    <label
      v-for="v in VALUES"
      :key="v"
      class="option"
      :class="{ on: modelValue === v }"
    >
      <input
        type="radio"
        :name="name"
        :value="v"
        :checked="modelValue === v"
        @change="emit('update:modelValue', v)"
      >
      {{ RATING_LABEL[v] }}
    </label>
  </fieldset>
</template>

<style scoped>
.rating { display: inline-flex; gap: var(--s-1); padding: 0.2rem; background: var(--surface-3); border-radius: var(--r-md); flex-wrap: wrap; }
.option {
  display: inline-flex; align-items: center; gap: var(--s-1); padding: 0.3rem 0.7rem; border-radius: var(--r-sm);
  font-size: var(--fs-sm); font-weight: 600; color: var(--text-2); cursor: pointer;
}
.option input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.option.on { background: var(--surface); color: var(--text); box-shadow: var(--shadow-sm); }
.option:focus-within { outline: 2px solid var(--accent); outline-offset: 1px; }
</style>
