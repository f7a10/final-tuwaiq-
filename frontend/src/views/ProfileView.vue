<template>
  <div class="app-shell" dir="rtl">
    <AppHeader />

    <main class="profile-page page-container">
      <header class="profile-heading">
        <div>
          <span class="eyebrow"><i class="fas fa-user" aria-hidden="true"></i> الحساب</span>
          <h1>بيانات الحساب</h1>
          <p>راجع معلومات حسابك وحالة الوصول إلى مشاريعك.</p>
        </div>
        <RouterLink to="/projects" class="button button--secondary">
          <i class="fas fa-folder-open" aria-hidden="true"></i> مشاريعي
        </RouterLink>
      </header>

      <div v-if="authStore.error" class="notice notice--warning" role="status">
        <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
        <span>تعذر تحديث البيانات الآن. تُعرض آخر بيانات محفوظة على هذا الجهاز.</span>
      </div>

      <section class="profile-grid" aria-label="تفاصيل الحساب">
        <article class="surface identity-panel">
          <div class="identity-panel__top">
            <span class="avatar" aria-hidden="true">{{ userInitial }}</span>
            <div>
              <h2>{{ user?.full_name || 'المستخدم' }}</h2>
              <p>{{ user?.email || 'لا يوجد بريد محفوظ' }}</p>
            </div>
            <span class="status-chip" :class="user?.is_active === false ? 'status-chip--danger' : 'status-chip--success'">
              <i :class="user?.is_active === false ? 'fas fa-ban' : 'fas fa-circle-check'" aria-hidden="true"></i>
              {{ user?.is_active === false ? 'الحساب موقوف' : 'الحساب نشط' }}
            </span>
          </div>

          <dl class="account-details">
            <div>
              <dt>نوع الحساب</dt>
              <dd>{{ accountTypeLabel }}</dd>
            </div>
            <div>
              <dt>الصلاحية</dt>
              <dd>{{ roleLabel }}</dd>
            </div>
            <div>
              <dt>تاريخ الانضمام</dt>
              <dd>{{ joinedAt }}</dd>
            </div>
            <div>
              <dt>المشاريع المسجلة</dt>
              <dd>{{ user?.plans_count ?? '—' }}</dd>
            </div>
          </dl>
        </article>

        <aside class="surface account-actions">
          <div>
            <span class="account-actions__icon"><i class="fas fa-shield-halved" aria-hidden="true"></i></span>
            <h2>الجلسة والخصوصية</h2>
            <p>سجّل الخروج عند استخدام جهاز مشترك. لن تُحذف مشاريعك أو تقاريرك.</p>
          </div>

          <div class="account-actions__note">
            <i class="fas fa-lock" aria-hidden="true"></i>
            <span>تعديل الاسم أو البريد غير متاح بعد؛ لن نعرض زرًا لا ينفّذ تغييرًا حقيقيًا.</span>
          </div>

          <button data-testid="logout" class="button button--danger button--full" type="button" @click="handleLogout">
            <i class="fas fa-arrow-right-from-bracket" aria-hidden="true"></i>
            تسجيل الخروج
          </button>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '../components/AppHeader.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const user = computed(() => authStore.currentUser)

const userInitial = computed(() => (user.value?.full_name || 'م').trim().charAt(0))
const accountTypeLabel = computed(() => (
  user.value?.account_type === 'office' ? 'مكتب هندسي' : 'شخصي'
))
const roleLabel = computed(() => ({
  admin: 'مدير النظام',
  office: 'مكتب هندسي',
  customer: 'مالك منزل',
  personal: 'مالك منزل',
}[user.value?.role] || 'مالك منزل'))
const joinedAt = computed(() => {
  if (!user.value?.created_at) return '—'
  const date = new Date(user.value.created_at)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('ar-SA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
})

function handleLogout() {
  authStore.logout()
  router.push('/')
}

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  authStore.fetchCurrentUser()
})
</script>

<style scoped>
.profile-page {
  padding-block: clamp(1.5rem, 4vw, 3rem);
}

.profile-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1.2rem;
  margin-bottom: 1.5rem;
}

.profile-heading h1,
.profile-heading p,
.identity-panel h2,
.identity-panel p,
.account-actions h2,
.account-actions p {
  margin: 0;
}

.profile-heading h1 {
  margin-top: 0.6rem;
  color: var(--emad-ink);
  font-size: clamp(1.55rem, 4vw, 2.25rem);
  letter-spacing: -0.035em;
}

.profile-heading p {
  margin-top: 0.35rem;
  color: var(--emad-muted);
  font-size: 0.82rem;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(17rem, 0.55fr);
  gap: 1rem;
  align-items: start;
  margin-top: 1rem;
}

.identity-panel,
.account-actions {
  padding: clamp(1.2rem, 3vw, 2rem);
}

.identity-panel__top {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1rem;
  align-items: center;
  padding-bottom: 1.4rem;
  border-bottom: 1px solid var(--emad-line);
}

.avatar {
  display: grid;
  width: 3.5rem;
  height: 3.5rem;
  place-items: center;
  border-radius: 0.85rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 1.3rem;
  font-weight: 780;
}

.identity-panel h2,
.account-actions h2 {
  color: var(--emad-ink);
  font-size: 1rem;
}

.identity-panel p,
.account-actions p {
  margin-top: 0.25rem;
  color: var(--emad-muted);
  font-size: 0.75rem;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2rem;
  padding-inline: 0.7rem;
  border: 1px solid;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

.status-chip--success {
  border-color: #badbcf;
  background: #eef8f4;
  color: var(--emad-accent-dark);
}

.status-chip--danger {
  border-color: #ecc3bf;
  background: #fff2f1;
  color: var(--emad-danger);
}

.account-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.account-details div {
  padding: 1.2rem 0;
  border-bottom: 1px solid var(--emad-line);
}

.account-details div:nth-child(odd) {
  padding-left: 1rem;
  border-left: 1px solid var(--emad-line);
}

.account-details div:nth-child(even) {
  padding-right: 1rem;
}

.account-details div:nth-last-child(-n + 2) {
  border-bottom: 0;
}

.account-details dt {
  color: var(--emad-muted);
  font-size: 0.7rem;
}

.account-details dd {
  margin: 0.3rem 0 0;
  color: var(--emad-ink);
  font-size: 0.85rem;
  font-weight: 700;
}

.account-actions {
  display: grid;
  gap: 1.3rem;
}

.account-actions__icon {
  display: grid;
  width: 2.8rem;
  height: 2.8rem;
  margin-bottom: 0.8rem;
  place-items: center;
  border-radius: 0.75rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-accent-dark);
}

.account-actions__note {
  display: flex;
  gap: 0.55rem;
  padding: 0.8rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.7rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  font-size: 0.7rem;
  line-height: 1.65;
}

.account-actions__note i {
  margin-top: 0.18rem;
  color: var(--emad-accent);
}

.button--full {
  width: 100%;
}

@media (max-width: 760px) {
  .profile-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }

  .identity-panel__top {
    grid-template-columns: auto 1fr;
  }

  .status-chip {
    grid-column: 1 / -1;
    justify-self: start;
  }
}

@media (max-width: 480px) {
  .account-details {
    grid-template-columns: 1fr;
  }

  .account-details div,
  .account-details div:nth-child(odd),
  .account-details div:nth-child(even) {
    padding: 1rem 0;
    border-bottom: 1px solid var(--emad-line);
    border-left: 0;
  }

  .account-details div:last-child {
    border-bottom: 0;
  }
}
</style>