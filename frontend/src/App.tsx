import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import type { ChallengeDetail, ChallengeSummary, InstanceInfo, RunInfo, StatsInfo } from './types'

function fmtDate(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

function difficultyLabel(value: string) {
  const map: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难',
  }
  return map[value] || value
}

function statusLabel(value: string) {
  const map: Record<string, string> = {
    starting: '启动中',
    running: '运行中',
    resetting: '重置中',
    destroyed: '已销毁',
    error: '错误',
  }
  return map[value] || value
}

function Shell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const sections = [
    { key: 'challenges', title: '题目管理', path: '/challenges', label: '题目列表' },
    { key: 'instances', title: '实例管理', path: '/instances', label: '运行实例' },
    { key: 'runs', title: '运行记录', path: '/runs', label: '执行记录' },
    { key: 'stats', title: '数据统计', path: '/stats', label: '基础统计' },
  ]
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">C7F</div>
          <div>
            <div className="brand-title">C7F-W3B-Q1LL3R</div>
            <div className="brand-subtitle">CTF Web Agent Range</div>
          </div>
        </div>
        <nav className="nav">
          {sections.map((section) => (
            <div className={`nav-section${collapsed[section.key] ? ' is-collapsed' : ''}`} key={section.key}>
              <button className="nav-section-toggle" onClick={() => setCollapsed((current) => ({ ...current, [section.key]: !current[section.key] }))} aria-expanded={!collapsed[section.key]}>
                <span>{section.title}</span><span className="nav-chevron">{collapsed[section.key] ? '＋' : '－'}</span>
              </button>
              {!collapsed[section.key] && <NavLink to={section.path} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{section.label}</NavLink>}
            </div>
          ))}
          {/* legacy links replaced by the grouped navigation above */}
          <div className="legacy-nav-hidden">
          <NavLink to="/challenges" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            题目列表
          </NavLink>
          <NavLink to="/instances" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            实例管理
          </NavLink>
          <NavLink to="/runs" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            运行记录
          </NavLink>
          <NavLink to="/stats" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            基础统计
          </NavLink>
          </div>
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">授权本地靶场</div>
            <h1>C7F-W3B-Q1LL3R 控制台</h1>
          </div>
          <div className="topbar-meta">后端接口：{import.meta.env.VITE_API_BASE_URL || 'http://localhost:18080'}</div>
        </header>
        {children}
      </main>
    </div>
  )
}

function PageCard({ title, children, actions }: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section className="card">
      <div className="card-header">
        <h2>{title}</h2>
        <div>{actions}</div>
      </div>
      {children}
    </section>
  )
}

function ChallengeListPage() {
  const [items, setItems] = useState<ChallengeSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})
  const navigate = useNavigate()
  const groups = ['core-a', 'core-b', 'core-c', 'core-d']

  useEffect(() => {
    api
      .getChallenges()
      .then(setItems)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <PageCard title="题目列表" actions={<span className="hint">共 {items.length} 道题</span>}>
      {loading ? (
        <div className="empty-state">正在加载题目...</div>
      ) : error ? (
        <div className="error-box">{error}</div>
      ) : (
        <div className="challenge-groups">
          {groups.map((group) => {
            const groupItems = items.filter((item) => item.id.startsWith(group))
            return (
              <section className="challenge-group" key={group}>
                <button className="challenge-group-header" onClick={() => setCollapsedGroups((current) => ({ ...current, [group]: !current[group] }))}>
                  <span><strong>{group.toUpperCase()}</strong><small>{groupItems.length} 个题目</small></span>
                  <span>{collapsedGroups[group] ? '+' : '-'}</span>
                </button>
                {!collapsedGroups[group] && <div className="challenge-grid">
          {groupItems.map((item) => (
            <article key={item.id} className="challenge-card">
              <div className="challenge-head">
                <div>
                  <div className="challenge-id">{item.id}</div>
                  <h3>{item.name}</h3>
                </div>
                <span className={`badge difficulty-${item.difficulty}`}>{difficultyLabel(item.difficulty)}</span>
              </div>
              <p className="challenge-desc">{item.description}</p>
              <div className="meta-row">
                <span>分类：{item.category}</span>
                <span>实例：{item.current_instances}</span>
                <span>入口：{item.entry.path}</span>
              </div>
              <div className="tag-row">
                {item.tags.map((tag) => (
                  <span key={tag} className="tag">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="card-actions">
                <button className="btn-primary" onClick={() => navigate(`/challenges/${item.id}`)}>
                  查看详情
                </button>
                <button className="btn-ghost" onClick={() => api.createInstance(item.id).then(() => navigate('/instances'))}>
                  创建实例
                </button>
              </div>
            </article>
          ))}
        </div>
                }
              </section>
            )
          })}
        </div>
      )}
    </PageCard>
  )
}

function ChallengeDetailPage() {
  const { challengeId } = useParams()
  const [item, setItem] = useState<ChallengeDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!challengeId) return
    api.getChallenge(challengeId).then(setItem)
  }, [challengeId])

  if (!challengeId) return <Navigate to="/challenges" replace />

  return (
    <PageCard title="题目详情">
      {!item ? (
        <div className="empty-state">正在加载题目详情...</div>
      ) : (
        <div className="detail-layout">
          <div>
            <h3>{item.name}</h3>
            <p>{item.description}</p>
            {item.guide && <div className="guide-box">
              <h4>解题线索：{item.guide.vulnerability}</h4>
              <ol>{item.guide.steps.map((step) => <li key={step}>{step}</li>)}</ol>
            </div>}
            <div className="detail-table">
              <div>编号</div>
              <div>{item.id}</div>
              <div>分类</div>
              <div>{item.category}</div>
              <div>难度</div>
              <div>{difficultyLabel(item.difficulty)}</div>
              <div>入口</div>
              <div>{item.entry.path}</div>
              <div>内网端口</div>
              <div>{item.entry.internal_port}</div>
              <div>Flag 格式</div>
              <div>{item.objective.format}</div>
            </div>
          </div>
          <div className="detail-box">
            <h4>运行约束</h4>
            <p>最大时长：{item.runtime.max_seconds} 秒</p>
            <p>内存限制：{item.runtime.memory_limit}</p>
            <p>CPU 限制：{item.runtime.cpu_limit}</p>
            <p>当前实例数：{item.current_instances}</p>
            <div className="card-actions">
              <button
                className="btn-primary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true)
                  try {
                    await api.createInstance(item.id)
                    navigate('/instances')
                  } finally {
                    setBusy(false)
                  }
                }}
              >
                创建实例
              </button>
              <button className="btn-ghost" onClick={() => navigate('/challenges')}>
                返回列表
              </button>
            </div>
          </div>
        </div>
      )}
    </PageCard>
  )
}

function InstancesPage() {
  const [items, setItems] = useState<InstanceInfo[]>([])
  const [flagValue, setFlagValue] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  const load = () => api.listInstances().then(setItems)

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message))
  }, [])

  return (
    <PageCard title="实例管理" actions={<button className="btn-ghost" onClick={() => load()}>刷新</button>}>
      {message ? <div className="error-box">{message}</div> : null}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>实例 ID</th>
              <th>题目</th>
              <th>目标地址</th>
              <th>创建时间</th>
              <th>过期时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.instance_id}>
                <td>{item.instance_id}</td>
                <td>{item.challenge_name}</td>
                <td>
                  <a href={item.target_url} target="_blank" rel="noreferrer">
                    {item.target_url}
                  </a>
                </td>
                <td>{fmtDate(item.created_at)}</td>
                <td>{fmtDate(item.expires_at)}</td>
                <td>
                  <span className={`badge status-${item.status}`}>{statusLabel(item.status)}</span>
                </td>
                <td>
                  <div className="action-stack">
                    <button className="btn-mini" onClick={() => api.resetInstance(item.instance_id).then(load)}>
                      重置
                    </button>
                    <button className="btn-mini danger" onClick={() => api.destroyInstance(item.instance_id).then(load)}>
                      销毁
                    </button>
                    <button
                      className="btn-mini"
                      onClick={async () => {
                        const next = window.prompt('请输入要提交的 Flag', flagValue)
                        if (!next) return
                        const result = await api.submitFlag(item.instance_id, next)
                        setMessage(result.correct ? `提交成功：${result.message}` : `提交失败：${result.message}`)
                      }}
                    >
                      提交 Flag
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageCard>
  )
}

function RunsPage() {
  const [items, setItems] = useState<RunInfo[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api
      .listRuns()
      .then(setItems)
      .catch((err: Error) => setError(err.message))
  }, [])
  return (
    <PageCard title="运行记录">
      {error ? <div className="error-box">{error}</div> : null}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Run ID</th>
              <th>题目</th>
              <th>模型</th>
              <th>成功</th>
              <th>耗时</th>
              <th>请求数</th>
              <th>工具调用</th>
              <th>失败原因</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.challenge_id}</td>
                <td>{item.model_name}</td>
                <td>{item.success ? '是' : '否'}</td>
                <td>{item.total_duration_ms} ms</td>
                <td>{item.http_request_count}</td>
                <td>{item.tool_call_count}</td>
                <td>{item.failure_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageCard>
  )
}

function StatsPage() {
  const [stats, setStats] = useState<StatsInfo | null>(null)
  useEffect(() => {
    api.getStats().then(setStats)
  }, [])
  return (
    <PageCard title="基础统计">
      {!stats ? (
        <div className="empty-state">统计数据加载中...</div>
      ) : (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_runs}</div>
            <div className="stat-label">总运行次数</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.success_runs}</div>
            <div className="stat-label">成功次数</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.success_rate}%</div>
            <div className="stat-label">成功率</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.average_duration_ms}</div>
            <div className="stat-label">平均耗时 ms</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.average_tool_calls}</div>
            <div className="stat-label">平均工具调用</div>
          </div>
        </div>
      )}
    </PageCard>
  )
}

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/challenges" replace />} />
        <Route path="/challenges" element={<ChallengeListPage />} />
        <Route path="/challenges/:challengeId" element={<ChallengeDetailPage />} />
        <Route path="/instances" element={<InstancesPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/stats" element={<StatsPage />} />
      </Routes>
    </Shell>
  )
}
