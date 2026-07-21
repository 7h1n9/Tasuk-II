import axios from 'axios'
import type { Envelope } from './types'
import type { ChallengeDetail, ChallengeSummary, InstanceInfo, RunInfo, StatsInfo } from './types'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:18080'

const client = axios.create({
  baseURL,
  timeout: 60000,
})

async function unwrap<T>(promise: Promise<{ data: Envelope<T> }>): Promise<T> {
  const response = await promise
  if (!response.data.success) {
    throw new Error(response.data.message || '请求失败')
  }
  return response.data.data
}

export const api = {
  getChallenges: async (): Promise<ChallengeSummary[]> => {
    const result = await unwrap<{ items: ChallengeSummary[] }>(client.get('/api/v1/challenges'))
    return result.items
  },
  getChallenge: (challengeId: string): Promise<ChallengeDetail> =>
    unwrap<ChallengeDetail>(client.get(`/api/v1/challenges/${challengeId}`)),
  createInstance: (challengeId: string): Promise<InstanceInfo> =>
    unwrap<InstanceInfo>(client.post('/api/v1/instances', { challenge_id: challengeId })),
  listInstances: async (): Promise<InstanceInfo[]> => {
    const result = await unwrap<{ items: InstanceInfo[] }>(client.get('/api/v1/instances'))
    return result.items
  },
  getInstance: (instanceId: string): Promise<InstanceInfo> => unwrap<InstanceInfo>(client.get(`/api/v1/instances/${instanceId}`)),
  resetInstance: (instanceId: string): Promise<InstanceInfo> =>
    unwrap<InstanceInfo>(client.post(`/api/v1/instances/${instanceId}/reset`)),
  destroyInstance: (instanceId: string): Promise<{ instance_id: string; status: string }> =>
    unwrap<{ instance_id: string; status: string }>(client.delete(`/api/v1/instances/${instanceId}`)),
  submitFlag: (instanceId: string, flag: string): Promise<{ correct: boolean; submission_id: string; message: string }> =>
    unwrap<{ correct: boolean; submission_id: string; message: string }>(client.post(`/api/v1/instances/${instanceId}/submit`, { flag })),
  listRuns: async (): Promise<RunInfo[]> => {
    const result = await unwrap<{ items: RunInfo[] }>(client.get('/api/v1/runs'))
    return result.items
  },
  getStats: (): Promise<StatsInfo> => unwrap<StatsInfo>(client.get('/api/v1/stats')),
  createRun: (payload: { challenge_id: string; instance_id?: string | null; model_name?: string; model_mode?: string }) =>
    unwrap<RunInfo>(client.post('/api/v1/runs', payload)),
}
