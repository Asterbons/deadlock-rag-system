export interface HeroTags {
  flavor?: string[]
  playstyle?: string[]
  damage_type?: string[]
  utility?: string[]
}

export interface HeroBaseStats {
  max_move_speed?: number
  sprint_speed?: number
  crouch_speed?: number
  move_acceleration?: number
  light_melee_damage?: number
  heavy_melee_damage?: number
  health?: number
  weapon_power?: number
  reload_speed?: number
  stamina?: number
  health_regen?: number
  stamina_regen_per_second?: number
  spirit_duration?: number
  spirit_range?: number
  ground_dash_distance_in_meters?: number
  ground_dash_duration?: number
  air_dash_distance_in_meters?: number
  air_dash_duration?: number
  [key: string]: number | undefined
}

export interface HeroScalingPerLevel {
  base_bullet_damage_from_level?: number
  health?: number
  base_melee_damage_from_level?: number
  boon_count?: number
  spirit_power?: number
  [key: string]: number | undefined
}

export interface HeroAbility {
  slot: number
  name: string
  cast_type: string
  targeting: string
  stats: Record<string, number | string>
  effect_types?: string[]
}

export interface Hero {
  hero: string
  hero_id: number
  name: string
  hero_type: string
  complexity: number
  tags: HeroTags
  base_stats: HeroBaseStats
  scaling_per_level: HeroScalingPerLevel
  abilities: HeroAbility[]
}

export interface Source {
  score: number
  type: 'hero' | 'ability' | 'item'
  label: string
  metadata: Record<string, unknown>
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  isStreaming?: boolean
}

export interface HealthStatus {
  status: string
  ollama: boolean
  qdrant: boolean
}

export type SSEEvent =
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: Source[] }
  | { type: 'done' }
  | { type: 'error'; content: string }
