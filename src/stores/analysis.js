import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
    // --- State ---
    const currentAnalysis = ref(null)

    // Load history from localStorage if available
    const storedHistory = localStorage.getItem('emad_history')
    const history = ref(storedHistory ? JSON.parse(storedHistory) : [
        {
            id: 'mock-1',
            date: '2026-01-10',
            name: 'فيلا الدور الأرضي.jpg',
            status: 'Compliant',
            score: 95,
            imageUrl: 'https://via.placeholder.com/150'
        }
    ])

    // Chat History: Map<taskId, messages[]>
    const storedChat = localStorage.getItem('emad_chat_history')
    const chatHistory = ref(storedChat ? JSON.parse(storedChat) : {})

    // --- Getters ---
    const getAnalysisById = (id) => {
        if (currentAnalysis.value && currentAnalysis.value.id === id) {
            return currentAnalysis.value
        }
        return null
    }

    const getChatHistory = (taskId) => {
        return chatHistory.value[taskId] || []
    }

    // --- Actions ---
    const saveState = () => {
        localStorage.setItem('emad_history', JSON.stringify(history.value))
        localStorage.setItem('emad_chat_history', JSON.stringify(chatHistory.value))
    }

    const setAnalysis = (data) => {
        currentAnalysis.value = data
        if (!history.value.find(h => h.id === data.id)) {
            history.value.unshift({
                id: data.id,
                date: new Date().toISOString().split('T')[0],
                name: 'مخطط جديد',
                status: data.rooms.every(r => r.isCompliant) ? 'Compliant' : 'Non-Compliant',
                score: calculateScore(data.rooms),
                imageUrl: data.imageUrl
            })
            saveState()
        }
    }

    const addToHistory = (metadata) => {
        history.value.unshift(metadata)
        saveState()
    }

    const updateAnalysis = (id, data) => {
        // Update current if matches
        if (currentAnalysis.value && currentAnalysis.value.id === id) {
            currentAnalysis.value = { ...currentAnalysis.value, ...data }
        }
        // Update history item
        const index = history.value.findIndex(h => h.id === id);
        if (index !== -1) {
            history.value[index] = { ...history.value[index], ...data };
            saveState();
        }
    }

    const addChatMessage = (taskId, message) => {
        if (!chatHistory.value[taskId]) {
            chatHistory.value[taskId] = []
        }
        chatHistory.value[taskId].push(message)
        saveState()
    }

    // Helper
    const calculateScore = (rooms) => {
        if (!rooms.length) return 0
        const compliant = rooms.filter(r => r.isCompliant).length
        return Math.round((compliant / rooms.length) * 100)
    }

    return {
        currentAnalysis,
        history,
        chatHistory,
        setAnalysis,
        addToHistory,
        getAnalysisById,
        getChatHistory,
        getChatHistory,
        addChatMessage,
        updateAnalysis
    }
})
