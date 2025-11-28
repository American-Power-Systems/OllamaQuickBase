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
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      toast({
        title: "Job Enqueued",
        description: "PO Record added to Redis Queue for processing.",
      });
    }, 1500);
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Submit Purchase Order</CardTitle>
            <CardDescription>
              Manually trigger a job for the worker. This mimics the POST request to <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">/process_po</code>
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="record-id">Record ID</Label>
                <Input id="record-id" placeholder="e.g., PO-2024-8821" required />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="prompt">Analysis Prompt</Label>
                <Input id="prompt" defaultValue="Extract key details: Vendor, Total Amount, and Approval Status" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="po-text">PO Content / Text</Label>
                <Textarea 
                  id="po-text" 
                  placeholder="Paste the full text of the Purchase Order here..." 
                  className="min-h-[200px] font-mono text-sm"
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
