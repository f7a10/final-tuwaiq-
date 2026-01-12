<template>
  <div class="min-h-screen bg-gray-50 flex flex-col font-sans" dir="rtl">
    
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
        <button class="text-base text-gray-200 hover:text-white hover:border-b-2 hover:border-white/50 pb-1 transition" @click="$router.push('/history')">السجل</button>
      </div>
    </nav>

    <main class="flex-grow flex flex-col items-center justify-center p-6 relative overflow-hidden">
      
      <!-- Ambient Background -->
      <div class="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
      <div class="absolute bottom-0 left-0 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[120px] translate-y-1/3 -translate-x-1/3"></div>

      <div v-if="!isProcessing" class="w-full max-w-5xl z-10 animate-fade-in-up">
        
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
                <button 
                  @click.stop="loadDemoData"
                  class="mt-6 px-5 py-2.5 text-sm font-bold text-primary bg-white border border-primary/20 rounded-xl hover:bg-primary hover:text-white transition shadow-sm z-20 pointer-events-auto"
                >
                  ✨ تجربة مخطط افتراضي
                </button>
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
            <div>
              <h3 class="text-xl font-bold text-primary mb-8 flex items-center gap-3 border-b border-gray-100 pb-4">
                <i class="fas fa-sliders-h"></i> إعدادات الفحص
              </h3>
              
              <div class="space-y-6">
                <label class="flex items-start gap-4 cursor-pointer group">
                  <div class="relative flex items-center">
                    <input type="checkbox" v-model="settings.checkVentilation" class="peer h-6 w-6 cursor-pointer appearance-none rounded-md border-2 border-gray-300 transition-all checked:border-primary checked:bg-primary hover:border-primary/50">
                    <i class="fas fa-check text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-xs opacity-0 peer-checked:opacity-100 pointer-events-none"></i>
                  </div>
                  <div>
                    <span class="font-bold text-gray-800 group-hover:text-primary transition text-lg">التحقق من التهوية</span>
                    <p class="text-sm text-gray-400 mt-1">مطابقة نسبة النوافذ لمساحة الغرفة حسب الكود.</p>
                  </div>
                </label>

                <label class="flex items-start gap-4 cursor-pointer group">
                  <div class="relative flex items-center">
                    <input type="checkbox" v-model="settings.checkDimensions" class="peer h-6 w-6 cursor-pointer appearance-none rounded-md border-2 border-gray-300 transition-all checked:border-primary checked:bg-primary hover:border-primary/50">
                    <i class="fas fa-check text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-xs opacity-0 peer-checked:opacity-100 pointer-events-none"></i>
                  </div>
                  <div>
                    <span class="font-bold text-gray-800 group-hover:text-primary transition text-lg">أبعاد الغرف</span>
                    <p class="text-sm text-gray-400 mt-1">التأكد من الحد الأدنى لطول وعرض كل غرفة.</p>
                  </div>
                </label>
              </div>
            </div>

            <button 
              @click="uploadAndAnalyze"
              :disabled="!selectedFile"
              class="w-full py-5 rounded-2xl font-bold text-xl shadow-lg transition-all duration-300 flex items-center justify-center gap-3 mt-8"
              :class="selectedFile 
                ? 'bg-primary text-white hover:bg-[#0c615b] hover:shadow-primary/30 hover:-translate-y-1' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'"
            >
              <span>بدء التحليل</span>
              <i class="fas fa-arrow-left"></i>
            </button>
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
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAnalysisStore } from '../stores/analysis';

const router = useRouter();
const store = useAnalysisStore();

const fileInput = ref(null);
const selectedFile = ref(null);
const previewUrl = ref(null);
const isDragging = ref(false);
const isProcessing = ref(false);
const processingStep = ref('جاري رفع الملف...');

const settings = ref({
  checkVentilation: true,
  checkDimensions: true
});

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

  isProcessing.value = true;
  processingStep.value = "جاري التعرف على الجدران والأبواب (YOLO)...";

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('settings', JSON.stringify(settings.value));

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

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