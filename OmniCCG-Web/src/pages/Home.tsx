import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FolderOpen, GitBranch, Github } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const Home = () => {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      toast.error("Please enter a valid repository URL");
      return;
    }

    // Validate URL format
    const gitUrlPattern =
      /^(https?:\/\/)?(www\.)?(github|gitlab|bitbucket)\.(com|org)\/.+\/.+$/;
    if (!gitUrlPattern.test(repoUrl)) {
      toast.error("Please enter a valid Git repository URL");
      return;
    }

    navigate("/configure", { state: { repoUrl } });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-accent/5">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-16">
          <div className="flex items-center justify-center gap-3 mb-4">
            <GitBranch className="w-12 h-12 text-primary" />
            <h1 className="text-5xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              OmniCCG
            </h1>
          </div>
          <h2 className="text-2xl text-muted-foreground font-medium">
            Code Clone Genealogy Viewer
          </h2>
          <p className="text-muted-foreground mt-4 max-w-2xl mx-auto">
            Visualize and analyze the evolution of code clones across your
            repository's history. Track how duplicated code fragments change,
            merge, and evolve over time.
          </p>
        </header>

        {/* Main Card */}
        <div className="max-w-3xl mx-auto">
          <div className="bg-card border border-border rounded-2xl p-8 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-elegant)] transition-[var(--transition-smooth)]">
            <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Github className="w-5 h-5 text-primary" />
              Repository Configuration
            </h3>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Git Repository Link */}
              <div className="space-y-3">
                <Label
                  htmlFor="repoUrl"
                  className="text-base font-medium flex items-center gap-2"
                >
                  Git Repository Link{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="repoUrl"
                  type="url"
                  placeholder="E.g., https://github.com/username/repository.git"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="h-12 text-base"
                  required
                />
                <p className="text-sm text-muted-foreground">
                  Enter the URL of your Git repository (GitHub, GitLab, or
                  Bitbucket)
                </p>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-4 my-6">
                <div className="flex-1 h-px bg-border"></div>
                {/* <span className="text-sm text-muted-foreground">or</span> */}
                <div className="flex-1 h-px bg-border"></div>
              </div>

              {/* Local Folder Option */}
              {/* <div className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary transition-[var(--transition-smooth)] cursor-pointer">
                <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground mb-2">
                  Select Repository Folder
                </p>
                <p className="text-sm text-muted-foreground">
                  or drag and drop the folder here
                </p>
              </div> */}

              {/* Submit Button */}
              <Button
                type="submit"
                size="lg"
                className="w-full h-12 text-base font-semibold bg-gradient-to-r from-primary to-accent hover:opacity-90 transition-[var(--transition-smooth)]"
              >
                <GitBranch className="w-5 h-5 mr-2" />
                Configure Analysis
              </Button>
            </form>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            <div className="bg-card border border-border rounded-lg p-4 text-center">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">🔍</span>
              </div>
              <h4 className="font-semibold mb-1">Clone Detection</h4>
              <p className="text-sm text-muted-foreground">
                Advanced algorithms to detect code clones
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4 text-center">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">📊</span>
              </div>
              <h4 className="font-semibold mb-1">Visual Analytics</h4>
              <p className="text-sm text-muted-foreground">
                Interactive graphs and detailed statistics
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4 text-center">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">⏱️</span>
              </div>
              <h4 className="font-semibold mb-1">Evolution Tracking</h4>
              <p className="text-sm text-muted-foreground">
                Follow clone lineages through time
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
