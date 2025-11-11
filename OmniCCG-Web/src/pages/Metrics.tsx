import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ArrowLeft,
  Activity,
  TrendingUp,
  TrendingDown,
  GitBranch,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { MetricsData } from "@/types";

/** Parse metrics XML to MetricsData */
function parseMetricsXml(xmlStr: string): MetricsData {
  const doc = new DOMParser().parseFromString(xmlStr, "application/xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error(err.textContent || "XML parse error");

  const metricsEl = doc.querySelector("results") || doc.querySelector("metrics");
  if (!metricsEl) throw new Error("No <results> or <metrics> element found");

  const getText = (selector: string): string => 
    metricsEl.querySelector(selector)?.textContent || "0";
  
  const getNumber = (selector: string): number => 
    parseFloat(getText(selector)) || 0;

  // Parse clone_density
  const cloneDensityEl = metricsEl.querySelector("clone_density");
  const clone_density = cloneDensityEl ? {
    points: Array.from(cloneDensityEl.querySelectorAll("point")).map(point => ({
      version: parseFloat(point.querySelector("version")?.textContent || "0"),
      clones_density: parseFloat(point.querySelector("clones_density")?.textContent || "0"),
    })),
    summary: {
      versions_count_present: parseFloat(cloneDensityEl.querySelector("summary > versions_count_present")?.textContent || "0"),
      avg_density_present: parseFloat(cloneDensityEl.querySelector("summary > avg_density_present")?.textContent || "0"),
      avg_density_full_range: parseFloat(cloneDensityEl.querySelector("summary > avg_density_full_range")?.textContent || "0"),
    }
  } : undefined;

  // Parse kvolatile
  const kvolatileEl = metricsEl.querySelector("kvolatile");
  const kvolatile = kvolatileEl ? {
    last_version: parseFloat(kvolatileEl.getAttribute("last_version") || "0"),
    points: Array.from(kvolatileEl.querySelectorAll("point")).map(point => ({
      k: parseFloat(point.getAttribute("k") || "0"),
      count: parseFloat(point.getAttribute("count") || "0"),
      cdf_dead: parseFloat(point.getAttribute("cdf_dead") || "0"),
      rvolatile: parseFloat(point.getAttribute("rvolatile") || "0"),
    })),
  } : undefined;

  return {
    clone_density,
    total_clone_lineages: getNumber("total_clone_lineages"),
    total_amount_of_versions: getNumber("total_amount_of_versions"),
    change_patterns_of_lineages: {
      consistent: getNumber("change_patterns_of_lineages > consistent"),
      stable: getNumber("change_patterns_of_lineages > stable") || getNumber("change_patterns_of_lineages > same"),
      inconsistent: getNumber("change_patterns_of_lineages > inconsistent"),
    },
    status_of_clone_lineages: {
      alive: {
        count: getNumber("status_of_clone_lineages > alive > count"),
        percentage: getNumber("status_of_clone_lineages > alive > percentage"),
      },
      dead: {
        count: getNumber("status_of_clone_lineages > dead > count"),
        percentage: getNumber("status_of_clone_lineages > dead > percentage"),
      },
    },
    length_of_dead_clone_lineages: {
      min: getNumber("length_of_dead_clone_lineages > min"),
      avg: getNumber("length_of_dead_clone_lineages > avg"),
      max: getNumber("length_of_dead_clone_lineages > max"),
    },
    evolution_pattern_of_versions: {
      add: getNumber("evolution_pattern_of_versions > add"),
      subtract: getNumber("evolution_pattern_of_versions > subtract"),
      same: getNumber("evolution_pattern_of_versions > same"),
    },
    change_pattern_of_versions: {
      consistent: getNumber("change_pattern_of_versions > consistent"),
      inconsistent: getNumber("change_pattern_of_versions > inconsistent"),
      same: getNumber("change_pattern_of_versions > same"),
    },
    consistent_changes_in_consistent_lineage: {
      min: getNumber("consistent_changes_in_consistent_lineage > min"),
      avg: getNumber("consistent_changes_in_consistent_lineage > avg"),
      max: getNumber("consistent_changes_in_consistent_lineage > max"),
    },
    consistent_changes_in_inconsistent_lineage: {
      min: getNumber("consistent_changes_in_inconsistent_lineage > min"),
      avg: getNumber("consistent_changes_in_inconsistent_lineage > avg"),
      max: getNumber("consistent_changes_in_inconsistent_lineage > max"),
    },
    inconsistent_changes_in_inconsistent_lineage: {
      min: getNumber("inconsistent_changes_in_inconsistent_lineage > min"),
      avg: getNumber("inconsistent_changes_in_inconsistent_lineage > avg"),
      max: getNumber("inconsistent_changes_in_inconsistent_lineage > max"),
    },
    kvolatile,
  };
}

const Metrics = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { taskId, config, xml: xmlFromState, repoUrl } = location.state || {};

  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [versionCommits, setVersionCommits] = useState<Map<number, string>>(new Map());

  // Suporte a XML direto (via state ou sessionStorage)
  const [xml, setXml] = useState<string | null>(xmlFromState ?? null);
  
  // Extrai commits da genealogia
  useEffect(() => {
    const genealogyXml = sessionStorage.getItem("omniccg_xml");
    if (genealogyXml) {
      try {
        const doc = new DOMParser().parseFromString(genealogyXml, "application/xml");
        const versions = doc.querySelectorAll("version");
        const commitMap = new Map<number, string>();
        
        versions.forEach((ver) => {
          const nr = ver.getAttribute("nr");
          const hash = ver.getAttribute("hash");
          if (nr && hash) {
            commitMap.set(parseInt(nr), hash);
          }
        });
        
        setVersionCommits(commitMap);
      } catch (e) {
        console.error("Failed to parse genealogy XML for commits", e);
      }
    }
  }, []);
  
  useEffect(() => {
    if (xmlFromState) {
      sessionStorage.setItem("omniccg_metrics_xml", xmlFromState);
      setXml(xmlFromState);
    } else {
      const cached = sessionStorage.getItem("omniccg_metrics_xml");
      if (cached) setXml(cached);
    }
  }, [xmlFromState]);

  useEffect(() => {
    // Caminho 1: temos taskId => usa API antiga
    if (taskId && config) {
      const loadMetrics = async () => {
        try {
          const metricsData = await api.getMetrics(taskId);
          setMetrics(metricsData);
          setIsLoading(false);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load metrics");
          setIsLoading(false);
          toast.error("Failed to load metrics");
        }
      };
      loadMetrics();
      return;
    }

    // Caminho 2: temos XML => parseia localmente
    if (xml) {
      try {
        setIsLoading(true);
        const parsed = parseMetricsXml(xml);
        setMetrics(parsed);
        setIsLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to parse metrics XML");
        setIsLoading(false);
        toast.error("Failed to parse metrics");
      }
      return;
    }

    // Caminho 3: sem dados
    if (!taskId && !xml) {
      toast.error("No metrics data found");
      navigate("/");
    }
  }, [taskId, config, xml, navigate]);

  if (!taskId && !xml && !config) return null;

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-accent/5 flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error}
            <div className="mt-4">
              <Button
                onClick={() => {
                  const genealogyXml = sessionStorage.getItem("omniccg_xml");
                  if (taskId) {
                    navigate("/visualize", { state: { taskId, config } });
                  } else if (genealogyXml) {
                    navigate("/visualize", { state: { xml: genealogyXml, config } });
                  } else {
                    navigate("/");
                  }
                }}
              >
                Back to Genealogy
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading || !metrics) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-accent/5 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
          <h2 className="text-2xl font-bold">Loading Metrics...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-accent/5">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <header className="mb-6">
          <Button
            variant="ghost"
            onClick={() => {
              const genealogyXml = sessionStorage.getItem("omniccg_xml");
              if (taskId) {
                navigate("/visualize", { state: { taskId, config } });
              } else if (genealogyXml) {
                navigate("/visualize", { state: { xml: genealogyXml, config } });
              } else {
                navigate("/");
              }
            }}
            className="mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Genealogy
          </Button>
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold">Clone Metrics</h1>
              <p className="text-sm text-muted-foreground">
                {repoUrl || config?.repoUrl || config?.git_repository || "Repository Metrics"}
              </p>
            </div>
          </div>
        </header>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Total Clone Lineages */}
          <Card className="shadow-[var(--shadow-card)] border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <GitBranch className="w-5 h-5 text-primary" />
                Total Clone Lineages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-primary">
                {metrics.total_clone_lineages}
              </p>
            </CardContent>
          </Card>

           {/* Change Patterns */}
          <Card className="shadow-[var(--shadow-card)] border-border md:col-span-2 lg:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <AlertCircle className="w-5 h-5 text-accent" />
                Change Patterns
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Same</span>
                <span className="font-bold text-info">
                  {metrics.change_patterns_of_lineages.stable.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Consistent</span>
                <span className="font-bold text-success">
                  {metrics.change_patterns_of_lineages.consistent.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Inconsistent</span>
                <span className="font-bold text-destructive">
                  {metrics.change_patterns_of_lineages.inconsistent.toFixed(2)}%
                </span>
              </div>
              <div className="mt-4">
                <div className="w-full h-3 bg-muted rounded-full overflow-hidden flex">
                  <div
                    className="bg-info h-full"
                    style={{
                      width: `${metrics.change_patterns_of_lineages.stable}%`,
                    }}
                  />
                  <div
                    className="bg-success h-full"
                    style={{
                      width: `${metrics.change_patterns_of_lineages.consistent}%`,
                    }}
                  />
                  <div
                    className="bg-destructive h-full"
                    style={{
                      width: `${metrics.change_patterns_of_lineages.inconsistent}%`,
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

           {/* Evolution Pattern */}
          <Card className="shadow-[var(--shadow-card)] border-border md:col-span-2 lg:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="w-5 h-5 text-primary" />
                Evolution Pattern
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
               {metrics.evolution_pattern_of_versions.same !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Same</span>
                  <span className="font-bold text-info">
                    {metrics.evolution_pattern_of_versions.same.toFixed(2)}%
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Add</span>
                <span className="font-bold text-success">
                  {metrics.evolution_pattern_of_versions.add.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Subtract</span>
                <span className="font-bold text-destructive">
                  {metrics.evolution_pattern_of_versions.subtract.toFixed(2)}%
                </span>
              </div>
              <div className="mt-4">
                <div className="w-full h-3 bg-muted rounded-full overflow-hidden flex">
                  <div
                    className="bg-success h-full"
                    style={{
                      width: `${metrics.evolution_pattern_of_versions.add}%`,
                    }}
                  />
                  {metrics.evolution_pattern_of_versions.same !== undefined && (
                    <div
                      className="bg-info h-full"
                      style={{
                        width: `${metrics.evolution_pattern_of_versions.same}%`,
                      }}
                    />
                  )}
                  <div
                    className="bg-destructive h-full"
                    style={{
                      width: `${metrics.evolution_pattern_of_versions.subtract}%`,
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

         

          {/* Status of Clone Lineages */}
          <Card className="shadow-[var(--shadow-card)] border-border md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Activity className="w-5 h-5 text-info" />
                Status of Clone Lineages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-success" />
                    <span className="text-sm font-medium text-muted-foreground">
                      Alive
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-success">
                    {metrics.status_of_clone_lineages.alive.count}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {metrics.status_of_clone_lineages.alive.percentage.toFixed(
                      2
                    )}
                    % of total
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-5 h-5 text-destructive" />
                    <span className="text-sm font-medium text-muted-foreground">
                      Dead
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-destructive">
                    {metrics.status_of_clone_lineages.dead.count}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {metrics.status_of_clone_lineages.dead.percentage.toFixed(
                      2
                    )}
                    % of total
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Length of Dead Clone Lineages */}
          <Card className="shadow-[var(--shadow-card)] border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingDown className="w-5 h-5 text-destructive" />
                Dead Lineage Length
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Minimum</span>
                <span className="font-bold">
                  {metrics.length_of_dead_clone_lineages.min}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Average</span>
                <span className="font-bold">
                  {metrics.length_of_dead_clone_lineages.avg.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Maximum</span>
                <span className="font-bold">
                  {metrics.length_of_dead_clone_lineages.max}
                </span>
              </div>
            </CardContent>
          </Card>


          {/* Clone Density Chart */}
          {metrics.clone_density && (
            <Card className="shadow-[var(--shadow-card)] border-border md:col-span-2 lg:col-span-3">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="w-5 h-5 text-primary" />
                  Clone Density Over Versions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Versions Analyzed</span>
                      <span className="text-2xl font-bold">{metrics.clone_density.summary.versions_count_present}</span>
                    </div>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Avg Density (Present)</span>
                      <span className="text-2xl font-bold">{metrics.clone_density.summary.avg_density_present.toFixed(2)}%</span>
                    </div>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Avg Density (Full Range)</span>
                      <span className="text-2xl font-bold">{metrics.clone_density.summary.avg_density_full_range.toFixed(2)}%</span>
                    </div>
                  </div>
                  <div className="relative h-64 bg-muted/10 rounded-lg p-4">
                    <div className="h-full flex items-end justify-around gap-2">
                      {metrics.clone_density.points.map((point, idx) => {
                        const maxDensity = Math.max(...metrics.clone_density!.points.map(p => p.clones_density));
                        const heightPercent = maxDensity > 0 ? (point.clones_density / maxDensity) * 90 : 0;
                        const commitHash = versionCommits.get(point.version);
                        
                        return (
                          <div key={idx} className="flex flex-col items-center flex-1 max-w-[80px]">
                            <div className="w-full flex flex-col items-center justify-end" style={{ height: '200px' }}>
                              <div 
                                className="w-full bg-primary rounded-t transition-all hover:bg-primary/80 cursor-pointer relative group"
                                style={{ 
                                  height: `${heightPercent}%`,
                                  minHeight: point.clones_density > 0 ? '4px' : '0px'
                                }}
                                title={`Version ${point.version}${commitHash ? `\nCommit: ${commitHash}` : ''}\nDensity: ${point.clones_density.toFixed(2)}%`}
                              >
                                <span className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                  {point.clones_density.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <span className="text-xs text-muted-foreground mt-2 font-medium">V{point.version}</span>
                            {commitHash && (
                              <span className="text-xs font-mono text-muted-foreground/70" title={commitHash}>
                                {commitHash.substring(0, 7)}
                              </span>
                            )}
                            <span className="text-xs font-bold text-primary">{point.clones_density.toFixed(1)}%</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* KVolatile Chart */}
          {metrics.kvolatile && (
            <Card className="shadow-[var(--shadow-card)] border-border md:col-span-2 lg:col-span-3">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingDown className="w-5 h-5 text-warning" />
                  K-Volatile Analysis: Clone Survival Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Explanation */}
                  <div className="bg-muted/30 p-4 rounded-lg border border-border">
                    <p className="text-sm text-muted-foreground">
                      <strong>K-Volatile</strong> refers to dead clone genealogies with age ≤ k. 
                      The chart below shows the <strong>cumulative distribution function</strong> (CDF) of clones that did not survive, 
                      allowing analysis of how long clones manage to survive before being removed.
                    </p>
                  </div>

                  {/* Summary metrics */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Last Version Analyzed</span>
                      <span className="text-2xl font-bold">{metrics.kvolatile.last_version}</span>
                    </div>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Total Dead Genealogies</span>
                      <span className="text-2xl font-bold">
                        {metrics.kvolatile.points[metrics.kvolatile.points.length - 1]?.count || 0}
                      </span>
                    </div>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <span className="text-xs text-muted-foreground block mb-1">Maximum Age Observed</span>
                      <span className="text-2xl font-bold">
                        {metrics.kvolatile.points[metrics.kvolatile.points.length - 1]?.k || 0}
                      </span>
                    </div>
                  </div>

                  {/* CDF curve chart */}
                  <div className="bg-muted/10 rounded-lg p-6 space-y-4">
                    {/* Y-axis label */}
                    <div className="text-xs font-medium text-muted-foreground text-center">
                      % Dead Clones (CDF)
                    </div>
                    
                    {/* Chart container */}
                    <div className="relative" style={{ height: '400px' }}>
                      {/* Y-axis with grid */}
                      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between w-14 pr-2">
                        {[100, 75, 50, 25, 0].map((value) => (
                          <div key={value} className="text-xs text-right text-muted-foreground">
                            {value}%
                          </div>
                        ))}
                      </div>

                      {/* Grid lines and SVG chart */}
                      <div className="absolute left-14 right-0 top-0 bottom-0">
                        {/* Horizontal grid lines */}
                        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                          {[0, 1, 2, 3, 4].map((idx) => (
                            <div key={idx} className="w-full border-t border-dashed border-border/30" />
                          ))}
                        </div>

                        {/* SVG Chart */}
                        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                          <defs>
                            <linearGradient id="cdfGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                              <stop offset="0%" style={{ stopColor: 'hsl(var(--destructive))', stopOpacity: 0.3 }} />
                              <stop offset="100%" style={{ stopColor: 'hsl(var(--destructive))', stopOpacity: 0.05 }} />
                            </linearGradient>
                          </defs>
                          
                          {(() => {
                            const maxK = Math.max(...metrics.kvolatile!.points.map(p => p.k));
                            
                            // Build points array for the curve
                            const points = metrics.kvolatile!.points.map(point => {
                              const x = (point.k / maxK) * 100;
                              const y = (1 - point.cdf_dead) * 100; // Invert Y (0 at bottom, 100 at top)
                              return { x, y, ...point };
                            });

                            const pathPoints = points.map(p => `${p.x},${p.y}`).join(' ');
                            const areaPoints = `0,100 ${pathPoints} 100,100`;

                            return (
                              <>
                                {/* Area under curve */}
                                <polygon
                                  points={areaPoints}
                                  fill="url(#cdfGradient)"
                                />
                                
                                {/* Curve line */}
                                <polyline
                                  points={pathPoints}
                                  fill="none"
                                  stroke="hsl(var(--destructive))"
                                  strokeWidth="0.8"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  vectorEffect="non-scaling-stroke"
                                />
                                
                                {/* Data points */}
                                {points.map((point, idx) => (
                                  <circle
                                    key={idx}
                                    cx={point.x}
                                    cy={point.y}
                                    r="1.5"
                                    fill="hsl(var(--destructive))"
                                    stroke="hsl(var(--background))"
                                    strokeWidth="0.3"
                                    className="cursor-pointer hover:r-3 transition-all"
                                    vectorEffect="non-scaling-stroke"
                                  >
                                    <title>
                                      Age k={point.k}: {(point.cdf_dead * 100).toFixed(1)}% of clones died (Total: {point.count})
                                    </title>
                                  </circle>
                                ))}
                              </>
                            );
                          })()}
                        </svg>
                      </div>
                    </div>

                    {/* X-axis label and ticks */}
                    <div className="space-y-2">
                      <div className="pl-14 flex justify-between items-center">
                        {metrics.kvolatile.points
                          .filter((_, idx) => {
                            const total = metrics.kvolatile!.points.length;
                            if (total <= 10) return true; 
                            const step = Math.ceil(total / 7);
                            return idx % step === 0 || idx === total - 1;
                          })
                          .map((point) => (
                            <div key={point.k} className="text-xs text-muted-foreground font-mono">
                              {point.k}
                            </div>
                          ))}
                      </div>
                      <div className="text-xs font-medium text-muted-foreground text-center">
                        Age (k)
                      </div>
                    </div>
                  </div>

                  {/* Interpretation */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-info/10 p-4 rounded-lg border border-info/20">
                      <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Interpretation
                      </h4>
                      <ul className="text-sm space-y-1 text-muted-foreground">
                        <li>• <strong>Steep curve at start:</strong> Many clones die early</li>
                        <li>• <strong>Smooth curve after:</strong> Older clones are more stable</li>
                        <li>• <strong>Plateau:</strong> Few clones survive to advanced ages</li>
                      </ul>
                    </div>
                     
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default Metrics;
