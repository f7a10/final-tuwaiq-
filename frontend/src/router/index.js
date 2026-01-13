import { createRouter, createWebHistory } from 'vue-router'

// Views (renamed from 'view' to 'views')
import HomeView from '../views/HomeView.vue'
import DashboardView from '../views/DashboardView.vue'
import HistoryView from '../views/HistoryView.vue'
import ProfileView from '../views/ProfileView.vue'

// Auth Views
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'

// Admin Views
import AdminDashboardView from '../views/admin/AdminDashboardView.vue'

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

    // Protected Routes
    {
        path: '/dashboard/:id',
        name: 'dashboard',
        component: DashboardView,
        props: true,
        meta: { requiresAuth: true }
    },
    {
        path: '/history',
        name: 'history',
        component: HistoryView,
        meta: { requiresAuth: true }
    },
    {
        path: '/profile',
        name: 'profile',
        component: ProfileView,
        meta: { requiresAuth: true }
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

// Navigation Guard - Protect routes
router.beforeEach((to, from, next) => {
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
})

export default router
