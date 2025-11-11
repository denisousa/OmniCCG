import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  ChevronDown,
  Code2,
  FileCode,
  GitCommit,
  Hash,
  Info,
  TrendingUp,
  X,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/services/api";

import CodeSnippetModal from "./CodeSnippetModal";

interface NodeDetailsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  nodeData: any;
  repoUrl?: string;
}

const NodeDetailsPanel = ({
  isOpen,
  onClose,
  nodeData,
  repoUrl,
}: NodeDetailsPanelProps) => {
  const [expandedFiles, setExpandedFiles] = useState<Set<number>>(new Set());
  const [modalOpen, setModalOpen] = useState(false);
  const [activeSnippetFile, setActiveSnippetFile] = useState<string>("");
  const [snippets, setSnippets] = useState<any[]>([]);
  const [isLoadingSnippets, setIsLoadingSnippets] = useState(false);

  if (!isOpen || !nodeData) return null;

  const toggleFile = (index: number) => {
    const newExpanded = new Set(expandedFiles);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedFiles(newExpanded);
  };

  const handleShowSnippet = async (file: string, source: any) => {
    // Extrai o node real (pode estar em nodeData.nodes[0])
    const actualNode = (nodeData.nodes && nodeData.nodes[0]) || nodeData;
    const commitHash = actualNode.hash || nodeData.hash;

    if (!repoUrl || !commitHash) {
      toast.error("Repository URL or commit hash not available");
      console.error("Missing data:", { repoUrl, hash: commitHash, nodeData, actualNode });
      return;
    }

    setIsLoadingSnippets(true);
    try {
      // Remove prefixos comuns do path (Unix e Windows)
      let cleanFile = source.file;
      
      // Remove path absoluto do Windows (ex: C:\Users\...)
      cleanFile = cleanFile.replace(/^[A-Z]:\\.*\\dataset\\production\\/, '');
      cleanFile = cleanFile.replace(/^[A-Z]:\\.*\/dataset\/production\//, '');
      
      // Remove paths absolutos do Linux (ex: /home/user/...)
      cleanFile = cleanFile.replace(/^\/home\/[^\/]+\/.*\/dataset\/production\//, '');
      cleanFile = cleanFile.replace(/^\/root\/.*\/dataset\/production\//, '');
      cleanFile = cleanFile.replace(/^\/var\/.*\/dataset\/production\//, '');
      cleanFile = cleanFile.replace(/^\/opt\/.*\/dataset\/production\//, '');
      cleanFile = cleanFile.replace(/^\/tmp\/.*\/dataset\/production\//, '');
      
      // Remove paths Unix comuns relativos
      cleanFile = cleanFile.replace(/^workspace\/repo\//, '');
      cleanFile = cleanFile.replace(/^\/repo\//, '');
      cleanFile = cleanFile.replace(/^repo\//, '');
      cleanFile = cleanFile.replace(/^.*\/dataset\/production\//, '');
      
      // Busca apenas o snippet do arquivo clicado
      const response = await api.getSnippets({
        git_url: repoUrl,
        commit: commitHash,
        sources: [{
          file: cleanFile,
          startline: Number(source.startline),
          endline: Number(source.endline),
        }],
      });

      // Mapeia a resposta para o formato esperado pelo modal
      const loadedSnippets = response.snippets.map((snippet) => ({
        file: snippet.file,
        startline: snippet.startline,
        endline: snippet.endline,
        function: source.function,
        code: snippet.content || `// Error: ${snippet.error || "Code not available"}`,
      }));

      setSnippets(loadedSnippets);
      setActiveSnippetFile(loadedSnippets[0]?.file || file);
      setModalOpen(true);
      
      if (loadedSnippets[0]?.code.startsWith("// Error:")) {
        toast.error("Failed to load code snippet");
      } else {
        toast.success("Code snippet loaded successfully");
      }
    } catch (error) {
      console.error("Failed to load snippet:", error);
      toast.error(
        "Failed to load code snippet: " +
          (error instanceof Error ? error.message : "Unknown error")
      );
    } finally {
      setIsLoadingSnippets(false);
    }
  };

  const getEvolutionColor = (evolution: string) => {
    switch (evolution) {
      case "Add":
        return "bg-success/10 text-success border-success/20";
      case "Subtraction":
        return "bg-destructive/10 text-destructive border-destructive/20";
      case "Same":
        return "bg-info/10 text-info border-info/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  const getChangeColor = (change: string) => {
    switch (change) {
      case "Same":
        return "bg-success/10 text-success border-success/20";
      case "Consistent":
        return "bg-info/10 text-info border-info/20";
      case "Inconsistent":
        return "bg-destructive/10 text-destructive border-destructive/20";
      default:
        return "bg-muted/10 text-muted-foreground border-muted/20";
    }
  };

  // Extrai sources de nodeData.classes (estrutura do XML parseado)
  // nodeData.classes = Array<{ nclones: number, sources: Array<{file, startline, endline}> }>
  const sources = (() => {
    // O nodeData vem do Cytoscape e tem uma estrutura diferente
    // nodeData.nodes[0] contém os dados reais do XML
    let actualNode = nodeData;
    
    // Se nodeData tem nodes (vem do grafo Cytoscape), pega o primeiro node
    if (nodeData.nodes && Array.isArray(nodeData.nodes) && nodeData.nodes.length > 0) {
      actualNode = nodeData.nodes[0];
    }
    
    // Agora extrai sources do actualNode
    if (actualNode.classes && Array.isArray(actualNode.classes)) {
      const extractedSources = actualNode.classes.flatMap((cls: any) => cls.sources || []);
      return extractedSources;
    }
    
    // Fallback: se actualNode tem nodes (estrutura antiga)
    if (actualNode.nodes && Array.isArray(actualNode.nodes)) {
      return actualNode.nodes;
    }
    
    // Fallback final: trata actualNode como um source único
    if (actualNode.file || actualNode.startline) {
      return [actualNode];
    }
    
    return [];
  })();

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <GitCommit className="w-6 h-6 text-primary" />
            {nodeData.hash}
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="hover:bg-destructive/10 hover:text-destructive"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          This node represents version {nodeData.version}. Contains{" "}
          {sources.length} source{sources.length !== 1 ? "s" : ""}/class
          {sources.length !== 1 ? "es" : ""}.
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Version Information */}
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Info className="w-5 h-5 text-primary" />
              Version Information
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/50 p-3 rounded-lg border border-border">
                <div className="flex items-center gap-2 mb-1">
                  <Hash className="w-4 h-4 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">
                    Hash
                  </span>
                </div>
                <p className="text-sm font-mono break-all">
                  {nodeData.hash || "N/A"}
                </p>
              </div>
              <div className="bg-muted/50 p-3 rounded-lg border border-border">
                <span className="text-xs font-medium text-muted-foreground block mb-2">
                  Evolution
                </span>
                <Badge className={getEvolutionColor(nodeData.evolution)}>
                  {nodeData.evolution || "N/A"}
                </Badge>
              </div>
              <div className="bg-muted/50 p-3 rounded-lg border border-border">
                <span className="text-xs font-medium text-muted-foreground block mb-2">
                  Change
                </span>
                <Badge className={getChangeColor(nodeData.change)}>
                  {nodeData.change || "N/A"}
                </Badge>
              </div>
            </div>
          </div>

          <Separator />

          {/* Classes/Sources */}
          <div>
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <FileCode className="w-5 h-5 text-primary" />
              Code snippets ({sources.length})
            </h3>
            <div className="space-y-2">
              {sources.map((source: any, index: number) => (
                <Collapsible
                  key={index}
                  open={expandedFiles.has(index)}
                  onOpenChange={() => toggleFile(index)}
                >
                  <div className="bg-muted/50 rounded-lg border border-border overflow-hidden">
                    <CollapsibleTrigger className="w-full p-3 flex items-center justify-between hover:bg-muted/70 transition-colors">
                      <span className="text-sm font-mono text-left break-all flex-1">
                        {source.file?.split(/[\\/]/).pop()?.trim() ?? "N/A"}
                      </span>
                      <ChevronDown
                        className={`w-4 h-4 text-muted-foreground transition-transform ${
                          expandedFiles.has(index) ? "rotate-180" : ""
                        }`}
                      />
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="p-3 pt-0 space-y-3">
                        <Separator />
                        <div className="space-y-2 text-sm">
                          {source.function && (
                            <div>
                              <span className="text-xs font-medium text-muted-foreground">
                                Method:
                              </span>
                              <p className="font-mono text-xs mt-1">
                                {source.function}
                              </p>
                            </div>
                          )}
                          <div>
                            <span className="text-xs font-medium text-muted-foreground">
                              Lines:
                            </span>
                            <p className="text-xs mt-1">
                              {source.startline && source.endline
                                ? `${source.startline} - ${source.endline}`
                                : "N/A"}
                            </p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          className="w-full"
                          onClick={() => handleShowSnippet(source.file, source)}
                          disabled={isLoadingSnippets}
                        >
                          {isLoadingSnippets ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Code2 className="w-4 h-4 mr-2" />
                          )}
                          {isLoadingSnippets ? "Loading..." : "Show Code Snippet"}
                        </Button>
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              ))}
            </div>
          </div>

          <Separator />

        </div>
      </ScrollArea>

      <CodeSnippetModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        snippets={snippets}
        activeFile={activeSnippetFile}
      />
    </div>
  );
};

export default NodeDetailsPanel;
