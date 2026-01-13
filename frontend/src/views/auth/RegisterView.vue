<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-gray-100 to-primary/5 p-4" dir="rtl">
    
    <!-- Background Decorations -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
      <div class="absolute bottom-0 left-0 w-[500px] h-[500px] bg-accent/10 rounded-full blur-[120px] translate-y-1/3 -translate-x-1/3"></div>
    </div>
    
    <div class="w-full max-w-lg relative z-10">
      
      <!-- Card -->
      <div class="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-8 md:p-10 animate-slide-up">
        
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary to-teal-600 rounded-2xl mb-4 shadow-xl shadow-primary/20 transform hover:scale-105 transition-transform duration-300">
            <span class="text-3xl font-bold text-white">ع</span>
          </div>
          <h1 class="text-2xl font-bold text-primary">إنشاء حساب جديد</h1>
          <p class="text-gray-500 mt-2">انضم إلى عماد وابدأ تحليل مخططاتك</p>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleRegister" class="space-y-5">
          
          <!-- Full Name -->
          <div class="group">
            <label class="block text-sm font-bold text-gray-700 mb-2">الاسم الكامل</label>
            <div class="relative">
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-primary">
                <i class="fas fa-user"></i>
              </span>
              <input 
                v-model="form.fullName"
                type="text" 
                required
                placeholder="أحمد محمد"
                class="w-full pr-12 pl-4 py-3.5 bg-gray-50/50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white transition-all duration-300 outline-none"
              >
            </div>
          </div>

          <!-- Email -->
          <div class="group">
            <label class="block text-sm font-bold text-gray-700 mb-2">البريد الإلكتروني</label>
            <div class="relative">
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-primary">
                <i class="fas fa-envelope"></i>
              </span>
              <input 
                v-model="form.email"
                type="email" 
                required
                placeholder="example@email.com"
                :class="[
                  'w-full pr-12 pl-4 py-3.5 border rounded-xl transition-all duration-300 outline-none',
                  emailError ? 'border-red-400 bg-red-50/50 focus:ring-red-200' : 'bg-gray-50/50 border-gray-200 focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white'
                ]"
              >
            </div>
            <transition
              enter-active-class="transition ease-out duration-200"
              enter-from-class="opacity-0 -translate-y-1"
              enter-to-class="opacity-100 translate-y-0"
            >
              <p v-if="emailError" class="text-red-500 text-xs mt-1.5 flex items-center gap-1">
                <i class="fas fa-exclamation-circle"></i>
                {{ emailError }}
              </p>
            </transition>
          </div>

          <!-- Account Type -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-3">نوع الحساب</label>
            <div class="grid grid-cols-2 gap-3">
              <button 
                type="button"
                @click="form.accountType = 'personal'"
                :class="[
                  'p-4 border-2 rounded-xl transition-all duration-300 text-center group',
                  form.accountType === 'personal' 
                    ? 'border-primary bg-primary/5 text-primary shadow-md shadow-primary/10' 
                    : 'border-gray-200 hover:border-primary/30 hover:bg-gray-50'
                ]"
              >
                <i class="fas fa-user text-2xl mb-2 transition-transform group-hover:scale-110"></i>
                <div class="font-bold text-sm">شخصي</div>
                <p class="text-xs text-gray-400 mt-1">للاستخدام الفردي</p>
              </button>
              <button 
                type="button"
                @click="form.accountType = 'office'"
                :class="[
                  'p-4 border-2 rounded-xl transition-all duration-300 text-center group',
                  form.accountType === 'office' 
                    ? 'border-primary bg-primary/5 text-primary shadow-md shadow-primary/10' 
                    : 'border-gray-200 hover:border-primary/30 hover:bg-gray-50'
                ]"
              >
                <i class="fas fa-building text-2xl mb-2 transition-transform group-hover:scale-110"></i>
                <div class="font-bold text-sm">مكتب هندسي</div>
                <p class="text-xs text-gray-400 mt-1">للمكاتب والشركات</p>
              </button>
            </div>
          </div>

          <!-- Password -->
          <div class="group">
            <label class="block text-sm font-bold text-gray-700 mb-2">كلمة المرور</label>
            <div class="relative">
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-primary">
                <i class="fas fa-lock"></i>
              </span>
              <input 
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'" 
                required
                minlength="8"
                placeholder="••••••••"
                class="w-full pr-12 pl-14 py-3.5 bg-gray-50/50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white transition-all duration-300 outline-none"
              >
              <button 
                type="button"
                @click="showPassword = !showPassword"
                class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition-colors"
              >
                <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </button>
            </div>
            
            <!-- Password Strength Indicator -->
            <div class="mt-3">
              <div class="flex gap-1 mb-1.5">
                <div 
                  v-for="i in 4" 
                  :key="i"
                  class="h-1.5 flex-1 rounded-full transition-all duration-300"
                  :class="passwordStrength >= i ? strengthColors[passwordStrength] : 'bg-gray-200'"
                ></div>
              </div>
              <p :class="['text-xs transition-colors', strengthTextColors[passwordStrength]]">
                {{ strengthLabels[passwordStrength] }}
              </p>
            </div>
          </div>

          <!-- Confirm Password -->
          <div class="group">
            <label class="block text-sm font-bold text-gray-700 mb-2">تأكيد كلمة المرور</label>
            <div class="relative">
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-primary">
                <i class="fas fa-lock"></i>
              </span>
              <input 
                v-model="form.confirmPassword"
                type="password" 
                required
                placeholder="••••••••"
                :class="[
                  'w-full pr-12 pl-4 py-3.5 border rounded-xl transition-all duration-300 outline-none',
                  passwordError ? 'border-red-400 bg-red-50/50 focus:ring-red-200' : 'bg-gray-50/50 border-gray-200 focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white'
                ]"
              >
              <!-- Match indicator -->
              <transition
                enter-active-class="transition ease-out duration-200"
                enter-from-class="opacity-0 scale-75"
                enter-to-class="opacity-100 scale-100"
              >
                <span 
                  v-if="form.confirmPassword && !passwordError" 
                  class="absolute left-4 top-1/2 -translate-y-1/2 text-green-500"
                >
                  <i class="fas fa-check-circle"></i>
                </span>
              </transition>
            </div>
            <transition
              enter-active-class="transition ease-out duration-200"
              enter-from-class="opacity-0 -translate-y-1"
              enter-to-class="opacity-100 translate-y-0"
            >
              <p v-if="passwordError" class="text-red-500 text-xs mt-1.5 flex items-center gap-1">
                <i class="fas fa-exclamation-circle"></i>
                {{ passwordError }}
              </p>
            </transition>
          </div>

          <!-- Terms -->
          <label class="flex items-start gap-3 cursor-pointer group/terms">
            <div class="relative mt-0.5">
              <input 
                v-model="form.acceptTerms"
                type="checkbox" 
                required
                class="peer h-5 w-5 cursor-pointer appearance-none rounded-md border-2 border-gray-300 transition-all checked:border-primary checked:bg-primary hover:border-primary/50"
              >
              <i class="fas fa-check text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] opacity-0 peer-checked:opacity-100 pointer-events-none"></i>
            </div>
            <span class="text-sm text-gray-600 leading-relaxed">
              أوافق على 
              <a href="#" class="text-primary hover:underline font-medium">الشروط والأحكام</a>
              و
              <a href="#" class="text-primary hover:underline font-medium">سياسة الخصوصية</a>
            </span>
          </label>

          <!-- Error Message -->
          <transition
            enter-active-class="transition ease-out duration-300"
            enter-from-class="opacity-0 -translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-200"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-2"
          >
            <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
              <i class="fas fa-exclamation-circle"></i>
              {{ error }}
            </div>
          </transition>

          <!-- Success Message -->
          <transition
            enter-active-class="transition ease-out duration-300"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
          >
            <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
              <i class="fas fa-check-circle"></i>
              {{ success }}
            </div>
          </transition>

          <!-- Submit Button -->
          <button 
            type="submit"
            :disabled="loading || !isFormValid"
            class="w-full py-4 bg-gradient-to-l from-primary to-teal-600 text-white font-bold rounded-xl hover:shadow-xl hover:shadow-primary/25 hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="animate-spin"><i class="fas fa-spinner"></i></span>
            <template v-else>
              <i class="fas fa-user-plus"></i>
              <span>إنشاء الحساب</span>
            </template>
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
const showPassword = ref(false);

// Password strength
const strengthLabels = {
  0: '8 أحرف على الأقل',
  1: 'ضعيفة',
  2: 'متوسطة',
  3: 'جيدة',
  4: 'قوية جداً'
};

const strengthColors = {
  1: 'bg-red-500',
  2: 'bg-yellow-500',
  3: 'bg-blue-500',
  4: 'bg-green-500'
};

const strengthTextColors = {
  0: 'text-gray-400',
  1: 'text-red-500',
  2: 'text-yellow-600',
  3: 'text-blue-500',
  4: 'text-green-500'
};

const passwordStrength = computed(() => {
  const pwd = form.password;
  if (!pwd) return 0;
  
  let score = 0;
  if (pwd.length >= 8) score++;
  if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++;
  if (/\d/.test(pwd)) score++;
  if (/[^a-zA-Z0-9]/.test(pwd)) score++;
  
  return score;
});

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

<style scoped>
@keyframes slide-up {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-slide-up {
  animation: slide-up 0.6s ease-out forwards;
}
</style>
