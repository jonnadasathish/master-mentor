<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import ErrorBanner from './components/common/ErrorBanner.vue'
import ErrorBoundary from './components/common/ErrorBoundary.vue'
import AppSidebar from './components/shell/AppSidebar.vue'
import Logo from './components/shell/Logo.vue'
import MobileNav from './components/shell/MobileNav.vue'
import BackupBanner from './components/settings/BackupBanner.vue'

const route = useRoute()
</script>

<template>
  <RouterView
    v-if="route.meta.bare"
    v-slot="{ Component }"
  >
    <component :is="Component" />
  </RouterView>
  <div
    v-else
    class="shell"
  >
    <a
      class="skip-link"
      href="#main"
    >Skip to content</a>
    <AppSidebar class="shell-nav" />
    <div class="shell-body">
      <header class="topbar">
        <RouterLink
          :to="{ name: 'today' }"
          class="topbar-brand"
          aria-label="Master Mentor, go to Today"
        >
          <Logo />
          <strong>Master Mentor</strong>
        </RouterLink>
      </header>
      <main
        id="main"
        tabindex="-1"
      >
        <BackupBanner />
        <ErrorBanner />
        <ErrorBoundary>
          <RouterView v-slot="{ Component }">
            <Transition
              name="page"
              mode="out-in"
            >
              <component
                :is="Component"
                :key="route.path"
              />
            </Transition>
          </RouterView>
        </ErrorBoundary>
      </main>
    </div>
    <MobileNav class="shell-mobile" />
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: var(--sidebar-w) minmax(0, 1fr); min-height: 100vh; }
.shell-body { min-width: 0; }
main { padding: var(--s-6) var(--s-6) var(--s-7); max-width: var(--content-max); margin: 0 auto; outline: none; }
.topbar { display: none; }
.shell-mobile { display: none; }
.skip-link { position: absolute; left: -999px; top: 0; z-index: 100; background: var(--accent); color: var(--on-accent); padding: var(--s-2) var(--s-4); border-radius: 0 0 var(--r-md) 0; }
.skip-link:focus { left: 0; }

@media (max-width: 1099px) {
  .shell { grid-template-columns: var(--rail-w) minmax(0, 1fr); }
  main { padding: var(--s-5) var(--s-5) var(--s-7); }
}
@media (max-width: 767px) {
  .shell { grid-template-columns: minmax(0, 1fr); }
  .shell-nav { display: none; }
  .shell-mobile { display: block; }
  .topbar { display: flex; align-items: center; padding: var(--s-3) var(--s-4); position: sticky; top: 0; z-index: 20; background: var(--bg); }
  .topbar-brand { display: flex; align-items: center; gap: var(--s-2); color: var(--text); }
  .topbar-brand:hover { text-decoration: none; }
  main { padding: var(--s-2) var(--s-4) 6rem; }
}
</style>
