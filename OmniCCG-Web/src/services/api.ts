import type {
  AnalysisConfig,
  AnalysisRequest,
  AnalysisStatus,
  AnalysisResult,
  GenealogyData,
  MetricsData,
  Lineage,
  LineageNode,
  CloneSource,
} from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

/** ---------------- XML -> GenealogyData ---------------- */
const parseXMLToGenealogyData = (xmlString: string): GenealogyData => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlString, "text/xml");

  const lineages: Lineage[] = [];
  const lineageElements = xmlDoc.getElementsByTagName("lineage");

  for (let i = 0; i < lineageElements.length; i++) {
    const lineageElement = lineageElements[i];
    const versionElements = lineageElement.getElementsByTagName("version");
    const nodes: LineageNode[] = [];

    for (let j = 0; j < versionElements.length; j++) {
      const versionElement = versionElements[j];

      // Coleta TODAS as <class> sob a <version>
      const classElements = versionElement.getElementsByTagName("class");
      const allClasses: { nclones: number; sources: CloneSource[] }[] = [];

      // Também preservamos a primeira <class> para compat com o campo "sources" existente
      let firstClassSources: CloneSource[] = [];

      for (let c = 0; c < classElements.length; c++) {
        const cls = classElements[c];
        const sourceElements = cls.getElementsByTagName("source");

        const sources: CloneSource[] = [];
        for (let k = 0; k < sourceElements.length; k++) {
          const sourceElement = sourceElements[k];
          sources.push({
            file: sourceElement.getAttribute("file") || "",
            startline: parseInt(sourceElement.getAttribute("startline") || "0"),
            endline: parseInt(sourceElement.getAttribute("endline") || "0"),
            function: sourceElement.getAttribute("function") || undefined,
            hash: parseInt(sourceElement.getAttribute("hash") || "0"),
          });
        }

        if (c === 0) {
          firstClassSources = sources;
        }

        const nclonesAttr = cls.getAttribute("nclones");
        allClasses.push({
          nclones: nclonesAttr ? parseInt(nclonesAttr) : sources.length,
          sources,
        });
      }

      const node: LineageNode = {
        version: versionElement.getAttribute("nr") || "",
        hash: versionElement.getAttribute("hash") || "",
        evolution: versionElement.getAttribute("evolution") || "None",
        change: versionElement.getAttribute("change") || "None",
        parent_hash: versionElement.getAttribute("parent_hash") || undefined,

        // Compat: mantém "sources" igual ao comportamento anterior (primeira <class>)
        sources: firstClassSources,
      };

      // Compat adicional: preenche campos soltos com o primeiro source
      if (firstClassSources.length > 0) {
        node.file = firstClassSources[0].file;
        node.startline = firstClassSources[0].startline;
        node.endline = firstClassSources[0].endline;
        node.function = firstClassSources[0].function;
      }

      // NOVO: anexa todas as classes para telas que usam node.classes
      (node as any).classes = allClasses;

      nodes.push(node);
    }

    lineages.push({
      id: i,
      nodes,
    });
  }

  return { lineages };
};

/** ---------------- API ---------------- */
export const api = {
  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error("Backend is not available");
    }
    return response.json();
  },

  // Start analysis
  async startAnalysis(config: AnalysisConfig): Promise<{ task_id: string }> {
    const request: AnalysisRequest = {
      user_settings: {
        repo_url: config.repoUrl,
        from_first_commit: config.analysisType === "first",
        from_a_specific_commit:
          config.analysisType === "specific" ? config.commitHash : undefined,
        days_pior:
          config.analysisType === "days"
            ? parseInt(config.daysAgo || "0")
            : undefined,
        merge_commit: config.includeMerge,
        fixed_leaps: config.includeLeaps
          ? parseInt(config.leapCount || "0")
          : undefined,
        clone_detector: config.detectionTool,
        language: "java", // default
      },
    };

    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) throw new Error("Failed to start analysis");
    return response.json();
  },

  // Get analysis status
  async getAnalysisStatus(taskId: string): Promise<AnalysisStatus> {
    const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
    if (!response.ok) throw new Error("Failed to get analysis status");
    return response.json();
  },

  // Get analysis results
  async getAnalysisResults(taskId: string): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/results/${taskId}`);
    if (!response.ok) throw new Error("Failed to get analysis results");

    const data = await response.json();
    return {
      xml_data: data.xml_data,
      metrics: data.metrics,
      genealogy: parseXMLToGenealogyData(data.xml_data),
    };
  },

  // Get genealogy data
  async getGenealogyData(taskId: string): Promise<GenealogyData> {
    const result = await this.getAnalysisResults(taskId);
    return result.genealogy;
  },

  // Get metrics data
  async getMetrics(taskId: string): Promise<MetricsData> {
    const result = await this.getAnalysisResults(taskId);
    return result.metrics;
  },

  /** -------- NEW: request real code snippets from backend -------- */
  async getSnippets(payload: {
    git_url: string;
    commit: string;
    sources: { file: string; startline: number; endline: number }[];
  }): Promise<{
    repo_dir: string;
    commit: string;
    count: number;
    snippets: Array<{
      file: string;
      startline: number;
      endline: number;
      content?: string;
      error?: string;
    }>;
  }> {
    const res = await fetch(`${API_BASE_URL}/get_code_snippets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Snippets request failed (${res.status})`);
    }
    return res.json();
  },

  /**
   * Helper: build and send a /snippets request from a LineageNode.
   * It uses node.hash and gathers ALL sources from node.classes (if available).
   */
  async requestSnippetsForNode(
    repoUrl: string,
    node: LineageNode & { classes?: { sources: CloneSource[] }[] }
  ) {
    const commit = String(node.hash || "");
    const classes = Array.isArray(node.classes) ? node.classes : [];

    // Fallback: if no classes array, use node.sources (first-class compat)
    const allSources =
      classes.flatMap((c) => c.sources || []) ||
      (Array.isArray(node.sources) ? node.sources : []);

    const sources = allSources
      .filter((s) => s?.file && s.startline && s.endline)
      .map((s) => ({
        file: s.file,
        startline: Number(s.startline),
        endline: Number(s.endline),
      }));

    if (!repoUrl || !commit || sources.length === 0) {
      throw new Error("Missing repoUrl, commit, or sources for snippet request.");
    }

    return this.getSnippets({ git_url: repoUrl, commit, sources });
  },

  /** -------- Get Metrics XML -------- */
  async getMetricsXml(git_url: string): Promise<string> {
    const res = await fetch(`${API_BASE_URL}/get_metrics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ git_url }),
    });
    if (!res.ok) {
      throw new Error(`Metrics request failed (${res.status})`);
    }
    return res.text(); // Retorna XML como texto
  },
};
