import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { X } from "lucide-react";

interface CodeSnippet {
  file: string;
  function?: string;
  startline: number;
  endline: number;
  code: string;
}

interface CodeSnippetModalProps {
  isOpen: boolean;
  onClose: () => void;
  snippets: CodeSnippet[];
  activeFile?: string;
}

const CodeSnippetModal = ({
  isOpen,
  onClose,
  snippets,
  activeFile,
}: CodeSnippetModalProps) => {
  if (!snippets || snippets.length === 0) return null;

  const defaultTab = activeFile || snippets[0]?.file || "";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0">
        <DialogHeader className="p-6 pb-4 border-b border-border flex-shrink-0">
          <DialogTitle className="text-2xl font-bold">
            Code Snippets
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue={defaultTab} className="flex flex-col flex-1 min-h-0 overflow-hidden">
          <div className="px-6 pt-2 flex-shrink-0">
            <TabsList className="w-full justify-start overflow-x-auto">
              {snippets.map((snippet, index) => (
                <TabsTrigger key={index} value={snippet.file} className="text-sm">
                  {snippet.file.split("/").pop() || snippet.file}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <div className="flex-1 min-h-0 overflow-hidden px-6 pb-6">
            {snippets.map((snippet, index) => (
              <TabsContent 
                key={index} 
                value={snippet.file} 
                className="mt-4 h-full overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
              >
                <div className="flex flex-col h-full overflow-hidden gap-3">
                  <div className="bg-muted/50 p-4 rounded-lg border border-border flex-shrink-0">
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <span className="text-sm font-medium text-muted-foreground block mb-1">
                          File:
                        </span>
                        <p className="font-mono text-sm">
                          {snippet.file.split("/").pop() || snippet.file}
                        </p>
                      </div>
                      {snippet.function && (
                        <div>
                          <span className="text-sm font-medium text-muted-foreground block mb-1">
                            Method:
                          </span>
                          <p className="font-mono text-sm">
                            {snippet.function}
                          </p>
                        </div>
                      )}
                      <div>
                        <span className="text-sm font-medium text-muted-foreground block mb-1">
                          Lines:
                        </span>
                        <p className="font-mono text-sm">
                          {snippet.startline} - {snippet.endline}
                        </p>
                      </div>
                    </div>
                    {snippet.file.includes("/") && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <span className="text-xs font-medium text-muted-foreground block mb-1">
                          Full path:
                        </span>
                        <p className="font-mono text-xs text-muted-foreground/80">
                          {snippet.file}
                        </p>
                      </div>
                    )}
                  </div>

                  <ScrollArea className="flex-1 bg-muted/30 rounded-lg border border-border">
                    <div className="bg-muted/50 px-4 py-2 border-b border-border sticky top-0">
                      <span className="text-sm font-medium text-muted-foreground">
                        Code:
                      </span>
                    </div>
                    <pre className="p-4 text-sm font-mono leading-relaxed">
                      <code className="language-java text-foreground">
                        {snippet.code || "// Code snippet not available"}
                      </code>
                    </pre>
                  </ScrollArea>
                </div>
              </TabsContent>
            ))}
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

export default CodeSnippetModal;
