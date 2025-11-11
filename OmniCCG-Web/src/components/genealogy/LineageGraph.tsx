import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";

cytoscape.use(dagre);

interface LineageNode {
  version: string;
  hash: string;
  evolution: string;
  change: string;
  file?: string;
  startline?: number;
  endline?: number;
  function?: string;
  sources?: any[];
}

interface LineageGraphProps {
  lineageData: LineageNode[];
  lineageIndex: number;
  onNodeClick: (nodeData: any) => void;
  selectedVersion?: string;
}

const LineageGraph = ({ lineageData, lineageIndex, onNodeClick, selectedVersion }: LineageGraphProps) => {
  const cyRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const savedPositionRef = useRef<{ zoom: number; pan: { x: number; y: number } } | null>(null);

  useEffect(() => {
    if (!lineageData || lineageData.length === 0 || !containerRef.current) return;

    // Save current position and zoom before recreating
    if (cyRef.current) {
      savedPositionRef.current = {
        zoom: cyRef.current.zoom(),
        pan: cyRef.current.pan(),
      };
    }

    const elements: any[] = [];

    // Group by version
    const versionGroups: Record<string, LineageNode[]> = {};
    lineageData.forEach((node) => {
      if (!versionGroups[node.version]) {
        versionGroups[node.version] = [];
      }
      versionGroups[node.version].push(node);
    });

    // Create nodes
    Object.keys(versionGroups).forEach((version) => {
      const versionNodes = versionGroups[version];
      const representativeNode = versionNodes[0];

      elements.push({
        data: {
          id: `v${version}_l${lineageIndex}`,
          label: `V${version}\n${representativeNode.hash?.substring(0, 7) || ""}`,
          version: version,
          hash: representativeNode.hash,
          evolution: representativeNode.evolution,
          change: representativeNode.change,
          nodes: versionNodes,
          type: "version",
        },
      });
    });

    // Create edges
    const sortedVersions = Object.keys(versionGroups).sort((a, b) => parseInt(a) - parseInt(b));
    for (let i = 1; i < sortedVersions.length; i++) {
      const fromVersion = sortedVersions[i - 1];
      const toVersion = sortedVersions[i];

      elements.push({
        data: {
          id: `edge_v${fromVersion}_to_v${toVersion}_l${lineageIndex}`,
          source: `v${fromVersion}_l${lineageIndex}`,
          target: `v${toVersion}_l${lineageIndex}`,
          type: "evolution",
        },
      });
    }

    // Destroy previous graph
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Create new graph
    const cy = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "hsl(174 100% 40%)",
            "border-color": "hsl(174 100% 35%)",
            "border-width": "4px",
            color: "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "12px",
            "font-weight": "bold",
            width: "90px",
            height: "90px",
            shape: "ellipse",
            label: "data(label)",
            "text-wrap": "wrap",
            "text-max-width": "70px",
          },
        },
        {
          selector: "node[evolution = 'Add']",
          style: {
            "background-color": "hsl(142 76% 45%)",
            "border-color": "hsl(142 76% 35%)",
          },
        },
        {
          selector: "node[evolution = 'Subtraction']",
          style: {
            "background-color": "hsl(0 84% 60%)",
            "border-color": "hsl(0 84% 50%)",
          },
        },
        {
          selector: "node[change = 'Same']",
          style: {
            "background-color": "hsl(199 89% 55%)",
            "border-color": "hsl(199 89% 45%)",
          },
        },
        {
          selector: "node[evolution = 'None']",
          style: {
            "background-color": "hsl(174 100% 40%)",
            "border-color": "hsl(174 100% 35%)",
          },
        },
        {
          selector: "edge",
          style: {
            width: "3px",
            "line-color": "hsl(var(--muted-foreground))",
            "target-arrow-color": "hsl(var(--muted-foreground))",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": "5px",
            "border-color": "hsl(var(--accent))",
            "overlay-opacity": 0.2,
            "overlay-color": "hsl(var(--accent))",
          },
        },
      ] as any,
      layout: {
        name: "dagre",
        rankDir: "LR",
        nodeSep: 100,
        rankSep: 150,
        spacingFactor: 1.5,
      } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    cy.on("zoom", () => {
      setZoomLevel(cy.zoom());
    });

    // Restore saved position and zoom, or fit if first time
    if (savedPositionRef.current) {
      cy.zoom(savedPositionRef.current.zoom);
      cy.pan(savedPositionRef.current.pan);
    } else {
      cy.fit(undefined, 50);
    }

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [lineageData, lineageIndex]);

  // Separate effect for node click handler to avoid recreating the graph
  useEffect(() => {
    if (!cyRef.current) return;

    const handleNodeClick = (evt: any) => {
      const node = evt.target;
      onNodeClick(node.data());
    };

    cyRef.current.on("tap", "node", handleNodeClick);

    return () => {
      if (cyRef.current) {
        cyRef.current.off("tap", "node", handleNodeClick);
      }
    };
  }, [onNodeClick]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 50);
    }
  };

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full bg-card rounded-lg border border-border" />
      
      {/* Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <Button
          size="icon"
          variant="secondary"
          onClick={handleZoomIn}
          className="shadow-lg"
        >
          <ZoomIn className="w-4 h-4" />
        </Button>
        <Button
          size="icon"
          variant="secondary"
          onClick={handleZoomOut}
          className="shadow-lg"
        >
          <ZoomOut className="w-4 h-4" />
        </Button>
        <Button
          size="icon"
          variant="secondary"
          onClick={handleFit}
          className="shadow-lg"
        >
          <Maximize2 className="w-4 h-4" />
        </Button>
      </div>

      {/* Zoom indicator */}
      <div className="absolute bottom-4 left-4 bg-secondary text-secondary-foreground px-3 py-1 rounded-md text-sm font-medium shadow-lg">
        {Math.round(zoomLevel * 100)}%
      </div>
    </div>
  );
};

export default LineageGraph;
