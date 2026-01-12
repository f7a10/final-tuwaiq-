<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 p-4" dir="rtl">
    
    <div class="w-full max-w-lg">
      
      <!-- Card -->
      <div class="bg-white rounded-3xl shadow-xl p-8 md:p-10">
        
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-14 h-14 bg-primary rounded-2xl mb-4 shadow-lg">
            <span class="text-2xl font-bold text-white">ع</span>
          </div>
          <h1 class="text-2xl font-bold text-primary">إنشاء حساب جديد</h1>
          <p class="text-gray-500 mt-2">انضم إلى عماد وابدأ تحليل مخططاتك</p>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleRegister" class="space-y-5">
          
          <!-- Full Name -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">الاسم الكامل</label>
            <div class="relative">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <i class="fas fa-user"></i>
              </span>
              <input 
                v-model="form.fullName"
                type="text" 
                required
                placeholder="أحمد محمد"
                class="w-full pr-10 pl-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-accent focus:border-primary transition outline-none"
              >
            </div>
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">البريد الإلكتروني</label>
            <div class="relative">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <i class="fas fa-envelope"></i>
              </span>
              <input 
                v-model="form.email"
                type="email" 
                required
                placeholder="example@email.com"
                :class="[
                  'w-full pr-10 pl-4 py-3 border rounded-xl transition outline-none',
                  emailError ? 'border-red-500 focus:ring-red-200' : 'border-gray-300 focus:ring-2 focus:ring-accent focus:border-primary'
                ]"
              >
            </div>
            <p v-if="emailError" class="text-red-500 text-xs mt-1">{{ emailError }}</p>
          </div>

          <!-- Account Type -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">نوع الحساب</label>
            <div class="grid grid-cols-2 gap-3">
              <button 
                type="button"
                @click="form.accountType = 'personal'"
                :class="[
                  'p-4 border-2 rounded-xl transition text-center',
                  form.accountType === 'personal' 
                    ? 'border-primary bg-primary/5 text-primary' 
                    : 'border-gray-200 hover:border-gray-300'
                ]"
              >
                <i class="fas fa-user text-xl mb-2"></i>
                <div class="font-bold text-sm">شخصي</div>
              </button>
              <button 
                type="button"
                @click="form.accountType = 'office'"
                :class="[
                  'p-4 border-2 rounded-xl transition text-center',
                  form.accountType === 'office' 
                    ? 'border-primary bg-primary/5 text-primary' 
                    : 'border-gray-200 hover:border-gray-300'
                ]"
              >
                <i class="fas fa-building text-xl mb-2"></i>
                <div class="font-bold text-sm">مكتب هندسي</div>
              </button>
            </div>
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">كلمة المرور</label>
            <div class="relative">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <i class="fas fa-lock"></i>
              </span>
              <input 
                v-model="form.password"
                type="password" 
                required
                minlength="8"
                placeholder="••••••••"
                class="w-full pr-10 pl-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-accent focus:border-primary transition outline-none"
              >
            </div>
            <p class="text-gray-400 text-xs mt-1">8 أحرف على الأقل</p>
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">تأكيد كلمة المرور</label>
            <div class="relative">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <i class="fas fa-lock"></i>
              </span>
              <input 
                v-model="form.confirmPassword"
                type="password" 
                required
                placeholder="••••••••"
                :class="[
                  'w-full pr-10 pl-4 py-3 border rounded-xl transition outline-none',
                  passwordError ? 'border-red-500 focus:ring-red-200' : 'border-gray-300 focus:ring-2 focus:ring-accent focus:border-primary'
                ]"
              >
            </div>
            <p v-if="passwordError" class="text-red-500 text-xs mt-1">{{ passwordError }}</p>
          </div>

          <!-- Terms -->
          <label class="flex items-start gap-3 cursor-pointer">
            <input 
              v-model="form.acceptTerms"
              type="checkbox" 
              required
              class="w-5 h-5 mt-0.5 rounded border-gray-300 text-primary focus:ring-accent"
            >
            <span class="text-sm text-gray-600">
              أوافق على 
              <a href="#" class="text-primary hover:underline">الشروط والأحكام</a>
              و
              <a href="#" class="text-primary hover:underline">سياسة الخصوصية</a>
            </span>
          </label>

          <!-- Error Message -->
          <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            <i class="fas fa-exclamation-circle ml-2"></i>
            {{ error }}
          </div>

          <!-- Success Message -->
          <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm">
            <i class="fas fa-check-circle ml-2"></i>
            {{ success }}
          </div>

          <!-- Submit Button -->
          <button 
            type="submit"
            :disabled="loading || !isFormValid"
            class="w-full py-3.5 bg-primary text-white font-bold rounded-xl hover:bg-primary/90 transition shadow-lg shadow-primary/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="animate-spin"><i class="fas fa-spinner"></i></span>
            <span v-else><i class="fas fa-user-plus ml-2"></i>إنشاء الحساب</span>
          </button>

        </form>

        <!-- Login Link -->
        <p class="text-center mt-6 text-gray-600">
          لديك حساب بالفعل؟
          <router-link to="/login" class="text-primary font-bold hover:underline">سجّل دخولك</router-link>
        </p>

      </div>

      <!-- Footer -->
      <p class="text-center text-gray-400 text-sm mt-6">
        © 2026 عماد - جميع الحقوق محفوظة
      </p>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const form = reactive({
  fullName: '',
  email: '',
  password: '',
  confirmPassword: '',
  accountType: 'personal',
  acceptTerms: false
});

const loading = ref(false);
const error = ref('');
const success = ref('');
const emailError = ref('');
const passwordError = ref('');

// Validate email format
watch(() => form.email, (val) => {
  if (val && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
    emailError.value = 'صيغة البريد الإلكتروني غير صحيحة';
  } else {
    emailError.value = '';
  }
});

// Validate password match
watch(() => form.confirmPassword, (val) => {
  if (val && val !== form.password) {
    passwordError.value = 'كلمات المرور غير متطابقة';
  } else {
    passwordError.value = '';
  }
});

const isFormValid = computed(() => {
  return form.fullName && 
         form.email && 
         !emailError.value && 
         form.password.length >= 8 && 
         form.password === form.confirmPassword &&
         form.acceptTerms;
});

const handleRegister = async () => {
  if (!isFormValid.value) return;
  
  loading.value = true;
  error.value = '';
  success.value = '';

  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: form.fullName,
        email: form.email,
        password: form.password,
        account_type: form.accountType
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'فشل إنشاء الحساب');
    }

    success.value = 'تم إنشاء الحساب بنجاح! جاري التحويل...';
    
    setTimeout(() => {
      router.push('/login');
    }, 2000);

  } catch (err) {
    error.value = err.message || 'حدث خطأ أثناء إنشاء الحساب';
  } finally {
    loading.value = false;
  }
};
</script>
