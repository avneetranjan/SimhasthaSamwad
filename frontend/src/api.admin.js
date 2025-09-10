import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export const adminApi = axios.create({ baseURL })

// Feedback listing – placeholder until backend adds a list endpoint
export const listFeedbackFallback = async () => {
  // Try a future endpoint; fallback to empty list
  try {
    const { data } = await adminApi.get('/api/tools/feedback/list')
    return data.items || []
  } catch {
    return []
  }
}

export const updateIssueStatus = async ({ id, status }) => {
  const { data } = await adminApi.post('/api/tools/update_issue_status', { id, status })
  return data
}

export const assignIssue = async ({ feedback_id, assignee, note }) => {
  const { data } = await adminApi.post('/api/tools/assign_issue', { feedback_id, assignee, note })
  return data
}

export const broadcastNotice = async ({ message, zones, phone_numbers }) => {
  const { data } = await adminApi.post('/api/tools/broadcast_notice', { message, zones, phone_numbers })
  return data
}

export const getZoneConfig = async () => {
  const { data } = await adminApi.get('/api/admin/zone_config')
  return data
}

export const upsertZoneConfig = async (payload) => {
  const { data } = await adminApi.post('/api/admin/zone_config', payload)
  return data
}

export const classifyIntent = async (text) => {
  const { data } = await adminApi.post('/api/tools/classify_intent', { text })
  return data
}

export const summarizeConversation = async ({ phone_number, max_messages = 50 }) => {
  const { data } = await adminApi.post('/api/tools/summarize', { phone_number, max_messages })
  return data
}

export const setContactMetadata = async (payload) => {
  const { data } = await adminApi.post('/api/tools/set_contact_metadata', payload)
  return data
}

// Templates CRUD
export const listTemplates = async () => {
  const { data } = await adminApi.get('/api/templates')
  return data
}

export const createTemplate = async (payload) => {
  const { data } = await adminApi.post('/api/templates', payload)
  return data
}

export const updateTemplate = async (id, payload) => {
  const { data } = await adminApi.put(`/api/templates/${id}`, payload)
  return data
}

export const deleteTemplate = async (id) => {
  const { data } = await adminApi.delete(`/api/templates/${id}`)
  return data
}

// Agent tools + approvals
export const listAgentTools = async () => {
  const { data } = await adminApi.get('/api/agent/tools')
  return data
}

export const invokeAgentTool = async (tool, args, dry_run=false) => {
  const { data } = await adminApi.post('/api/agent/tools/invoke', { tool, args, dry_run })
  return data
}

export const listApprovals = async (status='pending') => {
  const { data } = await adminApi.get('/api/admin/approvals', { params: { status } })
  return data
}

export const decideApproval = async (id, approve, actor='admin') => {
  const { data } = await adminApi.post(`/api/admin/approvals/${id}/decision`, { approve, actor })
  return data
}

// Messages by phone
export const listMessagesByPhone = async (phone_number) => {
  const { data } = await adminApi.get(`/api/messages/by_phone/${encodeURIComponent(phone_number)}`)
  return data.messages
}

// Resolve context (zone + ETAs)
export const resolveContext = async (phone_number) => {
  const { data } = await adminApi.get('/api/tools/resolve_context', { params: { phone_number } })
  return data
}

// Metrics
export const getMetrics = async () => {
  const { data } = await adminApi.get('/api/admin/metrics')
  return data
}
