<template>
  <div class="min-h-screen flex" dir="rtl">
    
    <!-- Right Side: Login Form -->
    <div class="w-full lg:w-1/2 flex items-center justify-center p-8 bg-gradient-to-br from-gray-50 to-gray-100">
      <div class="w-full max-w-md">
        
        <!-- Logo & Title -->
        <div class="text-center mb-10 animate-fade-in">
          <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary to-teal-600 rounded-2xl mb-4 shadow-xl shadow-primary/20 transform hover:scale-105 transition-transform duration-300">
            <span class="text-4xl font-bold text-white">ع</span>
          </div>
          <h1 class="text-3xl font-bold text-primary">مرحباً بك في عماد</h1>
          <p class="text-gray-500 mt-2">سجّل دخولك للمتابعة</p>
        </div>

        <!-- Login Form Card -->
        <div class="bg-white/70 backdrop-blur-xl rounded-3xl shadow-xl border border-white/50 p-8 animate-slide-up">
          <form @submit.prevent="handleLogin" class="space-y-6">
            
            <!-- Email Field -->
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
                  class="w-full pr-12 pl-4 py-4 bg-gray-50/50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white transition-all duration-300 outline-none"
                >
              </div>
            </div>

            <!-- Password Field -->
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
                  placeholder="••••••••"
                  class="w-full pr-12 pl-14 py-4 bg-gray-50/50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent/50 focus:border-primary focus:bg-white transition-all duration-300 outline-none"
                >
                <button 
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition-colors"
                >
                  <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                </button>
              </div>
            </div>

            <!-- Remember Me & Forgot Password -->
            <div class="flex items-center justify-between">
              <label class="flex items-center gap-2 cursor-pointer group/check">
                <div class="relative">
                  <input 
                    v-model="form.rememberMe"
                    type="checkbox" 
                    class="peer h-5 w-5 cursor-pointer appearance-none rounded-md border-2 border-gray-300 transition-all checked:border-primary checked:bg-primary hover:border-primary/50"
                  >
                  <i class="fas fa-check text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] opacity-0 peer-checked:opacity-100 pointer-events-none"></i>
                </div>
                <span class="text-sm text-gray-600 group-hover/check:text-gray-800 transition-colors">تذكرني</span>
              </label>
              <a href="#" class="text-sm text-primary hover:underline font-medium hover:text-primary/80 transition-colors">نسيت كلمة المرور؟</a>
            </div>

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
              :disabled="loading"
              class="w-full py-4 bg-gradient-to-l from-primary to-teal-600 text-white font-bold rounded-xl hover:shadow-xl hover:shadow-primary/25 hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none flex items-center justify-center gap-2"
            >
              <span v-if="loading" class="animate-spin"><i class="fas fa-spinner"></i></span>
              <template v-else>
                <i class="fas fa-sign-in-alt"></i>
                <span>تسجيل الدخول</span>
              </template>
            </button>

          </form>
        </div>

        <!-- Register Link -->
        <p class="text-center mt-8 text-gray-600 animate-fade-in" style="animation-delay: 0.3s">
          ليس لديك حساب؟
          <router-link to="/register" class="text-primary font-bold hover:underline">سجّل الآن</router-link>
        </p>

      </div>
    </div>

    <!-- Left Side: Branding -->
    <div class="hidden lg:flex w-1/2 bg-gradient-to-br from-primary via-primary to-teal-700 relative overflow-hidden">
      <!-- Decorative Elements -->
      <div class="absolute inset-0">
        <div class="absolute top-20 right-20 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div class="absolute bottom-20 left-20 w-96 h-96 bg-accent/20 rounded-full blur-3xl animate-pulse-slow" style="animation-delay: 1s"></div>
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-white/5 rounded-full"></div>
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] border border-white/5 rounded-full"></div>
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] border border-white/10 rounded-full"></div>
      </div>
      
      <!-- Content -->
      <div class="relative z-10 flex flex-col items-center justify-center w-full p-12 text-white text-center">
        <div class="w-28 h-28 bg-white/20 backdrop-blur-md rounded-3xl flex items-center justify-center mb-8 shadow-2xl border border-white/20 animate-float">
          <span class="text-6xl font-bold">ع</span>
        </div>
        <h2 class="text-5xl font-bold mb-4">عماد</h2>
        <p class="text-xl opacity-90 mb-12 max-w-md">مدقق المخططات المعمارية بالذكاء الاصطناعي وفق كود البناء السعودي</p>
        
        <div class="grid grid-cols-3 gap-8 mt-4">
          <div class="text-center group">
            <div class="text-4xl font-bold text-accent group-hover:scale-110 transition-transform">+1000</div>
            <div class="text-sm opacity-75 mt-1">مخطط تم تحليله</div>
          </div>
          <div class="text-center group">
            <div class="text-4xl font-bold text-accent group-hover:scale-110 transition-transform">99%</div>
            <div class="text-sm opacity-75 mt-1">دقة الفحص</div>
          </div>
          <div class="text-center group">
            <div class="text-4xl font-bold text-accent group-hover:scale-110 transition-transform">24/7</div>
            <div class="text-sm opacity-75 mt-1">دعم فني</div>
          </div>
        </div>
        
        <!-- Testimonial -->
        <div class="mt-16 bg-white/10 backdrop-blur-md rounded-2xl p-6 max-w-md border border-white/10">
          <p class="text-white/90 text-sm leading-relaxed italic">"أداة رائعة ساعدتني في تدقيق عشرات المخططات بسرعة ودقة عالية. وفرت علينا الكثير من الوقت والجهد."</p>
          <div class="flex items-center gap-3 mt-4">
            <div class="w-10 h-10 bg-accent/30 rounded-full flex items-center justify-center text-accent font-bold">م</div>
            <div class="text-right">
              <p class="font-bold text-sm">م. سعود الخالدي</p>
              <p class="text-xs opacity-70">مكتب هندسي - الرياض</p>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  email: '',
  password: '',
  rememberMe: false
});

const showPassword = ref(false);
const loading = ref(false);
const error = ref('');
const success = ref('');

const handleLogin = async () => {
  loading.value = true;
  error.value = '';
  success.value = '';

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

    // Store token using auth store
    authStore.setAuth(data.access_token, data.user);
    
    success.value = 'تم تسجيل الدخول بنجاح!';

    // Redirect after short delay
    setTimeout(() => {
      // Check for redirect query param
      const redirect = router.currentRoute.value.query.redirect;
      if (redirect) {
        router.push(redirect);
      } else if (data.user.role === 'admin') {
        router.push('/admin');
      } else {
        router.push('/');
      }
    }, 500);

  } catch (err) {
    error.value = err.message || 'حدث خطأ أثناء تسجيل الدخول';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Animations */
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

@keyframes pulse-slow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

.animate-fade-in {
  animation: fade-in 0.6s ease-out forwards;
}

.animate-slide-up {
  animation: slide-up 0.6s ease-out forwards;
}

.animate-float {
  animation: float 4s ease-in-out infinite;
}

.animate-pulse-slow {
  animation: pulse-slow 4s ease-in-out infinite;
}

/* Custom focus states with accent color */
input:focus {
  --tw-ring-color: #D6D693;
}
</style>
