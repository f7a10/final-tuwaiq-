<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink class="app-header__brand" to="/" aria-label="عماد — الصفحة الرئيسية">
        <BrandMark />
        <span>
          <strong>عماد</strong>
          <small>مخطط أوضح، قرار أهدأ</small>
        </span>
      </RouterLink>

      <nav class="app-header__nav" aria-label="التنقل الرئيسي">
        <RouterLink to="/" class="app-header__link">مخطط جديد</RouterLink>
        <RouterLink to="/projects" class="app-header__link">مشاريعي</RouterLink>
      </nav>

      <div class="app-header__account">
        <template v-if="authStore.isAuthenticated">
          <details class="account-menu">
            <summary class="account-menu__summary">
              <span class="account-menu__avatar">{{ userInitials }}</span>
              <span class="account-menu__name">{{ authStore.currentUser?.full_name }}</span>
              <i class="fas fa-chevron-down" aria-hidden="true"></i>
            </summary>
            <div class="account-menu__panel">
              <RouterLink to="/profile">الملف الشخصي</RouterLink>
              <RouterLink v-if="authStore.isAdmin" to="/admin">إدارة النظام</RouterLink>
              <button type="button" @click="logout">تسجيل الخروج</button>
            </div>
          </details>
        </template>
        <template v-else>
          <RouterLink class="app-header__login" to="/login">تسجيل الدخول</RouterLink>
          <RouterLink class="button button--primary button--small" to="/register">إنشاء حساب</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import BrandMark from './BrandMark.vue'

const router = useRouter()
const authStore = useAuthStore()

const userInitials = computed(() => {
  const parts = (authStore.currentUser?.full_name || 'مستخدم')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  return parts.slice(0, 2).map((part) => part[0]).join('')
})

function logout() {
  authStore.logout()
  router.push('/')
}
</script>

<style scoped>
.app-header {
  position: sticky;
  z-index: 40;
  top: 0;
  border-bottom: 1px solid var(--emad-line);
  background: color-mix(in srgb, var(--emad-surface) 94%, transparent);
  backdrop-filter: blur(12px);
}

.app-header__inner {
  display: grid;
  grid-template-columns: minmax(14rem, 1fr) auto minmax(14rem, 1fr);
  align-items: center;
  gap: 1.5rem;
  width: min(100% - 2rem, 86rem);
  min-height: 4.5rem;
  margin-inline: auto;
}

.app-header__brand,
.app-header__account,
.app-header__nav,
.account-menu__summary {
  display: flex;
  align-items: center;
}

.app-header__brand {
  justify-self: start;
  gap: 0.75rem;
  color: var(--emad-ink);
  text-decoration: none;
}

.app-header__brand strong,
.app-header__brand small {
  display: block;
}

.app-header__brand strong {
  font-size: 1.05rem;
}

.app-header__brand small {
  margin-top: 0.05rem;
  color: var(--emad-muted);
  font-size: 0.69rem;
}

.app-header__nav {
  justify-content: center;
  gap: 0.25rem;
  padding: 0.25rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.75rem;
  background: var(--emad-surface-subtle);
}

.app-header__link {
  min-height: 2.35rem;
  padding: 0.55rem 0.9rem;
  border-radius: 0.55rem;
  color: var(--emad-ink-soft);
  font-size: 0.88rem;
  font-weight: 650;
  text-decoration: none;
}

.app-header__link:hover,
.app-header__link.router-link-active {
  background: var(--emad-surface);
  color: var(--emad-accent-dark);
  box-shadow: 0 1px 2px rgba(24, 43, 36, 0.08);
}

.app-header__account {
  justify-self: end;
  gap: 0.75rem;
}

.app-header__login {
  color: var(--emad-ink-soft);
  font-size: 0.88rem;
  font-weight: 650;
  text-decoration: none;
}

.account-menu {
  position: relative;
}

.account-menu__summary {
  min-height: 2.75rem;
  gap: 0.6rem;
  padding: 0.3rem 0.45rem 0.3rem 0.75rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.75rem;
  background: var(--emad-surface);
  cursor: pointer;
  list-style: none;
}

.account-menu__summary::-webkit-details-marker {
  display: none;
}

.account-menu__summary i {
  color: var(--emad-muted);
  font-size: 0.65rem;
}

.account-menu__avatar {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 0.55rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 0.75rem;
  font-weight: 750;
}

.account-menu__name {
  max-width: 9rem;
  overflow: hidden;
  font-size: 0.82rem;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-menu__panel {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  width: 12.5rem;
  padding: 0.4rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.75rem;
  background: var(--emad-surface);
  box-shadow: var(--emad-shadow-lg);
}

.account-menu__panel a,
.account-menu__panel button {
  display: flex;
  width: 100%;
  min-height: 2.5rem;
  align-items: center;
  padding-inline: 0.75rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--emad-ink-soft);
  font: inherit;
  font-size: 0.83rem;
  font-weight: 620;
  text-align: right;
  text-decoration: none;
  cursor: pointer;
}

.account-menu__panel a:hover,
.account-menu__panel button:hover {
  background: var(--emad-surface-subtle);
  color: var(--emad-accent-dark);
}

@media (max-width: 760px) {
  .app-header__inner {
    grid-template-columns: 1fr auto;
    gap: 0.75rem;
    width: min(100% - 1rem, 86rem);
    padding-block: 0.55rem;
  }

  .app-header__nav {
    grid-column: 1 / -1;
    grid-row: 2;
    width: 100%;
  }

  .app-header__link {
    flex: 1;
    text-align: center;
  }

  .app-header__brand small,
  .account-menu__name,
  .app-header__login {
    display: none;
  }
}
</style>
