import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Database,
  FileCheck2,
  HeartPulse,
  LogOut,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  UploadCloud,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

const sections = [
  { id: "operations", label: "Clinical Operations", icon: HeartPulse },
  { id: "partner", label: "Partner Portal", icon: UploadCloud },
  { id: "qms", label: "QMS", icon: FileCheck2 },
  { id: "producer", label: "Data Producer", icon: Activity },
  { id: "exports", label: "Exports", icon: Database },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "health", label: "System Health", icon: ShieldCheck },
];

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

async function apiRequest(path, { token, method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  return response.headers.get("content-type")?.includes("application/json")
    ? response.json()
    : null;
}

async function login(username, password) {
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value || 0));
}

function MetricCard({ label, value, tone = "neutral" }) {
  return (
    <div className={cx("metric-card", tone)}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusPill({ status }) {
  const normalized = String(status || "Unknown");
  const tone = normalized.toLowerCase().includes("fail")
    ? "danger"
    : normalized.toLowerCase().includes("running")
      ? "warning"
      : normalized.toLowerCase().includes("pass") || normalized.toLowerCase().includes("ok")
        ? "success"
        : "neutral";
  return <span className={cx("status-pill", tone)}>{normalized}</span>;
}

function LoginPanel({ onLogin }) {
  const [username, setUsername] = useState("sysadmin");
  const [password, setPassword] = useState("ClinicalDemo!2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await login(username, password);
      if (payload.mfa_required) {
        setError("MFA is required for this account. Use API docs or a non-MFA demo user until React MFA is added.");
        return;
      }
      onLogin(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div>
          <p className="eyebrow">Clinical source-system simulator</p>
          <h1>Clinical Donor Platform</h1>
          <p className="lede">
            FastAPI operational app for donor screening, partner workflow, QMS, vendor SLA,
            validation, and source batch exports.
          </p>
        </div>
        <form onSubmit={submit} className="login-form">
          <label>
            Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <div className="error-state">{error}</div>}
          <button type="submit" disabled={busy}>
            {busy ? <RefreshCw size={16} /> : <ShieldCheck size={16} />}
            {busy ? "Signing in" : "Sign In"}
          </button>
        </form>
      </section>
    </main>
  );
}

function OperationsSection({ status }) {
  const counts = status?.row_counts || {};
  return (
    <div className="content-grid">
      <MetricCard label="Donors" value={formatNumber(counts.dim_donor)} />
      <MetricCard label="Screenings" value={formatNumber(counts.fact_donor_screening)} />
      <MetricCard label="Eligibility Decisions" value={formatNumber(counts.fact_eligibility_decision)} />
      <MetricCard label="Workflow Tasks" value={formatNumber(counts.fact_workflow_task)} />
      <MetricCard label="Partner Submissions" value={formatNumber(counts.dim_partner_submission)} />
      <MetricCard label="Documents" value={formatNumber(counts.dim_secure_document)} />
      <MetricCard label="QMS Deviations" value={formatNumber(counts.fact_deviation)} tone="warning" />
      <MetricCard label="Vendor SLA Events" value={formatNumber(counts.fact_vendor_incident)} tone="warning" />
    </div>
  );
}

function ProducerControls({ token, refresh }) {
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");

  async function runAction(action, path, body = {}) {
    setBusyAction(action);
    setMessage("");
    try {
      const result = await apiRequest(`${path}?confirm=true`, {
        token,
        method: "POST",
        body,
      });
      setMessage(`${action} ${result?.status || "submitted"}`);
      await refresh();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <div className="operation-panel">
      <button onClick={() => runAction("Incremental generation", "/api/generation/incremental", { seed: 42, scale: 1 })}>
        <Play size={16} />
        Incremental
      </button>
      <button onClick={() => runAction("Validation", "/api/generation/validate")}>
        <CheckCircle2 size={16} />
        Validate
      </button>
      <button onClick={() => runAction("Export", "/api/generation/export", { batch_id: `react_${Date.now()}` })}>
        <Database size={16} />
        Export
      </button>
      <button
        onClick={() =>
          runAction("Continuous generation", "/api/generation/continuous/start", {
            interval_seconds: 1,
            cycles: 1,
            seed: 42,
            scale: 1,
            allow_infinite: false,
          })
        }
      >
        <Activity size={16} />
        One Cycle
      </button>
      <button onClick={() => runAction("Stop", "/api/generation/continuous/stop")}>
        <Square size={16} />
        Stop
      </button>
      {busyAction && <span className="muted">Running {busyAction}...</span>}
      {message && <span className="message">{message}</span>}
    </div>
  );
}

function Table({ rows, columns }) {
  if (!rows?.length) return <div className="empty-state">No records available.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{Array.isArray(row[column]) ? row[column].length : String(row[column] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectionBody({ active, status, token, refresh }) {
  const validation = status?.latest_validation || {};
  const manifest = status?.latest_export_manifest || {};
  const freshness = status?.source_freshness?.freshness || [];
  const runs = status?.recent_runs || [];

  if (active === "operations") return <OperationsSection status={status} />;
  if (active === "partner") {
    return (
      <div className="info-list">
        <MetricCard label="Partner Submissions" value={formatNumber(status?.row_counts?.dim_partner_submission)} />
        <MetricCard label="Partner Messages" value={formatNumber(status?.row_counts?.fact_partner_message)} />
        <MetricCard label="Partner Documents" value={formatNumber(status?.row_counts?.dim_partner_document)} />
        <p>Partner operations are served by FastAPI endpoints and will be rebuilt as React operational screens.</p>
      </div>
    );
  }
  if (active === "qms") {
    return (
      <div className="content-grid">
        <MetricCard label="Open Deviations" value={formatNumber(status?.row_counts?.fact_deviation)} tone="warning" />
        <MetricCard label="CAPA Records" value={formatNumber(status?.row_counts?.fact_capa)} tone="warning" />
        <MetricCard label="Audit Events" value={formatNumber(status?.row_counts?.fact_audit_log)} />
        <MetricCard label="Training Records" value={formatNumber(status?.row_counts?.dim_training_record)} />
      </div>
    );
  }
  if (active === "producer") {
    return (
      <>
        <ProducerControls token={token} refresh={refresh} />
        <div className="split">
          <section>
            <h3>Recent Runs</h3>
            <Table rows={runs} columns={["run_type", "status", "started_at", "duration_seconds", "extraction_batch_id"]} />
          </section>
          <section>
            <h3>Validation</h3>
            <StatusPill status={validation.status || "Not run"} />
            <Table rows={validation.checks || []} columns={["name", "passed", "severity", "detail"]} />
          </section>
        </div>
      </>
    );
  }
  if (active === "exports") {
    return (
      <section>
        <h3>Latest Export Manifest</h3>
        <p className="muted">Batch: {manifest.batch_id || "None"}</p>
        <Table rows={manifest.files || []} columns={["table", "file", "row_count"]} />
      </section>
    );
  }
  if (active === "analytics") {
    return (
      <div className="analytics-panel">
        <BarChart3 size={28} />
        <h3>Power BI Service Strategy</h3>
        <p>
          Clinical analytics will flow through Snowflake and dbt into Power BI Service, then surface
          through <strong> teemails.com/analytics</strong>. Production analytics live outside this operational app.
        </p>
      </div>
    );
  }
  return (
    <div className="split">
      <section>
        <h3>Source Freshness</h3>
        <Table rows={freshness} columns={["entity", "watermark_column", "latest_watermark"]} />
      </section>
      <section>
        <h3>Continuous Producer</h3>
        <StatusPill status={status?.continuous?.running ? "Running" : "Stopped"} />
        <pre>{JSON.stringify(status?.continuous || {}, null, 2)}</pre>
      </section>
    </div>
  );
}

function App() {
  const [tokenPayload, setTokenPayload] = useState(() => {
    const raw = window.localStorage.getItem("clinical_token_payload");
    return raw ? JSON.parse(raw) : null;
  });
  const [active, setActive] = useState("operations");
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const token = tokenPayload?.access_token;

  const activeSection = useMemo(() => sections.find((section) => section.id === active), [active]);

  async function refresh() {
    if (!token) return;
    setError("");
    try {
      const [generationStatus, runs] = await Promise.all([
        apiRequest("/api/generation/status", { token }),
        apiRequest("/api/generation/runs?limit=25", { token }),
      ]);
      setStatus({ ...generationStatus, recent_runs: runs });
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
  }, [token]);

  function handleLogin(payload) {
    setTokenPayload(payload);
    window.localStorage.setItem("clinical_token_payload", JSON.stringify(payload));
  }

  function logout() {
    setTokenPayload(null);
    window.localStorage.removeItem("clinical_token_payload");
  }

  if (!tokenPayload) return <LoginPanel onLogin={handleLogin} />;

  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          <HeartPulse size={24} />
          <div>
            <strong>Clinical Donor</strong>
            <span>Source System</span>
          </div>
        </div>
        <nav>
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={cx(active === section.id && "active")}
                onClick={() => setActive(section.id)}
              >
                <Icon size={17} />
                {section.label}
              </button>
            );
          })}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Azure-ready FastAPI + React</p>
            <h1>{activeSection?.label}</h1>
          </div>
          <div className="topbar-actions">
            <button onClick={refresh}>
              <RefreshCw size={16} />
              Refresh
            </button>
            <button onClick={logout}>
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        </header>
        {error && (
          <div className="error-state">
            <AlertTriangle size={16} />
            {error}
          </div>
        )}
        <SectionBody active={active} status={status || {}} token={token} refresh={refresh} />
      </main>
    </div>
  );
}

export default App;
