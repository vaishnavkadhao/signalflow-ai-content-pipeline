import React, { useState, useEffect, useRef } from "react";
import {
  Play, Table, Settings, Calendar as CalendarIcon, FileText,
  Check, Plus, Trash, CheckCircle, Eye, BookOpen, Sparkles,
  Clock, Share2, RotateCw, Save, AlertCircle, ThumbsUp,
  ArrowRight, User, Upload, Download, X, Zap, Shield,
  BarChart3, Target, TrendingUp, FileUp, ChevronDown,
  ListChecks, Copy, RefreshCw, AlertTriangle, Info,
  Star, Layers, Radio
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Mode = "free" | "ai_assist" | "pro";
type Tab = "start" | "sources" | "strategy" | "approval" | "calendar" | "report";

type Trend = {
  trend_title: string;
  views: number | string;
  likes: number | string;
  comments: number | string;
  shares: number | string;
  platform: string;
  url: string;
  [key: string]: any;
};

type ApprovalState = "pending" | "approved" | "rejected";

type TrendWithApproval = Trend & {
  _approvalState: ApprovalState;
  _engagementScore: number;
};

type CalendarItem = {
  date: string;
  local_time: string;
  timezone: string;
  platform: string;
  content_pillar: string;
  topic: string;
  format: string;
  hook: string;
  script_status: string;
  caption_status: string;
  cta: string;
  priority: string;
  repurpose_plan: string;
  human_review_status: string;
};

type CSVHealth = {
  valid: boolean;
  errors: string[];
  warnings: string[];
  row_count: number;
  detected_columns: string[];
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function calcEngagement(t: Trend): number {
  const v = Number(t.views) || 0;
  const l = Number(t.likes) || 0;
  const c = Number(t.comments) || 0;
  const s = Number(t.shares) || 0;
  if (v === 0) return 0;
  return Math.min(((l + c * 2 + s * 1.5) / v) * 100, 100);
}

function fmtNum(n: number | string): string {
  const num = Number(n) || 0;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}K`;
  return String(num);
}

function getPlatformColor(platform: string) {
  const p = platform.toLowerCase();
  if (p.includes("youtube")) return { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" };
  if (p.includes("instagram")) return { bg: "bg-pink-500/10", text: "text-pink-400", border: "border-pink-500/20" };
  if (p.includes("tiktok")) return { bg: "bg-slate-500/10", text: "text-slate-300", border: "border-slate-500/20" };
  if (p.includes("linkedin")) return { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" };
  if (p.includes("x ") || p.includes("twitter")) return { bg: "bg-slate-500/10", text: "text-slate-300", border: "border-slate-500/20" };
  return { bg: "bg-violet-500/10", text: "text-violet-400", border: "border-violet-500/20" };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PlatformBadge({ platform }: { platform: string }) {
  const colors = getPlatformColor(platform);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}>
      {platform}
    </span>
  );
}

function StatusBadge({ label, type }: { label: string; type: "success" | "warning" | "neutral" | "error" }) {
  const map = {
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    error: "bg-red-500/10 text-red-400 border-red-500/20",
    neutral: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${map[type]}`}>
      {label}
    </span>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  // Tab
  const [activeTab, setActiveTab] = useState<Tab>("start");

  // Trend data
  const [trends, setTrends] = useState<Trend[]>([]);
  const [trendsWithApproval, setTrendsWithApproval] = useState<TrendWithApproval[]>([]);
  const [maxApprove, setMaxApprove] = useState<number>(20);

  // CSV upload / health
  const [csvHealth, setCsvHealth] = useState<CSVHealth | null>(null);
  const [csvCheckLoading, setCsvCheckLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stratFileInputRef = useRef<HTMLInputElement>(null);

  // Strategy tab
  const [strategyFiles, setStrategyFiles] = useState<{ name: string; type: string; size: number; preview: string }[]>([]);
  const [creatorMemory, setCreatorMemory] = useState<{
    creator_name?: string;
    timezone?: string;
    content_pillars?: string[];
    banned_phrases?: string[];
    formatting?: { scripts?: string; duration_target_seconds?: number };
  }>({});
  const [promptContent, setPromptContent] = useState("");
  const [newPillar, setNewPillar] = useState("");
  const [newBannedWord, setNewBannedWord] = useState("");

  // Mode + API key
  const [mode, setMode] = useState<Mode>("free");
  const [geminiKey, setGeminiKey] = useState("");
  const [showKey, setShowKey] = useState(false);

  // Pipeline
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineLogs, setPipelineLogs] = useState("");
  const [activeStep, setActiveStep] = useState(0);
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([]);
  const [reportMd, setReportMd] = useState("");
  const [hasResults, setHasResults] = useState(false);
  const [selectedPost, setSelectedPost] = useState<CalendarItem | null>(null);

  // Inline trend editor (Sources tab)
  const [isAddingTrend, setIsAddingTrend] = useState(false);
  const [newTrend, setNewTrend] = useState<Trend>({
    trend_title: "", views: "", likes: "", comments: "", shares: "", platform: "YouTube", url: ""
  });

  // Notification
  const [notification, setNotification] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const notify = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchTrends();
    fetchPrompts();
    fetchCreatorMemory();
    fetchResults();
  }, []);

  useEffect(() => {
    // Build approval list whenever trends change
    const withApproval = trends.map(t => ({
      ...t,
      _approvalState: "pending" as ApprovalState,
      _engagementScore: calcEngagement(t),
    })).sort((a, b) => b._engagementScore - a._engagementScore);
    setTrendsWithApproval(withApproval);
  }, [trends]);

  // ── Fetchers ──────────────────────────────────────────────────────────────
  async function fetchTrends() {
    try {
      const res = await fetch("/api/trends");
      const data = await res.json();
      setTrends(Array.isArray(data) ? data : []);
    } catch { /* silent */ }
  }

  async function fetchPrompts() {
    try {
      const res = await fetch("/api/prompts");
      const data = await res.json();
      setPromptContent(data.content || "");
    } catch { /* silent */ }
  }

  async function fetchCreatorMemory() {
    try {
      const res = await fetch("/api/creator-memory");
      const data = await res.json();
      setCreatorMemory(data);
    } catch { /* silent */ }
  }

  async function fetchResults() {
    try {
      const res = await fetch("/api/results");
      const data = await res.json();
      if (data.exists) {
        setCalendarItems(data.calendar || []);
        setReportMd(data.report || "");
        setHasResults(true);
      }
    } catch { /* silent */ }
  }

  // ── CSV Actions ───────────────────────────────────────────────────────────
  async function saveTrends(updated: Trend[]) {
    try {
      const res = await fetch("/api/trends", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updated),
      });
      if (res.ok) { setTrends(updated); notify("Trends saved to data/sample_trends.csv"); }
      else notify("Failed to save trends.", "error");
    } catch { notify("Connection error.", "error"); }
  }

  async function handleCSVFileUpload(file: File) {
    const text = await file.text();
    setCsvCheckLoading(true);
    try {
      const res = await fetch("/api/csv-health-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv_text: text }),
      });
      const health = await res.json();
      setCsvHealth(health);
      if (health.valid) {
        // Parse locally and update trends
        const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
        const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
        const parsed: Trend[] = [];
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(",").map(v => v.trim().replace(/^"|"$/g, ""));
          const obj: any = {};
          headers.forEach((h, idx) => { obj[h] = cols[idx] || ""; });
          // Normalize: map topic → trend_title, source_url → url
          parsed.push({
            trend_title: obj.topic || obj.trend_title || obj.title || "Untitled",
            views: obj.views || "0",
            likes: obj.likes || "0",
            comments: obj.comments || "0",
            shares: obj.shares || "0",
            platform: obj.platform || "Unknown",
            url: obj.source_url || obj.url || obj.post_url || "",
          });
        }
        await saveTrends(parsed);
        notify(`Loaded ${parsed.length} trends from ${file.name}`);
      }
    } finally {
      setCsvCheckLoading(false);
    }
  }

  function handleDropZone(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.endsWith(".csv")) handleCSVFileUpload(file);
    else notify("Only CSV files are accepted here.", "error");
  }

  // ── Approval Actions ──────────────────────────────────────────────────────
  function setApproval(idx: number, state: ApprovalState) {
    setTrendsWithApproval(prev => prev.map((t, i) => i === idx ? { ...t, _approvalState: state } : t));
  }

  function approveTopN() {
    setTrendsWithApproval(prev => prev.map((t, i) => ({
      ...t,
      _approvalState: i < maxApprove ? "approved" : "pending",
    })));
    notify(`Approved top ${maxApprove} trends by engagement.`);
  }

  function resetApprovals() {
    setTrendsWithApproval(prev => prev.map(t => ({ ...t, _approvalState: "pending" })));
  }

  // ── Pipeline Run ──────────────────────────────────────────────────────────
  async function handleRunPipeline() {
    const approved = trendsWithApproval.filter(t => t._approvalState === "approved");
    const useApproved = approved.length > 0;

    setIsPipelineRunning(true);
    setPipelineLogs("Initializing SignalFlow AI pipeline...\n");
    setActiveStep(1);

    const stepInterval = setInterval(() => {
      setActiveStep(prev => prev < 7 ? prev + 1 : 7);
    }, 1600);

    try {
      const body: any = {
        dry_run: mode === "free",
        use_llm: mode !== "free",
        max_trends: maxApprove,
      };

      if (useApproved) {
        // Pass approved trends as plain objects (strip _approvalState)
        body.approved_trends = approved.map(({ _approvalState, _engagementScore, ...t }) => t);
      }

      if (mode !== "free" && geminiKey.trim()) {
        body.gemini_api_key = geminiKey.trim();
      }

      const res = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      clearInterval(stepInterval);

      if (data.success) {
        setPipelineLogs(data.stdout || "Pipeline completed.");
        setCalendarItems(data.calendar || []);
        setReportMd(data.report || "");
        setHasResults(true);
        setActiveStep(7);
        notify("Content calendar generated! Check the Calendar tab.");
        setActiveTab("calendar");
      } else {
        setPipelineLogs(`${pipelineLogs}\n\nERROR:\n${data.stderr || data.error}`);
        notify("Pipeline run failed. Check the Report tab for logs.", "error");
      }
    } catch (e: any) {
      clearInterval(stepInterval);
      setPipelineLogs(`${pipelineLogs}\n\nConnection error:\n${e.message}`);
      notify("Network error during pipeline run.", "error");
    } finally {
      setIsPipelineRunning(false);
    }
  }

  // ── Strategy Actions ──────────────────────────────────────────────────────
  async function handleStrategyFileUpload(file: File) {
    const allowed = [".txt", ".md", ".csv"];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (!allowed.includes(ext)) {
      notify(`Only .txt, .md, .csv files are accepted. Got: ${ext}`, "error");
      return;
    }
    const text = await file.text();
    const preview = text.slice(0, 400);
    setStrategyFiles(prev => [...prev, { name: file.name, type: ext, size: file.size, preview }]);
    notify(`Loaded strategy file: ${file.name}`);
  }

  async function saveMemory(updated = creatorMemory) {
    try {
      const res = await fetch("/api/creator-memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updated),
      });
      if (res.ok) { setCreatorMemory(updated); notify("Brand settings saved."); }
      else notify("Failed to save settings.", "error");
    } catch { notify("Network error.", "error"); }
  }

  async function savePrompt() {
    try {
      const res = await fetch("/api/prompts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: promptContent }),
      });
      if (res.ok) notify("Prompt template saved.");
      else notify("Failed to save prompt.", "error");
    } catch { notify("Network error.", "error"); }
  }

  // Approval counts
  const approvedCount = trendsWithApproval.filter(t => t._approvalState === "approved").length;
  const rejectedCount = trendsWithApproval.filter(t => t._approvalState === "rejected").length;

  // ──────────────────────────────────────────────────────────────────────────
  // RENDER
  // ──────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0f1117] text-slate-100 font-sans selection:bg-violet-500/30 selection:text-white">

      {/* Toast */}
      {notification && (
        <div className={`toast-enter fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-4 rounded-2xl border shadow-2xl max-w-sm ${
          notification.type === "success"
            ? "bg-[#1a2038] border-slate-700/60 text-slate-100"
            : "bg-[#2a1520] border-red-900/60 text-red-200"
        }`}>
          {notification.type === "success"
            ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            : <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />}
          <span className="text-sm font-medium">{notification.text}</span>
        </div>
      )}

      {/* ── Header ── */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#0f1117]/90 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#4f72ff] to-[#7c3aed] flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Radio className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white leading-none">SignalFlow AI</h1>
              <p className="text-[10px] text-slate-500 font-mono leading-none mt-0.5">Content Ops</p>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex items-center gap-0.5 overflow-x-auto scrollbar-none">
            {([
              { id: "start",    label: "Start",    icon: Sparkles },
              { id: "sources",  label: "Sources",  icon: Upload },
              { id: "strategy", label: "Strategy", icon: Target },
              { id: "approval", label: "Approval", icon: ListChecks, badge: approvedCount > 0 ? String(approvedCount) : undefined },
              { id: "calendar", label: "Calendar", icon: CalendarIcon, badge: hasResults ? "●" : undefined },
              { id: "report",   label: "Report",   icon: BarChart3 },
            ] as { id: Tab; label: string; icon: any; badge?: string }[]).map(({ id, label, icon: Icon, badge }) => (
              <button
                key={id}
                id={`tab-${id}`}
                onClick={() => setActiveTab(id)}
                className={`relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  activeTab === id
                    ? "bg-white/8 text-white"
                    : "text-slate-500 hover:text-slate-300 hover:bg-white/4"
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {label}
                {badge && (
                  <span className={`text-[9px] font-bold px-1.5 rounded-full ${
                    badge === "●" ? "text-emerald-400" : "bg-violet-500/20 text-violet-300"
                  }`}>{badge}</span>
                )}
              </button>
            ))}
          </nav>

          {/* Quick run btn */}
          <button
            id="header-run-btn"
            onClick={handleRunPipeline}
            disabled={isPipelineRunning}
            className="shrink-0 flex items-center gap-2 bg-gradient-to-r from-[#4f72ff] to-[#7c3aed] hover:opacity-90 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50"
          >
            {isPipelineRunning ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            {isPipelineRunning ? "Running..." : "Run Pipeline"}
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* ════════════════════════════════════════════════════
            TAB: START
        ════════════════════════════════════════════════════ */}
        {activeTab === "start" && (
          <div className="space-y-8">

            {/* Hero section */}
            <div className="relative rounded-3xl overflow-hidden border border-white/6 bg-[#171b27]">
              {/* Animated orbs */}
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="hero-orb-1 absolute -top-32 -right-32 w-96 h-96 rounded-full bg-gradient-to-br from-blue-600/20 to-violet-600/10 blur-3xl" />
                <div className="hero-orb-2 absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-gradient-to-tr from-violet-600/15 to-blue-600/10 blur-3xl" />
                <div className="bg-grid-subtle absolute inset-0" />
              </div>

              <div className="relative z-10 px-10 py-14 max-w-2xl">
                <div className="flex items-center gap-2 mb-6">
                  <span className="inline-flex items-center gap-1.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-semibold px-3 py-1 rounded-full font-mono uppercase tracking-wider">
                    <span className="signal-dot w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
                    Phase 1 · Review Ready
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">Free Mode</span>
                </div>

                <h2 className="text-4xl font-bold tracking-tight text-white mb-4 leading-tight">
                  Turn trends into
                  <br />
                  <span className="text-gradient-signal">review-ready content.</span>
                </h2>
                <p className="text-slate-400 text-sm leading-relaxed mb-8">
                  Upload your trend signals and strategy context. Approve the best topics.
                  Run the AI pipeline. Get hooks, scripts, captions, and a content calendar —
                  ready for human review.
                </p>

                {/* Flow steps */}
                <div className="flex flex-wrap items-center gap-2 mb-10">
                  {["Upload Trends", "Review & Approve", "Run Pipeline", "Get Content Calendar"].map((step, i) => (
                    <React.Fragment key={step}>
                      <span className="text-xs text-slate-300 font-medium bg-white/5 border border-white/10 px-3 py-1.5 rounded-lg">{step}</span>
                      {i < 3 && <ArrowRight className="w-3 h-3 text-slate-600 shrink-0" />}
                    </React.Fragment>
                  ))}
                </div>

                {/* Mode selector */}
                <div className="mb-8">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-3">Select Mode</p>
                  <div className="grid grid-cols-3 gap-3 max-w-lg">
                    {([
                      { id: "free", label: "Free Mode", sub: "No API key needed", icon: Shield },
                      { id: "ai_assist", label: "AI Assist", sub: "BYOK Gemini", icon: Sparkles },
                      { id: "pro", label: "Pro Quality", sub: "Write + Critique", icon: Star },
                    ] as { id: Mode; label: string; sub: string; icon: any }[]).map(({ id, label, sub, icon: Icon }) => (
                      <button
                        key={id}
                        id={`mode-${id}`}
                        onClick={() => setMode(id)}
                        className={`flex flex-col items-start p-3.5 rounded-xl border text-left transition-all ${
                          mode === id
                            ? "border-blue-500/50 bg-blue-500/8 text-white"
                            : "border-white/8 bg-white/3 text-slate-400 hover:border-white/16 hover:text-slate-300"
                        }`}
                      >
                        <Icon className={`w-4 h-4 mb-2 ${mode === id ? "text-blue-400" : "text-slate-500"}`} />
                        <span className="text-xs font-semibold leading-none">{label}</span>
                        <span className="text-[10px] text-slate-500 mt-1 leading-none">{sub}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Gemini key (AI modes only) */}
                {mode !== "free" && (
                  <div className="mb-8 max-w-md">
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">
                      Gemini API Key (BYOK)
                    </label>
                    <div className="flex gap-2">
                      <input
                        id="gemini-key-input"
                        type={showKey ? "text" : "password"}
                        placeholder="AIza..."
                        value={geminiKey}
                        onChange={e => setGeminiKey(e.target.value)}
                        className="flex-1 text-xs font-mono border border-white/10 rounded-xl px-4 py-2.5 bg-white/3 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/5"
                      />
                      <button
                        onClick={() => setShowKey(!showKey)}
                        className="px-3 border border-white/10 rounded-xl text-slate-500 hover:text-slate-300 hover:border-white/20 transition text-xs"
                      >
                        {showKey ? "Hide" : "Show"}
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-600 mt-1.5 font-mono">
                      Key is never saved to disk or logs. Passed only at run-time.
                    </p>
                  </div>
                )}

                {/* Run button */}
                <div className="flex items-center gap-4">
                  <button
                    id="start-run-btn"
                    onClick={handleRunPipeline}
                    disabled={isPipelineRunning}
                    className="inline-flex items-center gap-2.5 bg-gradient-to-r from-[#4f72ff] to-[#7c3aed] hover:opacity-90 text-white font-semibold px-7 py-3.5 rounded-2xl transition-all shadow-2xl shadow-blue-500/30 disabled:opacity-50 text-sm"
                  >
                    {isPipelineRunning ? <RotateCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                    {isPipelineRunning ? "Running Pipeline..." : "Run Pipeline"}
                  </button>
                  <button
                    onClick={() => setActiveTab("sources")}
                    className="text-slate-500 hover:text-slate-300 text-sm font-medium flex items-center gap-1.5 transition-all"
                  >
                    Upload trends first <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Status cards row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Trend Signals", value: String(trends.length), sub: "loaded from CSV", icon: TrendingUp, color: "text-blue-400" },
                { label: "Approved", value: String(approvedCount), sub: "ready to run", icon: CheckCircle, color: "text-emerald-400" },
                { label: "Mode", value: mode === "free" ? "Free" : mode === "ai_assist" ? "AI Assist" : "Pro", sub: "selected generation mode", icon: Zap, color: "text-violet-400" },
                { label: "Calendar Items", value: hasResults ? String(calendarItems.length) : "—", sub: hasResults ? "generated" : "run pipeline first", icon: CalendarIcon, color: "text-amber-400" },
              ].map(({ label, value, sub, icon: Icon, color }) => (
                <div key={label} className="card-glow rounded-2xl border border-white/6 bg-[#171b27] p-5">
                  <div className={`${color} mb-3`}><Icon className="w-5 h-5" /></div>
                  <p className="text-2xl font-bold text-white mb-0.5">{value}</p>
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{label}</p>
                  <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>
                </div>
              ))}
            </div>

            {/* Pipeline step progress */}
            <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-sm font-semibold text-white">Pipeline Flow</h3>
                  <p className="text-[10px] text-slate-500">7-agent content generation pipeline</p>
                </div>
                {isPipelineRunning && (
                  <span className="text-[10px] font-mono text-blue-400 flex items-center gap-1.5 animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    Processing
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                {[
                  { title: "Collect", role: "CSV Connector", s: 1 },
                  { title: "Validate", role: "Validator", s: 2 },
                  { title: "Patterns", role: "Analyzer", s: 3 },
                  { title: "Prompts", role: "Prompt Gen", s: 4 },
                  { title: "Scripts", role: "Script Writer", s: 5 },
                  { title: "Hooks", role: "Hook Gen", s: 6 },
                  { title: "Calendar", role: "Planner", s: 7 },
                ].map((step, idx) => {
                  const num = idx + 1;
                  const done = activeStep > num;
                  const active = activeStep === num;
                  return (
                    <div key={step.title} className={`rounded-xl border p-3.5 flex flex-col gap-2 transition-all ${
                      active
                        ? "step-active-shimmer border-blue-500/30"
                        : done
                        ? "bg-emerald-500/5 border-emerald-500/20"
                        : "bg-white/2 border-white/5"
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className={`font-mono text-[9px] font-semibold ${active ? "text-blue-400" : done ? "text-emerald-400" : "text-slate-600"}`}>
                          0{num}
                        </span>
                        {done ? <Check className="w-3 h-3 text-emerald-400" /> : active ? <div className="w-2 h-2 rounded-full bg-blue-400 animate-ping" /> : null}
                      </div>
                      <div>
                        <p className={`text-[10px] font-semibold leading-tight ${active ? "text-white" : done ? "text-slate-300" : "text-slate-500"}`}>{step.title}</p>
                        <p className={`text-[9px] mt-0.5 ${active ? "text-slate-400" : "text-slate-600"}`}>{step.role}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            TAB: SOURCES
        ════════════════════════════════════════════════════ */}
        {activeTab === "sources" && (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Trend Signals</h2>
              <p className="text-sm text-slate-500">Upload or edit your trend data. This feeds the pipeline.</p>
            </div>

            {/* Upload guidance cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  label: "Trend Data",
                  required: true,
                  icon: TrendingUp,
                  color: "text-blue-400",
                  fmt: "CSV",
                  desc: "Topics, platforms, and engagement data. This is the main input to the pipeline.",
                  cols: "topic, platform, source_url, views, likes, comments",
                  template: "/data/templates/sample_trends.csv",
                },
                {
                  label: "Brand Strategy",
                  required: false,
                  icon: Target,
                  color: "text-violet-400",
                  fmt: "MD / TXT",
                  desc: "Brand tone, content pillars, audience, banned phrases. Guides AI generation.",
                  cols: "tone, pillars, audience, banned phrases, CTA templates",
                  template: "/data/templates/sample_content_strategy.md",
                },
                {
                  label: "Existing Calendar",
                  required: false,
                  icon: CalendarIcon,
                  color: "text-amber-400",
                  fmt: "CSV",
                  desc: "Your current scheduled content. Helps avoid topic duplication.",
                  cols: "date, platform, topic, format, status",
                  template: "/data/templates/sample_existing_calendar.csv",
                },
                {
                  label: "Performance Report",
                  required: false,
                  icon: BarChart3,
                  color: "text-emerald-400",
                  fmt: "CSV",
                  desc: "Past post performance data. Used for pattern analysis in Phase 2.",
                  cols: "post_id, views, likes, watch_time_pct, engagement_rate",
                  template: "/data/templates/sample_performance_report.csv",
                },
              ].map(({ label, required, icon: Icon, color, fmt, desc, cols, template }) => (
                <div key={label} className="card-glow rounded-2xl border border-white/6 bg-[#171b27] p-5 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg bg-white/4 flex items-center justify-center ${color}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">{label}</p>
                        <p className="text-[9px] font-mono text-slate-500">{fmt}</p>
                      </div>
                    </div>
                    {required
                      ? <span className="text-[9px] font-bold text-red-400 border border-red-500/20 bg-red-500/8 px-2 py-0.5 rounded-full">Required</span>
                      : <span className="text-[9px] text-slate-600 border border-white/8 px-2 py-0.5 rounded-full">Optional</span>}
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{desc}</p>
                  <div className="bg-white/2 rounded-lg p-2 font-mono text-[9px] text-slate-600 border border-white/4">
                    {cols}
                  </div>
                  <a
                    href={template}
                    download
                    className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition font-mono mt-auto"
                  >
                    <Download className="w-3 h-3" /> Download sample template
                  </a>
                </div>
              ))}
            </div>

            {/* CSV Upload drop zone */}
            <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Upload Trend CSV</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">Drag & drop or click to select. Replaces current trend data.</p>
                </div>
                <button
                  onClick={() => setIsAddingTrend(!isAddingTrend)}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-white/8 hover:border-white/16 px-3 py-1.5 rounded-lg transition"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Row
                </button>
              </div>

              {/* Drop zone */}
              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleDropZone}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-white/8 hover:border-white/20 rounded-2xl p-10 text-center cursor-pointer transition-all hover:bg-white/2"
              >
                <Upload className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-400 font-medium">Drop your trends CSV here</p>
                <p className="text-xs text-slate-600 mt-1">or click to browse — accepts .csv files</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) handleCSVFileUpload(f); }}
                />
              </div>

              {/* CSV health result */}
              {csvCheckLoading && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" /> Checking CSV...
                </div>
              )}
              {csvHealth && (
                <div className={`rounded-xl border p-4 space-y-2 ${csvHealth.valid ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"}`}>
                  <div className="flex items-center gap-2">
                    {csvHealth.valid
                      ? <CheckCircle className="w-4 h-4 text-emerald-400" />
                      : <AlertCircle className="w-4 h-4 text-red-400" />}
                    <span className={`text-xs font-semibold ${csvHealth.valid ? "text-emerald-400" : "text-red-400"}`}>
                      {csvHealth.valid ? `CSV looks good — ${csvHealth.row_count} rows detected` : "CSV has errors — fix before running"}
                    </span>
                  </div>
                  {csvHealth.errors.map((e, i) => (
                    <p key={i} className="text-[11px] text-red-400 font-mono">✗ {e}</p>
                  ))}
                  {csvHealth.warnings.map((w, i) => (
                    <p key={i} className="text-[11px] text-amber-400 font-mono">⚠ {w}</p>
                  ))}
                  <p className="text-[10px] text-slate-500 font-mono">Detected columns: {csvHealth.detected_columns.join(", ")}</p>
                </div>
              )}
            </div>

            {/* Trend table */}
            {trends.length > 0 && (
              <div className="rounded-2xl border border-white/6 bg-[#171b27] overflow-hidden">
                <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white">{trends.length} Trend Signals Loaded</h3>
                    <p className="text-[10px] text-slate-500 mt-0.5">From data/sample_trends.csv</p>
                  </div>
                  <button
                    onClick={fetchTrends}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh
                  </button>
                </div>

                {/* Add trend form */}
                {isAddingTrend && (
                  <form
                    onSubmit={e => {
                      e.preventDefault();
                      if (!newTrend.trend_title) return;
                      const updated = [...trends, { ...newTrend, views: Number(newTrend.views) || 0, likes: Number(newTrend.likes) || 0, comments: Number(newTrend.comments) || 0, shares: Number(newTrend.shares) || 0 }];
                      saveTrends(updated);
                      setNewTrend({ trend_title: "", views: "", likes: "", comments: "", shares: "", platform: "YouTube", url: "" });
                      setIsAddingTrend(false);
                    }}
                    className="px-6 py-4 border-b border-white/5 bg-white/2 grid grid-cols-2 md:grid-cols-4 gap-3"
                  >
                    <div className="md:col-span-2">
                      <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Topic</label>
                      <input
                        required
                        type="text"
                        placeholder="e.g. How AI is changing content creation"
                        value={newTrend.trend_title}
                        onChange={e => setNewTrend({ ...newTrend, trend_title: e.target.value })}
                        className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50"
                      />
                    </div>
                    <div>
                      <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Platform</label>
                      <select
                        value={newTrend.platform}
                        onChange={e => setNewTrend({ ...newTrend, platform: e.target.value })}
                        className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500/50"
                      >
                        {["YouTube", "Instagram", "TikTok", "LinkedIn", "X Thread"].map(p => <option key={p}>{p}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Views</label>
                      <input
                        type="number"
                        placeholder="500000"
                        value={newTrend.views}
                        onChange={e => setNewTrend({ ...newTrend, views: e.target.value })}
                        className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50"
                      />
                    </div>
                    <div className="md:col-span-2 flex gap-2 items-end">
                      <div className="flex-1">
                        <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Likes</label>
                        <input type="number" placeholder="20000" value={newTrend.likes} onChange={e => setNewTrend({ ...newTrend, likes: e.target.value })} className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none" />
                      </div>
                      <div className="flex-1">
                        <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Comments</label>
                        <input type="number" placeholder="800" value={newTrend.comments} onChange={e => setNewTrend({ ...newTrend, comments: e.target.value })} className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none" />
                      </div>
                      <div className="flex-1">
                        <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Source URL</label>
                        <input type="url" placeholder="https://..." value={newTrend.url} onChange={e => setNewTrend({ ...newTrend, url: e.target.value })} className="w-full text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none" />
                      </div>
                    </div>
                    <div className="flex items-end gap-2 md:col-span-2">
                      <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition">Add Trend</button>
                      <button type="button" onClick={() => setIsAddingTrend(false)} className="text-slate-500 hover:text-slate-300 text-xs transition px-3 py-2">Cancel</button>
                    </div>
                  </form>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-xs text-slate-400">
                    <thead className="bg-white/2 border-b border-white/5 font-mono text-[9px] uppercase tracking-wider text-slate-600">
                      <tr>
                        <th className="px-5 py-3">Topic</th>
                        <th className="px-5 py-3">Platform</th>
                        <th className="px-5 py-3 text-right">Views</th>
                        <th className="px-5 py-3 text-right">Engagement</th>
                        <th className="px-5 py-3">Source</th>
                        <th className="px-5 py-3 text-center">Del</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/3">
                      {trends.map((t, idx) => {
                        const eng = calcEngagement(t);
                        return (
                          <tr key={idx} className="hover:bg-white/2 transition">
                            <td className="px-5 py-3 text-slate-200 font-medium max-w-xs truncate">"{t.trend_title}"</td>
                            <td className="px-5 py-3"><PlatformBadge platform={t.platform} /></td>
                            <td className="px-5 py-3 text-right font-mono text-slate-300">{fmtNum(t.views)}</td>
                            <td className="px-5 py-3 text-right font-mono">
                              <span className={`font-semibold ${eng > 5 ? "text-emerald-400" : eng > 2 ? "text-amber-400" : "text-slate-500"}`}>
                                {eng.toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-5 py-3">
                              {t.url ? (
                                <a href={t.url} target="_blank" rel="noreferrer" className="text-blue-400/70 hover:text-blue-400 flex items-center gap-1 transition">
                                  View <Share2 className="w-3 h-3" />
                                </a>
                              ) : <span className="text-slate-700">—</span>}
                            </td>
                            <td className="px-5 py-3 text-center">
                              <button
                                id={`del-trend-${idx}`}
                                onClick={() => saveTrends(trends.filter((_, i) => i !== idx))}
                                className="text-slate-600 hover:text-red-400 p-1 rounded transition"
                              >
                                <Trash className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            TAB: STRATEGY
        ════════════════════════════════════════════════════ */}
        {activeTab === "strategy" && (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Strategy Intake</h2>
              <p className="text-sm text-slate-500">Upload strategy files and set brand settings. This guides AI generation in Phase 2.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

              {/* Brand Settings */}
              <div className="lg:col-span-1 space-y-5">
                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6 space-y-5">
                  <h3 className="text-sm font-semibold text-white">Brand Settings</h3>

                  <div>
                    <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">Brand / Creator Name</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={creatorMemory.creator_name || ""}
                        onChange={e => setCreatorMemory({ ...creatorMemory, creator_name: e.target.value })}
                        placeholder="@yourbrand"
                        className="flex-1 text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/40"
                      />
                      <button onClick={() => saveMemory()} className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg transition"><Save className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">Timezone</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={creatorMemory.timezone || "Asia/Kolkata"}
                        onChange={e => setCreatorMemory({ ...creatorMemory, timezone: e.target.value })}
                        className="flex-1 text-xs font-mono bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500/40"
                      />
                      <button onClick={() => saveMemory()} className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg transition"><Save className="w-3.5 h-3.5" /></button>
                    </div>
                    <p className="text-[9px] text-slate-600 mt-1 font-mono">Default: Asia/Kolkata</p>
                  </div>

                  <div className="pt-1">
                    <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-2">Content Pillars</label>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        placeholder="e.g. AI Automation"
                        value={newPillar}
                        onChange={e => setNewPillar(e.target.value)}
                        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); if (newPillar.trim()) { const p = [...(creatorMemory.content_pillars || []), newPillar.trim()]; const u = { ...creatorMemory, content_pillars: p }; saveMemory(u); setNewPillar(""); } } }}
                        className="flex-1 text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/40"
                      />
                      <button
                        onClick={() => { if (newPillar.trim()) { const p = [...(creatorMemory.content_pillars || []), newPillar.trim()]; const u = { ...creatorMemory, content_pillars: p }; saveMemory(u); setNewPillar(""); } }}
                        className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg transition"
                      ><Plus className="w-3.5 h-3.5" /></button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(creatorMemory.content_pillars || []).map((p, i) => (
                        <span key={i} className="inline-flex items-center gap-1 bg-blue-500/10 text-blue-300 text-[10px] font-medium px-2.5 py-1 rounded-full border border-blue-500/20">
                          {p}
                          <button onClick={() => { const u = { ...creatorMemory, content_pillars: (creatorMemory.content_pillars || []).filter((_, idx) => idx !== i) }; saveMemory(u); }} className="text-blue-400/60 hover:text-red-400 ml-0.5 transition">×</button>
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-1 border-t border-white/5">
                    <label className="block text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-2">Banned Phrases</label>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        placeholder="e.g. mind-blowing"
                        value={newBannedWord}
                        onChange={e => setNewBannedWord(e.target.value)}
                        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); if (newBannedWord.trim()) { const b = [...(creatorMemory.banned_phrases || []), newBannedWord.trim()]; const u = { ...creatorMemory, banned_phrases: b }; saveMemory(u); setNewBannedWord(""); } } }}
                        className="flex-1 text-xs bg-white/4 border border-white/8 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/40"
                      />
                      <button
                        onClick={() => { if (newBannedWord.trim()) { const b = [...(creatorMemory.banned_phrases || []), newBannedWord.trim()]; const u = { ...creatorMemory, banned_phrases: b }; saveMemory(u); setNewBannedWord(""); } }}
                        className="bg-red-600 hover:bg-red-500 text-white p-2 rounded-lg transition"
                      ><Plus className="w-3.5 h-3.5" /></button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(creatorMemory.banned_phrases || []).map((w, i) => (
                        <span key={i} className="inline-flex items-center gap-1 bg-red-500/10 text-red-300 text-[10px] font-medium px-2.5 py-1 rounded-full border border-red-500/20">
                          {w}
                          <button onClick={() => { const u = { ...creatorMemory, banned_phrases: (creatorMemory.banned_phrases || []).filter((_, idx) => idx !== i) }; saveMemory(u); }} className="text-red-400/60 hover:text-red-300 ml-0.5 transition">×</button>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Strategy files + Prompt */}
              <div className="lg:col-span-2 space-y-5">

                {/* Strategy file upload */}
                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Strategy Files</h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">Upload .txt, .md, or .csv files. Phase 1: preview only. Phase 2: used to guide AI generation.</p>
                    </div>
                  </div>
                  <div
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleStrategyFileUpload(f); }}
                    onClick={() => stratFileInputRef.current?.click()}
                    className="border-2 border-dashed border-white/8 hover:border-white/20 rounded-xl p-8 text-center cursor-pointer transition hover:bg-white/2"
                  >
                    <FileUp className="w-7 h-7 text-slate-600 mx-auto mb-2" />
                    <p className="text-xs text-slate-400">Drop strategy file or click to browse</p>
                    <p className="text-[10px] text-slate-600 mt-1">Accepts .txt · .md · .csv</p>
                    <input
                      ref={stratFileInputRef}
                      type="file"
                      accept=".txt,.md,.csv"
                      className="hidden"
                      onChange={e => { const f = e.target.files?.[0]; if (f) handleStrategyFileUpload(f); }}
                    />
                  </div>

                  {/* Uploaded files list */}
                  {strategyFiles.length > 0 && (
                    <div className="space-y-3">
                      {strategyFiles.map((f, i) => (
                        <div key={i} className="rounded-xl border border-white/8 bg-white/2 p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-violet-400" />
                              <div>
                                <p className="text-xs font-medium text-slate-200">{f.name}</p>
                                <p className="text-[9px] font-mono text-slate-500">{f.type.toUpperCase()} · {(f.size / 1024).toFixed(1)} KB</p>
                              </div>
                            </div>
                            <button
                              onClick={() => setStrategyFiles(prev => prev.filter((_, idx) => idx !== i))}
                              className="text-slate-600 hover:text-red-400 transition"
                            ><X className="w-3.5 h-3.5" /></button>
                          </div>
                          <div className="bg-white/2 rounded-lg p-3 font-mono text-[10px] text-slate-500 max-h-24 overflow-y-auto border border-white/4 whitespace-pre-wrap">
                            {f.preview}{f.preview.length >= 400 ? "..." : ""}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/5 border border-amber-500/15">
                    <Info className="w-4 h-4 text-amber-400 shrink-0" />
                    <p className="text-[10px] text-amber-300/70">
                      Strategy files are not stored permanently in Phase 1. They are previewed here only.
                      In Phase 2, they will be passed to the AI generation pipeline.
                    </p>
                  </div>
                </div>

                {/* Prompt template */}
                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Reusable Prompt Template</h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">Saved to prompts/reusable_script_prompt.txt</p>
                    </div>
                    <button
                      id="save-prompt-btn"
                      onClick={savePrompt}
                      className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
                    >
                      <Save className="w-3.5 h-3.5" /> Save
                    </button>
                  </div>
                  <textarea
                    rows={8}
                    value={promptContent}
                    onChange={e => setPromptContent(e.target.value)}
                    placeholder="Write your reusable script prompt template here..."
                    className="w-full text-xs font-mono bg-white/3 border border-white/8 rounded-xl p-4 text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/40 resize-none"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            TAB: APPROVAL
        ════════════════════════════════════════════════════ */}
        {activeTab === "approval" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white mb-1">Approval Queue</h2>
                <p className="text-sm text-slate-500">Review trends sorted by engagement. Approve the ones you want to use.</p>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                {/* Max approve selector */}
                <div className="flex items-center gap-2">
                  <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider whitespace-nowrap">Max trends</label>
                  <select
                    value={maxApprove}
                    onChange={e => setMaxApprove(Number(e.target.value))}
                    className="text-xs font-mono bg-white/4 border border-white/8 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none"
                  >
                    {[5, 10, 15, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <button
                  id="approve-top-n-btn"
                  onClick={approveTopN}
                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
                >
                  <ThumbsUp className="w-3.5 h-3.5" /> Approve Top {maxApprove}
                </button>
                <button
                  onClick={resetApprovals}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 border border-white/8 hover:border-white/16 px-3 py-2 rounded-lg transition"
                >
                  <RotateCw className="w-3.5 h-3.5" /> Reset
                </button>
              </div>
            </div>

            {/* Stats bar */}
            <div className="flex items-center gap-6 text-xs">
              <span className="text-slate-500">{trendsWithApproval.length} total</span>
              <span className="text-emerald-400 font-semibold">{approvedCount} approved</span>
              <span className="text-red-400">{rejectedCount} rejected</span>
              <span className="text-slate-600">{trendsWithApproval.length - approvedCount - rejectedCount} pending</span>
            </div>

            {trendsWithApproval.length === 0 ? (
              <div className="rounded-2xl border border-white/6 bg-[#171b27] p-16 text-center">
                <TrendingUp className="w-10 h-10 text-slate-700 mx-auto mb-4" />
                <p className="text-sm text-slate-500">No trends loaded yet.</p>
                <button onClick={() => setActiveTab("sources")} className="mt-4 text-blue-400 text-xs hover:text-blue-300 transition flex items-center gap-1 mx-auto">
                  Upload trends <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {trendsWithApproval.map((t, idx) => {
                  const state = t._approvalState;
                  return (
                    <div
                      key={idx}
                      className={`rounded-2xl border p-5 flex items-center gap-4 transition-all ${
                        state === "approved"
                          ? "border-emerald-500/30 bg-emerald-500/5"
                          : state === "rejected"
                          ? "border-red-500/15 bg-white/1 opacity-50"
                          : "border-white/6 bg-[#171b27]"
                      }`}
                    >
                      {/* Rank */}
                      <div className="w-8 text-center shrink-0">
                        <span className="font-mono text-xs text-slate-600">#{idx + 1}</span>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-semibold truncate ${state === "rejected" ? "text-slate-600" : "text-slate-200"}`}>
                          "{t.trend_title}"
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <PlatformBadge platform={t.platform} />
                          <span className="text-[10px] text-slate-500 font-mono">{fmtNum(t.views)} views</span>
                          <span className="text-[10px] font-mono font-semibold text-emerald-400">{t._engagementScore.toFixed(1)}% eng.</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          id={`approve-trend-${idx}`}
                          onClick={() => setApproval(idx, state === "approved" ? "pending" : "approved")}
                          className={`flex items-center gap-1.5 text-xs font-semibold px-3.5 py-1.5 rounded-lg border transition-all ${
                            state === "approved"
                              ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                              : "text-slate-500 border-white/8 hover:border-emerald-500/30 hover:text-emerald-400 hover:bg-emerald-500/8"
                          }`}
                        >
                          <Check className="w-3.5 h-3.5" />
                          {state === "approved" ? "Approved" : "Approve"}
                        </button>
                        <button
                          id={`reject-trend-${idx}`}
                          onClick={() => setApproval(idx, state === "rejected" ? "pending" : "rejected")}
                          className={`flex items-center gap-1.5 text-xs font-semibold px-3.5 py-1.5 rounded-lg border transition-all ${
                            state === "rejected"
                              ? "bg-red-500/20 text-red-400 border-red-500/30"
                              : "text-slate-500 border-white/8 hover:border-red-500/30 hover:text-red-400 hover:bg-red-500/8"
                          }`}
                        >
                          <X className="w-3.5 h-3.5" />
                          {state === "rejected" ? "Rejected" : "Reject"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Run from approval */}
            {approvedCount > 0 && (
              <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-white">{approvedCount} trend{approvedCount !== 1 ? "s" : ""} approved</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Pipeline will run on these trends only.</p>
                </div>
                <button
                  id="approval-run-btn"
                  onClick={handleRunPipeline}
                  disabled={isPipelineRunning}
                  className="flex items-center gap-2 bg-gradient-to-r from-[#4f72ff] to-[#7c3aed] hover:opacity-90 text-white text-sm font-semibold px-6 py-3 rounded-xl transition shadow-lg shadow-blue-500/20 disabled:opacity-50 shrink-0"
                >
                  {isPipelineRunning ? <RotateCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  Run Pipeline
                </button>
              </div>
            )}

            {approvedCount === 0 && trendsWithApproval.length > 0 && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                <p className="text-[11px] text-amber-300/80">
                  No trends approved yet. If you run the pipeline now, it will automatically use the top {maxApprove} trends by engagement score.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            TAB: CALENDAR
        ════════════════════════════════════════════════════ */}
        {activeTab === "calendar" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white mb-1">Content Calendar</h2>
                <p className="text-sm text-slate-500">Generated content — ready for human review.</p>
              </div>
              {hasResults && (
                <span className="text-[10px] font-mono text-slate-500">{calendarItems.length} items · Asia/Kolkata</span>
              )}
            </div>

            {!hasResults ? (
              <div className="rounded-2xl border border-white/6 bg-[#171b27] p-20 text-center space-y-5">
                <CalendarIcon className="w-12 h-12 text-slate-700 mx-auto" />
                <div>
                  <h3 className="text-base font-semibold text-white mb-2">No calendar generated yet</h3>
                  <p className="text-sm text-slate-500 max-w-sm mx-auto">Approve trends in the Approval tab and run the pipeline to generate your content calendar.</p>
                </div>
                <button
                  id="calendar-empty-run-btn"
                  onClick={handleRunPipeline}
                  disabled={isPipelineRunning}
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-[#4f72ff] to-[#7c3aed] hover:opacity-90 text-white text-sm font-semibold px-6 py-3 rounded-xl transition shadow-lg shadow-blue-500/20 disabled:opacity-50"
                >
                  {isPipelineRunning ? <RotateCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  Run Pipeline Now
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Calendar cards */}
                <div className="lg:col-span-2 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {calendarItems.map((item, idx) => {
                      const isSelected = selectedPost?.topic === item.topic;
                      return (
                        <div
                          key={idx}
                          id={`cal-item-${idx}`}
                          onClick={() => setSelectedPost(item)}
                          className={`card-glow rounded-2xl border p-5 cursor-pointer transition-all ${
                            isSelected
                              ? "border-blue-500/40 bg-blue-500/8"
                              : "border-white/6 bg-[#171b27] hover:border-white/12"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <PlatformBadge platform={item.platform} />
                            <span className="font-mono text-[10px] text-slate-600 flex items-center gap-1">
                              <CalendarIcon className="w-3 h-3" /> {item.date}
                            </span>
                          </div>
                          <h4 className="text-xs font-semibold text-slate-200 line-clamp-2 mb-2">{item.topic}</h4>
                          <p className="text-[10px] text-slate-500 italic line-clamp-2 mb-4">"{item.hook}"</p>
                          <div className="flex items-center justify-between pt-3 border-t border-white/5">
                            <span className="text-[10px] font-medium text-slate-500 bg-white/4 px-2 py-0.5 rounded">{item.content_pillar}</span>
                            <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full ${
                              item.human_review_status === "Approved"
                                ? "text-emerald-400 bg-emerald-500/10"
                                : "text-slate-500 bg-white/4"
                            }`}>{item.human_review_status}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Detail panel */}
                <div className="lg:col-span-1 rounded-2xl border border-white/6 bg-[#171b27] p-5 sticky top-24 self-start">
                  {selectedPost ? (
                    <div className="space-y-5">
                      <div className="border-b border-white/5 pb-4">
                        <div className="flex items-center justify-between mb-2">
                          <PlatformBadge platform={selectedPost.platform} />
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            selectedPost.priority === "High" ? "text-red-400 bg-red-500/10" : "text-blue-400 bg-blue-500/10"
                          }`}>{selectedPost.priority} Priority</span>
                        </div>
                        <h3 className="text-sm font-semibold text-white">{selectedPost.topic}</h3>
                        <p className="text-[10px] text-slate-500 mt-1 font-mono flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {selectedPost.date} · {selectedPost.local_time}
                        </p>
                      </div>

                      {/* Approval status toggle */}
                      <div>
                        <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-2">Review Status</p>
                        <div className="grid grid-cols-3 gap-1.5">
                          {["Needs Review", "Approved", "Scheduled"].map(st => (
                            <button
                              key={st}
                              onClick={() => {
                                const updated = calendarItems.map(item =>
                                  item.topic === selectedPost.topic ? { ...item, human_review_status: st } : item
                                );
                                setCalendarItems(updated);
                                setSelectedPost({ ...selectedPost, human_review_status: st });
                                notify(`Status → ${st}`);
                              }}
                              className={`text-[9px] font-semibold py-1.5 rounded-lg border transition-all ${
                                selectedPost.human_review_status === st
                                  ? "bg-blue-500/20 text-blue-300 border-blue-500/30"
                                  : "text-slate-500 border-white/8 hover:text-slate-300 hover:border-white/16"
                              }`}
                            >{st}</button>
                          ))}
                        </div>
                      </div>

                      <div className="bg-white/2 rounded-xl p-3 border border-white/5">
                        <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-1">Hook</p>
                        <blockquote className="text-[11px] text-slate-300 italic leading-relaxed">"{selectedPost.hook}"</blockquote>
                      </div>

                      <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-3">
                        <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-1">CTA</p>
                        <p className="text-[11px] text-emerald-300 font-medium leading-relaxed">{selectedPost.cta}</p>
                      </div>

                      <div className="bg-white/2 rounded-xl p-3 border border-white/5">
                        <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-1">Repurpose Plan</p>
                        <p className="text-[10px] text-slate-400 font-mono leading-relaxed">{selectedPost.repurpose_plan}</p>
                      </div>

                      <div className="flex items-center justify-between border-t border-white/5 pt-4">
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(
                              `Topic: ${selectedPost.topic}\nPlatform: ${selectedPost.platform}\nHook: "${selectedPost.hook}"\nCTA: ${selectedPost.cta}\nScheduled: ${selectedPost.date} at ${selectedPost.local_time}`
                            );
                            notify("Content package copied!");
                          }}
                          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
                        >
                          <Copy className="w-3.5 h-3.5" /> Copy
                        </button>
                        <button onClick={() => setSelectedPost(null)} className="text-[10px] text-slate-600 hover:text-slate-400 transition">Deselect</button>
                      </div>
                    </div>
                  ) : (
                    <div className="h-80 flex flex-col items-center justify-center text-center space-y-3">
                      <Eye className="w-8 h-8 text-slate-700" />
                      <p className="text-xs text-slate-600">Select a calendar item to review its hook, CTA, and repurpose plan.</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            TAB: REPORT
        ════════════════════════════════════════════════════ */}
        {activeTab === "report" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Report</h2>
              <p className="text-sm text-slate-500">Pipeline output report and execution logs.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Report content */}
              <div className="lg:col-span-2 space-y-5">
                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-6">
                  <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Run Report</h3>
                      <p className="text-[10px] text-slate-500 mt-0.5">data/exports/run_report.md</p>
                    </div>
                    {reportMd && (
                      <button
                        onClick={() => { navigator.clipboard.writeText(reportMd); notify("Report copied!"); }}
                        className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 hover:text-slate-300 bg-white/4 hover:bg-white/8 border border-white/8 px-3 py-1.5 rounded-lg transition"
                      >
                        <Copy className="w-3 h-3" /> Copy MD
                      </button>
                    )}
                  </div>

                  {reportMd ? (
                    <div className="space-y-5">
                      <pre className="font-mono text-[11px] text-slate-400 overflow-y-auto max-h-80 leading-relaxed whitespace-pre-wrap bg-white/2 border border-white/5 rounded-xl p-4">
                        {reportMd}
                      </pre>

                      {/* Calendar table summary */}
                      {calendarItems.length > 0 && (
                        <div className="overflow-x-auto rounded-xl border border-white/5">
                          <table className="w-full text-left text-[11px] text-slate-500">
                            <thead className="bg-white/3 border-b border-white/5 font-mono text-[9px] uppercase tracking-wider">
                              <tr>
                                <th className="px-4 py-2.5">Date</th>
                                <th className="px-4 py-2.5">Platform</th>
                                <th className="px-4 py-2.5">Pillar</th>
                                <th className="px-4 py-2.5">Topic</th>
                                <th className="px-4 py-2.5 text-center">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/3">
                              {calendarItems.map((item, idx) => (
                                <tr key={idx} className="hover:bg-white/2">
                                  <td className="px-4 py-2.5 font-mono text-slate-400">{item.date}</td>
                                  <td className="px-4 py-2.5"><PlatformBadge platform={item.platform} /></td>
                                  <td className="px-4 py-2.5 text-slate-500">{item.content_pillar}</td>
                                  <td className="px-4 py-2.5 text-slate-300 max-w-xs truncate">{item.topic}</td>
                                  <td className="px-4 py-2.5 text-center">
                                    <StatusBadge label={item.human_review_status} type={item.human_review_status === "Approved" ? "success" : "neutral"} />
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="h-48 flex flex-col items-center justify-center text-center space-y-3">
                      <FileText className="w-8 h-8 text-slate-700" />
                      <p className="text-xs text-slate-600">No report yet. Run the pipeline to generate output.</p>
                    </div>
                  )}
                </div>

                {/* Pipeline logs */}
                {pipelineLogs && (
                  <div className="rounded-2xl border border-white/5 bg-[#0a0d16] p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">Pipeline Logs</span>
                      <button
                        onClick={() => { navigator.clipboard.writeText(pipelineLogs); notify("Logs copied!"); }}
                        className="text-[9px] font-mono text-slate-600 hover:text-slate-400 bg-white/4 px-2 py-1 rounded transition"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="font-mono text-[10px] text-slate-400 overflow-y-auto max-h-64 leading-relaxed whitespace-pre-wrap">
                      {pipelineLogs}
                    </pre>
                  </div>
                )}
              </div>

              {/* Sidebar: exports + rules */}
              <div className="lg:col-span-1 space-y-5">
                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-5 space-y-4">
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Output Files</h4>
                  {[
                    { fn: "content_calendar.csv", desc: "Spreadsheet export", icon: FileText, color: "text-emerald-400" },
                    { fn: "content_calendar.json", desc: "JSON data export", icon: Layers, color: "text-violet-400" },
                    { fn: "run_report.md", desc: "Executive summary", icon: BookOpen, color: "text-blue-400" },
                  ].map(({ fn, desc, icon: Icon, color }) => (
                    <div key={fn} className="flex items-center gap-3 bg-white/2 p-3 rounded-lg border border-white/5">
                      <Icon className={`w-4 h-4 ${color} shrink-0`} />
                      <div className="min-w-0">
                        <p className="text-[10px] font-mono text-slate-300 truncate">{fn}</p>
                        <p className="text-[9px] text-slate-600">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-2xl border border-white/6 bg-[#171b27] p-5 space-y-3">
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Safety Rules</h4>
                  <ul className="space-y-2 font-mono text-[10px] text-slate-500">
                    {[
                      "No auto-posting. Human review required.",
                      "API keys are never saved to disk.",
                      "Free Mode works without any API key.",
                      "No platform scraping in Phase 1.",
                      "Outputs saved to /data/exports only.",
                    ].map(r => <li key={r} className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">✓</span>{r}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
