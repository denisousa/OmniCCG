// API Types
export interface CloneSource {
  file: string;
  startline: number;
  endline: number;
  function?: string;
  hash?: number;
}

export interface LineageNode {
  version: string;
  hash: string;
  evolution: string;
  change: string;
  parent_hash?: string;
  file?: string;
  startline?: number;
  endline?: number;
  function?: string;
  sources?: CloneSource[];
}

export interface Lineage {
  id: number;
  nodes: LineageNode[];
}

export interface GenealogyData {
  lineages: Lineage[];
}

export interface MetricsData {
  clone_density?: {
    points: Array<{
      version: number;
      clones_density: number;
    }>;
    summary: {
      versions_count_present: number;
      avg_density_present: number;
      avg_density_full_range: number;
    };
  };
  total_clone_lineages: number;
  change_patterns_of_lineages: {
    consistent: number;
    stable: number;
    inconsistent: number;
  };
  status_of_clone_lineages: {
    alive: {
      count: number;
      percentage: number;
    };
    dead: {
      count: number;
      percentage: number;
    };
  };
  length_of_dead_clone_lineages: {
    min: number;
    avg: number;
    max: number;
  };
  total_amount_of_versions: number;
  evolution_pattern_of_versions: {
    add: number;
    subtract: number;
    same?: number;
  };
  change_pattern_of_versions: {
    consistent: number;
    inconsistent: number;
    same?: number;
  };
  consistent_changes_in_consistent_lineage: {
    min: number;
    avg: number;
    max: number;
  };
  consistent_changes_in_inconsistent_lineage: {
    min: number;
    avg: number;
    max: number;
  };
  inconsistent_changes_in_inconsistent_lineage: {
    min: number;
    avg: number;
    max: number;
  };
  kvolatile?: {
    last_version: number;
    points: Array<{
      k: number;
      count: number;
      cdf_dead: number;
      rvolatile: number;
    }>;
  };
}

export interface AnalysisConfig {
  repoUrl: string;
  analysisType: "first" | "specific" | "days";
  commitHash?: string;
  daysAgo?: string;
  commitCount?: string;
  includeLeaps: boolean;
  leapCount?: string;
  includeMerge: boolean;
  detectionTool: string;
}

export interface AnalysisRequest {
  user_settings: {
    repo_url?: string;
    local_path?: string;
    from_first_commit?: boolean;
    from_a_specific_commit?: string;
    days_pior?: number;
    merge_commit?: boolean;
    fixed_leaps?: number;
    clone_detector?: string;
    language?: string;
  };
}

export interface AnalysisStatus {
  status: "idle" | "running" | "completed" | "error";
  progress?: number;
  message?: string;
  current_commit?: string;
  total_commits?: number;
  processed_commits?: number;
}

export interface AnalysisResult {
  xml_data: string;
  metrics: MetricsData;
  genealogy: GenealogyData;
}
