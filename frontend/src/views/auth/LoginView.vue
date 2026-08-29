<template>
  <div class="auth-page" dir="rtl">
    <header class="auth-topbar">
      <RouterLink to="/" class="auth-brand" aria-label="عماد — الصفحة الرئيسية">
        <BrandMark />
        <span>عماد</span>
      </RouterLink>
      <RouterLink to="/" class="button button--ghost button--small">
        <i class="fas fa-arrow-right" aria-hidden="true"></i> العودة
      </RouterLink>
    </header>

    <main class="auth-main">
      <section class="surface auth-shell" aria-labelledby="login-title">
        <div class="auth-form-side">
          <span class="eyebrow"><i class="fas fa-user" aria-hidden="true"></i> الحساب</span>
          <h1 id="login-title">تسجيل الدخول</h1>
          <p class="auth-lead">ادخل إلى مشاريعك وتابع آخر تحليل أو تعديل من حيث توقفت.</p>

          <form @submit.prevent="handleLogin">
            <div class="field">
              <label for="login-email" class="field__label">البريد الإلكتروني</label>
              <input
                id="login-email"
                v-model.trim="form.email"
                class="input"
                type="email"
                autocomplete="email"
                required
                placeholder="name@example.com"
              >
            </div>

            <div class="field">
              <label for="login-password" class="field__label">كلمة المرور</label>
              <div class="password-field">
                <input
                  id="login-password"
                  v-model="form.password"
                  class="input"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="current-password"
                  required
                  placeholder="••••••••"
                >
                <button
                  type="button"
                  :aria-label="showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'"
                  @click="showPassword = !showPassword"
                >
                  <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'" aria-hidden="true"></i>
                </button>
              </div>
            </div>

            <div v-if="error" class="notice notice--danger" role="alert">
              <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
              <span>{{ error }}</span>
            </div>

            <button class="button button--primary auth-submit" type="submit" :disabled="loading">
              <i :class="loading ? 'fas fa-circle-notch fa-spin' : 'fas fa-arrow-left-to-bracket'" aria-hidden="true"></i>
              {{ loading ? 'جاري التحقق…' : 'تسجيل الدخول' }}
            </button>
          </form>

          <p class="auth-switch">
            ليس لديك حساب؟
            <RouterLink :to="registerLink">إنشاء حساب جديد</RouterLink>
          </p>
        </div>

        <aside class="auth-context" aria-label="ما الذي يمكنك متابعته بعد الدخول">
          <div>
            <span class="auth-context__mark"><i class="fas fa-compass-drafting" aria-hidden="true"></i></span>
            <h2>مشروعك يبقى في مكان واحد</h2>
            <p>الملف الأصلي، التحليل، المعاينات، والنسخ التي اعتمدتها تُجمع تحت المشروع نفسه.</p>
          </div>
          <ul>
            <li><i class="fas fa-circle-check" aria-hidden="true"></i> متابعة حالة التحليل الحقيقية</li>
            <li><i class="fas fa-circle-check" aria-hidden="true"></i> مراجعة الملاحظات والدليل المتاح</li>
            <li><i class="fas fa-circle-check" aria-hidden="true"></i> العودة إلى Preview أو Revision محفوظة</li>
          </ul>
          <p class="auth-context__note"><i class="fas fa-lock" aria-hidden="true"></i> لا تشارك كلمة المرور أو مفاتيح API داخل المحادثات.</p>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandMark from '../../components/BrandMark.vue'
import { api } from '../../services/api'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '' })
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

const safeRedirect = computed(() => {
  const value = route.query.redirect
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    ? value
    : ''
})
const registerLink = computed(() => ({
  path: '/register',
  query: safeRedirect.value ? { redirect: safeRedirect.value } : {},
}))

async function handleLogin() {
  if (loading.value) return
  loading.value = true
  error.value = ''

  try {
    const data = await api.auth.login({
      email: form.email,
      password: form.password,
    })
    authStore.setAuth(data.access_token, data.user)
    await router.push(
      safeRedirect.value || (data.user.role === 'admin' ? '/admin' : '/projects'),
    )
  } catch (requestError) {
    error.value = requestError.message || 'تعذر تسجيل الدخول. تحقق من البيانات وحاول مرة أخرى.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: var(--emad-bg);
}

.auth-topbar {
  display: flex;
  min-height: 4.5rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-inline: clamp(1rem, 4vw, 3rem);
  border-bottom: 1px solid var(--emad-line);
  background: var(--emad-surface);
}

.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  color: var(--emad-ink);
  font-size: 1rem;
  font-weight: 750;
  text-decoration: none;
}

.auth-main {
  display: grid;
  min-height: calc(100vh - 4.5rem);
  place-items: center;
  padding: clamp(1rem, 5vw, 4rem);
}

.auth-shell {
  display: grid;
  width: min(100%, 56rem);
  grid-template-columns: minmax(0, 1.1fr) minmax(18rem, 0.9fr);
  overflow: hidden;
}

.auth-form-side,
.auth-context {
  padding: clamp(1.4rem, 4vw, 3rem);
}

.auth-form-side h1,
.auth-form-side p,
.auth-context h2,
.auth-context p {
  margin: 0;
}

.auth-form-side h1 {
  margin-top: 0.8rem;
  color: var(--emad-ink);
  font-size: clamp(1.6rem, 4vw, 2.25rem);
  letter-spacing: -0.035em;
}

.auth-lead {
  margin-top: 0.55rem !important;
  color: var(--emad-muted);
  font-size: 0.84rem;
}

.auth-form-side form {
  display: grid;
  gap: 1rem;
  margin-top: 2rem;
}

.password-field {
  position: relative;
}

.password-field .input {
  padding-left: 3rem;
}

.password-field button {
  position: absolute;
  top: 50%;
  left: 0.4rem;
  display: grid;
  width: 2.4rem;
  height: 2.4rem;
  place-items: center;
  border: 0;
  border-radius: 0.55rem;
  background: transparent;
  color: var(--emad-muted);
  cursor: pointer;
  transform: translateY(-50%);
}

.password-field button:hover {
  background: var(--emad-surface-subtle);
  color: var(--emad-accent-dark);
}

.auth-submit {
  width: 100%;
  min-height: 3.2rem;
}

.auth-switch {
  margin-top: 1.35rem !important;
  color: var(--emad-muted);
  font-size: 0.78rem;
  text-align: center;
}

.auth-switch a {
  color: var(--emad-accent-dark);
  font-weight: 720;
}

.auth-context {
  display: grid;
  align-content: space-between;
  gap: 2rem;
  border-right: 1px solid var(--emad-line);
  background-color: #eef1ed;
  background-image: linear-gradient(rgba(31, 39, 34, 0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(31, 39, 34, 0.035) 1px, transparent 1px);
  background-size: 22px 22px;
}

.auth-context__mark {
  display: grid;
  width: 3.2rem;
  height: 3.2rem;
  place-items: center;
  border-radius: 0.85rem;
  background: var(--emad-accent-soft);
  color: var(--emad-accent-dark);
  font-size: 1.15rem;
}

.auth-context h2 {
  margin-top: 1rem;
  font-size: 1.08rem;
}

.auth-context p {
  margin-top: 0.45rem;
  color: var(--emad-muted);
  font-size: 0.76rem;
}

.auth-context ul {
  display: grid;
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  color: var(--emad-ink-soft);
  font-size: 0.76rem;
  list-style: none;
}

.auth-context li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.auth-context li i,
.auth-context__note i {
  color: var(--emad-accent);
}

.auth-context__note {
  padding-top: 1rem;
  border-top: 1px solid var(--emad-line-strong);
  font-size: 0.68rem !important;
}

@media (max-width: 720px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-context {
    border-top: 1px solid var(--emad-line);
    border-right: 0;
  }
}
</style>