import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
})

export const fetchMessages = async () => {
  const { data } = await api.get('/api/messages')
  return data.messages
}

export const sendReply = async ({ phone_number, body }) => {
  const { data } = await api.post('/api/reply', { phone_number, body })
  return data
}

