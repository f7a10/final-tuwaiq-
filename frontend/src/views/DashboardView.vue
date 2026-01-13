<template>
  <div class="h-screen flex flex-col bg-gray-50 overflow-hidden font-sans" dir="rtl">
    
    <header class="h-16 bg-white border-b border-gray-200 flex justify-between items-center px-6 shadow-sm z-20">
      <div class="flex items-center gap-4">
        <button @click="$router.push('/')" class="text-gray-400 hover:text-primary transition">
          <i class="fas fa-arrow-right text-lg"></i>
        </button>
        <div>
          <h1 class="font-bold text-lg text-primary">تحليل المخطط #{{ taskId.slice(0,8) }}</h1>
          <div class="flex items-center gap-2 text-xs">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            <span class="text-gray-500">فحص كود البناء السعودي (SBC 1101)</span>
          </div>
        </div>
      </div>
      
      <div class="flex gap-3">
        <button 
          @click="downloadImage"
          class="px-4 py-2 text-sm font-bold text-primary bg-secondary/10 rounded-lg hover:bg-secondary/20 transition flex items-center gap-2"
        >
          <i class="fas fa-download"></i>
          <span>تحميل المخطط</span>
        </button>
        <button class="px-4 py-2 text-sm font-bold text-primary bg-secondary/10 rounded-lg hover:bg-secondary/20 transition flex items-center gap-2">
          <i class="fas fa-file-pdf"></i>
          <span>تصدير التقرير</span>
        </button>
      </div>
    </header>

    <div class="flex-1 flex overflow-hidden">
      
      <!-- Right Sidebar (Compliance & Chat) -->
      <div class="w-[450px] bg-white border-l border-gray-200 flex flex-col shadow-xl z-10 order-first">
        
        <div class="flex border-b border-gray-200">
          <button 
            @click="activeTab = 'report'"
            class="flex-1 py-4 text-sm font-bold border-b-2 transition-colors flex items-center justify-center gap-2"
            :class="activeTab === 'report' ? 'border-primary text-primary' : 'border-transparent text-gray-400 hover:text-gray-600'"
          >
            <i class="fas fa-clipboard-list"></i> تقرير المطابقة
          </button>
          <button 
            @click="activeTab = 'chat'"
            class="flex-1 py-4 text-sm font-bold border-b-2 transition-colors flex items-center justify-center gap-2"
            :class="activeTab === 'chat' ? 'border-primary text-primary' : 'border-transparent text-gray-400 hover:text-gray-600'"
          >
            <i class="fas fa-robot"></i> المستشار الذكي
          </button>
        </div>

        <!-- Compliance Report Tab -->
        <div v-if="activeTab === 'report'" class="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/50">
          
          <div class="bg-primary text-white p-5 rounded-2xl shadow-lg mb-4 relative overflow-hidden">
            <div class="absolute top-0 left-0 w-32 h-32 bg-white/10 rounded-full blur-2xl -translate-x-10 -translate-y-10"></div>
            <div class="relative z-10">
                <div class="flex justify-between items-center mb-2">
                <h3 class="font-bold text-lg">نسبة الامتثال</h3>
                <span class="text-3xl font-bold text-accent">{{ complianceScore }}%</span>
                </div>
                <div class="h-2 bg-black/20 rounded-full overflow-hidden mb-2">
                <div class="h-full bg-accent transition-all duration-1000 ease-out" :style="{ width: complianceScore + '%' }"></div>
                </div>
                <p class="text-xs opacity-90">تم العثور على {{ violationsCount }} مخالفات وفقاً لكود البناء السعودي.</p>
            </div>
          </div>

          <div 
            v-for="room in analysisData.rooms" 
            :key="room.id"
            :id="'card-' + room.id"
            class="bg-white rounded-xl border-r-4 p-4 shadow-sm transition-all duration-200 cursor-pointer hover:shadow-md"
            :class="[
              activeRoomId === room.id ? 'ring-2 ring-primary scale-[1.02]' : '',
              room.isCompliant ? 'border-green-500' : 'border-red-500'
            ]"
            @mouseenter="activeRoomId = room.id"
          >
            <div class="flex justify-between items-start mb-2">
              <div>
                <h4 class="font-bold text-gray-800 text-lg">{{ getArabicRoomType(room.type) }}</h4>
                <p class="text-xs text-gray-500 font-mono" dir="ltr">ID: {{ room.id }}</p>
              </div>
              <span 
                class="px-2 py-1 rounded-lg text-[10px] font-bold"
                :class="room.isCompliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
              >
                {{ room.isCompliant ? 'موافق للكود' : 'مخالف' }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-3 text-xs text-gray-600">
              <div class="bg-gray-50 p-2 rounded-lg">
                <span class="block text-gray-400 mb-1">المساحة</span>
                <span class="font-bold text-gray-800 text-sm" dir="ltr">{{ room.metrics.area }} m²</span>
              </div>
              <div class="bg-gray-50 p-2 rounded-lg">
                <span class="block text-gray-400 mb-1">أقل بعد</span>
                <span class="font-bold text-gray-800 text-sm" dir="ltr">{{ room.metrics.minDim }} m</span>
              </div>
            </div>

            <div v-if="!room.isCompliant" class="bg-red-50 p-3 rounded-xl border border-red-100">
              <p class="text-xs text-red-800 leading-relaxed font-medium">
                <i class="fas fa-exclamation-triangle ml-1"></i>
                <strong>مخالفة:</strong> {{ room.ragReason }}
              </p>
              <button @click="askAboutRoom(room)" class="mt-3 text-xs text-primary font-bold hover:underline flex items-center gap-1">
                 استشر الذكاء الاصطناعي
                 <i class="fas fa-arrow-left text-[10px]"></i>
              </button>
              
              <!-- Proposed Fix Button -->
              <button 
                v-if="room.proposedFix" 
                @click="toggleFix(room.id)"
                class="mt-2 w-full py-2 bg-blue-50 text-blue-600 rounded-lg text-xs font-bold hover:bg-blue-100 transition flex items-center justify-center gap-2 border border-blue-200"
              >
                <i class="fas fa-magic"></i>
                {{ showingFixId === room.id ? 'إخفاء التعديل المقترح' : 'عرض التعديل المقترح' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Chat Tab -->
        <div v-else class="flex-1 flex flex-col bg-white">
          <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="chatContainer">
            <div v-for="(msg, i) in currentChatHistory" :key="i" class="flex flex-col" :class="msg.role === 'user' ? 'items-start' : 'items-end'">
              <div 
                class="max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm"
                :class="msg.role === 'user' ? 'bg-primary text-white rounded-br-none' : 'bg-gray-100 text-gray-800 rounded-bl-none'"
              >
                {{ msg.text }}
              </div>
              <span class="text-[10px] text-gray-400 mt-1 mx-1">{{ msg.time }}</span>
            </div>
            
            <div v-if="isTyping" class="flex gap-1 p-2 items-center justify-end opacity-50">
              <span class="text-xs ml-2">جاري الكتابة</span>
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span>
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-100"></span>
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-200"></span>
            </div>
          </div>

          <div class="p-3 border-t bg-gray-50">
            <div class="flex gap-2">
              <input 
                v-model="newMessage" 
                @keyup.enter="sendMessage"
                placeholder="اسأل عن الكود أو المخطط..." 
                class="flex-1 p-2.5 rounded-xl border border-gray-300 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
              >
              <button @click="sendMessage" class="p-3 bg-accent text-primary rounded-xl hover:bg-[#caca8b] transition shadow-sm">
                <i class="fas fa-paper-plane flip-horizontal"></i>
              </button>
            </div>
          </div>
        </div>

      </div>

      <!-- Main Canvas (Center - Left) -->
      <div class="flex-1 bg-gray-100 relative overflow-hidden flex items-center justify-center p-8">
        
        <div v-if="loading" class="text-center">
          <div class="animate-spin text-5xl text-primary mb-6">⚙️</div>
          <p class="text-gray-500 font-bold">جاري تحميل البيانات...</p>
        </div>

        <div v-else class="relative shadow-2xl rounded-lg bg-white inline-block transition-transform duration-200" :style="{ transform: `scale(${zoomLevel})` }">
          <img 
            :src="imageUrl" 
            ref="planImage"
            @load="onImageLoad"
            @error="onImageError"
            class="max-w-full max-h-[85vh] block select-none"
          >
          
          <div 
            v-for="room in analysisData.rooms" 
            :key="room.id"
            class="absolute border-2 transition-all duration-300 cursor-pointer flex items-center justify-center group"
            :class="[
              activeRoomId === room.id ? 'bg-accent/40 border-accent z-10 scale-105 shadow-xl' : '',
              room.isCompliant ? 'border-green-500 bg-green-500/5 hover:bg-green-500/20' : 'border-red-500 bg-red-500/5 hover:bg-red-500/20'
            ]"
            :style="getBoxStyle(room.box)"
            @mouseenter="activeRoomId = room.id"
            @mouseleave="activeRoomId = null"
            @click="scrollToCard(room.id)"
          >
            <span 
              class="absolute -top-6 px-2 py-0.5 text-[10px] font-bold text-white rounded bg-gray-800 shadow-md opacity-0 group-hover:opacity-100 transition whitespace-nowrap z-20 pointer-events-none"
            >
              {{ getArabicRoomType(room.type) }}
            </span>
          </div>

          <!-- Proposed Fix Overlay -->
          <template v-for="room in analysisData.rooms" :key="'fix-' + room.id">
            <div 
              v-if="showingFixId === room.id && room.proposedFix"
              class="absolute border-4 border-dashed border-blue-500 bg-blue-500/10 z-20 transition-all duration-300 pointer-events-none flex items-center justify-center animate-pulse"
              :style="getBoxStyle(room.proposedFix.box)"
            >
               <span class="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded shadow-lg">
                 ✨ {{ room.proposedFix.description }}
               </span>
            </div>
          </template>
        </div>

        <!-- Zoom Controls -->
        <div class="absolute bottom-8 right-8 bg-white/90 backdrop-blur rounded-xl shadow-lg flex flex-col overflow-hidden border border-gray-200">
          <button @click="zoomLevel += 0.1" class="p-3 hover:bg-gray-50 text-gray-600 border-b transition"><i class="fas fa-plus"></i></button>
          <button @click="zoomLevel = 1" class="p-3 hover:bg-gray-50 text-gray-600 border-b text-xs font-bold font-mono">100%</button>
          <button @click="zoomLevel = Math.max(0.5, zoomLevel - 0.1)" class="p-3 hover:bg-gray-50 text-gray-600 transition"><i class="fas fa-minus"></i></button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAnalysisStore } from '../stores/analysis';

const route = useRoute();
const store = useAnalysisStore();
const taskId = ref(route.params.id);
const activeTab = ref('report');
const activeRoomId = ref(null);
const zoomLevel = ref(1);
const planImage = ref(null);
const imgNaturalWidth = ref(1000);
const imgNaturalHeight = ref(1000);
const chatContainer = ref(null);
const newMessage = ref('');
const isTyping = ref(false);
const imageLoadError = ref(false);
const showingFixId = ref(null);

// Arabic Translations
const roomTypeMap = {
    'Bedroom': 'غرفة نوم',
    'Kitchen': 'مطبخ',
    'Living Room': 'غرفة معيشة',
    'Bathroom': 'دورة مياه',
    'Dining Room': 'غرفة طعام',
    'Majlis': 'مجلس'
};

const getArabicRoomType = (type) => roomTypeMap[type] || type;

// Data from Store
const analysisData = computed(() => {
  return store.getAnalysisById(taskId.value) || { imageUrl: '', rooms: [] };
});

const currentChatHistory = computed(() => {
    const history = store.getChatHistory(taskId.value);
    if (history.length === 0) {
       // Initialize welcome message if empty
       store.addChatMessage(taskId.value, { 
           role: 'ai', 
           text: 'مرحباً! أنا "عماد"، مساعدك المعماري. قمت بتحليل المخطط واكتشفت بعض الملاحظات. يمكنك الضغط على الغرف المحددة بالأحمر لمعرفة التفاصيل.', 
           time: new Date().toLocaleTimeString('ar-SA', {hour: '2-digit', minute:'2-digit'}) 
       });
       return store.getChatHistory(taskId.value);
    }
    return history;
});

const imageUrl = computed(() => {
    // 1. Prefer URL from Store (set by HomeView or fetch)
    if (analysisData.value && analysisData.value.imageUrl) {
        return analysisData.value.imageUrl;
    }
    
    // 2. Fallback: If we have an ID but no URL in store, we might be reloading.
    // Ideally we fetch from API. For now, rely on what the backend *should* return.
    // Since we fixed main.py to return full URL, we should rely on Store.
    // If Store is empty, onMounted deals with mock data.
    
    return 'https://via.placeholder.com/800x600?text=Loading+Plan...'; 
});

const loading = computed(() => !analysisData.value || !analysisData.value.rooms || analysisData.value.rooms.length === 0);

// Computed Stats
const complianceScore = computed(() => {
  if (!analysisData.value.rooms) return 0;
  if (!analysisData.value.rooms.length) return 0;
  const compliant = analysisData.value.rooms.filter(r => r.isCompliant).length;
  return Math.round((compliant / analysisData.value.rooms.length) * 100);
});

const violationsCount = computed(() => {
  if (!analysisData.value.rooms) return 0;
  return analysisData.value.rooms.filter(r => !r.isCompliant).length;
});

// --- Methods ---

onMounted(async () => {
    // Scroll chat to bottom
    if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }

    // Polling logic
    if (analysisData.value && (analysisData.value.status === 'Processing' || analysisData.value.status === 'processing_started' || analysisData.value.status === 'processing')) {
        pollInterval = setInterval(async () => {
            if (!taskId.value) return; 
            try {
                const res = await fetch(`/api/analysis/${taskId.value}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'completed' || data.result) {
                        const finalData = data.result || data;
                        store.updateAnalysis(taskId.value, finalData);
                        if (finalData.status !== 'processing') {
                             clearInterval(pollInterval);
                        }
                    }
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 3000);
    }

    // Mock data load if store is empty (Simulating backend fetch)
    if (!analysisData.value.rooms || analysisData.value.rooms.length === 0) {
        const mockFullData = {
            id: taskId.value,
            imageUrl: 'https://raw.githubusercontent.com/zhixuhao/unet/master/img/30.png',
            rooms: [
                { id: 1, type: 'Bedroom', isCompliant: true, metrics: { area: 14.5, minDim: 3.2 }, box: { x: 0.1, y: 0.1, w: 0.3, h: 0.4 } },
                { id: 2, type: 'Kitchen', isCompliant: false, metrics: { area: 4.2, minDim: 1.8 }, ragReason: 'المساحة أقل من الحد الأدنى للمطبخ (4.5م²) حسب كود البناء السعودي 501.2.', box: { x: 0.5, y: 0.1, w: 0.2, h: 0.25 } },
                { id: 3, type: 'Living Room', isCompliant: true, metrics: { area: 22.0, minDim: 4.5 }, box: { x: 0.1, y: 0.55, w: 0.5, h: 0.35 } },
                { id: 4, type: 'Bathroom', isCompliant: false, metrics: { area: 3.0, minDim: 1.5 }, ragReason: 'عدم وجود نافذة للتهوية الطبيعية. يجب توفير مروحة شفط ميكانيكية (كود 1202.5).', box: { x: 0.65, y: 0.6, w: 0.15, h: 0.2 } }
            ]
        };
        store.setAnalysis(mockFullData);
    }
});

const onImageLoad = (e) => {
  imgNaturalWidth.value = e.target.naturalWidth;
  imgNaturalHeight.value = e.target.naturalHeight;
};

const onImageError = () => {
    // Fallback if png fails, maybe try jpg? Or show placeholder
    imageLoadError.value = true;
};


// Convert relative coordinates (0.1) to percentages (10%) for responsiveness
const getBoxStyle = (box) => {
  return {
    left: `${box.x * 100}%`,
    top: `${box.y * 100}%`,
    width: `${box.w * 100}%`,
    height: `${box.h * 100}%`
  };
};

const scrollToCard = (id) => {
  activeTab.value = 'report'; 
  nextTick(() => {
    const el = document.getElementById(`card-${id}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
};

const toggleFix = (id) => {
    if (showingFixId.value === id) {
        showingFixId.value = null;
    } else {
        showingFixId.value = id;
        activeRoomId.value = id; // Also highlight the original room
    }
};

// Chat Functions
const askAboutRoom = (room) => {
  activeTab.value = 'chat';
  newMessage.value = `لماذا تعتبر ${getArabicRoomType(room.type)} (ID: ${room.id}) مخالفة؟`;
  sendMessage();
};

const sendMessage = async () => {
  if (!newMessage.value.trim()) return;
  
  // Add user message to store
  store.addChatMessage(taskId.value, { 
      role: 'user', 
      text: newMessage.value, 
      time: new Date().toLocaleTimeString('ar-SA', {hour: '2-digit', minute:'2-digit'}) 
  });

  const textToSend = newMessage.value;
  newMessage.value = '';
  
  // Scroll to bottom
  nextTick(() => chatContainer.value.scrollTop = chatContainer.value.scrollHeight);

  // Show AI typing indicator
  isTyping.value = true;
  
  try {
    // Call real AI chat endpoint
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: textToSend,
        task_id: taskId.value
      })
    });
    
    const data = await response.json();
    isTyping.value = false;
    
    store.addChatMessage(taskId.value, { 
       role: 'ai', 
       text: data.reply || 'عذراً، لم أتمكن من الرد.', 
       time: new Date().toLocaleTimeString('ar-SA', {hour: '2-digit', minute:'2-digit'}) 
    });
    
  } catch (error) {
    console.error('Chat error:', error);
    isTyping.value = false;
    store.addChatMessage(taskId.value, { 
       role: 'ai', 
       text: 'عذراً، حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.', 
       time: new Date().toLocaleTimeString('ar-SA', {hour: '2-digit', minute:'2-digit'}) 
    });
  }
  
  nextTick(() => chatContainer.value.scrollTop = chatContainer.value.scrollHeight);
};

const downloadImage = () => {
    if (!taskId.value) return;
    const url = `/api/download/${taskId.value}`;
    window.open(url, '_blank');
};
</script>

<style scoped>
.flip-horizontal {
    transform: scaleX(-1);
}
</style>