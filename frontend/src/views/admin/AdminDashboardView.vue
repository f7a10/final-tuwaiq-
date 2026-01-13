<template>
  <div class="min-h-screen flex bg-gray-100" dir="rtl">
    
    <!-- Sidebar -->
    <aside class="w-64 bg-primary text-white flex flex-col shadow-xl">
      
      <!-- Logo -->
      <div class="p-6 border-b border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
            <span class="text-xl font-bold">ع</span>
          </div>
          <div>
            <h1 class="font-bold text-lg">عماد</h1>
            <p class="text-xs opacity-75">لوحة الإدارة</p>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1">
        <button 
          v-for="item in navItems" 
          :key="item.id"
          @click="activeSection = item.id"
          :class="[
            'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-right',
            activeSection === item.id 
              ? 'bg-white/20 text-white' 
              : 'text-white/70 hover:bg-white/10 hover:text-white'
          ]"
        >
          <i :class="item.icon" class="w-5 text-center"></i>
          <span class="font-medium">{{ item.label }}</span>
        </button>
      </nav>

      <!-- User Info -->
      <div class="p-4 border-t border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-accent rounded-full flex items-center justify-center text-primary font-bold">
            م
          </div>
          <div class="flex-1">
            <div class="font-bold text-sm">مدير النظام</div>
            <div class="text-xs opacity-75">admin@emad.sa</div>
          </div>
          <button @click="logout" class="text-white/50 hover:text-white transition">
            <i class="fas fa-sign-out-alt"></i>
          </button>
        </div>
      </div>

    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-auto">
      
      <!-- Header -->
      <header class="bg-white shadow-sm px-8 py-5 flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">{{ currentSection.label }}</h2>
          <p class="text-gray-500 text-sm">إدارة {{ currentSection.label }} في النظام</p>
        </div>
        <div class="flex items-center gap-4">
          <button class="p-2 text-gray-400 hover:text-primary transition relative">
            <i class="fas fa-bell text-xl"></i>
            <span class="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button @click="refreshData" class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition text-gray-700">
            <i class="fas fa-sync-alt ml-2"></i>
            تحديث
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <div class="p-8">

        <!-- Users Section -->
        <div v-if="activeSection === 'users'">
          
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-gray-500 text-sm">إجمالي المستخدمين</p>
                  <p class="text-3xl font-bold text-gray-800 mt-1">{{ users.length }}</p>
                </div>
                <div class="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
                  <i class="fas fa-users text-xl"></i>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-gray-500 text-sm">المستخدمون النشطون</p>
                  <p class="text-3xl font-bold text-green-600 mt-1">{{ activeUsers }}</p>
                </div>
                <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-green-600">
                  <i class="fas fa-user-check text-xl"></i>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-gray-500 text-sm">المكاتب الهندسية</p>
                  <p class="text-3xl font-bold text-blue-600 mt-1">{{ officeUsers }}</p>
                </div>
                <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600">
                  <i class="fas fa-building text-xl"></i>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-gray-500 text-sm">المخططات المحللة</p>
                  <p class="text-3xl font-bold text-accent mt-1">{{ totalPlans }}</p>
                </div>
                <div class="w-12 h-12 bg-accent/20 rounded-xl flex items-center justify-center text-primary">
                  <i class="fas fa-file-alt text-xl"></i>
                </div>
              </div>
            </div>
          </div>

          <!-- Users Table -->
          <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            
            <!-- Table Header -->
            <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 class="font-bold text-gray-800">قائمة المستخدمين</h3>
              <div class="flex items-center gap-3">
                <div class="relative">
                  <i class="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                  <input 
                    v-model="searchQuery"
                    type="text" 
                    placeholder="بحث..."
                    class="pr-10 pl-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-primary"
                  >
                </div>
              </div>
            </div>

            <!-- Table -->
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">ID</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">الاسم</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">البريد الإلكتروني</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">الدور</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">المخططات</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">الحالة</th>
                    <th class="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">الإجراءات</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="user in filteredUsers" :key="user.id" class="hover:bg-gray-50 transition">
                    <td class="px-6 py-4 text-sm text-gray-500 font-mono">#{{ user.id }}</td>
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold">
                          {{ user.name.charAt(0) }}
                        </div>
                        <span class="font-medium text-gray-800">{{ user.name }}</span>
                      </div>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-600">{{ user.email }}</td>
                    <td class="px-6 py-4">
                      <span 
                        :class="[
                          'px-3 py-1 rounded-full text-xs font-bold',
                          user.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                          user.role === 'office' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        ]"
                      >
                        {{ getRoleLabel(user.role) }}
                      </span>
                    </td>
                    <td class="px-6 py-4 text-sm font-bold text-gray-800">{{ user.plansCount }}</td>
                    <td class="px-6 py-4">
                      <span 
                        :class="[
                          'px-3 py-1 rounded-full text-xs font-bold',
                          user.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        ]"
                      >
                        {{ user.status === 'active' ? 'نشط' : 'محظور' }}
                      </span>
                    </td>
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-2">
                        <button 
                          @click="viewUser(user)"
                          class="p-2 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-lg transition"
                          title="عرض الملف"
                        >
                          <i class="fas fa-eye"></i>
                        </button>
                        <button 
                          @click="deleteUser(user)"
                          class="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                          title="حذف المستخدم"
                        >
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Empty State -->
            <div v-if="filteredUsers.length === 0" class="text-center py-12">
              <i class="fas fa-users text-4xl text-gray-300 mb-4"></i>
              <p class="text-gray-500">لا يوجد مستخدمين</p>
            </div>

          </div>
        </div>

        <!-- Projects Section -->
        <div v-else-if="activeSection === 'projects'" class="text-center py-20">
          <i class="fas fa-folder-open text-6xl text-gray-300 mb-4"></i>
          <h3 class="text-xl font-bold text-gray-600">قسم المشاريع</h3>
          <p class="text-gray-500">قريباً...</p>
        </div>

        <!-- Settings Section -->
        <div v-else-if="activeSection === 'settings'" class="text-center py-20">
          <i class="fas fa-cog text-6xl text-gray-300 mb-4"></i>
          <h3 class="text-xl font-bold text-gray-600">الإعدادات</h3>
          <p class="text-gray-500">قريباً...</p>
        </div>

      </div>
    </main>

    <!-- User Detail Modal -->
    <div v-if="selectedUser" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="selectedUser = null">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div class="text-center mb-6">
          <div class="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center text-primary text-3xl font-bold mx-auto mb-4">
            {{ selectedUser.name.charAt(0) }}
          </div>
          <h3 class="text-xl font-bold text-gray-800">{{ selectedUser.name }}</h3>
          <p class="text-gray-500">{{ selectedUser.email }}</p>
        </div>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between py-2 border-b">
            <span class="text-gray-500">الدور</span>
            <span class="font-bold">{{ getRoleLabel(selectedUser.role) }}</span>
          </div>
          <div class="flex justify-between py-2 border-b">
            <span class="text-gray-500">المخططات المحللة</span>
            <span class="font-bold">{{ selectedUser.plansCount }}</span>
          </div>
          <div class="flex justify-between py-2 border-b">
            <span class="text-gray-500">الحالة</span>
            <span :class="selectedUser.status === 'active' ? 'text-green-600' : 'text-red-600'" class="font-bold">
              {{ selectedUser.status === 'active' ? 'نشط' : 'محظور' }}
            </span>
          </div>
        </div>
        <button @click="selectedUser = null" class="w-full mt-6 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-bold text-gray-700 transition">
          إغلاق
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const activeSection = ref('users');
const searchQuery = ref('');
const selectedUser = ref(null);

const navItems = [
  { id: 'users', label: 'المستخدمين', icon: 'fas fa-users' },
  { id: 'projects', label: 'المشاريع', icon: 'fas fa-folder' },
  { id: 'settings', label: 'الإعدادات', icon: 'fas fa-cog' }
];

const currentSection = computed(() => navItems.find(i => i.id === activeSection.value));

// Mock users data
const users = ref([
  { id: 1, name: 'أحمد محمد', email: 'ahmed@example.com', role: 'admin', plansCount: 45, status: 'active' },
  { id: 2, name: 'سارة الأحمد', email: 'sara@example.com', role: 'office', plansCount: 128, status: 'active' },
  { id: 3, name: 'خالد العتيبي', email: 'khaled@example.com', role: 'personal', plansCount: 12, status: 'active' },
  { id: 4, name: 'مريم الشمري', email: 'mariam@example.com', role: 'office', plansCount: 67, status: 'active' },
  { id: 5, name: 'فهد القحطاني', email: 'fahad@example.com', role: 'personal', plansCount: 5, status: 'banned' },
]);

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value;
  const query = searchQuery.value.toLowerCase();
  return users.value.filter(u => 
    u.name.toLowerCase().includes(query) || 
    u.email.toLowerCase().includes(query)
  );
});

const activeUsers = computed(() => users.value.filter(u => u.status === 'active').length);
const officeUsers = computed(() => users.value.filter(u => u.role === 'office').length);
const totalPlans = computed(() => users.value.reduce((sum, u) => sum + u.plansCount, 0));

const getRoleLabel = (role) => {
  const labels = {
    admin: 'مدير',
    office: 'مكتب هندسي',
    personal: 'شخصي'
  };
  return labels[role] || role;
};

const viewUser = (user) => {
  selectedUser.value = user;
};

const deleteUser = (user) => {
  if (confirm(`هل أنت متأكد من حذف "${user.name}"?`)) {
    users.value = users.value.filter(u => u.id !== user.id);
  }
};

const refreshData = () => {
  // Refresh logic
  console.log('Refreshing data...');
};

const logout = () => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user');
  router.push('/login');
};
</script>
