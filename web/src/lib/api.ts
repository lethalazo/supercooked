const API_BASE = 'http://localhost:8888';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface PlatformConfig {
  enabled: boolean;
  handle: string;
}

export interface Platforms {
  youtube_shorts: PlatformConfig;
  x: PlatformConfig;
  instagram: PlatformConfig;
  tiktok: PlatformConfig;
  twitch: PlatformConfig;
}

export interface Persona {
  archetype: string;
  age_presentation: string;
  tone: string;
  perspective: string;
  voice_traits: string[];
  boundaries: string[];
}

export interface BeingInfo {
  slug: string;
  name: string;
  tagline: string;
  created: string;
}

export interface Being {
  being: BeingInfo;
  persona: Persona;
  platforms: Platforms;
  content_strategy: {
    posting_frequency: {
      shorts: string;
      images: string;
      tweets: string;
    };
    series: Array<{
      name: string;
      format: string;
      frequency: string;
    }>;
  };
}

export interface ContentItem {
  id?: string;
  content_id?: string;
  title: string;
  template?: string;
  type?: string;
  concept?: string;
  caption?: string;
  status?: string;
  created?: string;
  published_at?: string;
  platform?: string;
  slug?: string;
  being?: {
    slug: string;
    name: string;
    tagline: string;
  };
}

export interface FeedResponse {
  total: number;
  offset: number;
  limit: number;
  items: ContentItem[];
}

export interface ContentResponse {
  slug: string;
  drafts: ContentItem[];
  published: ContentItem[];
}

export interface IdeasResponse {
  slug: string;
  ideas: ContentIdea[];
}

export interface ActionEntry {
  timestamp: string;
  action: string;
  platform: string;
  details: Record<string, any>;
  result: string;
  error: string | null;
}

export interface ActivityResponse {
  slug: string;
  days: number;
  actions: ActionEntry[];
}

export interface ContentIdea {
  id: string;
  title: string;
  concept: string;
  template: string;
  status: string;
  created: string;
  tags: string[];
  content_types: string[];
}

export interface AddIdeaData {
  title: string;
  concept: string;
  template?: string;
  content_types?: string[];
  tags?: string[];
}

export async function fetchBeings(): Promise<Being[]> {
  return request<Being[]>('/beings');
}

export async function fetchBeing(slug: string): Promise<Being> {
  return request<Being>(`/beings/${slug}`);
}

export async function fetchContent(slug: string): Promise<ContentResponse> {
  return request<ContentResponse>(`/beings/${slug}/content`);
}

export async function fetchFeed(limit = 50, offset = 0): Promise<FeedResponse> {
  return request<FeedResponse>(`/feed?limit=${limit}&offset=${offset}`);
}

export async function fetchBeingFeed(slug: string, limit = 50, offset = 0): Promise<FeedResponse> {
  return request<FeedResponse>(`/feed/${slug}?limit=${limit}&offset=${offset}`);
}

export async function fetchActivity(slug: string, days = 7): Promise<ActivityResponse> {
  return request<ActivityResponse>(`/beings/${slug}/activity?days=${days}`);
}

export async function fetchIdeas(slug: string): Promise<IdeasResponse> {
  return request<IdeasResponse>(`/beings/${slug}/ideas`);
}

export async function generateIdeas(slug: string, count = 5, focus?: string): Promise<any> {
  return request<any>(`/beings/${slug}/ideas/generate`, {
    method: 'POST',
    body: JSON.stringify({ count, focus: focus || null }),
  });
}

export async function draftIdea(slug: string, ideaId: string): Promise<any> {
  return request<any>(`/beings/${slug}/ideas/${ideaId}/draft`, {
    method: 'POST',
  });
}

export async function generateIdea(slug: string, ideaId: string): Promise<any> {
  return request<any>(`/beings/${slug}/ideas/${ideaId}/generate`, {
    method: 'POST',
  });
}

export async function publishIdea(slug: string, ideaId: string): Promise<any> {
  return request<any>(`/beings/${slug}/ideas/${ideaId}/publish`, {
    method: 'POST',
  });
}

export async function regenerateIdea(slug: string, ideaId: string): Promise<any> {
  return request<any>(`/beings/${slug}/ideas/${ideaId}/regenerate`, {
    method: 'POST',
  });
}

export async function generateFace(slug: string): Promise<{ slug: string; path: string; filename: string }> {
  return request(`/beings/${slug}/face/generate`, {
    method: 'POST',
  });
}

export function getFaceUrl(slug: string): string {
  return `${API_BASE}/beings/${slug}/face`;
}

export async function addIdea(slug: string, data: AddIdeaData): Promise<any> {
  return request<any>(`/beings/${slug}/ideas`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchContentDetail(slug: string, ideaId: string): Promise<any> {
  return request<any>(`/beings/${slug}/content/${ideaId}`);
}

export function getFileUrl(slug: string, contentId: string, filename: string): string {
  return `${API_BASE}/beings/${slug}/content/${contentId}/files/${filename}`;
}
