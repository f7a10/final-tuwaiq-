<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100" dir="rtl">
    
    <!-- Header -->
    <header class="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          
          <!-- Title & Back -->
          <div class="flex items-center gap-4">
            <button 
              @click="$router.push('/')" 
              class="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-primary hover:bg-primary/5 rounded-xl transition-all duration-200"
            >
              <i class="fas fa-arrow-right text-lg"></i>
            </button>
            <div>
              <h1 class="text-2xl font-bold text-gray-800">سجل المشاريع</h1>
              <p class="text-sm text-gray-500">جميع المخططات التي قمت بتحليلها</p>
            </div>
          </div>

          <!-- User Info & New Analysis Button -->
          <div class="flex items-center gap-4">
            <div v-if="authStore.isAuthenticated" class="hidden sm:flex items-center gap-2 text-sm text-gray-500">
              <i class="fas fa-user-circle text-primary"></i>
              <span>{{ authStore.currentUser?.full_name }}</span>
            </div>
            <router-link 
              to="/"
              class="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-l from-primary to-teal-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-primary/25 hover:-translate-y-0.5 transition-all duration-300"
            >
              <i class="fas fa-plus"></i>
              <span>تحليل جديد</span>
            </router-link>
          </div>

        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      <!-- Search & Filters Bar -->
      <div class="bg-white/80 backdrop-blur-md rounded-2xl shadow-sm border border-gray-100 p-4 mb-8">
        <div class="flex flex-col md:flex-row gap-4">
          
          <!-- Search Input -->
          <div class="flex-1 relative group">
            <i class="fas fa-search absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-primary"></i>
            <input 
              v-model="searchQuery"
              type="text"
              placeholder="ابحث في المشاريع..."
              class="w-full pr-12 pl-4 py-3 bg-gray-50/50 border border-gray-200 rounded-xl focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 focus:bg-white transition-all duration-200"
            >
          </div>

          <!-- Filter Chips -->
          <div class="flex items-center gap-2 flex-wrap">
            <button 
              v-for="filter in filters" 
              :key="filter.value"
              @click="activeFilter = filter.value"
              :class="[
                'px-4 py-2.5 rounded-xl text-sm font-bold transition-all duration-200',
                activeFilter === filter.value 
                  ? 'bg-gradient-to-l from-primary to-teal-600 text-white shadow-md shadow-primary/20' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              ]"
            >
              {{ filter.label }}
              <span v-if="filter.count !== undefined" class="mr-1 opacity-75">({{ filter.count }})</span>
            </button>
          </div>

        </div>
      </div>

      <!-- Stats Summary -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white/80 backdrop-blur-md rounded-xl p-4 border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <i class="fas fa-layer-group"></i>
            </div>
            <div>
              <div class="text-2xl font-bold text-gray-800">{{ totalProjects }}</div>
              <div class="text-sm text-gray-500">إجمالي المشاريع</div>
            </div>
          </div>
        </div>
        <div class="bg-white/80 backdrop-blur-md rounded-xl p-4 border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center text-green-600 group-hover:scale-110 transition-transform">
              <i class="fas fa-check-circle"></i>
            </div>
            <div>
              <div class="text-2xl font-bold text-green-600">{{ compliantCount }}</div>
              <div class="text-sm text-gray-500">مطابقة للكود</div>
            </div>
          </div>
        </div>
        <div class="bg-white/80 backdrop-blur-md rounded-xl p-4 border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center text-red-600 group-hover:scale-110 transition-transform">
              <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div>
              <div class="text-2xl font-bold text-red-600">{{ violationsCount }}</div>
              <div class="text-sm text-gray-500">بها مخالفات</div>
            </div>
          </div>
        </div>
        <div class="bg-white/80 backdrop-blur-md rounded-xl p-4 border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center text-yellow-600 group-hover:scale-110 transition-transform">
              <i class="fas fa-clock"></i>
            </div>
            <div>
              <div class="text-2xl font-bold text-yellow-600">{{ processingCount }}</div>
              <div class="text-sm text-gray-500">قيد المعالجة</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State: Skeleton -->
      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm animate-pulse">
          <div class="aspect-video bg-gray-200"></div>
          <div class="p-4 space-y-3">
            <div class="h-5 bg-gray-200 rounded w-3/4"></div>
            <div class="h-4 bg-gray-200 rounded w-1/2"></div>
            <div class="flex justify-between">
              <div class="h-6 bg-gray-200 rounded-full w-20"></div>
              <div class="h-6 bg-gray-200 rounded w-16"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Projects Grid -->
      <div v-else-if="filteredProjects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        <div 
          v-for="(project, index) in filteredProjects" 
          :key="project.id"
          @click="openProject(project)"
          class="group bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm cursor-pointer transition-all duration-300 hover:-translate-y-2 hover:shadow-xl animate-fade-in-up"
          :style="{ animationDelay: `${index * 50}ms` }"
        >
          <!-- Thumbnail -->
          <div class="aspect-video bg-gradient-to-br from-gray-100 to-gray-50 relative overflow-hidden">
            <img 
              :src="project.analyzed_image_url || project.original_image_url || placeholderImage"
              :alt="project.title"
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
              @error="handleImageError"
            >
            
            <!-- Overlay on Hover -->
            <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-center pb-4">
              <span class="text-white text-sm font-bold px-4 py-2 bg-primary rounded-full">
                <i class="fas fa-eye ml-2"></i>
                عرض التفاصيل
              </span>
            </div>
            
            <!-- Status Badge Overlay -->
            <div class="absolute top-3 left-3">
              <span 
                v-if="project.status === 'processing'"
                class="px-3 py-1.5 bg-yellow-500/90 backdrop-blur-sm text-white text-xs font-bold rounded-full flex items-center gap-1.5 shadow-lg"
              >
                <i class="fas fa-spinner animate-spin"></i>
                جاري التحليل
              </span>
              <span 
                v-else-if="project.compliance_status === 'compliant'"
                class="px-3 py-1.5 bg-green-500/90 backdrop-blur-sm text-white text-xs font-bold rounded-full shadow-lg"
              >
                <i class="fas fa-check ml-1"></i>
                مطابق
              </span>
              <span 
                v-else
                class="px-3 py-1.5 bg-red-500/90 backdrop-blur-sm text-white text-xs font-bold rounded-full shadow-lg"
              >
                <i class="fas fa-exclamation-triangle ml-1"></i>
                مخالفات
              </span>
            </div>

            <!-- Score Badge -->
            <div 
              v-if="project.compliance_score !== null && project.status === 'completed'" 
              class="absolute bottom-3 right-3 w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-xl border-2 border-white transition-transform group-hover:scale-110"
              :class="project.compliance_score >= 80 ? 'bg-gradient-to-br from-green-500 to-green-600' : project.compliance_score >= 50 ? 'bg-gradient-to-br from-yellow-500 to-yellow-600' : 'bg-gradient-to-br from-red-500 to-red-600'"
            >
              {{ Math.round(project.compliance_score) }}%
            </div>
          </div>

          <!-- Content -->
          <div class="p-4">
            <h3 class="font-bold text-gray-800 text-lg mb-1 truncate group-hover:text-primary transition-colors">
              {{ project.title }}
            </h3>
            <p class="text-sm text-gray-500 flex items-center gap-2 mb-3">
              <i class="fas fa-calendar-alt"></i>
              {{ formatDate(project.created_at) }}
            </p>

            <!-- Stats Row -->
            <div class="flex items-center justify-between text-sm pt-3 border-t border-gray-100">
              <div class="flex items-center gap-4">
                <span class="text-gray-500 flex items-center gap-1">
                  <i class="fas fa-door-open text-primary/60"></i>
                  {{ project.rooms_count }} غرف
                </span>
                <span v-if="project.violations_count > 0" class="text-red-500 flex items-center gap-1">
                  <i class="fas fa-times-circle"></i>
                  {{ project.violations_count }} مخالفات
                </span>
              </div>
              <i class="fas fa-chevron-left text-gray-300 group-hover:text-primary group-hover:translate-x-1 transition-all"></i>
            </div>
          </div>
        </div>

      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-20 animate-fade-in">
        <div class="inline-flex items-center justify-center w-32 h-32 bg-gradient-to-br from-gray-100 to-gray-50 rounded-full mb-6 shadow-inner">
          <svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
        </div>
        <h3 class="text-xl font-bold text-gray-700 mb-2">لا توجد مشاريع حتى الآن</h3>
        <p class="text-gray-500 mb-8 max-w-md mx-auto">ابدأ بتحليل أول مخطط معماري لك وسيظهر هنا في سجلك الشخصي</p>
        <router-link 
          to="/"
          class="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-l from-primary to-teal-600 text-white font-bold rounded-xl hover:shadow-xl hover:shadow-primary/25 hover:-translate-y-1 transition-all duration-300"
        >
          <i class="fas fa-upload"></i>
          <span>رفع مخطط جديد</span>
        </router-link>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

// State
const projects = ref([]);
const loading = ref(true);
const searchQuery = ref('');
const activeFilter = ref('all');

const placeholderImage = 'https://via.placeholder.com/400x300?text=Floor+Plan';

// Filters config
const filters = computed(() => [
  { value: 'all', label: 'الكل', count: totalProjects.value },
  { value: 'compliant', label: 'مطابق', count: compliantCount.value },
  { value: 'non_compliant', label: 'غير مطابق', count: violationsCount.value }
]);

// Computed stats
const totalProjects = computed(() => projects.value.length);

const compliantCount = computed(() => 
  projects.value.filter(p => p.compliance_status === 'compliant').length
);

const violationsCount = computed(() => 
  projects.value.filter(p => p.compliance_status === 'non_compliant').length
);

const processingCount = computed(() => 
  projects.value.filter(p => p.status === 'processing').length
);

// Filtered projects
const filteredProjects = computed(() => {
  let result = [...projects.value];
  
  // Apply search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(p => 
      p.title.toLowerCase().includes(query)
    );
  }
  
  // Apply filter
  if (activeFilter.value === 'compliant') {
    result = result.filter(p => p.compliance_status === 'compliant');
  } else if (activeFilter.value === 'non_compliant') {
    result = result.filter(p => p.compliance_status === 'non_compliant');
  }
  
  return result;
});

// Methods
const fetchProjects = async () => {
  loading.value = true;
  
  try {
    const response = await fetch('/api/projects/me', {
      headers: authStore.getAuthHeader()
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        authStore.logout();
        router.push('/login');
        return;
      }
      throw new Error('Failed to fetch projects');
    }
    
    const data = await response.json();
    projects.value = data.projects || [];
    
  } catch (error) {
    console.error('Error fetching projects:', error);
  } finally {
    loading.value = false;
  }
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

const openProject = (project) => {
  router.push({ name: 'dashboard', params: { id: project.task_id } });
};

const handleImageError = (e) => {
  e.target.src = placeholderImage;
};

// Debounced search
let searchTimeout;
watch(searchQuery, () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    // Could call API with search param for server-side filtering
  }, 300);
});

// Lifecycle
onMounted(() => {
  // Redirect to login if not authenticated
  if (!authStore.isAuthenticated) {
    router.push('/login');
    return;
  }
  fetchProjects();
});
</script>

<style scoped>
@keyframes fade-in-up {
  from { 
    opacity: 0; 
    transform: translateY(20px); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in-up {
  animation: fade-in-up 0.5s ease-out forwards;
  opacity: 0;
}

.animate-fade-in {
  animation: fade-in 0.5s ease-out forwards;
}

/* Smooth card animations */
.group {
  will-change: transform, box-shadow;
}
</style>
