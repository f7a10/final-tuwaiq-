// ==========================================
// Auth Store - Pinia
// Manages authentication state and logout
// ==========================================

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

export const useAuthStore = defineStore('auth', () => {
    // State
    const token = ref(localStorage.getItem('auth_token') || null);
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
    const loading = ref(false);
    const error = ref(null);

    // Getters
    const isAuthenticated = computed(() => !!token.value);
    const isAdmin = computed(() => user.value?.role === 'admin');
    const currentUser = computed(() => user.value);

    // Actions
    function setAuth(authToken, userData) {
        token.value = authToken;
        user.value = userData;
        localStorage.setItem('auth_token', authToken);
        localStorage.setItem('user', JSON.stringify(userData));
    }

    function updateUser(userData) {
        user.value = userData;
        localStorage.setItem('user', JSON.stringify(userData));
    }

    async function fetchCurrentUser() {
        if (!token.value) return null;

        loading.value = true;
        error.value = null;

        try {
            const response = await fetch('/api/me', {
                headers: {
                    'Authorization': `Bearer ${token.value}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Token expired or invalid
                    logout();
                    return null;
                }
                throw new Error('Failed to fetch user');
            }

            const userData = await response.json();
            updateUser(userData);
            return userData;

        } catch (err) {
            error.value = err.message;
            return null;
        } finally {
            loading.value = false;
        }
    }

    function logout() {
        // Clear state
        token.value = null;
        user.value = null;

        // Clear localStorage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');

        // Redirect to login (will be handled by component)
        return true;
    }

    function getAuthHeader() {
        if (!token.value) return {};
        return {
            'Authorization': `Bearer ${token.value}`
        };
    }

    // Return store
    return {
        // State
        token,
        user,
        loading,
        error,

        // Getters
        isAuthenticated,
        isAdmin,
        currentUser,

        // Actions
        setAuth,
        updateUser,
        fetchCurrentUser,
        logout,
        getAuthHeader
    };
});
