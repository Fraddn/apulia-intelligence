export type Province = 'BA' | 'BT' | 'BR' | 'FG' | 'LE' | 'TA'
export type Assurance = 'official' | 'company' | 'inferred' | 'derived' | 'manual'

export interface CompanySummary {
  vat_number: string
  name: string
  province: Province | ''
  city: string
  ateco_section: string
  ateco_code: string
  size_class: string
}

export interface CompanyListItem extends CompanySummary {
  beneficiary_projects: number
  sole_beneficiary_funding: number | null
}

export interface Source {
  name: string
  url: string
  licence: string
  attribution: string
}

export interface Provenance {
  field: string
  raw_value: string
  assurance: Assurance
  confidence: number | null
  source: Source
  reference: string
  data_date: string | null
  collected_at: string
}

export type ProjectRole = 'beneficiary' | 'implementer' | 'contractor' | 'programmer'
export type ProjectStatus = 'not_started' | 'ongoing' | 'completed' | 'settled' | 'unknown'

export interface FundedProject {
  code: string
  title: string
  summary: string
  theme_code: string
  theme: string
  cycle: string
  status: ProjectStatus
  role: ProjectRole
  public_funding: number | null
  beneficiaries_count: number
  start_date: string | null
  expected_end_date: string | null
  actual_end_date: string | null
  url: string
}

export interface CompanyFunding {
  beneficiary_projects: number
  sole_beneficiary_projects: number
  shared_projects: number
  sole_beneficiary_funding: number | null
  roles: Partial<Record<ProjectRole, number>>
}

export interface StateAidItem {
  cor: string
  granted_on: string | null
  measure_title: string
  granting_body: string
  project_title: string
  objectives: string
  procedures: string
  instruments: string
  aid_amount: number | null
  transparency_url: string
}

export interface CompanyAid {
  count: number
  total_amount: number | null
  latest_date: string | null
  items: StateAidItem[]
}

export interface CompanyDetail extends CompanySummary {
  tax_code: string
  legal_form_code: string
  legal_form: string
  ateco_description: string
  ateco_version: string
  municipality_code: string
  address: string
  postcode: string
  website: string
  status: string
  employees_band: string
  founded_on: string | null
  profile_level: string
  provenance: Provenance[]
  funding: CompanyFunding
  projects: FundedProject[]
  projects_total: number
  aid: CompanyAid
}

export interface Page<T> {
  items: T[]
  count: number
}

export interface Stats {
  total: number
  with_ateco: number
  size_known: number
  by_province: { province: Province; count: number }[]
  by_section: { section: string; count: number }[]
  sources: (Source & { data_date: string | null })[]
  funding: {
    beneficiary_companies: number
    beneficiary_projects: number
    sole_beneficiary_funding: number
    by_theme: { theme_code: string; theme: string; count: number }[]
  }
  aid: {
    companies: number
    grants: number
    total_amount: number
  }
}

export type CompanySort = 'name' | 'funding' | 'projects'

export interface CompanyQuery {
  search?: string
  province?: string
  section?: string
  division?: string
  theme?: string
  funded?: boolean
  sort?: CompanySort
  page?: number
  page_size?: number
}

export class ApiError extends Error {
  constructor(public status: number) {
    super(`API error ${status}`)
  }
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}

export function buildQuery(params: CompanyQuery): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== null) query.set(key, String(value))
  }
  const text = query.toString()
  return text ? `?${text}` : ''
}

export interface Health {
  status: string
  version: string
}

export const api = {
  health: () => get<Health>('/health'),
  stats: () => get<Stats>('/stats'),
  companies: (params: CompanyQuery = {}) => get<Page<CompanyListItem>>(`/companies${buildQuery(params)}`),
  company: (vat: string) => get<CompanyDetail>(`/companies/${encodeURIComponent(vat)}`),
}
