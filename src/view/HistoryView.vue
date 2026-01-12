<template>
  <div class="min-h-screen bg-gray-50" dir="rtl">
    
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          
          <!-- Title & Back -->
          <div class="flex items-center gap-4">
            <button @click="$router.push('/')" class="text-gray-400 hover:text-primary transition">
              <i class="fas fa-arrow-right text-lg"></i>
            </button>
            <div>
              <h1 class="text-2xl font-bold text-gray-800">سجل المشاريع</h1>
              <p class="text-sm text-gray-500">جميع المخططات التي قمت بتحليلها</p>
            </div>
          </div>

          <!-- New Analysis Button -->
          <router-link 
            to="/"
            class="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-primary font-bold rounded-xl hover:bg-accent/80 transition shadow-sm"
          >
            <i class="fas fa-plus"></i>
            <span>تحليل جديد</span>
          </router-link>

        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      <!-- Search & Filters Bar -->
      <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 mb-8">
        <div class="flex flex-col md:flex-row gap-4">
          
          <!-- Search Input -->
          <div class="flex-1 relative">
            <i class="fas fa-search absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input 
              v-model="searchQuery"
              type="text"
              placeholder="ابحث في المشاريع..."
              class="w-full pr-12 pl-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
            >
          </div>

          <!-- Filter Chips -->
          <div class="flex items-center gap-2 flex-wrap">
            <button 
              v-for="filter in filters" 
              :key="filter.value"
              @click="activeFilter = filter.value"
              :class="[
                'px-4 py-2 rounded-xl text-sm font-bold transition',
                activeFilter === filter.value 
                  ? 'bg-primary text-white shadow-md' 
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
        <div class="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div class="text-2xl font-bold text-gray-800">{{ totalProjects }}</div>
          <div class="text-sm text-gray-500">إجمالي المشاريع</div>
        </div>
        <div class="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div class="text-2xl font-bold text-green-600">{{ compliantCount }}</div>
          <div class="text-sm text-gray-500">مطابقة للكود</div>
        </div>
        <div class="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div class="text-2xl font-bold text-red-600">{{ violationsCount }}</div>
          <div class="text-sm text-gray-500">بها مخالفات</div>
        </div>
        <div class="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div class="text-2xl font-bold text-primary">{{ processingCount }}</div>
          <div class="text-sm text-gray-500">قيد المعالجة</div>
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
          v-for="project in filteredProjects" 
          :key="project.id"
          @click="openProject(project)"
          class="group bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
        >
          <!-- Thumbnail -->
          <div class="aspect-video bg-gray-100 relative overflow-hidden">
            <img 
              :src="project.analyzed_image_url || project.original_image_url || placeholderImage"
              :alt="project.title"
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              @error="handleImageError"
            >
            
            <!-- Status Badge Overlay -->
            <div class="absolute top-3 left-3">
              <span 
                v-if="project.status === 'processing'"
                class="px-3 py-1 bg-yellow-500 text-white text-xs font-bold rounded-full flex items-center gap-1"
              >
                <i class="fas fa-spinner animate-spin"></i>
                جاري التحليل
              </span>
              <span 
                v-else-if="project.compliance_status === 'compliant'"
                class="px-3 py-1 bg-green-500 text-white text-xs font-bold rounded-full"
              >
                <i class="fas fa-check ml-1"></i>
                مطابق
              </span>
              <span 
                v-else
                class="px-3 py-1 bg-red-500 text-white text-xs font-bold rounded-full"
              >
                <i class="fas fa-exclamation-triangle ml-1"></i>
                مخالفات
              </span>
            </div>

            <!-- Score Badge -->
            <div 
              v-if="project.compliance_score !== null && project.status === 'completed'" 
              class="absolute bottom-3 right-3 w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg"
              :class="project.compliance_score >= 80 ? 'bg-green-500' : project.compliance_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'"
            >
              {{ Math.round(project.compliance_score) }}%
            </div>
          </div>

          <!-- Content -->
          <div class="p-4">
            <h3 class="font-bold text-gray-800 text-lg mb-1 truncate group-hover:text-primary transition">
              {{ project.title }}
            </h3>
            <p class="text-sm text-gray-500 flex items-center gap-2 mb-3">
              <i class="fas fa-calendar-alt"></i>
              {{ formatDate(project.created_at) }}
            </p>

            <!-- Stats Row -->
            <div class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-4">
                <span class="text-gray-500">
                  <i class="fas fa-door-open ml-1"></i>
                  {{ project.rooms_count }} غرف
                </span>
                <span v-if="project.violations_count > 0" class="text-red-500">
                  <i class="fas fa-times-circle ml-1"></i>
                  {{ project.violations_count }} مخالفات
                </span>
              </div>
              <i class="fas fa-chevron-left text-gray-300 group-hover:text-primary transition"></i>
            </div>
          </div>
        </div>

      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-20">
        <div class="inline-flex items-center justify-center w-32 h-32 bg-gray-100 rounded-full mb-6">
          <svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
        </div>
        <h3 class="text-xl font-bold text-gray-700 mb-2">لا توجد مشاريع حتى الآن</h3>
        <p class="text-gray-500 mb-6">ابدأ بتحليل أول مخطط معماري لك</p>
        <router-link 
          to="/"
          class="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white font-bold rounded-xl hover:bg-primary/90 transition shadow-lg shadow-primary/25"
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
      // DISABLED: Auth redirect for debugging
      // if (response.status === 401) {
      //   router.push('/login');
      //   return;
      // }
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
  // DISABLED: Auth check for debugging - always fetch
  // if (!authStore.isAuthenticated) {
  //   router.push('/login');
  //   return;
  // }
  fetchProjects();
});
</script>

<style scoped>
/* Smooth card animations */
.group {
  will-change: transform, box-shadow;
}
</style>
