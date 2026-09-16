export type VoiceTier = 'free' | 'standard' | 'premium' | 'ultra' | 'custom';

export type GenerationStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface Voice {
  id: string;
  name: string;
  slug: string;
  description: string;
  language: string;
  locale: string;
  accent: string;
  gender: string;
  style: string;
  tier: VoiceTier;
  preview_audio_url?: string;
  is_public: boolean;
  commercial_use_allowed: boolean;
  owner_user_id?: string;
  created_at: string;
}

export interface Generation {
  id: string;
  user_id: string;
  voice_id: string;
  voice_name?: string;
  model: string;
  provider: string;
  input_characters: number;
  estimated_audio_seconds: number;
  actual_audio_seconds: number;
  format: 'mp3' | 'wav';
  status: GenerationStatus;
  error_code?: string;
  error_message?: string;
  audio_url?: string;
  estimated_cost: number;
  created_at: string;
  completed_at?: string;
}

export interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  monthly_price: number;
  currency: string;
  included_characters: number;
  included_seconds: number;
  allow_cloning: boolean;
  allow_premium_voices: boolean;
  allow_api: boolean;
  allow_commercial_use: boolean;
  fair_use_limit: number;
}
