import { useState } from "react";
import Layout from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Send, Sparkles } from "lucide-react";

export default function SubmitPO() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  
  const [mode, setMode] = useState<"po" | "contract">("po");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      toast({
        title: "Job Enqueued",
        description: `Document sent to Redis. Mode: ${mode === "po" ? "PO Extraction" : "Contract Analysis"}`,
      });
    }, 1500);
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
               <div>
                <CardTitle>Submit Document</CardTitle>
                <CardDescription>
                  Manually trigger a job. This mimics the POST request to <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">/process_po</code>
                </CardDescription>
               </div>
               <div className="flex bg-muted p-1 rounded-lg">
                 <button 
                    onClick={() => setMode("po")}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${mode === "po" ? "bg-white shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                 >
                    PO Mode
                 </button>
                 <button 
                    onClick={() => setMode("contract")}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${mode === "contract" ? "bg-white shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                 >
                    Contract Mode
                 </button>
               </div>
            </div>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="record-id">Record ID</Label>
                <Input id="record-id" placeholder="e.g., DOC-2024-8821" required />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="prompt">Analysis Prompt (JSON)</Label>
                  <span className="text-xs text-muted-foreground">Dynamic Schema</span>
                </div>
                <Textarea 
                  id="prompt" 
                  className="font-mono text-xs bg-slate-50 text-slate-600 min-h-[100px]"
                  value={mode === "po" 
                    ? '{\n  "vendor": "Extract the vendor name",\n  "total": "Extract the total amount"\n}' 
                    : '{\n  "insurance_reqs": "Where are the insurance requirements located?",\n  "liability_limit": "What is the liability limit?"\n}'
                  } 
                  readOnly
                />
                <p className="text-[10px] text-muted-foreground">
                   * This JSON tells the Worker WHAT to extract. It can be changed per-document.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="po-text">Document Text</Label>
                <Textarea 
                  id="po-text" 
                  placeholder={mode === "po" ? "Paste Purchase Order text..." : "Paste Contract text..."}
                  className="min-h-[150px] font-mono text-sm"
                  required 
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-between border-t border-border pt-6">
              <Button variant="ghost" type="button">Clear Form</Button>
              <Button type="submit" disabled={isLoading} className="bg-primary hover:bg-primary/90">
                {isLoading ? (
                  <>Enqueuing...</>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Submit to Queue
                  </>
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <div className="mt-8 bg-blue-50 border border-blue-100 rounded-lg p-4 flex gap-4">
          <Sparkles className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-blue-900">How this works</h4>
            <p className="text-sm text-blue-700">
              When you click submit, the frontend sends a payload to the Flask API. 
              The API validates the request and pushes a job to Redis. 
              The Python Worker picks it up asynchronously, calls Ollama, and updates Quickbase.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
