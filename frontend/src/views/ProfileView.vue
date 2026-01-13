<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4" dir="rtl">
    
    <div class="max-w-2xl mx-auto">
      
      <!-- Back Button -->
      <button 
        @click="$router.push('/')" 
        class="mb-6 flex items-center gap-2 text-gray-500 hover:text-primary transition"
      >
        <i class="fas fa-arrow-right"></i>
        <span>العودة للرئيسية</span>
      </button>

      <!-- Profile Card -->
      <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
        
        <!-- Header with gradient -->
        <div class="bg-gradient-to-l from-primary via-primary to-secondary h-32 relative">
          <div class="absolute inset-0 opacity-20">
            <div class="absolute top-4 left-10 w-32 h-32 bg-white rounded-full blur-3xl"></div>
            <div class="absolute bottom-0 right-20 w-48 h-24 bg-accent rounded-full blur-3xl"></div>
          </div>
        </div>

        <!-- Avatar & Info -->
        <div class="px-8 pb-8 relative">
          
          <!-- Avatar -->
          <div class="absolute -top-12 right-8">
            <div class="w-24 h-24 bg-accent rounded-2xl shadow-lg flex items-center justify-center text-primary text-4xl font-bold border-4 border-white">
              {{ userInitial }}
            </div>
          </div>

          <!-- User Info -->
          <div class="pt-16">
            <div class="flex items-start justify-between">
              <div>
                <h1 class="text-2xl font-bold text-gray-800">{{ user?.full_name || 'المستخدم' }}</h1>
                <p class="text-gray-500 mt-1">{{ user?.email }}</p>
              </div>
              
              <!-- Role Badge -->
              <span 
                :class="[
                  'px-4 py-2 rounded-xl text-sm font-bold',
                  user?.role === 'admin' ? 'bg-red-100 text-red-700' :
                  user?.role === 'office' ? 'bg-blue-100 text-blue-700' :
                  'bg-green-100 text-green-700'
                ]"
              >
                {{ getRoleLabel(user?.role) }}
              </span>
            </div>

            <!-- Joined Date -->
            <div class="flex items-center gap-2 mt-4 text-sm text-gray-400">
              <i class="fas fa-calendar-alt"></i>
              <span>عضو منذ {{ formatDate(user?.created_at) }}</span>
            </div>
          </div>

          <!-- Divider -->
          <hr class="my-6 border-gray-100">

          <!-- Stats Grid -->
          <div class="grid grid-cols-2 gap-4">
            
            <!-- Projects Count -->
            <div class="bg-gray-50 rounded-2xl p-5 text-center">
              <div class="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary mx-auto mb-3">
                <i class="fas fa-folder-open text-xl"></i>
              </div>
              <div class="text-3xl font-bold text-gray-800">{{ user?.plans_count || 0 }}</div>
              <div class="text-sm text-gray-500 mt-1">مخططات محللة</div>
            </div>

            <!-- Account Status -->
            <div class="bg-gray-50 rounded-2xl p-5 text-center">
              <div class="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3"
                   :class="user?.is_active ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'">
                <i :class="user?.is_active ? 'fas fa-check-circle' : 'fas fa-ban'" class="text-xl"></i>
              </div>
              <div class="text-lg font-bold" :class="user?.is_active ? 'text-green-600' : 'text-red-600'">
                {{ user?.is_active ? 'نشط' : 'محظور' }}
              </div>
              <div class="text-sm text-gray-500 mt-1">حالة الحساب</div>
            </div>

          </div>

          <!-- Divider -->
          <hr class="my-6 border-gray-100">

          <!-- Account Type -->
          <div class="bg-gray-50 rounded-2xl p-5 flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 bg-accent/30 rounded-xl flex items-center justify-center text-primary">
                <i :class="user?.account_type === 'office' ? 'fas fa-building' : 'fas fa-user'" class="text-xl"></i>
              </div>
              <div>
                <div class="font-bold text-gray-800">نوع الحساب</div>
                <div class="text-sm text-gray-500">{{ user?.account_type === 'office' ? 'مكتب هندسي' : 'شخصي' }}</div>
              </div>
            </div>
            <i class="fas fa-chevron-left text-gray-300"></i>
          </div>

          <!-- Divider -->
          <hr class="my-6 border-gray-100">

          <!-- Action Buttons -->
          <div class="space-y-3">
            
            <!-- Edit Profile Button -->
            <button 
              @click="editProfile"
              class="w-full py-4 bg-accent text-primary font-bold rounded-xl hover:bg-accent/80 transition flex items-center justify-center gap-2 shadow-sm"
            >
              <i class="fas fa-pen"></i>
              <span>تعديل البيانات</span>
            </button>

            <!-- Logout Button -->
            <button 
              @click="handleLogout"
              class="w-full py-4 bg-red-50 text-red-600 font-bold rounded-xl hover:bg-red-100 transition flex items-center justify-center gap-2 border border-red-100"
            >
              <i class="fas fa-sign-out-alt"></i>
              <span>تسجيل الخروج</span>
            </button>

          </div>

        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-gray-400 text-sm mt-8">
        © 2026 عماد - مدقق المخططات بالذكاء الاصطناعي
      </p>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const user = computed(() => authStore.currentUser);

const userInitial = computed(() => {
  const name = user.value?.full_name || 'م';
  return name.charAt(0);
});

const getRoleLabel = (role) => {
  const labels = {
    admin: 'مدير النظام',
    office: 'مكتب هندسي',
    customer: 'عميل',
    personal: 'شخصي'
  };
  return labels[role] || 'عميل';
};

const formatDate = (dateString) => {
  if (!dateString) return '---';
  const date = new Date(dateString);
  return date.toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

const editProfile = () => {
  // TODO: Implement edit profile modal/page
  alert('قريباً - تعديل البيانات');
};

const handleLogout = () => {
  if (confirm('هل أنت متأكد من تسجيل الخروج؟')) {
    authStore.logout();
    router.push('/');  // CHANGED: Go to home instead of login
  }
};

onMounted(async () => {
  // Fetch fresh user data (no redirect for debugging)
  if (authStore.isAuthenticated) {
    await authStore.fetchCurrentUser();
  }
  // DISABLED: Auth redirect for debugging
  // else { router.push('/login'); }
});
</script>
