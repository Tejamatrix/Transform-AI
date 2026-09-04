export type SourceOut = {
  id: string;
  project_id: string;
  source_type: string;
  title: string;
  filename: string;
  status: string;
  error: string;
  char_count: number;
  chunk_count: number;
  created_at: string;
};

export type SourceRef = {
  source_id: string;
  source_title: string;
  page: number;
  section: string;
  paragraph: number;
  chunk_index: number;
  quote: string;
};

export type Blueprint = {
  id: string;
  project_id: string;
  version: number;
  status: string;
  content: {
    domain: string;
    intent: string;
    summary: string;
    audience: string;
    communication_objective: string;
    entities: { name: string; type: string; description: string }[];
    key_facts: { text: string; source_refs: SourceRef[] }[];
    statistics: string[];
    timeline: { date: string; label: string; event: string }[];
    risks: string[];
    recommendations: string[];
    important_quotes: string[];
    source_references: SourceRef[];
    conflicts: { type: string; detail: string; status: string; occurrences: unknown[] }[];
    recommended_outputs: string[];
    confidence: number;
  };
  created_at: string;
  updated_at: string;
};

export type ProjectOut = {
  id: string;
  name: string;
  description: string;
  created_at: string;
  source_count: number;
  output_count: number;
};

export type OutputOut = {
  id: string;
  project_id: string;
  blueprint_id: string;
  output_type: string;
  config: Record<string, unknown>;
  content: Record<string, unknown>;
  status: string;
  current_version: number;
  created_at: string;
  updated_at: string;
};

export type JobOut = {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  detail: string;
  result_json: { output_ids?: string[] };
};

export type ValidationClaim = {
  claim: string;
  status: "VERIFIED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED";
  confidence: number;
  evidence: SourceRef[];
};

export type GroundingClaim = {
  index: number;
  claim: string;
  status: "VERIFIED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED";
  confidence: number;
  evidence: SourceRef[];
};

export type ValidationResp = {
  validated: boolean;
  claims?: ValidationClaim[];
  summary?: Record<string, number>;
  grounding?: {
    validated: boolean;
    claims: GroundingClaim[];
    summary: Record<string, number>;
  } | null;
};

export type QualityScores = {
  accuracy: number;
  source_fidelity: number;
  relevance: number;
  readability: number;
  audience_fit: number;
  completeness: number;
  overall: number;
};

export type OutputVersion = {
  id: string;
  version_number: number;
  action: string;
  created_at: string;
  content: Record<string, unknown>;
};

export type AuditEntry = {
  id: string;
  action: string;
  detail: string;
  created_at: string;
  project_id: string | null;
};

export const OUTPUT_LABELS: Record<string, string> = {
  executive_summary: "Executive Summary",
  advisory: "Advisory",
  linkedin: "LinkedIn Post",
  x_thread: "X Thread",
  presentation: "Presentation",
  infographic: "Infographic",
  video_package: "Video Package",
};

export const AUDIENCES = [
  ["general_public", "General public"],
  ["government_officials", "Government officials"],
  ["executives", "Executives"],
  ["technical_teams", "Technical teams"],
  ["security_professionals", "Security professionals"],
  ["students", "Students"],
  ["customers", "Customers"],
  ["internal_employees", "Internal employees"],
  ["custom", "Custom audience"],
];

export const TONES = [
  "professional", "formal", "neutral", "urgent",
  "educational", "persuasive", "technical", "conversational",
];

export const LANGUAGES = ["English", "Hindi", "Telugu"];

export const DETAIL_LEVELS = ["brief", "moderate", "detailed", "highly_detailed"];

export const OBJECTIVES = ["inform", "alert", "educate", "persuade", "promote", "brief", "mobilise"];

export const STYLES = [
  ["standard", "Standard"],
  ["storytelling", "Storytelling"],
  ["data_driven", "Data-driven"],
  ["action_oriented", "Action-oriented"],
];
