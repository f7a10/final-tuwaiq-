<template>
  <div class="register-page" dir="rtl">
    <header class="register-topbar">
      <RouterLink to="/" class="register-brand" aria-label="عماد — الصفحة الرئيسية">
        <BrandMark />
        <span>عماد</span>
      </RouterLink>
      <RouterLink :to="loginLink" class="button button--ghost button--small">لدي حساب</RouterLink>
    </header>

    <main class="register-main">
      <section class="surface register-shell" aria-labelledby="register-title">
        <div class="register-heading">
          <span class="eyebrow"><i class="fas fa-user-plus" aria-hidden="true"></i> حساب جديد</span>
          <h1 id="register-title">أنشئ مساحة مشاريعك</h1>
          <p>احفظ المخططات وارجع إلى التحليل والمعاينات والنسخ المعتمدة من أي جلسة.</p>
        </div>

        <form @submit.prevent="handleRegister">
          <div class="field field--wide">
            <label for="register-name" class="field__label">الاسم الكامل</label>
            <input id="register-name" v-model.trim="form.fullName" name="full_name" class="input" type="text" autocomplete="name" required>
          </div>

          <div class="field field--wide">
            <label for="register-email" class="field__label">البريد الإلكتروني</label>
            <input id="register-email" v-model.trim="form.email" class="input" type="email" autocomplete="email" required placeholder="name@example.com">
            <p v-if="emailError" class="field-error" role="alert">{{ emailError }}</p>
          </div>

          <div class="field">
            <label for="register-password" class="field__label">كلمة المرور</label>
            <input id="register-password" v-model="form.password" name="password" class="input" type="password" autocomplete="new-password" minlength="8" required>
            <p class="field__hint">8 أحرف على الأقل.</p>
          </div>

          <div class="field">
            <label for="register-confirm" class="field__label">تأكيد كلمة المرور</label>
            <input id="register-confirm" v-model="form.confirmPassword" name="confirm_password" class="input" type="password" autocomplete="new-password" required>
            <p v-if="passwordError" class="field-error" role="alert">{{ passwordError }}</p>
          </div>

          <label class="acknowledgement field--wide">
            <input v-model="form.acceptGuidance" type="checkbox" required>
            <span>أفهم أن نتائج عماد إرشادية أولية، وأن القرارات الإنشائية والاعتماد النهائي تحتاج مختصًا مرخّصًا.</span>
          </label>

          <div v-if="error" class="notice notice--danger field--wide" role="alert">
            <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
            <span>{{ error }}</span>
          </div>

          <button class="button button--primary register-submit field--wide" type="submit" :disabled="!isFormValid || loading">
            <i :class="loading ? 'fas fa-circle-notch fa-spin' : 'fas fa-user-plus'" aria-hidden="true"></i>
            {{ loading ? 'جاري إنشاء الحساب…' : 'إنشاء الحساب' }}
          </button>
        </form>

        <p class="register-login">لديك حساب؟ <RouterLink :to="loginLink">تسجيل الدخول</RouterLink></p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandMark from '../../components/BrandMark.vue'
import { api } from '../../services/api'

const route = useRoute()
const router = useRouter()
const form = reactive({
  fullName: '',
  email: '',
  password: '',
  confirmPassword: '',
  acceptGuidance: false,
})
const loading = ref(false)
const error = ref('')

const safeRedirect = computed(() => {
  const value = route.query.redirect
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    ? value
    : ''
})
const loginLink = computed(() => ({
  path: '/login',
  query: safeRedirect.value ? { redirect: safeRedirect.value } : {},
}))
const emailError = computed(() => {
  if (!form.email) return ''
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)
    ? ''
    : 'صيغة البريد الإلكتروني غير صحيحة.'
})
const passwordError = computed(() => {
  if (!form.confirmPassword) return ''
  return form.password === form.confirmPassword ? '' : 'كلمتا المرور غير متطابقتين.'
})
const isFormValid = computed(() => Boolean(
  form.fullName
  && form.email
  && !emailError.value
  && form.password.length >= 8
  && form.password === form.confirmPassword
  && form.acceptGuidance,
))

async function handleRegister() {
  if (!isFormValid.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    await api.auth.register({
      full_name: form.fullName,
      email: form.email,
      password: form.password,
      account_type: 'personal',
    })
    await router.push(loginLink.value)
  } catch (requestError) {
    error.value = requestError.message || 'تعذر إنشاء الحساب. حاول مرة أخرى.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: var(--emad-bg);
}

.register-topbar {
  display: flex;
  min-height: 4.5rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-inline: clamp(1rem, 4vw, 3rem);
  border-bottom: 1px solid var(--emad-line);
  background: var(--emad-surface);
}

.register-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  color: var(--emad-ink);
  font-weight: 750;
  text-decoration: none;
}

.register-main {
  display: grid;
  min-height: calc(100vh - 4.5rem);
  place-items: center;
  padding: clamp(1rem, 5vw, 4rem);
}

.register-shell {
  width: min(100%, 42rem);
  padding: clamp(1.3rem, 4vw, 2.6rem);
}

.register-heading {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--emad-line);
}

.register-heading h1,
.register-heading p,
.register-login {
  margin: 0;
}

.register-heading h1 {
  margin-top: 0.7rem;
  font-size: clamp(1.55rem, 4vw, 2.1rem);
  letter-spacing: -0.035em;
}

.register-heading p {
  margin-top: 0.45rem;
  color: var(--emad-muted);
  font-size: 0.82rem;
}

.register-shell form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1.5rem;
}

.field--wide {
  grid-column: 1 / -1;
}

.field-error {
  margin: 0.35rem 0 0;
  color: var(--emad-danger);
  font-size: 0.72rem;
}

.acknowledgement {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.65rem;
  align-items: start;
  padding: 0.8rem;
  border: 1px solid var(--emad-line);
  border-radius: 0.7rem;
  background: var(--emad-surface-subtle);
  color: var(--emad-muted);
  font-size: 0.74rem;
  line-height: 1.75;
  cursor: pointer;
}

.acknowledgement input {
  width: 1.1rem;
  height: 1.1rem;
  margin-top: 0.2rem;
  accent-color: var(--emad-accent);
}

.register-submit {
  min-height: 3.2rem;
}

.register-login {
  margin-top: 1.2rem;
  color: var(--emad-muted);
  font-size: 0.76rem;
  text-align: center;
}

.register-login a {
  color: var(--emad-accent-dark);
  font-weight: 720;
}

@media (max-width: 560px) {
  .register-shell form {
    grid-template-columns: 1fr;
  }

  .field--wide {
    grid-column: auto;
  }
}
</style>