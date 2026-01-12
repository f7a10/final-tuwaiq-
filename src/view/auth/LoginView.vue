<template>
  <div class="min-h-screen flex" dir="rtl">
    
    <!-- Right Side: Login Form -->
    <div class="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
      <div class="w-full max-w-md">
        
        <!-- Logo & Title -->
        <div class="text-center mb-10">
          <div class="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-2xl mb-4 shadow-lg">
            <span class="text-3xl font-bold text-white">ع</span>
          </div>
          <h1 class="text-3xl font-bold text-primary">مرحباً بك في عماد</h1>
          <p class="text-gray-500 mt-2">سجّل دخولك للمتابعة</p>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-6">
          
          <!-- Email Field -->
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
                class="w-full pr-10 pl-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-accent focus:border-primary transition outline-none"
              >
            </div>
          </div>

          <!-- Password Field -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">كلمة المرور</label>
            <div class="relative">
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <i class="fas fa-lock"></i>
              </span>
              <input 
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'" 
                required
                placeholder="••••••••"
                class="w-full pr-10 pl-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-accent focus:border-primary transition outline-none"
              >
              <button 
                type="button"
                @click="showPassword = !showPassword"
                class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition"
              >
                <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </button>
            </div>
          </div>

          <!-- Remember Me & Forgot Password -->
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-2 cursor-pointer">
              <input 
                v-model="form.rememberMe"
                type="checkbox" 
                class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-accent"
              >
              <span class="text-sm text-gray-600">تذكرني</span>
            </label>
            <a href="#" class="text-sm text-primary hover:underline font-medium">نسيت كلمة المرور؟</a>
          </div>

          <!-- Error Message -->
          <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            <i class="fas fa-exclamation-circle ml-2"></i>
            {{ error }}
          </div>

          <!-- Submit Button -->
          <button 
            type="submit"
            :disabled="loading"
            class="w-full py-3.5 bg-primary text-white font-bold rounded-xl hover:bg-primary/90 transition shadow-lg shadow-primary/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="animate-spin"><i class="fas fa-spinner"></i></span>
            <span v-else><i class="fas fa-sign-in-alt ml-2"></i>تسجيل الدخول</span>
          </button>

        </form>

        <!-- Register Link -->
        <p class="text-center mt-8 text-gray-600">
          ليس لديك حساب؟
          <router-link to="/register" class="text-primary font-bold hover:underline">سجّل الآن</router-link>
        </p>

      </div>
    </div>

    <!-- Left Side: Branding -->
    <div class="hidden lg:flex w-1/2 bg-gradient-to-br from-primary via-primary to-secondary relative overflow-hidden">
      <!-- Decorative Elements -->
      <div class="absolute inset-0 opacity-10">
        <div class="absolute top-20 right-20 w-64 h-64 bg-white rounded-full blur-3xl"></div>
        <div class="absolute bottom-20 left-20 w-96 h-96 bg-accent rounded-full blur-3xl"></div>
      </div>
      
      <!-- Content -->
      <div class="relative z-10 flex flex-col items-center justify-center w-full p-12 text-white text-center">
        <div class="w-24 h-24 bg-white/20 backdrop-blur rounded-3xl flex items-center justify-center mb-8 shadow-2xl">
          <span class="text-5xl font-bold">ع</span>
        </div>
        <h2 class="text-4xl font-bold mb-4">عماد</h2>
        <p class="text-xl opacity-90 mb-8">مدقق المخططات المعمارية بالذكاء الاصطناعي</p>
        
        <div class="grid grid-cols-3 gap-6 mt-8">
          <div class="text-center">
            <div class="text-3xl font-bold text-accent">+1000</div>
            <div class="text-sm opacity-75">مخطط تم تحليله</div>
          </div>
          <div class="text-center">
            <div class="text-3xl font-bold text-accent">99%</div>
            <div class="text-sm opacity-75">دقة الفحص</div>
          </div>
          <div class="text-center">
            <div class="text-3xl font-bold text-accent">24/7</div>
            <div class="text-sm opacity-75">دعم فني</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const form = reactive({
  email: '',
  password: '',
  rememberMe: false
});

const showPassword = ref(false);
const loading = ref(false);
const error = ref('');

const handleLogin = async () => {
  loading.value = true;
  error.value = '';

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: form.email,
        password: form.password,
        remember_me: form.rememberMe
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'فشل تسجيل الدخول');
    }

    // Store token
    localStorage.setItem('auth_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));

    // Redirect based on role
    if (data.user.role === 'admin') {
      router.push('/admin');
    } else {
      router.push('/');
    }

  } catch (err) {
    error.value = err.message || 'حدث خطأ أثناء تسجيل الدخول';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Custom focus states with accent color */
input:focus {
  --tw-ring-color: #D6D693;
}
</style>
