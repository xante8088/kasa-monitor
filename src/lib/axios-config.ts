import axios from 'axios'

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: typeof window !== 'undefined' ? window.location.origin : '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to include auth token
axiosInstance.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    
    // Add token to headers if it exists
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor to handle auth errors
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // If we get a 401, redirect to login
    if (error.response?.status === 401) {
      // Only redirect if we're not already on the login page
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        // Clear invalid token
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        
        // Redirect to login
        window.location.href = '/login'
      }
    }
    
    return Promise.reject(error)
  }
)

export default axiosInstance