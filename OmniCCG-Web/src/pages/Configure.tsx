import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowLeft, Settings } from "lucide-react";
import { Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { genericExamples, preliminaryExamples } from "@/lib/examplesData";
import { formatTime } from "@/lib/utils";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

// agora inclui "other"
type DetectionTool = "nicad" | "simian" | "other";
const API_BASE_URL = import.meta.env.VITE_API_URL;
const API_URL = API_BASE_URL + "/detect_clones";
const STOP_API_URL = API_BASE_URL + "/stop_detect_clones"; // ⬅ novo


// ---------- Loading Overlay (full-screen) ----------
const LoadingOverlay = ({
  text = "Running clone detection...",
  onCancel,
}: {
  text?: string;
  onCancel?: () => void;
}) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
    <div className="bg-card border border-border rounded-2xl p-8 shadow-xl flex flex-col items-center gap-4 w-[min(90vw,420px)]">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      <div className="text-sm text-muted-foreground text-center">{text}</div>
      {onCancel && (
        <Button variant="outline" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </div>
  </div>
);
// ---------------------------------------------------

const Configure = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const repoUrl: string = location.state?.repoUrl || "";

  const [analysisType, setAnalysisType] =
    useState<"first" | "specific" | "days">("first");
  const [commitHash, setCommitHash] = useState("");
  const [daysAgo, setDaysAgo] = useState("");
  const [includeLeaps, setIncludeLeaps] = useState(false);
  const [leapCount, setLeapCount] = useState("");
  const [includeMerge, setIncludeMerge] = useState(false);

  const [detectionTool, setDetectionTool] = useState<DetectionTool | "">("");
  // novo input para "Other"
  const [detectionApi, setDetectionApi] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validação
  const [errors, setErrors] = useState<{
    commitHash?: string;
    daysAgo?: string;
    tool?: string;
  }>({});

  // Para suportar cancelamento
  const [abortCtrl, setAbortCtrl] = useState<AbortController | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const nextErrors: typeof errors = {};

    // detector obrigatório
    if (!detectionTool) {
      nextErrors.tool = "Please select a clone detection tool";
    }

    // se for Other, o input detectionApi é obrigatório
    if (detectionTool === "other" && !detectionApi.trim()) {
      nextErrors.tool = "Please enter the clone detector API";
    }

    // bloco "Analyze the repository commits from:"
    if (analysisType === "specific") {
      if (!commitHash.trim()) {
        nextErrors.commitHash = "Enter a commit hash";
      }
    } else if (analysisType === "days") {
      const n = Number(daysAgo);
      if (!daysAgo || Number.isNaN(n) || n < 1) {
        nextErrors.daysAgo = "Enter a valid number of days (≥ 1)";
      }
    } else if (analysisType !== "first") {
      nextErrors.commitHash = "Select a valid analysis start option";
    }

    // leaps (quando marcado) precisa ser válido
    if (includeLeaps) {
      const leaps = Number(leapCount);
      if (!leapCount || Number.isNaN(leaps) || leaps < 1) {
        toast.error("Enter a valid number of leaps (≥ 1)");
      }
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      if (nextErrors.tool) toast.error(nextErrors.tool);
      if (nextErrors.commitHash) toast.error(nextErrors.commitHash);
      if (nextErrors.daysAgo) toast.error(nextErrors.daysAgo);
      return;
    }

    // monta o user_settings normalmente
    const userSettings: any = {
      from_first_commit: analysisType === "first",
      from_a_specific_commit:
        analysisType === "specific" ? commitHash.trim() : null,
      days_prior: analysisType === "days" ? Number(daysAgo) : null,
      merge_commit: includeMerge ? true : null,
      fixed_leaps: includeLeaps ? Number(leapCount) : null,
      clone_detector: detectionTool,
    };

    // se a pessoa escolheu "Other", adiciona "detection-api" com valor do input
    if (detectionTool === "other") {
      userSettings["detection-api"] = detectionApi.trim();
    }

    const payload = {
      git_repository: repoUrl,
      user_settings: userSettings,
    };

    const controller = new AbortController();
    setAbortCtrl(controller);
    setIsSubmitting(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/xml",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      const text = await res.text();
      if (!res.ok) {
        throw new Error(text || `HTTP ${res.status}`);
      }

      toast.success("Analysis completed!");
      navigate("/visualize", { state: { xml: text, config: payload } });
    } catch (error) {
      if ((error as any)?.name === "AbortError") {
        toast.message("Extraction canceled");
      } else {
        toast.error(
          "Failed to start analysis: " +
            (error instanceof Error ? error.message : "Unknown error")
        );
        console.error("Analysis error:", error);
      }
    } finally {
      setIsSubmitting(false);
      setAbortCtrl(null);
    }
  };

  const handleStopDetection = async () => {
    try {
      // 1) avisa o backend para parar de monitorar esse repositório
      await fetch(STOP_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // o backend está usando "gir_url", então seguimos isso:
        body: JSON.stringify({ gir_url: repoUrl }),
      });
    } catch (err) {
      console.error("Failed to notify stop_detect_clones:", err);
      // não precisa dar erro pro usuário, o principal é abortar o fetch
    } finally {
      // 2) aborta a requisição atual de /detect_clones (se existir)
      abortCtrl?.abort();

      // 3) reseta estado de loading e controller
      setIsSubmitting(false);
      setAbortCtrl(null);

      // 4) feedback visual
      toast.message("Clone detection stopped");
    }
  };


  if (!repoUrl) {
    navigate("/");
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-accent/5">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/")}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div className="flex items-center gap-3">
            <Settings className="w-8 h-8 text-primary" />
            <h1 className="text-3xl font-bold">Repository Configuration</h1>
          </div>
          <p className="text-muted-foreground mt-2">
            Repository: <span className="font-mono text-sm">{repoUrl}</span>
          </p>
        </header>

        <form onSubmit={handleSubmit} aria-busy={isSubmitting}>
          {/* Basic Configurations Section */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Basic configurations</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Analysis Starting Point */}
              <div className="bg-card border border-border rounded-xl p-6 shadow-[var(--shadow-card)]">
                <Label className="text-base font-medium mb-4 block">
                  Analyze the repository commits from:{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <RadioGroup
                  value={analysisType}
                  onValueChange={(v: "first" | "specific" | "days") => {
                    setAnalysisType(v);
                    setErrors((prev) => ({
                      ...prev,
                      commitHash: undefined,
                      daysAgo: undefined,
                    }));
                  }}
                >
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="first" id="first" />
                      <Label
                        htmlFor="first"
                        className="font-normal cursor-pointer"
                      >
                        From the first commit
                      </Label>
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      The genealogy is built from the repository’s first commit.
                    </p>

                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="specific" id="specific" />
                      <Label
                        htmlFor="specific"
                        className="font-normal cursor-pointer flex-shrink-0"
                      >
                        The genealogy is built from the hash commit.
                      </Label>
                      <Input
                        placeholder="Enter the hash. E.g., a1b2c3d"
                        value={commitHash}
                        onChange={(e) => {
                          setCommitHash(e.target.value);
                          if (errors.commitHash) {
                            setErrors((prev) => ({
                              ...prev,
                              commitHash: undefined,
                            }));
                          }
                        }}
                        disabled={analysisType !== "specific"}
                        className={`h-10 w-full ${
                          analysisType === "specific" && errors.commitHash
                            ? "border-destructive focus-visible:ring-destructive"
                            : ""
                        }`}
                        aria-invalid={
                          analysisType === "specific" && !!errors.commitHash
                        }
                        required={analysisType === "specific"}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      The genealogy is built starting from the first commit made
                      within the last N days
                    </p>

                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="days" id="days" />
                      <Label
                        htmlFor="days"
                        className="font-normal cursor-pointer flex-shrink-0"
                      >
                        From the last few days
                      </Label>
                      <Input
                        type="number"
                        placeholder="Enter the number of days. E.g., 3"
                        value={daysAgo}
                        onChange={(e) => {
                          setDaysAgo(e.target.value);
                          if (errors.daysAgo) {
                            setErrors((prev) => ({
                              ...prev,
                              daysAgo: undefined,
                            }));
                          }
                        }}
                        disabled={analysisType !== "days"}
                        className={`h-10 w-40 ${
                          analysisType === "days" && errors.daysAgo
                            ? "border-destructive focus-visible:ring-destructive"
                            : ""
                        }`}
                        aria-invalid={
                          analysisType === "days" && !!errors.daysAgo
                        }
                        min={1}
                        required={analysisType === "days"}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      The genealogy is built starting from the first commit made
                      within the last N days
                    </p>
                  </div>
                </RadioGroup>
              </div>

              {/* Clone Detection Tool */}
              <div className="bg-card border border-border rounded-xl p-6 shadow-[var(--shadow-card)]">
                <Label
                  htmlFor="tool"
                  className="text-base font-medium mb-4 block"
                >
                  Select a clone detection tool:{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={detectionTool}
                  onValueChange={(v: DetectionTool) => {
                    setDetectionTool(v);
                    setErrors((prev) => ({ ...prev, tool: undefined }));
                    // se trocar de "other" para outro, limpa o input
                    if (v !== "other") {
                      setDetectionApi("");
                    }
                  }}
                >
                  <SelectTrigger
                    id="tool"
                    className={`h-10 ${
                      errors.tool
                        ? "border-destructive focus-visible:ring-destructive"
                        : ""
                    }`}
                    aria-invalid={!!errors.tool}
                  >
                    <SelectValue placeholder="Select tool" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="nicad">NiCad</SelectItem>
                    <SelectItem value="simian">Simian</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>

                {/* Input extra quando "Other" for selecionado */}
                {detectionTool === "other" && (
                  <div className="mt-4">
                    <Label
                      htmlFor="detection-api"
                      className="text-sm font-normal"
                    >
                      Clone detection API endpoint
                    </Label>
                    <Input
                      id="detection-api"
                      placeholder="Enter the endpoint of your API that performs clone detection. (e.g., https://my-api.com)"
                      value={detectionApi}
                      onChange={(e) => setDetectionApi(e.target.value)}
                      className={`mt-1 h-10 ${
                        errors.tool
                          ? "border-destructive focus-visible:ring-destructive"
                          : ""
                      }`}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      This endpoint will be called for each commit extracted.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Refine Your Analysis Section */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Refine your analysis</h2>
            <div className="bg-card border border-border rounded-xl p-6 shadow-[var(--shadow-card)]">
              <Label className="text-base font-medium mb-4 block">
                You can enable any combination of the options below:
              </Label>

              <div className="space-y-4">
                {/* Leaps */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Checkbox
                      id="leaps"
                      checked={includeLeaps}
                      onCheckedChange={(val) => {
                        const v = Boolean(val);
                        setIncludeLeaps(v);
                        if (!v) setLeapCount("");
                      }}
                    />
                    <Label
                      htmlFor="leaps"
                      className="font-normal cursor-pointer"
                    >
                      Analyze commits in leaps
                    </Label>
                    <Input
                      id="leapCount"
                      type="number"
                      placeholder="e.g., 4"
                      value={leapCount}
                      onChange={(e) => setLeapCount(e.target.value)}
                      disabled={!includeLeaps}
                      className="h-10 w-28"
                      min={1}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground pl-7">
                    The genealogy is built with a fixed step N, selecting one
                    commit every N
                  </p>
                </div>

                {/* Merge */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="merge"
                      checked={includeMerge}
                      onCheckedChange={(val) =>
                        setIncludeMerge(Boolean(val))
                      }
                    />
                    <Label
                      htmlFor="merge"
                      className="font-normal cursor-pointer"
                    >
                      Analyze only merge commits
                    </Label>
                  </div>
                  <p className="text-xs text-muted-foreground pl-7">
                    The genealogy is built using only merge commits.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 mt-8">
            <div className="flex items-center gap-6">
            {/* Generic Examples (black text) */}
            <Dialog>
              <DialogTrigger asChild>
                <a className="text-base text-black underline cursor-pointer font-medium">
                  Generic Examples
                </a>
              </DialogTrigger>

              <DialogContent>
                <DialogTitle className="text-2xl">Generic Examples</DialogTitle>
                <DialogDescription className="text-base">
                  Examples of git repositories and configurations you can use
                </DialogDescription>

                <div className="mt-4 max-h-[60vh] overflow-auto space-y-4 text-base">
                  {genericExamples.map((group, gi) => (
                    <div key={gi} className="space-y-3">
                      {group.title && (
                        <h4 className="font-semibold text-lg mb-2">
                          {group.title}
                        </h4>
                      )}

                      {group.items.map((it, i) => (
                        <div key={i} className="p-3 border rounded-md bg-card">
                          <div className="font-semibold text-lg">
                            {it.name}
                          </div>

                          {it.git && (
                            <div className="text-sm text-muted-foreground mt-1">
                              URL:{" "}
                              <span className="font-mono text-sm">
                                {it.git}
                              </span>
                            </div>
                          )}

                          {typeof it.from_lasy_days !== "undefined" && (
                            <div className="text-sm text-muted-foreground mt-1">
                              From last days: {it.from_lasy_days}
                            </div>
                          )}

                          {it.from_specific_commit && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Specific commit:{" "}
                              <span className="font-mono text-xs">
                                {it.from_specific_commit}
                              </span>
                            </div>
                          )}

                          {it.merge_commits && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Merge: true
                            </div>
                          )}

                          {typeof it.fixed_leaps !== "undefined" && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Fixed leaps: {it.fixed_leaps}
                            </div>
                          )}

                          {/* NOVO: Clone Detector */}
                          {it.clone_detector && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Clone Detector: {it.clone_detector}
                            </div>
                          )}

                          {it.time && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Time: {it.time}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </DialogContent>
            </Dialog>

            {/* Preliminary Evaluation */}
            <Dialog>
              <DialogTrigger asChild>
                <a className="text-base text-black underline cursor-pointer font-medium">
                  Preliminary Evaluation
                </a>
              </DialogTrigger>

              <DialogContent>
                <DialogTitle className="text-2xl">
                  Preliminary Evaluation
                </DialogTitle>
                <DialogDescription className="text-base">
                  Git repositories and configurations used in preliminary
                  evaluation.
                </DialogDescription>
                <div className="mt-4 max-h-[60vh] overflow-auto space-y-4 text-base">
                  {preliminaryExamples.map((group, gi) => (
                    <div key={gi}>
                      {group.items.map((it, i) => (
                        <div
                          key={i}
                          className="p-3 border rounded-md bg-card"
                        >
                          <div className="font-semibold text-lg">
                            {it.name}
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            URL:{" "}
                            <span className="font-mono text-sm">
                              {it.git}
                            </span>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Start Commit:{" "}
                            {it.start_commit ??
                              (it.from_first_commit ? "first" : "specific")}
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Fixed Leaps: {String(it.fixed_leaps ?? "-")}
                          </div>

                          {/* NOVO: Clone Detector */}
                          {it.clone_detector && (
                            <div className="text-sm text-muted-foreground mt-1">
                              Clone Detector: {it.clone_detector}
                            </div>
                          )}

                          <div className="text-sm text-muted-foreground mt-1">
                            Time: {it.time}
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </DialogContent>
            </Dialog>


            </div>

            <div className="flex justify-end gap-4">
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => navigate("/")}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="lg"
                className="bg-gradient-to-r from-primary to-accent hover:opacity-90"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Starting Extraction..." : "Start Extraction"}
              </Button>
            </div>
          </div>
        </form>
      </div>

      {isSubmitting && (
        <LoadingOverlay
          text="Running clone detection. This may take a while..."
          onCancel={handleStopDetection}
        />
      )}
    </div>
  );
};

export default Configure;
