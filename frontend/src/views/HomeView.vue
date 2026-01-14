<template>
  <div class="min-h-screen bg-gray-50 flex flex-col font-sans" dir="rtl">
    
    <!-- Navigation Bar with User Authentication -->
    <nav class="bg-primary px-8 py-4 flex justify-between items-center text-white shadow-lg z-50">
      <div class="flex items-center gap-3">
        <span class="text-3xl bg-white/10 p-2 rounded-lg">🏛️</span>
        <div>
          <h1 class="font-bold text-2xl tracking-wide">عماد</h1>
          <p class="text-[10px] text-accent/90 font-medium tracking-wider">المدقق المعماري الذكي</p>
        </div>
      </div>
      
      <div class="flex gap-6 items-center">
        <button class="text-base font-bold text-white border-b-2 border-accent pb-1">الرئيسية</button>
        <button 
          class="text-base text-gray-200 hover:text-white hover:border-b-2 hover:border-white/50 pb-1 transition" 
          @click="goToHistory"
        >السجل</button>
        
        <!-- User Menu (Authenticated) -->
        <div v-if="authStore.isAuthenticated" class="relative">
          <button 
            @click="showUserMenu = !showUserMenu"
            class="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-xl transition"
          >
            <div class="w-8 h-8 bg-accent rounded-full flex items-center justify-center text-primary font-bold">
              {{ userInitials }}
            </div>
            <span class="text-sm font-medium hidden sm:inline">{{ authStore.currentUser?.full_name }}</span>
            <i class="fas fa-chevron-down text-xs transition-transform" :class="{ 'rotate-180': showUserMenu }"></i>
          </button>
          
          <!-- Dropdown Menu -->
          <transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-1"
          >
            <div 
              v-if="showUserMenu"
              class="absolute left-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50"
            >
              <div class="px-4 py-3 border-b border-gray-100">
                <p class="text-sm font-bold text-gray-800">{{ authStore.currentUser?.full_name }}</p>
                <p class="text-xs text-gray-500">{{ authStore.currentUser?.email }}</p>
              </div>
              <button 
                @click="goToProfile"
                class="w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition"
              >
                <i class="fas fa-user text-gray-400"></i>
                الملف الشخصي
              </button>
              <button 
                @click="goToHistory"
                class="w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition"
              >
                <i class="fas fa-history text-gray-400"></i>
                سجل المشاريع
              </button>
              <div class="border-t border-gray-100 mt-2 pt-2">
                <button 
                  @click="handleLogout"
                  class="w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition"
                >
                  <i class="fas fa-sign-out-alt"></i>
                  تسجيل الخروج
                </button>
              </div>
            </div>
          </transition>
        </div>
        
        <!-- Login/Register (Not Authenticated) -->
        <div v-else class="flex items-center gap-3">
          <router-link 
            to="/login"
            class="text-sm font-medium text-white/90 hover:text-white transition"
          >
            تسجيل الدخول
          </router-link>
          <router-link 
            to="/register"
            class="px-4 py-2 bg-accent text-primary text-sm font-bold rounded-xl hover:bg-accent/90 transition shadow-md"
          >
            إنشاء حساب
          </router-link>
        </div>
      </div>
    </nav>

    <main class="flex-grow flex flex-col items-center justify-center p-6 relative overflow-hidden">
      
      <!-- Ambient Background -->
      <div class="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
      <div class="absolute bottom-0 left-0 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[120px] translate-y-1/3 -translate-x-1/3"></div>

      <div v-if="!isProcessing" class="w-full max-w-5xl z-10 animate-fade-in-up">
        
        <!-- Welcome Message for Authenticated Users -->
        <div v-if="authStore.isAuthenticated" class="text-center mb-6">
          <p class="text-lg text-gray-600">
            مرحباً <span class="font-bold text-primary">{{ authStore.currentUser?.full_name }}</span>! 👋
          </p>
        </div>
        
        <div class="text-center mb-12">
          <span class="px-4 py-1.5 bg-accent/20 text-accent text-sm font-bold rounded-full mb-6 inline-block border border-accent/20">
             ✨ متوافق مع كود البناء السعودي 1101
          </span>
          <h2 class="text-4xl md:text-6xl font-black text-primary mb-6 leading-tight">
            دقق مخططاتك الهندسية <br/>
            <span class="text-transparent bg-clip-text bg-gradient-to-l from-primary to-accent">بالذكاء الاصطناعي</span>
          </h2>
          <p class="text-xl text-secondary max-w-2xl mx-auto leading-relaxed">
            ارفع صورة المخطط، وسيقوم "عماد" بتحليل المساحات واكتشاف المخالفات وتقديم تقرير فوري للمطابقة.
          </p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div class="lg:col-span-2">
            <div 
              class="border-2 border-dashed rounded-[2rem] p-12 flex flex-col items-center justify-center min-h-[450px] transition-all duration-300 relative group cursor-pointer bg-white/80 backdrop-blur-sm shadow-sm hover:shadow-xl hover:border-primary/50 hover:-translate-y-1"
              :class="isDragging ? 'border-accent bg-accent/5 scale-[1.02]' : 'border-gray-200'"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input 
                type="file" 
                ref="fileInput" 
                class="hidden" 
                accept="image/png, image/jpeg, application/pdf" 
                @change="handleFileSelect"
              >
              
              <div v-if="!selectedFile" class="text-center space-y-6 pointer-events-none">
                <div class="w-24 h-24 bg-primary/5 rounded-3xl flex items-center justify-center mx-auto group-hover:bg-primary/10 transition duration-500">
                  <i class="fas fa-cloud-upload-alt text-5xl text-primary group-hover:scale-110 transition duration-300"></i>
                </div>
                <div>
                  <h3 class="text-2xl font-bold text-gray-800 mb-2">اضغط أو اسحب ملف المخطط هنا</h3>
                  <p class="text-base text-gray-400">يدعم JPG, PNG, PDF (الحد الأقصى 10 ميجا)</p>
                </div>

              </div>

              <div v-else class="w-full h-full flex flex-col items-center">
                <div class="relative w-full h-80 mb-6 rounded-2xl overflow-hidden border border-gray-100 shadow-inner bg-gray-50/50">
                  <img :src="previewUrl" class="w-full h-full object-contain p-4">
                  <button @click.stop="resetFile" class="absolute top-4 left-4 bg-red-500 text-white w-10 h-10 rounded-full shadow-lg hover:bg-red-600 transition flex items-center justify-center">
                    <i class="fas fa-times"></i>
                  </button>
                </div>
                <div class="flex items-center gap-3 text-primary font-bold bg-primary/5 px-6 py-3 rounded-xl">
                  <i class="fas fa-file-image text-xl"></i>
                  <span>{{ selectedFile.name }}</span>
                  <span class="text-sm text-gray-400 font-normal ltr">({{ (selectedFile.size / 1024 / 1024).toFixed(1) }} MB)</span>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white/90 backdrop-blur rounded-[2rem] p-8 shadow-xl border border-gray-100 flex flex-col justify-between h-full">


            <button 
              @click="uploadAndAnalyze"
              :disabled="!selectedFile || !authStore.isAuthenticated"
              class="w-full py-5 rounded-2xl font-bold text-xl shadow-lg transition-all duration-300 flex items-center justify-center gap-3 mt-8"
              :class="selectedFile && authStore.isAuthenticated
                ? 'bg-primary text-white hover:bg-[#0c615b] hover:shadow-primary/30 hover:-translate-y-1' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'"
            >
              <template v-if="!authStore.isAuthenticated">
                <i class="fas fa-lock"></i>
                <span>سجّل دخولك أولاً</span>
              </template>
              <template v-else>
                <span>بدء التحليل</span>
                <i class="fas fa-arrow-left"></i>
              </template>
            </button>
            
            <!-- Login prompt for unauthenticated users -->
            <div v-if="!authStore.isAuthenticated" class="mt-4 text-center">
              <p class="text-sm text-gray-500">
                ليس لديك حساب؟ 
                <router-link to="/register" class="text-primary font-bold hover:underline">أنشئ حساباً مجاناً</router-link>
              </p>
            </div>
          </div>

        </div>
      </div>

      <!-- Processing State -->
      <div v-else class="text-center w-full max-w-md animate-fade-in-up">
        <div class="relative w-40 h-40 mx-auto mb-10">
          <div class="absolute inset-0 border-8 border-gray-100 rounded-full"></div>
          <div class="absolute inset-0 border-8 border-primary border-t-transparent rounded-full animate-spin"></div>
          <div class="absolute inset-0 flex items-center justify-center">
             <span class="text-4xl">🏗️</span>
          </div>
        </div>
        <h3 class="text-3xl font-bold text-primary mb-4">جاري تحليل المخطط...</h3>
        <p class="text-secondary text-lg">{{ processingStep }}</p>
      </div>

    </main>

    <footer class="text-center p-6 text-gray-400 text-sm">
      &copy; 2026 عماد - جميع الحقوق محفوظة
    </footer>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAnalysisStore } from '../stores/analysis';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const store = useAnalysisStore();
const authStore = useAuthStore();

const fileInput = ref(null);
const selectedFile = ref(null);
const previewUrl = ref(null);
const isDragging = ref(false);
const isProcessing = ref(false);
const processingStep = ref('جاري رفع الملف...');
const showUserMenu = ref(false);

const settings = ref({
  checkVentilation: true,
  checkDimensions: true
});

// Computed
const userInitials = computed(() => {
  const name = authStore.currentUser?.full_name || '';
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return parts[0][0] + parts[1][0];
  }
  return name.substring(0, 2);
});

// Close menu when clicking outside
const closeMenuOnClickOutside = (e) => {
  if (!e.target.closest('.relative')) {
    showUserMenu.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', closeMenuOnClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', closeMenuOnClickOutside);
});

// Navigation
const goToHistory = () => {
  showUserMenu.value = false;
  if (!authStore.isAuthenticated) {
    router.push('/login');
  } else {
    router.push('/history');
  }
};

const goToProfile = () => {
  showUserMenu.value = false;
  router.push('/profile');
};

const handleLogout = () => {
  showUserMenu.value = false;
  authStore.logout();
  router.push('/');
};

const triggerFileInput = () => fileInput.value.click();

const handleFileSelect = (event) => {
  const file = event.target.files[0];
  if (file) processFile(file);
};

const handleDrop = (event) => {
  isDragging.value = false;
  const file = event.dataTransfer.files[0];
  if (file) processFile(file);
};

const processFile = (file) => {
  if (file.type.startsWith('image/') || file.type === 'application/pdf') {
    selectedFile.value = file;
    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => previewUrl.value = e.target.result;
    reader.readAsDataURL(file);
  } else {
    alert('يرجى رفع ملف صورة (JPG, PNG) أو PDF فقط.');
  }
};

const resetFile = () => {
  selectedFile.value = null;
  previewUrl.value = null;
  fileInput.value.value = null;
};

const loadDemoData = () => {
    // Hack fetch a demo image
    fetch('https://raw.githubusercontent.com/zhixuhao/unet/master/img/30.png')
        .then(res => res.blob())
        .then(blob => {
            const file = new File([blob], "مخطط_فيلا_تجريبي.png", { type: "image/png" });
            processFile(file);
        });
};

const uploadAndAnalyze = async () => {
  if (!selectedFile.value) return;
  
  // Check authentication
  if (!authStore.isAuthenticated) {
    router.push('/login');
    return;
  }

  isProcessing.value = true;
  processingStep.value = "جاري التعرف على الجدران والأبواب (YOLO)...";

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('settings', JSON.stringify(settings.value));

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      headers: authStore.getAuthHeader(),
      body: formData
    });

    if (response.status === 401) {
      // Token expired
      authStore.logout();
      router.push('/login');
      return;
    }

    if (!response.ok) throw new Error('Upload failed');

    const data = await response.json();
    
    // Simulate steps for UX
    setTimeout(() => { processingStep.value = "قياس مساحات الغرف..."; }, 1500);
    setTimeout(() => { processingStep.value = "مطابقة كود البناء السعودي 1101..."; }, 3000);
    
    setTimeout(() => {
        // PERISTENCE: Save the new analysis to the store immediately
        store.setAnalysis({
            id: data.task_id,
            imageUrl: data.image_url,
            rooms: [], // Empty initially, will be filled by polling or real analysis later
            status: 'Processing',
            date: new Date().toISOString().split('T')[0]
        });
        
        router.push({ name: 'dashboard', params: { id: data.task_id } });
    }, 4500);

  } catch (error) {
    console.error(error);
    alert('حدث خطأ أثناء الرفع. حاول مرة أخرى.');
    isProcessing.value = false;
  }
};
</script>

<style scoped>
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 0.6s ease-out forwards;
}
</style>