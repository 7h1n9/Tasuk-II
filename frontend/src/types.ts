export type Envelope<T> = {
  success: boolean
  message: string
  data: T
  error?: { status_code?: number; detail?: string }
}

export type ChallengeSummary = {
  id: string
  name: string
  category: string
  difficulty: string
  description: string
  available: boolean
  current_instances: number
  entry: { protocol: string; internal_port: number; path: string }
  tags: string[]
  version?: string
  objective?: { type: string; format: string }
  runtime?: { max_seconds: number; memory_limit: string; cpu_limit: string }
  constraints?: Record<string, unknown>
  guide?: { vulnerability: string; steps: string[] }
}

export type ChallengeDetail = ChallengeSummary & {
  version: string
  objective: { type: string; format: string }
  runtime: { max_seconds: number; memory_limit: string; cpu_limit: string }
  constraints: Record<string, unknown>
}

export type InstanceInfo = {
  instance_id: string
  challenge_id: string
  challenge_name: string
  target_url: string
  status: string
  host_port: number
  created_at: string
  expires_at: string
  updated_at: string
  last_error?: string | null
}

export type RunInfo = {
  id: string
  challenge_id: string
  instance_id?: string | null
  model_name: string
  model_mode: string
  started_at: string
  finished_at?: string | null
  total_duration_ms: number
  success: boolean
  flag_correct: boolean
  http_request_count: number
  tool_call_count: number
  model_call_count: number
  token_input_count: number
  token_output_count: number
  payload_attempts: number
  failure_count: number
  retry_count: number
  human_intervention_count: number
  crossed_boundary: boolean
  failure_reason: string
}

export type StatsInfo = {
  total_runs: number
  success_runs: number
  success_rate: number
  average_duration_ms: number
  average_tool_calls: number
  challenge_success: Array<{ challenge_id: string; success_rate: number; total: number; success: number }>
}
