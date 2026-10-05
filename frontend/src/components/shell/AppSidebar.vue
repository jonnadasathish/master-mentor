<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { isActive, NAV_ITEMS, type NavItem } from '../../router/nav'
import { useTodayStore } from '../../stores/data'
import Icon from '../common/Icon.vue'
import Logo from './Logo.vue'

/** Desktop sidebar (full) and tablet rail (icons only). */
const route = useRoute()
const today = useTodayStore()
/** Revision items due or overdue, shown only when the server has already told us (no extra fetch). */
/** The parent is highlighted unless one of its children is the current page (then the child is). */
function highlighted(item: NavItem): boolean {
  return isActive(item, route.path) && !item.children?.some((c) => isActive(c, route.path))
}
const revisionBadge = computed(() => {
  const r = today.data?.revisions
  return r ? r.due + r.overdue : 0
})
</script>

<template>
  <nav
    class="sidebar"
    aria-label="Main"
  >
    <RouterLink
      :to="{ name: 'today' }"
      class="brand"
      aria-label="Master Mentor, go to Today"
    >
      <Logo />
      <span class="brand-name">Master Mentor</span>
    </RouterLink>

    <RouterLink
      :to="{ name: 'log' }"
      class="btn btn-primary log-btn"
      data-testid="log-practice"
    >
      <Icon name="plus" />
      <span class="label">Log practice</span>
    </RouterLink>

    <ul class="items">
      <li
        v-for="item in NAV_ITEMS"
        :key="item.key"
      >
        <RouterLink
          :to="item.to"
          class="item"
          :class="{ active: isActive(item, route.path), highlighted: highlighted(item) }"
          :data-testid="`nav-${item.key}`"
          :title="item.label"
        >
          <Icon :name="item.icon" />
          <span class="label">{{ item.label }}</span>
          <span
            v-if="item.key === 'revise' && revisionBadge"
            class="count"
          >
            {{ revisionBadge }}<span class="sr-only"> reviews waiting</span>
          </span>
        </RouterLink>
        <ul
          v-if="item.children && isActive(item, route.path)"
          class="children"
        >
          <li
            v-for="child in item.children"
            :key="child.key"
          >
            <RouterLink
              :to="child.to"
              class="child"
              :class="{ active: isActive(child, route.path) }"
              :data-testid="`nav-${child.key}`"
            >
              <Icon
                :name="child.icon"
                :size="15"
              />
              <span class="label">{{ child.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto; display: flex; flex-direction: column; gap: var(--s-4);
  padding: var(--s-4) var(--s-3); background: var(--surface); border-right: 1px solid var(--border);
}
.brand { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-1) var(--s-2); color: var(--text); font-weight: 700; letter-spacing: -0.02em; }
.brand:hover { text-decoration: none; }
.log-btn { width: 100%; }
.items { display: grid; gap: 2px; }
.item, .child {
  display: flex; align-items: center; gap: var(--s-3); padding: 0.5rem var(--s-3); border-radius: var(--r-md);
  color: var(--text-2); font-weight: 560; text-decoration: none;
  transition: background var(--t-fast) var(--ease), color var(--t-fast) var(--ease);
}
.item:hover, .child:hover { background: var(--surface-2); color: var(--text); text-decoration: none; }
.item.active { color: var(--text); font-weight: 650; }
.item.highlighted, .child.active { background: var(--accent-soft); color: var(--accent-text); }
.children { display: grid; gap: 1px; margin: 2px 0 var(--s-2) 1.1rem; padding-left: var(--s-2); border-left: 1px solid var(--border); }
.child { padding: 0.35rem var(--s-3); font-size: var(--fs-sm); }
.count {
  margin-left: auto; min-width: 1.4rem; text-align: center; font-size: var(--fs-xs); font-weight: 700; padding: 0 0.4rem;
  border-radius: 999px; background: var(--due-bg); color: var(--due-fg); border: 1px solid var(--due-bd);
}

/* Tablet: icon rail */
@media (max-width: 1099px) {
  .sidebar { align-items: center; padding: var(--s-4) var(--s-2); }
  .brand-name, .label, .children { display: none; }
  .brand { padding: 0; }
  .log-btn { width: 2.5rem; padding: 0; }
  .item { justify-content: center; padding: 0.6rem; position: relative; }
  .count { position: absolute; top: 2px; right: 0; margin: 0; min-width: 1.1rem; font-size: 0.65rem; }
}
</style>
