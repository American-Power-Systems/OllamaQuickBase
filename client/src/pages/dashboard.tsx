import { useState } from "react";
import Layout from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, CheckCircle2, Clock, AlertCircle, RefreshCw, Database } from "lucide-react";

// Mock Data for the Queue
const mockQueue = [
  { id: "job_9a8b7c", recordId: "PO-2024-001", status: "queued", time: "Just now", text: "Purchase of 50 Dell Latitude Laptops..." },
  { id: "job_1x2y3z", recordId: "PO-2024-002", status: "processing", time: "2m ago", text: "Services for cloud migration Q4..." },
  { id: "job_7h6j5k", recordId: "PO-2023-899", status: "completed", time: "15m ago", result: "Approved: IT Budget", text: "Annual software license renewal..." },
  { id: "job_3m4n5p", recordId: "PO-2023-898", status: "completed", time: "1h ago", result: "Pending: Finance Review", text: "Office furniture for new wing..." },
  { id: "job_9q8r7s", recordId: "PO-2023-897", status: "failed", time: "2h ago", error: "Ollama timeout", text: "Catering for annual event..." },
];

export default function Dashboard() {
  const [jobs, setJobs] = useState(mockQueue);

  return (
    <Layout>
      <div className="space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Queue Depth</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">12</div>
              <p className="text-xs text-muted-foreground">+2 from last hour</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Processed Today</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">145</div>
              <p className="text-xs text-muted-foreground">98% success rate</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1.2s</div>
              <p className="text-xs text-muted-foreground">-0.3s from yesterday</p>
            </CardContent>
          </Card>
        </div>

        {/* Queue Table */}
        <Card>
          <CardHeader>
            <CardTitle>Live Job Queue</CardTitle>
            <CardDescription>Real-time view of Redis/RQ processing status.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border border-border">
              <div className="grid grid-cols-12 gap-4 p-4 bg-muted/50 font-medium text-sm text-muted-foreground border-b border-border">
                <div className="col-span-2">Job ID</div>
                <div className="col-span-2">Record ID</div>
                <div className="col-span-4">PO Preview</div>
                <div className="col-span-2">Status</div>
                <div className="col-span-2 text-right">Time</div>
              </div>
              <div className="divide-y divide-border">
                {jobs.map((job) => (
                  <div key={job.id} className="grid grid-cols-12 gap-4 p-4 text-sm items-center hover:bg-muted/30 transition-colors">
                    <div className="col-span-2 font-mono text-xs text-muted-foreground">{job.id}</div>
                    <div className="col-span-2 font-medium">{job.recordId}</div>
                    <div className="col-span-4 truncate text-muted-foreground">{job.text}</div>
                    <div className="col-span-2">
                      <StatusBadge status={job.status} />
                    </div>
                    <div className="col-span-2 text-right text-muted-foreground text-xs">{job.time}</div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "queued":
      return <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-200">Queued</Badge>;
    case "processing":
      return <Badge variant="outline" className="bg-blue-50 text-blue-600 border-blue-200 animate-pulse">Processing</Badge>;
    case "completed":
      return <Badge variant="outline" className="bg-emerald-50 text-emerald-600 border-emerald-200">Completed</Badge>;
    case "failed":
      return <Badge variant="outline" className="bg-red-50 text-red-600 border-red-200">Failed</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}
