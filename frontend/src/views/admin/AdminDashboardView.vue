<template>
  <div class="app-shell" dir="rtl">
    <AppHeader />

    <main class="admin-page page-container">
      <header class="admin-heading">
        <div>
          <span class="eyebrow"><i class="fas fa-shield-halved" aria-hidden="true"></i> الإدارة</span>
          <h1>المستخدمون والوصول</h1>
          <p>قائمة الحسابات الفعلية التي أعادها الخادم. لا تُعرض بيانات تجريبية أو تنبيهات مصطنعة.</p>
        </div>
        <button type="button" class="button button--secondary" :disabled="loading" @click="loadUsers">
          <i :class="loading ? 'fas fa-circle-notch fa-spin' : 'fas fa-rotate'" aria-hidden="true"></i>
          تحديث
        </button>
      </header>

      <section class="admin-summary" aria-label="ملخص المستخدمين">
        <article class="surface admin-summary__primary">
          <span>الحسابات الظاهرة</span>
          <strong>{{ users.length }}</strong>
          <p>إجمالي النتائج المسترجعة من `/api/auth/users`.</p>
        </article>
        <dl class="surface admin-summary__facts">
          <div><dt>نشط</dt><dd>{{ activeUsers }}</dd></div>
          <div><dt>مديرو النظام</dt><dd>{{ adminUsers }}</dd></div>
          <div><dt>المشاريع المسجلة</dt><dd>{{ totalPlans }}</dd></div>
        </dl>
      </section>

      <section class="surface users-panel" aria-labelledby="users-title">
        <header class="users-toolbar">
          <div>
            <h2 id="users-title">قائمة المستخدمين</h2>
            <p>ابحث بالاسم أو البريد. الإجراءات المدمرة غير مفعلة قبل إضافة تأكيد ومراجعة مناسبة.</p>
          </div>
          <label class="search-field">
            <span class="sr-only">البحث عن مستخدم</span>
            <i class="fas fa-magnifying-glass" aria-hidden="true"></i>
            <input v-model.trim="searchQuery" type="search" placeholder="بحث بالاسم أو البريد">
          </label>
        </header>

        <div v-if="loading" class="table-state" role="status">
          <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>
          <p>جاري تحميل المستخدمين…</p>
        </div>

        <div v-else-if="error" class="table-state table-state--error" role="alert">
          <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
          <h3>تعذر تحميل القائمة</h3>
          <p>{{ error }}</p>
          <button type="button" class="button button--primary button--small" @click="loadUsers">إعادة المحاولة</button>
        </div>

        <div v-else-if="filteredUsers.length" class="users-table-wrap">
          <table class="users-table">
            <thead>
              <tr>
                <th scope="col">المستخدم</th>
                <th scope="col">الصلاحية</th>
                <th scope="col">المشاريع</th>
                <th scope="col">الحالة</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in filteredUsers" :key="user.id">
                <td>
                  <div class="user-cell">
                    <span class="user-avatar" aria-hidden="true">{{ (user.name || 'م').charAt(0) }}</span>
                    <div>
                      <strong>{{ user.name || 'مستخدم دون اسم' }}</strong>
                      <span>{{ user.email || 'لا يوجد بريد' }}</span>
                    </div>
                  </div>
                </td>
                <td><span class="role-label">{{ roleLabel(user.role) }}</span></td>
                <td>{{ Number.isFinite(Number(user.plansCount)) ? Number(user.plansCount) : '—' }}</td>
                <td>
                  <span class="account-status" :class="user.status === 'active' ? 'account-status--active' : 'account-status--blocked'">
                    <i :class="user.status === 'active' ? 'fas fa-circle-check' : 'fas fa-ban'" aria-hidden="true"></i>
                    {{ user.status === 'active' ? 'نشط' : 'موقوف' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="table-state">
          <i class="fas fa-users" aria-hidden="true"></i>
          <h3>{{ searchQuery ? 'لا توجد نتيجة مطابقة' : 'لا يوجد مستخدمون' }}</h3>
          <p>{{ searchQuery ? 'جرّب اسمًا أو بريدًا مختلفًا.' : 'لم يُرجع الخادم أي حسابات.' }}</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import AppHeader from '../../components/AppHeader.vue'
import { api } from '../../services/api'

const users = ref([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')

const filteredUsers = computed(() => {
  const query = searchQuery.value.toLocaleLowerCase('ar')
  if (!query) return users.value
  return users.value.filter((user) => (
    String(user.name || '').toLocaleLowerCase('ar').includes(query)
    || String(user.email || '').toLocaleLowerCase('en').includes(query)
  ))
})
const activeUsers = computed(() => users.value.filter((user) => user.status === 'active').length)
const adminUsers = computed(() => users.value.filter((user) => user.role === 'admin').length)
const totalPlans = computed(() => users.value.reduce((total, user) => (
  total + (Number.isFinite(Number(user.plansCount)) ? Number(user.plansCount) : 0)
), 0))

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.admin.users.list()
    users.value = Array.isArray(data) ? data : []
  } catch (requestError) {
    error.value = requestError.message || 'تعذر الاتصال بالخادم.'
    users.value = []
  } finally {
    loading.value = false
  }
}

function roleLabel(role) {
  return {
    admin: 'مدير النظام',
    office: 'مكتب هندسي',
    customer: 'مالك منزل',
    personal: 'مالك منزل',
  }[role] || 'غير محدد'
}

onMounted(loadUsers)
</script>

<style scoped>
.admin-page { padding-block: clamp(1.4rem, 3vw, 2.6rem); }
.admin-heading { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; }
.admin-heading h1, .admin-heading p, .admin-summary p, .users-toolbar h2, .users-toolbar p, .table-state h3, .table-state p { margin: 0; }
.admin-heading h1 { margin-top: .55rem; font-size: clamp(1.55rem, 4vw, 2.2rem); letter-spacing: -.035em; }
.admin-heading p { margin-top: .35rem; color: var(--emad-muted); font-size: .78rem; }
.admin-summary { display: grid; grid-template-columns: minmax(0, 1fr) minmax(26rem, 1fr); gap: 1rem; margin-bottom: 1rem; }
.admin-summary__primary, .admin-summary__facts { padding: 1.1rem 1.2rem; }
.admin-summary__primary span, .admin-summary__facts dt { color: var(--emad-muted); font-size: .67rem; }
.admin-summary__primary strong { display: block; margin-top: .2rem; font-size: 1.35rem; }
.admin-summary__primary p { margin-top: .2rem; color: var(--emad-muted); font-size: .68rem; }
.admin-summary__facts { display: grid; grid-template-columns: repeat(3, 1fr); margin-block: 0; }
.admin-summary__facts div { padding-inline: .9rem; border-left: 1px solid var(--emad-line); }
.admin-summary__facts div:last-child { border-left: 0; }
.admin-summary__facts dd { margin: .25rem 0 0; font-size: 1rem; font-weight: 760; }
.users-panel { overflow: hidden; }
.users-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.15rem; border-bottom: 1px solid var(--emad-line); }
.users-toolbar h2 { font-size: .92rem; }
.users-toolbar p { margin-top: .2rem; color: var(--emad-muted); font-size: .66rem; }
.search-field { position: relative; width: min(100%, 18rem); }
.search-field i { position: absolute; top: 50%; right: .75rem; color: var(--emad-muted); transform: translateY(-50%); }
.search-field input { width: 100%; min-height: 44px; padding: .65rem 2.25rem .65rem .75rem; border: 1px solid var(--emad-line-strong); border-radius: .65rem; background: var(--emad-surface); color: var(--emad-ink); font: inherit; font-size: .72rem; }
.search-field input:focus { border-color: var(--emad-accent); outline: 3px solid var(--emad-focus); }
.users-table-wrap { overflow-x: auto; }
.users-table { width: 100%; border-collapse: collapse; font-size: .74rem; }
.users-table th { padding: .75rem 1rem; background: var(--emad-surface-subtle); color: var(--emad-muted); font-size: .64rem; font-weight: 700; text-align: right; }
.users-table td { padding: .85rem 1rem; border-top: 1px solid var(--emad-line); color: var(--emad-ink-soft); }
.user-cell { display: flex; align-items: center; gap: .7rem; min-width: 15rem; }
.user-avatar { display: grid; width: 2.3rem; height: 2.3rem; flex: 0 0 auto; place-items: center; border-radius: .6rem; background: var(--emad-accent-soft); color: var(--emad-accent-dark); font-weight: 760; }
.user-cell strong, .user-cell span { display: block; }
.user-cell strong { color: var(--emad-ink); font-size: .76rem; }
.user-cell div > span { margin-top: .1rem; color: var(--emad-muted); font-size: .64rem; }
.role-label { display: inline-flex; min-height: 1.8rem; align-items: center; padding-inline: .65rem; border-radius: 99px; background: var(--emad-surface-subtle); font-size: .64rem; font-weight: 700; white-space: nowrap; }
.account-status { display: inline-flex; min-height: 1.8rem; align-items: center; gap: .35rem; padding-inline: .6rem; border: 1px solid; border-radius: 99px; font-size: .64rem; font-weight: 700; white-space: nowrap; }
.account-status--active { border-color: #badbcf; background: #eef8f4; color: var(--emad-accent-dark); }
.account-status--blocked { border-color: #ecc3bf; background: #fff2f1; color: var(--emad-danger); }
.table-state { display: grid; min-height: 18rem; place-items: center; align-content: center; gap: .5rem; padding: 1.5rem; color: var(--emad-muted); text-align: center; }
.table-state > i { font-size: 1.5rem; }
.table-state h3 { color: var(--emad-ink); font-size: .84rem; }
.table-state p { max-width: 25rem; font-size: .7rem; }
.table-state--error > i { color: var(--emad-danger); }
@media (max-width: 780px) { .admin-heading, .users-toolbar { align-items: stretch; flex-direction: column; } .admin-summary { grid-template-columns: 1fr; } .search-field { width: 100%; } }
@media (max-width: 520px) { .admin-summary__facts { grid-template-columns: 1fr; } .admin-summary__facts div { padding: .65rem 0; border-bottom: 1px solid var(--emad-line); border-left: 0; } .admin-summary__facts div:last-child { border-bottom: 0; } }
</style>