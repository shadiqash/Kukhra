import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/token/refresh/', { refresh })
          localStorage.setItem('access', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return client(original)
        } catch {
          localStorage.clear()
          window.location.replace('/#/login')
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
