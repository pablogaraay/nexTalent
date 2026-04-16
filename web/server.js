import cors from "cors";
import express from "express";
import multer from "multer";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const tempDir = path.join(os.tmpdir(), "nextalent-web");

const app = express();
const upload = multer({ dest: tempDir });
const apiPort = Number(process.env.API_PORT || 8787);

app.use(cors());
app.use(express.json({ limit: "2mb" }));
app.use(express.urlencoded({ extended: true }));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, timestamp: new Date().toISOString() });
});

function extractJsonFromStdout(stdoutText) {
  const start = stdoutText.indexOf("{");
  const end = stdoutText.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    throw new Error("No se pudo extraer JSON de la salida del proceso.");
  }
  return stdoutText.slice(start, end + 1);
}

function runPythonProcess({ script, args = [] }) {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", [script, ...args], {
      cwd: projectRoot,
      env: process.env
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("close", (code) => {
      if (code !== 0) {
        return reject(
          new Error(stderr || stdout || `El proceso Python terminó con código ${code}.`)
        );
      }
      resolve(stdout);
    });
  });
}

async function ensureTempDir() {
  await fs.mkdir(tempDir, { recursive: true });
}

app.post("/api/search", upload.single("cv"), async (req, res) => {
  await ensureTempDir();

  const profileText = (req.body.profileText || "").trim();
  let cvPath = req.file?.path || "";

  if (cvPath) {
    const originalExt = path.extname(req.file?.originalname || "").toLowerCase();
    if (originalExt !== ".pdf") {
      await fs.unlink(cvPath).catch(() => undefined);
      return res.status(400).json({
        error: "Solo se aceptan archivos con extensión .pdf."
      });
    }
  }

  // Preserve original extension so Python CV parser can detect .pdf reliably.
  if (cvPath && req.file?.originalname) {
    const originalExt = path.extname(req.file.originalname || "").toLowerCase();
    const hasExt = Boolean(path.extname(cvPath));
    if (originalExt && !hasExt) {
      const cvPathWithExt = `${cvPath}${originalExt}`;
      await fs.rename(cvPath, cvPathWithExt);
      cvPath = cvPathWithExt;
    }
  }

  if (!profileText && !cvPath) {
    if (cvPath) {
      await fs.unlink(cvPath).catch(() => undefined);
    }
    return res.status(400).json({
      error: "Debes enviar al menos un prompt de perfil o un archivo CV (.pdf)."
    });
  }

  const args = ["multiagent_cli.py", "--profile-text", profileText];
  if (cvPath) {
    args.push("--cv-file", cvPath);
  }

  try {
    const stdout = await runPythonProcess({ script: "multiagent_cli.py", args: args.slice(1) });
    const payload = JSON.parse(extractJsonFromStdout(stdout));
    return res.json(payload);
  } catch (error) {
    return res.status(500).json({
      error: "Falló la ejecución del flujo multiagente.",
      details: String(error)
    });
  } finally {
    if (cvPath) {
      await fs.unlink(cvPath).catch(() => undefined);
    }
  }
});

app.get("/api/insights", async (req, res) => {
  const topN = Number(req.query.topN || 10);
  const safeTopN = Number.isFinite(topN) ? Math.max(1, Math.min(topN, 50)) : 10;

  try {
    const stdout = await runPythonProcess({
      script: "multiagent_cli.py",
      args: ["--use-case", "market_insights", "--top-n", String(safeTopN)]
    });
    const payload = JSON.parse(extractJsonFromStdout(stdout));
    return res.json(payload);
  } catch (error) {
    return res.status(500).json({
      error: "Falló la generación de insights de mercado.",
      details: String(error)
    });
  }
});

const server = app.listen(apiPort, () => {
  console.log(`API web escuchando en http://localhost:${apiPort}`);
});

server.on("error", (error) => {
  if (error?.code === "EADDRINUSE") {
    console.error(
      `El puerto ${apiPort} ya está en uso. Lanza con otro puerto, por ejemplo: API_PORT=8788 npm run dev:api`
    );
    process.exit(1);
  }
  throw error;
});
