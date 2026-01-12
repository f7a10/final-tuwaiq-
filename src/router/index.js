import { createRouter, createWebHistory } from 'vue-router'

// Views
import HomeView from '../view/HomeView.vue'
import DashboardView from '../view/DashboardView.vue'
import HistoryView from '../view/HistoryView.vue'
import ProfileView from '../view/ProfileView.vue'

// Auth Views
import LoginView from '../view/auth/LoginView.vue'
import RegisterView from '../view/auth/RegisterView.vue'

// Admin Views
import AdminDashboardView from '../view/admin/AdminDashboardView.vue'

const routes = [
    // Public Routes
    {
        path: '/',
        name: 'home',
        component: HomeView
    },

    // Auth Routes
    {
        path: '/login',
        name: 'login',
        component: LoginView,
        meta: { guest: true }
    },
    {
        path: '/register',
        name: 'register',
        component: RegisterView,
        meta: { guest: true }
    },

    // Protected Routes (TEMPORARILY OPEN for debugging)
    {
        path: '/dashboard/:id',
        name: 'dashboard',
        component: DashboardView,
        props: true
        // meta: { requiresAuth: true }  // DISABLED FOR DEBUGGING
    },
    {
        path: '/history',
        name: 'history',
        component: HistoryView
        // meta: { requiresAuth: true }  // DISABLED FOR DEBUGGING
    },
    {
        path: '/profile',
        name: 'profile',
        component: ProfileView
        // meta: { requiresAuth: true }  // DISABLED FOR DEBUGGING
    },

    // Admin Routes
    {
        path: '/admin',
        name: 'admin',
        component: AdminDashboardView,
        meta: { requiresAuth: true, requiresAdmin: true }
    }
]


const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation Guard (DISABLED FOR DEBUGGING)
router.beforeEach((to, from, next) => {
    // TEMPORARILY DISABLED - All routes are open access
    next()

    /* ORIGINAL AUTH LOGIC - Uncomment to re-enable
    const token = localStorage.getItem('auth_token')
    const user = JSON.parse(localStorage.getItem('user') || '{}')

    // Check if route requires authentication
    if (to.meta.requiresAuth && !token) {
        // Redirect to login if not authenticated
        return next({ name: 'login', query: { redirect: to.fullPath } })
    }

    // Check if route requires admin role
    if (to.meta.requiresAdmin && user.role !== 'admin') {
        // Redirect to home if not admin
        return next({ name: 'home' })
    }

    // Redirect authenticated users away from guest pages (login/register)
    if (to.meta.guest && token) {
        return next({ name: 'home' })
    }

    next()
    */
})

export default router
