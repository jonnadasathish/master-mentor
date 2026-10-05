<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { isActive, NAV_ITEMS } from '../../router/nav'
import Icon from '../common/Icon.vue'

/** Phone navigation: a bottom bar with the four daily destinations and a "More" sheet for the rest. */
const route = useRoute()
const open = ref(false)
const PRIMARY = ['today', 'prepare', 'revise', 'mocks']
const primary = NAV_ITEMS.filter((i) => PRIMARY.includes(i.key))
const more = NAV_ITEMS.filter((i) => !PRIMARY.includes(i.key))
watch(() => route.path, () => (open.value = false))
</script>

<template>
  <div class="mobile-nav">
    <div
      v-if="open"
      id="more-menu"
      class="sheet"
      role="menu"
      aria-label="More"
      data-testid="more-menu"
    >
      <RouterLink
        v-for="item in more"
        :key="item.key"
        :to="item.to"
        class="sheet-item"
        role="menuitem"
      >
        <Icon :name="item.icon" />
        {{ item.label }}
      </RouterLink>
      <RouterLink
        :to="{ name: 'log' }"
        class="sheet-item"
        role="menuitem"
      >
        <Icon name="plus" />
        Log practice
      </RouterLink>
    </div>
    <nav
      class="bar"
      aria-label="Main"
    >
      <RouterLink
        v-for="item in primary"
        :key="item.key"
        :to="item.to"
        class="tab-item"
        :class="{ active: isActive(item, route.path) }"
        :data-testid="`mobile-nav-${item.key}`"
      >
        <Icon
          :name="item.icon"
          :size="20"
        />
        <span>{{ item.label }}</span>
      </RouterLink>
      <button
        type="button"
        class="tab-item"
        :class="{ active: open || more.some((m) => isActive(m, route.path)) }"
        :aria-expanded="open"
        aria-controls="more-menu"
        data-testid="mobile-nav-more"
        @click="open = !open"
      >
        <Icon
          name="more"
          :size="20"
        />
        <span>More</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.bar {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 30; display: grid; grid-template-columns: repeat(5, 1fr);
  background: var(--surface); border-top: 1px solid var(--border); padding-bottom: env(safe-area-inset-bottom);
}
.tab-item {
  display: grid; justify-items: center; gap: 2px; padding: 0.55rem 0.25rem 0.5rem; font: inherit; font-size: 0.7rem; font-weight: 600;
  color: var(--text-3); background: none; border: 0; cursor: pointer; text-decoration: none;
}
.tab-item.active { color: var(--accent-text); }
.tab-item:hover { text-decoration: none; }
.sheet {
  position: fixed; left: var(--s-3); right: var(--s-3); bottom: 4.6rem; z-index: 40; display: grid; gap: 2px; padding: var(--s-2);
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--shadow-md);
}
.sheet-item { display: flex; align-items: center; gap: var(--s-3); padding: 0.7rem var(--s-3); border-radius: var(--r-md); color: var(--text); font-weight: 600; }
.sheet-item:hover { background: var(--surface-2); text-decoration: none; }
</style>
