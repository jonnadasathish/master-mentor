<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import BackupBanner from './components/BackupBanner.vue'
import ErrorBanner from './components/ErrorBanner.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'
import { NAV_ROUTES } from './router'
</script>

<template>
  <div class="shell">
    <nav aria-label="Main">
      <strong class="brand">Master Mentor</strong>
      <RouterLink
        v-for="route in NAV_ROUTES"
        :key="String(route.name)"
        :to="{ name: route.name }"
      >
        {{ route.meta?.title }}
      </RouterLink>
      <RouterLink
        :to="{ name: 'catalog' }"
        class="internal-link"
      >
        Catalog (internal)
      </RouterLink>
      <RouterLink
        :to="{ name: 'status' }"
        class="status-link"
      >
        Status
      </RouterLink>
    </nav>
    <main>
      <BackupBanner />
      <ErrorBanner />
      <ErrorBoundary>
        <RouterView />
      </ErrorBoundary>
    </main>
  </div>
</template>

<style>
:root { font-family: system-ui, sans-serif; color: #1d1d1f; background: #fafafa; }
body { margin: 0; }
.shell { display: grid; grid-template-columns: 200px 1fr; min-height: 100vh; }
nav { display: flex; flex-direction: column; gap: 0.25rem; padding: 1rem; background: #f0f0f2; }
nav a { color: inherit; text-decoration: none; padding: 0.35rem 0.5rem; border-radius: 6px; }
nav a.router-link-exact-active { background: #dfe3ea; font-weight: 600; }
nav a:focus-visible, button:focus-visible { outline: 2px solid #3366cc; outline-offset: 2px; }
.brand { margin-bottom: 0.75rem; }
.internal-link { margin-top: auto; }
main { padding: 1.5rem; min-width: 0; }
select, input, textarea { max-width: 100%; }
table { max-width: 100%; }
.muted { color: #5c5c66; }
.error-banner { list-style: none; padding: 0; margin: 0 0 1rem; }
.error-banner li { background: #fde8e8; border: 1px solid #f3b4b4; padding: 0.5rem 0.75rem; border-radius: 6px; }
@media (max-width: 640px) {
  main { padding: 0.75rem; }
  main table { display: block; overflow-x: auto; }
  .shell { grid-template-columns: 1fr; }
  nav { flex-direction: row; flex-wrap: wrap; }
  .internal-link { margin-top: 0; }
}
</style>
