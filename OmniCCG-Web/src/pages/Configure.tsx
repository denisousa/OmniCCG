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
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

type DetectionTool = "nicad" | "ccfinder" | "conqat" | "simian" | "pmd";

const API_URL = "http://127.0.0.1:5000/detect_clones";

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

    const payload = {
      git_repository: repoUrl,
      user_settings: {
        from_first_commit: analysisType === "first",
        from_a_specific_commit:
          analysisType === "specific" ? commitHash.trim() : null,
        days_prior: analysisType === "days" ? Number(daysAgo) : null,
        merge_commit: includeMerge ? true : null, // pode combinar com leaps
        fixed_leaps: includeLeaps ? Number(leapCount) : null,
        clone_detector: detectionTool,
      },
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
        toast.message("Analysis canceled");
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
                        aria-invalid={analysisType === "specific" && !!errors.commitHash}
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
                        aria-invalid={analysisType === "days" && !!errors.daysAgo}
                        min={1}
                        required={analysisType === "days"}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      The genealogy is built starting from the first commit made within the last N days
                    </p>
                  </div>
                </RadioGroup>
              </div>

              {/* Clone Detection Tool */}
              <div className="bg-card border border-border rounded-xl p-6 shadow-[var(--shadow-card)]">
                <Label htmlFor="tool" className="text-base font-medium mb-4 block">
                  Select a clone detection tool:{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={detectionTool}
                  onValueChange={(v: DetectionTool) => {
                    setDetectionTool(v);
                    setErrors((prev) => ({ ...prev, tool: undefined }));
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
                    {/* adicione outras opções se quiser */}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Refine Your Analysis Section (múltiplas seleções, input inline) */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Refine your analysis</h2>
            <div className="bg-card border border-border rounded-xl p-6 shadow-[var(--shadow-card)]">
              {/* Título com mesmo tamanho das outras seções */}
              <Label className="text-base font-medium mb-4 block">
                You can enable any combination of the options below:
              </Label>

              <div className="space-y-4">
                {/* Leaps (input ao lado; dica embaixo) */}
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
                    <Label htmlFor="leaps" className="font-normal cursor-pointer">
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
                    The genealogy is built with a fixed step N, selecting one commit every N
                  </p>
                </div>

                {/* Merge (inline) */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="merge"
                      checked={includeMerge}
                      onCheckedChange={(val) => setIncludeMerge(Boolean(val))}
                    />
                    <Label htmlFor="merge" className="font-normal cursor-pointer">
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

          {/* Action Buttons */}
          <div className="flex justify-end gap-4 mt-8">
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
        </form>
      </div>

      {/* Overlay de loading enquanto isSubmitting for true */}
      {isSubmitting && (
        <LoadingOverlay
          text="Running clone detection. This may take a while..."
          onCancel={() => abortCtrl?.abort()}
        />
      )}
    </div>
  );
};

export default Configure;
