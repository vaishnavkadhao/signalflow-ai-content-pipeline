import express from "express";
import path from "path";
import fs from "fs";
import { exec } from "child_process";
import { createServer as createViteServer } from "vite";

const PROJECT_ROOT = process.cwd();

// ─── Python Resolver ─────────────────────────────────────────────────────────
/**
 * Resolve the correct Python executable for the current OS.
 * Priority: .venv (Windows) → .venv (Unix) → system python3 → python
 */
function getPythonExecutable(): string {
  const winVenv = path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe");
  const unixVenv = path.join(PROJECT_ROOT, ".venv", "bin", "python3");

  if (fs.existsSync(winVenv)) return `"${winVenv}"`;
  if (fs.existsSync(unixVenv)) return unixVenv;
  // Fall back to system python
  return process.platform === "win32" ? "python" : "python3";
}

// ─── CSV Helpers ─────────────────────────────────────────────────────────────
/** Parse CSV content into an array of objects (handles quoted fields). */
function parseCSV(content: string): any[] {
  const lines = content.split("\n").map(l => l.trim()).filter(Boolean);
  if (lines.length === 0) return [];

  const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
  const items: any[] = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const matches = line.match(/(\".*?\"|[^\",\s]+|(?<=,)(?=,))/g) || [];
    const item: any = {};
    headers.forEach((h, idx) => {
      let val = matches[idx] || "";
      val = val.trim().replace(/^"|"$/g, "");
      item[h] = val;
    });
    items.push(item);
  }
  return items;
}

/** Serialize an array of objects to CSV (legacy format for backward compat). */
function formatCSV(items: any[]): string {
  if (items.length === 0) return "";
  const headers = ["trend_title", "views", "likes", "comments", "shares", "platform", "url"];
  const lines = [headers.join(",")];

  for (const item of items) {
    const row = headers.map(h => {
      const val = String(item[h] || "");
      if (val.includes(",") || val.includes('"') || val.includes("\n")) {
        return `"${val.replace(/"/g, '""')}"`;
      }
      return val;
    });
    lines.push(row.join(","));
  }
  return lines.join("\n") + "\n";
}

/** Write an approved trends array to a temporary CSV for pipeline consumption. */
function writeApprovedTrendsCsv(trends: any[]): string {
  const runtimeDir = path.join(PROJECT_ROOT, "data", "runtime");
  fs.mkdirSync(runtimeDir, { recursive: true });
  const outPath = path.join(runtimeDir, "approved_trends.csv");
  fs.writeFileSync(outPath, formatCSV(trends), "utf-8");
  return outPath;
}

// ─── Server Setup ─────────────────────────────────────────────────────────────
async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;

  app.use(express.json({ limit: "5mb" }));
  app.use(express.urlencoded({ extended: true, limit: "5mb" }));

  // ── API 1: Get trends ────────────────────────────────────────────────────
  app.get("/api/trends", (req, res) => {
    const csvPath = path.join(PROJECT_ROOT, "data", "sample_trends.csv");
    try {
      if (!fs.existsSync(csvPath)) return res.json([]);
      const content = fs.readFileSync(csvPath, "utf-8");
      res.json(parseCSV(content));
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 2: Save trends ───────────────────────────────────────────────────
  app.post("/api/trends", (req, res) => {
    const csvPath = path.join(PROJECT_ROOT, "data", "sample_trends.csv");
    try {
      const trends = req.body;
      if (!Array.isArray(trends)) {
        return res.status(400).json({ error: "Payload must be an array of trend objects" });
      }
      fs.writeFileSync(csvPath, formatCSV(trends), "utf-8");
      res.json({ success: true, count: trends.length });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 3: Get prompt template ───────────────────────────────────────────
  app.get("/api/prompts", (req, res) => {
    const promptPath = path.join(PROJECT_ROOT, "prompts", "reusable_script_prompt.txt");
    try {
      if (!fs.existsSync(promptPath)) return res.json({ content: "" });
      res.json({ content: fs.readFileSync(promptPath, "utf-8") });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 4: Save prompt template ──────────────────────────────────────────
  app.post("/api/prompts", (req, res) => {
    const promptPath = path.join(PROJECT_ROOT, "prompts", "reusable_script_prompt.txt");
    try {
      const { content } = req.body;
      if (typeof content !== "string") {
        return res.status(400).json({ error: "Prompt content must be a string" });
      }
      fs.mkdirSync(path.dirname(promptPath), { recursive: true });
      fs.writeFileSync(promptPath, content, "utf-8");
      res.json({ success: true });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 5: Get creator memory ────────────────────────────────────────────
  app.get("/api/creator-memory", (req, res) => {
    const memoryPath = path.join(PROJECT_ROOT, "creator_memory", "tone_rules.json");
    try {
      if (!fs.existsSync(memoryPath)) return res.json({});
      res.json(JSON.parse(fs.readFileSync(memoryPath, "utf-8")));
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 6: Save creator memory ───────────────────────────────────────────
  app.post("/api/creator-memory", (req, res) => {
    const memoryPath = path.join(PROJECT_ROOT, "creator_memory", "tone_rules.json");
    try {
      const config = req.body;
      fs.mkdirSync(path.dirname(memoryPath), { recursive: true });
      fs.writeFileSync(memoryPath, JSON.stringify(config, null, 2), "utf-8");
      res.json({ success: true });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 7: Fetch pipeline output results ─────────────────────────────────
  app.get("/api/results", (req, res) => {
    const calendarJsonPath = path.join(PROJECT_ROOT, "data", "exports", "content_calendar.json");
    const reportMdPath = path.join(PROJECT_ROOT, "data", "exports", "run_report.md");

    let calendarData: any[] = [];
    let reportMdContent = "";
    let exists = false;

    try {
      if (fs.existsSync(calendarJsonPath)) {
        calendarData = JSON.parse(fs.readFileSync(calendarJsonPath, "utf-8"));
        exists = true;
      }
      if (fs.existsSync(reportMdPath)) {
        reportMdContent = fs.readFileSync(reportMdPath, "utf-8");
        exists = true;
      }
      res.json({ exists, calendar: calendarData, report: reportMdContent });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── API 8: Run the Python pipeline ───────────────────────────────────────
  /**
   * Body params:
   *   dry_run        boolean  — whether to skip LLM calls (default true)
   *   use_llm        boolean  — enable LLM generation (default false)
   *   approved_trends array  — if provided, pipeline runs on these trends only
   *   max_trends     number  — limit top N trends if no approval list given
   *   gemini_api_key string  — BYOK key, passed via env, never logged or stored
   *   mode           string  — "free" | "ai_assist" | "pro" (informational for now)
   */
  app.post("/api/pipeline/run", (req, res) => {
    const {
      use_llm = false,
      dry_run = true,
      approved_trends,
      max_trends,
      gemini_api_key,
    } = req.body;

    // Determine input CSV
    let inputCsv = path.join("data", "sample_trends.csv");

    if (Array.isArray(approved_trends) && approved_trends.length > 0) {
      // Write to temporary runtime file — do NOT overwrite sample_trends.csv
      const runtimePath = writeApprovedTrendsCsv(approved_trends);
      // Use relative path for the Python command
      inputCsv = path.relative(PROJECT_ROOT, runtimePath);
    }

    const python = getPythonExecutable();
    const dryRunFlag = dry_run ? "--dry-run" : "";
    const useLlmFlag = use_llm ? "--use-llm" : "";
    const maxTrendsFlag = max_trends ? `--max-trends ${Number(max_trends)}` : "";

    const command = `${python} -m workflows.run_pipeline --input "${inputCsv}" ${dryRunFlag} ${useLlmFlag} ${maxTrendsFlag}`.trim();
    console.log(`[SignalFlow AI] Running: ${command}`);

    // Build a safe env — pass Gemini key if provided, but never log it
    const runEnv: NodeJS.ProcessEnv = { ...process.env, PYTHONPATH: "." };
    if (typeof gemini_api_key === "string" && gemini_api_key.trim()) {
      runEnv.GEMINI_API_KEY = gemini_api_key.trim();
    }

    exec(command, { env: runEnv, cwd: PROJECT_ROOT }, (error, stdout, stderr) => {
      const success = !error;
      const calendarJsonPath = path.join(PROJECT_ROOT, "data", "exports", "content_calendar.json");
      const reportMdPath = path.join(PROJECT_ROOT, "data", "exports", "run_report.md");

      let calendarData: any[] = [];
      let reportMdContent = "";

      try {
        if (success && fs.existsSync(calendarJsonPath)) {
          calendarData = JSON.parse(fs.readFileSync(calendarJsonPath, "utf-8"));
        }
        if (success && fs.existsSync(reportMdPath)) {
          reportMdContent = fs.readFileSync(reportMdPath, "utf-8");
        }
      } catch (ex) {
        console.error("[SignalFlow AI] Error reading pipeline outputs:", ex);
      }

      res.json({
        success,
        stdout,
        stderr,
        error: error ? error.message : null,
        calendar: calendarData,
        report: reportMdContent,
      });
    });
  });

  // ── API 9: CSV health check ───────────────────────────────────────────────
  app.post("/api/csv-health-check", (req, res) => {
    const { csv_text } = req.body;
    if (typeof csv_text !== "string") {
      return res.status(400).json({ error: "csv_text must be a string" });
    }

    const lines = csv_text.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length < 2) {
      return res.json({ valid: false, errors: ["CSV has no data rows (only a header or is empty)"] });
    }

    const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, "").toLowerCase());
    const errors: string[] = [];
    const warnings: string[] = [];

    // Required: at least a title column
    const hasTopic = headers.some(h => ["topic", "trend_title", "title"].includes(h));
    if (!hasTopic) {
      errors.push("Missing required column: topic, trend_title, or title");
    }

    // Required: platform
    if (!headers.includes("platform")) {
      errors.push("Missing required column: platform");
    }

    // Recommended
    const hasUrl = headers.some(h => ["source_url", "url", "post_url"].includes(h));
    if (!hasUrl) warnings.push("Recommended column missing: source_url or url");
    if (!headers.includes("posted_date")) warnings.push("Recommended column missing: posted_date");

    const numericCols = ["views", "likes", "comments", "shares"];
    numericCols.forEach(col => {
      if (!headers.includes(col)) warnings.push(`Recommended column missing: ${col}`);
    });

    const rowCount = lines.length - 1;
    res.json({
      valid: errors.length === 0,
      errors,
      warnings,
      row_count: rowCount,
      detected_columns: headers,
    });
  });

  // ── Vite integration ──────────────────────────────────────────────────────
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(PROJECT_ROOT, "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`SignalFlow AI server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
