import LineageGraph from "@/components/genealogy/LineageGraph";
import NodeDetailsPanel from "@/components/genealogy/NodeDetailsPanel";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ArrowLeft,
  BarChart3,
  GitBranch,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/services/api";
import type { GenealogyData, AnalysisStatus } from "@/types";

/** ---------------- XML -> GenealogyData adapter ---------------- */
type ParsedSource = { file: string; startline: number; endline: number; hash: string };
type ParsedClass = { nclones: number; sources: ParsedSource[] };
type ParsedVersion = {
  nr: string;
  hash: string;
  parent_hash: string;
  evolution: string;
  change: string;
  classes: ParsedClass[];
};
type ParsedLineage = { versions: ParsedVersion[] };

function parseXml(xmlStr: string): ParsedLineage[] {
  const doc = new DOMParser().parseFromString(xmlStr, "application/xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error(err.textContent || "XML parse error");

  const lineages: ParsedLineage[] = [];
  doc.querySelectorAll("lineage").forEach((lin) => {
    const versions: ParsedVersion[] = [];
    lin.querySelectorAll(":scope > version").forEach((ver) => {
      const classes: ParsedClass[] = [];
      ver.querySelectorAll(":scope > class").forEach((cls) => {
        const sources: ParsedSource[] = [];
        cls.querySelectorAll(":scope > source").forEach((src) => {
          sources.push({
            file: src.getAttribute("file") ?? "",
            startline: Number(src.getAttribute("startline") ?? "0"),
            endline: Number(src.getAttribute("endline") ?? "0"),
            hash: src.getAttribute("hash") ?? "",
          });
        });
        classes.push({
          nclones: Number(cls.getAttribute("nclones") ?? sources.length),
          sources,
        });
      });
      versions.push({
        nr: ver.getAttribute("nr") ?? "",
        hash: ver.getAttribute("hash") ?? "",
        parent_hash: ver.getAttribute("parent_hash") ?? "",
        evolution: ver.getAttribute("evolution") ?? "",
        change: ver.getAttribute("change") ?? "",
        classes,
      });
    });
    lineages.push({ versions });
  });

  return lineages;
}

/** Mapeia o XML parseado para o formato esperado pelo grafo.
 *  Se o seu GenealogyData tiver outra estrutura, ajuste aqui.
 */
function toGenealogyData(parsed: ParsedLineage[]): GenealogyData {
  return {
    lineages: parsed.map((lin, idx) => ({
      id: idx,
      // nodes: cada versão vira um nó no grafo
      nodes: lin.versions.map((v, i) => ({
        id: `${v.hash}-${v.nr}-${i}`,
        // campos úteis para Tooltips / painel lateral
        hash: v.hash,
        parentHash: v.parent_hash || null,
        version: Number(v.nr),
        evolution: v.evolution,
        change: v.change,
        classes: v.classes,
        // campos comuns em grafos: label e parent
        label: `v${v.nr} • ${v.evolution || "None"}`,
        parent: v.parent_hash || null,
      })),
    })),
  } as unknown as GenealogyData;
}
/** ------------------------------------------------------------- */

const Visualize = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { taskId, config, xml: xmlFromState } = (location.state || {}) as {
    taskId?: string;
    config?: any;
    xml?: string;
  };

  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("0");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [genealogyData, setGenealogyData] = useState<GenealogyData | null>(null);
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Suporte a XML direto (via state ou sessionStorage, p/ sobreviver a refresh)
  const [xml, setXml] = useState<string | null>(xmlFromState ?? null);
  useEffect(() => {
    if (xmlFromState) {
      sessionStorage.setItem("omniccg_xml", xmlFromState);
      setXml(xmlFromState);
    } else if (!taskId) {
      const cached = sessionStorage.getItem("omniccg_xml");
      if (cached) setXml(cached);
    }
  }, [xmlFromState, taskId]);

  useEffect(() => {
    // Caminho 1: temos taskId => faz polling como antes
    if (taskId && config) {
      let pollInterval: NodeJS.Timeout;
      const checkStatus = async () => {
        try {
          const statusData = await api.getAnalysisStatus(taskId);
          setStatus(statusData);

          if (statusData.status === "completed") {
            const results = await api.getAnalysisResults(taskId);
            setGenealogyData(results.genealogy);
            setIsLoading(false);
            clearInterval(pollInterval);
          } else if (statusData.status === "error") {
            setError(statusData.message || "Analysis failed");
            setIsLoading(false);
            clearInterval(pollInterval);
            toast.error("Analysis failed: " + statusData.message);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load analysis");
          setIsLoading(false);
          clearInterval(pollInterval);
          toast.error("Failed to load analysis");
        }
      };

      setIsLoading(true);
      checkStatus();
      pollInterval = setInterval(checkStatus, 2000);
      return () => pollInterval && clearInterval(pollInterval);
    }

    // Caminho 2: sem taskId, mas com XML => parseia e mostra
    if (!taskId && xml) {
      try {
        setIsLoading(true);
        const parsed = parseXml(xml);
        const mapped = toGenealogyData(parsed);
        setGenealogyData(mapped);
        setIsLoading(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to parse XML");
        setIsLoading(false);
      }
      return;
    }

    // Caminho 3: sem taskId e sem XML => volta
    if (!taskId && !xml) {
      toast.error("No analysis result found");
      navigate("/");
    }
  }, [taskId, config, xml, navigate]);

  const handleNodeClick = (nodeData: any) => {
    setSelectedNode(nodeData);
    setSidebarOpen(true);
  };

  const handleCloseSidebar = () => {
    setSidebarOpen(false);
    setSelectedNode(null);
  };

  const totalVersions = useMemo(() => {
    if (!genealogyData) return 0;
    return genealogyData.lineages.reduce(
      (acc, lineage) => acc + lineage.nodes.length,
      0
    );
  }, [genealogyData]);

  // Enquanto decide (polling ou parsing)
  if ((taskId && !genealogyData) || isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-accent/5 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
          <div>
            <h2 className="text-2xl font-bold mb-2">
              {taskId
                ? status?.status === "running"
                  ? "Analyzing Repository..."
                  : "Loading Results..."
                : "Parsing XML..."}
            </h2>
            <p className="text-muted-foreground">
              {taskId ? status?.message || "Please wait..." : "Preparing visualization"}
            </p>
            {taskId && status?.progress !== undefined && (
              <div className="mt-4">
                <div className="w-64 h-2 bg-muted rounded-full overflow-hidden mx-auto">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  {status.progress}% complete
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-accent/5 flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error}
            <div className="mt-4">
              <Button
                onClick={() =>
                  navigate("/configure", { state: { repoUrl: config?.repoUrl } })
                }
              >
                Try Again
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!genealogyData) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background  to-accent/5">
      <div className="container mx-auto px-4 py-6 h-screen flex flex-col">
        {/* Header */}
        <header className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <GitBranch className="w-8 h-8 text-primary" />
                <div>
                  <h1 className="text-3xl font-bold">
                    Code Clone Genealogy
                  </h1>
                  {config?.repoUrl && (
                    <p className="text-sm text-muted-foreground">{config.repoUrl}</p>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={async () => {
                  const repoUrl = config?.git_repository || config?.repoUrl;
                  if (!repoUrl) {
                    toast.error("Repository URL not available");
                    return;
                  }
                  try {
                    const metricsXml = await api.getMetricsXml(repoUrl);
                    navigate("/metrics", { 
                      state: { 
                        xml: metricsXml,
                        config,
                        repoUrl 
                      } 
                    });
                  } catch (error) {
                    toast.error("Failed to load metrics: " + (error instanceof Error ? error.message : "Unknown error"));
                  }
                }}
                variant="default"
                className="gap-2"
              >
                <BarChart3 className="w-4 h-4" />
                View Metrics
              </Button>
              <Button onClick={() => navigate("/")} variant="outline" className="gap-2">
                New Repository
              </Button>
            </div>
          </div>
        </header>

        {/* Graph Area */}
        <div className="flex-1 bg-card border border-border rounded-xl shadow-[var(--shadow-card)] overflow-hidden">
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="h-full flex flex-col"
          >
            <div className="border-b border-border px-6 pt-4 overflow-x-auto">
              <TabsList className="w-full justify-start inline-flex min-w-max">
                {genealogyData.lineages.map((lineage) => (
                  <TabsTrigger key={lineage.id} value={lineage.id.toString()}>
                    Lineage {String.fromCharCode(65 + lineage.id)}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            {genealogyData.lineages.map((lineage) => (
              <TabsContent
                key={lineage.id}
                value={lineage.id.toString()}
                className="flex-1 m-0 p-6 data-[state=active]:flex"
              >
                <LineageGraph
                  lineageData={lineage.nodes}
                  lineageIndex={lineage.id}
                  onNodeClick={handleNodeClick}
                />
              </TabsContent>
            ))}
          </Tabs>
        </div>
      </div>

      {/* Details Panel */}
      <NodeDetailsPanel
        isOpen={sidebarOpen}
        onClose={handleCloseSidebar}
        nodeData={selectedNode}
        repoUrl={config?.git_repository || config?.repoUrl}
      />
    </div>
  );
};

export default Visualize;
