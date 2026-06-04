import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bell,
  CheckCircle2,
  Database,
  FileCheck2,
  HeartPulse,
  Home,
  KeyRound,
  LogIn,
  LogOut,
  Mail,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  UploadCloud,
  User,
  UserPlus,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function resolvePublicBase() {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/Clinical")) {
    return "/Clinical";
  }
  return "";
}

function resolveApiBase() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");
  return resolvePublicBase();
}

const PUBLIC_BASE = resolvePublicBase();
const API_BASE = resolveApiBase();

const PASSWORD_RESET_NOTICE = "If the email matches an account in our system, a reset link will be sent.";
const INTERNAL_ADMIN_ASSIGNED_ROLES = [
  "Operations Manager",
  "Clinical Reviewer",
  "QA Specialist",
  "Vendor Operations Analyst",
  "Donor Intake Coordinator",
];
const MONITOR_LINK_ROLES = ["System Administrator", "Business Technology Analyst", "Operations Manager"];
const EXTERNAL_REQUEST_TYPES = [
  { value: "Partner", label: "Partner", assignedRole: "Partner External User" },
  { value: "Supplier", label: "Supplier", assignedRole: "Supplier External User" },
];
const EXTERNAL_ROLE_BY_REQUEST_TYPE = Object.fromEntries(
  EXTERNAL_REQUEST_TYPES.map((requestType) => [requestType.value, requestType.assignedRole]),
);
const DEMO_LOGIN_PROFILES = [
  { label: "Demo User", username: "clinical", role: "Clinical Reviewer", icon: Play },
  { label: "Demo QA", username: "qa", role: "Quality Assurance Specialist", icon: ShieldCheck },
  { label: "Demo Operations", username: "opsmanager", role: "Operations Manager", icon: User },
];
const DEMO_LOGIN_PASSWORD = "ClinicalDemo!2026";
const DEMO_LOGIN_MFA_CODE = "000000";
const DEMO_LOGIN_USERNAMES = new Set(DEMO_LOGIN_PROFILES.map((profile) => profile.username));

const portfolioLinks = [
  { label: "Home", href: "https://teemails.com", icon: Home },
  { label: "ERP", href: "/ERP", icon: Database },
  { label: "HR", href: "/HR", icon: User },
  { label: "Clinical", href: "/Clinical", icon: HeartPulse },
  { label: "Monitor", href: "/Monitor", icon: Activity, requiresMonitorAccess: true },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
];

const sections = [
  { id: "dashboard", label: "Dashboard", route: "/dashboard", icon: HeartPulse },
  { id: "referrals", label: "Donor Referrals", route: "/referrals", icon: UserPlus },
  { id: "screening", label: "Screening Queue", route: "/screening", icon: CheckCircle2 },
  {
    id: "clinical_review",
    label: "Clinical Review",
    route: "/clinical-review",
    icon: ShieldCheck,
    roles: ["System Administrator", "Operations Manager", "Clinical Reviewer", "Quality Assurance Specialist"],
  },
  {
    id: "eligibility",
    label: "Eligibility",
    route: "/eligibility",
    icon: FileCheck2,
    roles: ["System Administrator", "Operations Manager", "Clinical Reviewer", "Quality Assurance Specialist"],
  },
  { id: "recovery_cases", label: "Recovery Cases", route: "/recovery-cases", icon: Database },
  {
    id: "partner",
    label: "Partner Portal",
    route: "/partner-portal",
    icon: UploadCloud,
    roles: [
      "System Administrator",
      "Operations Manager",
      "Partner External User",
      "Supplier External User",
      "Donor Intake Coordinator",
    ],
  },
  {
    id: "qms",
    label: "QMS Deviations",
    route: "/qms",
    icon: AlertTriangle,
    roles: ["System Administrator", "Operations Manager", "Quality Assurance Specialist"],
  },
  {
    id: "capa",
    label: "CAPA Aging",
    route: "/capa",
    icon: FileCheck2,
    roles: ["System Administrator", "Operations Manager", "Quality Assurance Specialist"],
  },
  {
    id: "vendor_sla",
    label: "Vendor SLA",
    route: "/vendor-sla",
    icon: Bell,
    roles: ["System Administrator", "Operations Manager", "Vendor Operations Analyst", "Quality Assurance Specialist"],
  },
  {
    id: "documents",
    label: "Documents",
    route: "/documents",
    icon: UploadCloud,
    roles: ["System Administrator", "Operations Manager", "Quality Assurance Specialist", "Clinical Reviewer"],
  },
  {
    id: "audit",
    label: "Audit Events",
    route: "/audit",
    icon: ShieldCheck,
    roles: ["System Administrator", "Operations Manager", "Quality Assurance Specialist"],
  },
  {
    id: "producer",
    label: "Data Producer",
    route: "/data-producer",
    icon: Activity,
    roles: ["System Administrator", "Business Technology Analyst", "Operations Manager"],
  },
  {
    id: "health",
    label: "System Health",
    route: "/health",
    icon: ShieldCheck,
    roles: ["System Administrator", "Business Technology Analyst", "Operations Manager"],
  },
];

const routeToSection = Object.fromEntries(sections.map((section) => [section.route, section.id]));
const sectionById = Object.fromEntries(sections.map((section) => [section.id, section]));

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function normalizeRoute(route) {
  const withSlash = route?.startsWith("/") ? route : `/${route || ""}`;
  const clean = withSlash.replace(/\/+$/, "");
  return clean || "/";
}

function appPath(route) {
  const normalized = normalizeRoute(route);
  return `${PUBLIC_BASE}${normalized === "/" ? "" : normalized}` || "/";
}

function canSeeMonitor(user) {
  const permissions = new Set(user?.permissions || []);
  return permissions.has("system.admin") || MONITOR_LINK_ROLES.includes(user?.role_name);
}

function visiblePortfolioLinks(user) {
  return portfolioLinks.filter((item) => !item.requiresMonitorAccess || canSeeMonitor(user));
}

function browserRoute() {
  let path = window.location.pathname || "/";
  if (PUBLIC_BASE && (path === PUBLIC_BASE || path.startsWith(`${PUBLIC_BASE}/`))) {
    path = path.slice(PUBLIC_BASE.length) || "/";
  }
  return normalizeRoute(path);
}

async function apiRequest(path, { token, method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const response = await fetch(apiUrl(path), {
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
  const response = await fetch(apiUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
}

function apiUrl(path) {
  const cleanPath = `/${String(path || "").replace(/^\/+/, "")}`;
  if (/^https?:\/\//i.test(API_BASE)) {
    return `${API_BASE}${cleanPath}`;
  }
  const normalizedBase = (API_BASE || PUBLIC_BASE).replace(/\/+$/, "");
  if (!normalizedBase) return cleanPath;
  if (cleanPath === normalizedBase || cleanPath.startsWith(`${normalizedBase}/api/`)) {
    return cleanPath;
  }
  const withoutDuplicateBase = cleanPath.replace(new RegExp(`^${normalizedBase}/+`, "i"), "/");
  return `${normalizedBase}${withoutDuplicateBase}`;
}

async function verifyMfa(mfaToken, code) {
  return apiRequest("/api/auth/mfa/verify", {
    method: "POST",
    body: { mfa_token: mfaToken, code },
  });
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value || 0));
}

function sumCounts(rows, field = "count") {
  return (rows || []).reduce((total, row) => total + Number(row?.[field] || 0), 0);
}

function normalizeDashboardStatus(dashboard, enterprise) {
  const donorTotal = sumCounts(dashboard?.status_distribution);
  const riskTotal = sumCounts(dashboard?.risk_distribution);
  const vendorIncidentTotal = sumCounts(dashboard?.vendor_health, "incident_count");
  return {
    row_counts: {
      dim_donor: donorTotal,
      fact_donor_screening: riskTotal || donorTotal,
      fact_eligibility_decision: donorTotal,
      fact_workflow_task: enterprise?.kpis?.open_tasks ?? 0,
      dim_partner_submission: sumCounts(dashboard?.partner_activity),
      dim_secure_document: enterprise?.kpis?.audit_events ?? 0,
      fact_deviation: dashboard?.kpis?.open_investigations ?? 0,
      fact_vendor_incident: enterprise?.kpis?.open_vendor_incidents ?? vendorIncidentTotal,
      fact_risk_factor: riskTotal,
      fact_lab_result: sumCounts(dashboard?.daily_review_trend),
      fact_audit_log: enterprise?.kpis?.audit_events ?? 0,
      fact_capa: enterprise?.kpis?.open_change_controls ?? 0,
      fact_change_control: enterprise?.kpis?.open_change_controls ?? 0,
      fact_notification: enterprise?.kpis?.unread_notifications ?? 0,
      fact_escalation: enterprise?.kpis?.escalated_tasks ?? 0,
      dim_vendor: dashboard?.vendor_health?.length ?? 0,
    },
    dashboard,
    enterprise_dashboard: enterprise,
  };
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

function AuthShell({ eyebrow, title, lede, children, navigate }) {
  return (
    <main className="login-shell">
      <section className="login-panel">
        <div>
          <div className="portfolio-nav public-nav" aria-label="Portfolio navigation">
            {visiblePortfolioLinks(null).map((item) => {
              const Icon = item.icon;
              return (
                <a key={item.label} href={item.href} className={item.label === "Clinical" ? "active" : ""}>
                  <Icon size={15} />
                  {item.label}
                </a>
              );
            })}
          </div>
          <button type="button" className="ghost-link" onClick={() => navigate("/")}>
            <Home size={16} />
            Clinical home
          </button>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="lede">{lede}</p>
        </div>
        {children}
      </section>
    </main>
  );
}

function PublicHome({ navigate }) {
  return (
    <AuthShell
      eyebrow="Clinical source-system simulator"
      title="Clinical Donor Platform"
      lede="Secure operational entry point for donor referrals, screening queues, partner portal work, QMS, CAPA, audit events, data producer operations, and future Entra ID integration."
      navigate={navigate}
    >
      <div className="login-form">
        <h2>Access center</h2>
        <div className="access-actions" aria-label="Clinical access actions">
          <button type="button" onClick={() => navigate("/login")}>
            <ShieldCheck size={16} />
            Sign in
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/request-access")}>
            <UserPlus size={16} />
            Request partner or supplier access
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/forgot-password")}>
            <Mail size={16} />
            Forgot password
          </button>
        </div>
        <div className="access-policy">
          <strong>Internal access</strong>
          <span>{INTERNAL_ADMIN_ASSIGNED_ROLES.join(", ")} roles are assigned by administrators.</span>
        </div>
      </div>
    </AuthShell>
  );
}

function LoginPage({ onLogin, navigate }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [demoUsername, setDemoUsername] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = mfaToken ? await verifyMfa(mfaToken, mfaCode) : await login(username, password);
      if (payload.mfa_required) {
        if (demoUsername && DEMO_LOGIN_USERNAMES.has(username)) {
          const demoPayload = await verifyMfa(payload.mfa_token, DEMO_LOGIN_MFA_CODE);
          onLogin(demoPayload);
          return;
        }
        setMfaToken(payload.mfa_token);
        setMfaCode(demoUsername ? DEMO_LOGIN_MFA_CODE : "");
        setError("MFA verification is required. Enter the approved verification code to continue.");
        return;
      }
      onLogin(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function prepareDemoLogin(profile) {
    setUsername(profile.username);
    setPassword(DEMO_LOGIN_PASSWORD);
    setMfaToken("");
    setMfaCode(DEMO_LOGIN_MFA_CODE);
    setDemoUsername(profile.username);
    setError(`${profile.label} credentials loaded for ${profile.role}. Demo MFA will be completed automatically if required.`);
  }

  return (
    <AuthShell
      eyebrow="Clinical authentication"
      title="Sign in"
      lede="Native Clinical sign-in remains active while Microsoft Entra ID integration is prepared. Internal users and partner users retain their existing role model."
      navigate={navigate}
    >
      <form onSubmit={submit} className="login-form">
        <label>
          Username or email
          <input
            value={username}
            onChange={(event) => {
              setUsername(event.target.value);
              setDemoUsername("");
            }}
            disabled={Boolean(mfaToken)}
          />
        </label>
        {!mfaToken && (
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
        )}
        {mfaToken && (
          <label>
            MFA code
            <input value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} autoComplete="one-time-code" />
          </label>
        )}
        {demoUsername && (
          <div className="access-policy">
            <strong>Demo MFA</strong>
            <span>Demo accounts use approved code {DEMO_LOGIN_MFA_CODE}; non-demo accounts keep normal MFA behavior.</span>
          </div>
        )}
        {error && <div className="error-state">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? <RefreshCw size={16} /> : <ShieldCheck size={16} />}
          {mfaToken ? "Verify MFA" : "Sign in"}
        </button>
        {mfaToken && (
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setMfaToken("");
              setDemoUsername("");
            }}
          >
            <ArrowLeft size={16} />
            Use different account
          </button>
        )}
        <div className="access-actions login-shortcuts" aria-label="Clinical login access links">
          {DEMO_LOGIN_PROFILES.map((profile) => {
            const Icon = profile.icon;
            return (
              <button
                type="button"
                className="secondary-button"
                onClick={() => prepareDemoLogin(profile)}
                key={profile.label}
              >
                <Icon size={16} />
                {profile.label}
              </button>
            );
          })}
          <button type="button" className="secondary-button" onClick={() => navigate("/request-access")}>
            <UserPlus size={16} />
            Request access
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/forgot-password")}>
            <Mail size={16} />
            Forgot password
          </button>
        </div>
      </form>
    </AuthShell>
  );
}

function ForgotPasswordPage({ navigate }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/api/auth/password-reset/request", {
        method: "POST",
        body: { email },
      });
    } catch {
      // Account recovery must not reveal whether an account exists or expose backend details.
    } finally {
      setMessage(PASSWORD_RESET_NOTICE);
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Account recovery"
      title="Forgot password"
      lede="Request a single-use reset link for native Clinical accounts. Future Entra ID accounts will use Microsoft-managed recovery."
      navigate={navigate}
    >
      <form onSubmit={submit} className="login-form">
        <label>
          Work email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" />
        </label>
        {message && <div className="notice-state">{message}</div>}
        <button type="submit" disabled={busy}>
          {busy ? <RefreshCw size={16} /> : <Mail size={16} />}
          Send reset link
        </button>
        <button type="button" className="secondary-button" onClick={() => navigate("/login")}>
          Back to sign in
        </button>
      </form>
    </AuthShell>
  );
}

function ResetPasswordPage({ navigate }) {
  const [token, setToken] = useState(() => new URLSearchParams(window.location.search).get("token") || "");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiRequest("/api/auth/password-reset/confirm", {
        method: "POST",
        body: { token, new_password: newPassword },
      });
      setMessage("Password reset completed. You can sign in with the new password.");
      setNewPassword("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Account recovery"
      title="Reset password"
      lede="Complete a single-use reset token flow for a native Clinical account."
      navigate={navigate}
    >
      <form onSubmit={submit} className="login-form">
        <label>
          Reset token
          <input value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" />
        </label>
        <label>
          New password
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
          />
        </label>
        {message && <div className="notice-state">{message}</div>}
        {error && <div className="error-state">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? <RefreshCw size={16} /> : <KeyRound size={16} />}
          Reset password
        </button>
      </form>
    </AuthShell>
  );
}

function RequestAccessPage({ navigate }) {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    organization_name: "",
    request_type: "Partner",
    business_reason: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const requestType = EXTERNAL_REQUEST_TYPES.some((item) => item.value === form.request_type)
        ? form.request_type
        : "Partner";
      const result = await apiRequest("/api/auth/access-request", {
        method: "POST",
        body: {
          ...form,
          organization_type: requestType,
          requested_role: EXTERNAL_ROLE_BY_REQUEST_TYPE[requestType],
        },
      });
      setMessage(result?.message || "Access request received.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Partner onboarding"
      title="Request access"
      lede="Partner and supplier requests are reviewed before any account, organization, invitation, or role assignment is created."
      navigate={navigate}
    >
      <form onSubmit={submit} className="login-form">
        <label>
          Full name
          <input value={form.full_name} onChange={(event) => update("full_name", event.target.value)} />
        </label>
        <label>
          Work email
          <input value={form.email} type="email" onChange={(event) => update("email", event.target.value)} />
        </label>
        <label>
          Organization
          <input value={form.organization_name} onChange={(event) => update("organization_name", event.target.value)} />
        </label>
        <label>
          Request type
          <select value={form.request_type} onChange={(event) => update("request_type", event.target.value)}>
            {EXTERNAL_REQUEST_TYPES.map((requestType) => (
              <option key={requestType.value} value={requestType.value}>
                {requestType.label}
              </option>
            ))}
          </select>
        </label>
        <div className="access-policy">
          <strong>Role assignment</strong>
          <span>
            {form.request_type} requests are reviewed and assigned the appropriate external access role by an administrator.
          </span>
        </div>
        <label>
          Business reason
          <textarea value={form.business_reason} onChange={(event) => update("business_reason", event.target.value)} rows={4} />
        </label>
        {message && <div className="notice-state">{message}</div>}
        {error && <div className="error-state">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? <RefreshCw size={16} /> : <UserPlus size={16} />}
          Submit request
        </button>
      </form>
    </AuthShell>
  );
}

function LogoutPage({ onLogout, navigate }) {
  const [done, setDone] = useState(false);

  useEffect(() => {
    let mounted = true;
    onLogout().finally(() => {
      if (mounted) setDone(true);
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AuthShell
      eyebrow="Clinical authentication"
      title="Signed out"
      lede="Your local session has been cleared. If the backend session was active, it has been revoked and logged for monitoring."
      navigate={navigate}
    >
      <div className="login-form">
        <StatusPill status={done ? "Logged out" : "Signing out"} />
        <button type="button" onClick={() => navigate("/login")}>
          <LogIn size={16} />
          Sign in again
        </button>
      </div>
    </AuthShell>
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
      <button type="button" onClick={() => runAction("Incremental generation", "/api/generation/incremental", { seed: 42, scale: 1 })}>
        <Play size={16} />
        Incremental
      </button>
      <button type="button" onClick={() => runAction("Validation", "/api/generation/validate")}>
        <CheckCircle2 size={16} />
        Validate
      </button>
      <button type="button" onClick={() => runAction("Export", "/api/generation/export", { batch_id: `react_${Date.now()}` })}>
        <Database size={16} />
        Export
      </button>
      <button
        type="button"
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
      <button type="button" onClick={() => runAction("Stop", "/api/generation/continuous/stop")}>
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

function ProfilePage({ token, user, onUserUpdate }) {
  const [form, setForm] = useState({
    full_name: user?.full_name || "",
    display_name: user?.display_name || "",
    email: user?.email || "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const updated = await apiRequest("/api/auth/me", { token, method: "PATCH", body: form });
      onUserUpdate(updated);
      setMessage("Profile updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="account-panel">
      <h3>Profile</h3>
      <form onSubmit={submit} className="stacked-form">
        <label>
          Full name
          <input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
        </label>
        <label>
          Display name
          <input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} />
        </label>
        <label>
          Email
          <input value={form.email} type="email" onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </label>
        {message && <div className="notice-state">{message}</div>}
        {error && <div className="error-state">{error}</div>}
        <button type="submit">
          <User size={16} />
          Save profile
        </button>
      </form>
    </section>
  );
}

function PreferencesPage({ token }) {
  const [preferences, setPreferences] = useState({
    task_assignments: true,
    partner_notifications: true,
    document_requests: true,
    approval_requests: true,
    security_alerts: true,
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    apiRequest("/api/auth/me/preferences", { token })
      .then((payload) => {
        if (!mounted) return;
        setPreferences((current) => ({
          ...current,
          ...(payload.notification_preferences || {}),
        }));
      })
      .catch((err) => {
        if (mounted) setError(err.message);
      });
    return () => {
      mounted = false;
    };
  }, [token]);

  function toggle(key) {
    setPreferences((current) => ({ ...current, [key]: !current[key] }));
  }

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      await apiRequest("/api/auth/me/preferences", {
        token,
        method: "PATCH",
        body: { notification_preferences: preferences, last_route: "/preferences" },
      });
      setMessage("Notification preferences updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="account-panel">
      <h3>Notification Preferences</h3>
      <form onSubmit={submit} className="stacked-form">
        <div className="preference-list">
          {Object.entries(preferences).map(([key, enabled]) => (
            <label key={key} className="checkbox-row">
              <input type="checkbox" checked={Boolean(enabled)} onChange={() => toggle(key)} />
              {key.replaceAll("_", " ")}
            </label>
          ))}
        </div>
        {message && <div className="notice-state">{message}</div>}
        {error && <div className="error-state">{error}</div>}
        <button type="submit">
          <Bell size={16} />
          Save preferences
        </button>
      </form>
    </section>
  );
}

function hasRouteAccess(section, user) {
  if (!section?.roles?.length) return true;
  const permissions = new Set(user?.permissions || []);
  if (permissions.has("system.admin")) return true;
  return section.roles.includes(user?.role_name);
}

function AccessDenied({ section, user }) {
  return (
    <section className="access-denied">
      <ShieldCheck size={28} />
      <h3>Access denied</h3>
      <p>
        {section?.label || "This page"} requires one of these roles: {section?.roles?.join(", ") || "restricted role"}.
      </p>
      <p className="muted">Current role: {user?.role_name || "Unknown"}</p>
    </section>
  );
}

function SectionBody({ active, status, token, refresh }) {
  const validation = status?.latest_validation || {};
  const manifest = status?.latest_export_manifest || {};
  const freshness = status?.source_freshness?.freshness || [];
  const runs = status?.recent_runs || [];

  if (active === "dashboard") return <OperationsSection status={status} />;
  if (active === "referrals") {
    return (
      <div className="content-grid">
        <MetricCard label="Referral Sources" value={formatNumber(status?.row_counts?.dim_referral_source)} />
        <MetricCard label="Donors" value={formatNumber(status?.row_counts?.dim_donor)} />
        <MetricCard label="Partner Submissions" value={formatNumber(status?.row_counts?.dim_partner_submission)} />
        <MetricCard label="Workflow Tasks" value={formatNumber(status?.row_counts?.fact_workflow_task)} tone="warning" />
      </div>
    );
  }
  if (active === "screening") {
    return (
      <div className="content-grid">
        <MetricCard label="Screenings" value={formatNumber(status?.row_counts?.fact_donor_screening)} />
        <MetricCard label="Risk Factors" value={formatNumber(status?.row_counts?.fact_risk_factor)} tone="warning" />
        <MetricCard label="Lab Results" value={formatNumber(status?.row_counts?.fact_lab_result)} />
        <MetricCard label="Medical History" value={formatNumber(status?.row_counts?.fact_medical_social_history)} />
      </div>
    );
  }
  if (active === "clinical_review") {
    return (
      <div className="content-grid">
        <MetricCard label="Clinical Reviews" value={formatNumber(status?.row_counts?.fact_donor_screening)} />
        <MetricCard label="Open Tasks" value={formatNumber(status?.row_counts?.fact_workflow_task)} tone="warning" />
        <MetricCard label="Document Packets" value={formatNumber(status?.row_counts?.dim_secure_document)} />
        <MetricCard label="Audit Events" value={formatNumber(status?.row_counts?.fact_audit_log)} />
      </div>
    );
  }
  if (active === "eligibility") {
    return (
      <div className="content-grid">
        <MetricCard label="Eligibility Decisions" value={formatNumber(status?.row_counts?.fact_eligibility_decision)} />
        <MetricCard label="Eligibility Rules" value={formatNumber(status?.row_counts?.dim_eligibility_rule)} />
        <MetricCard label="Tissue Suitability" value={formatNumber(status?.row_counts?.fact_tissue_suitability)} />
        <MetricCard label="Processing Releases" value={formatNumber(status?.row_counts?.fact_processing_release)} />
      </div>
    );
  }
  if (active === "recovery_cases") {
    return (
      <div className="content-grid">
        <MetricCard label="Recovery Cases" value={formatNumber(status?.row_counts?.fact_recovery_case)} />
        <MetricCard label="Tissue Types" value={formatNumber(status?.row_counts?.dim_tissue_type)} />
        <MetricCard label="Product Suitability" value={formatNumber(status?.row_counts?.fact_tissue_suitability)} />
        <MetricCard label="Documents" value={formatNumber(status?.row_counts?.dim_secure_document)} />
      </div>
    );
  }
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
  if (active === "capa") {
    return (
      <div className="content-grid">
        <MetricCard label="CAPA Records" value={formatNumber(status?.row_counts?.fact_capa)} tone="warning" />
        <MetricCard label="Open Deviations" value={formatNumber(status?.row_counts?.fact_deviation)} tone="warning" />
        <MetricCard label="Change Controls" value={formatNumber(status?.row_counts?.fact_change_control)} />
        <MetricCard label="Approval Tasks" value={formatNumber(status?.row_counts?.fact_workflow_task)} />
      </div>
    );
  }
  if (active === "vendor_sla") {
    return (
      <div className="content-grid">
        <MetricCard label="Vendor Incidents" value={formatNumber(status?.row_counts?.fact_vendor_incident)} tone="warning" />
        <MetricCard label="Vendors" value={formatNumber(status?.row_counts?.dim_vendor)} />
        <MetricCard label="Partner Messages" value={formatNumber(status?.row_counts?.fact_partner_message)} />
        <MetricCard label="Escalations" value={formatNumber(status?.row_counts?.fact_escalation)} tone="warning" />
      </div>
    );
  }
  if (active === "documents") {
    return (
      <div className="content-grid">
        <MetricCard label="Secure Documents" value={formatNumber(status?.row_counts?.dim_secure_document)} />
        <MetricCard label="Partner Documents" value={formatNumber(status?.row_counts?.dim_partner_document)} />
        <MetricCard label="Document Versions" value={formatNumber(status?.row_counts?.fact_document_version)} />
        <MetricCard label="Access Events" value={formatNumber(status?.row_counts?.fact_document_access)} />
      </div>
    );
  }
  if (active === "audit") {
    return (
      <div className="content-grid">
        <MetricCard label="Audit Events" value={formatNumber(status?.row_counts?.fact_audit_log)} />
        <MetricCard label="Security Events" value={formatNumber(status?.row_counts?.fact_security_event)} />
        <MetricCard label="Active Sessions" value={formatNumber(status?.row_counts?.fact_user_session)} />
        <MetricCard label="Notifications" value={formatNumber(status?.row_counts?.fact_notification)} />
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
  const [route, setRoute] = useState(browserRoute);
  const [tokenPayload, setTokenPayload] = useState(() => {
    const raw = window.localStorage.getItem("clinical_token_payload");
    return raw ? JSON.parse(raw) : null;
  });
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const token = tokenPayload?.access_token;
  const user = tokenPayload?.user;
  const active = routeToSection[route] || (route === "/" && token ? "dashboard" : "");
  const activeSection = useMemo(() => sectionById[active], [active]);

  useEffect(() => {
    function onPopState() {
      setRoute(browserRoute());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextRoute, options = {}) {
    const normalized = normalizeRoute(nextRoute);
    const method = options.replace ? "replaceState" : "pushState";
    window.history[method]({}, "", appPath(normalized));
    setRoute(normalized);
  }

  function clearSession() {
    setTokenPayload(null);
    setStatus(null);
    window.localStorage.removeItem("clinical_token_payload");
  }

  async function performLogout() {
    if (token) {
      await apiRequest("/api/auth/logout", { token, method: "POST" }).catch(() => null);
    }
    clearSession();
  }

  async function refresh() {
    if (!token) return;
    setError("");
    try {
      const [dashboard, enterprise] = await Promise.all([
        apiRequest("/api/dashboard", { token }),
        apiRequest("/api/enterprise-dashboard", { token }),
      ]);
      const nextStatus = normalizeDashboardStatus(dashboard, enterprise);
      const permissions = new Set(user?.permissions || []);
      if (permissions.has("system.admin")) {
        const [generationStatus, runs] = await Promise.all([
          apiRequest("/api/generation/status", { token }),
          apiRequest("/api/generation/runs?limit=25", { token }),
        ]);
        setStatus({ ...nextStatus, ...generationStatus, recent_runs: runs });
        return;
      }
      setStatus(nextStatus);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (token && active) refresh();
  }, [token, active]);

  useEffect(() => {
    if (token && route === "/") {
      navigate("/dashboard", { replace: true });
    }
  }, [token, route]);

  function handleLogin(payload) {
    setTokenPayload(payload);
    window.localStorage.setItem("clinical_token_payload", JSON.stringify(payload));
    const nextRoute = route === "/login" || route === "/" ? "/dashboard" : route;
    navigate(nextRoute, { replace: true });
  }

  function updateUser(userPayload) {
    setTokenPayload((current) => {
      const next = { ...current, user: userPayload };
      window.localStorage.setItem("clinical_token_payload", JSON.stringify(next));
      return next;
    });
  }

  if (route === "/logout") {
    return <LogoutPage onLogout={performLogout} navigate={navigate} />;
  }

  if (!tokenPayload) {
    if (route === "/forgot-password") return <ForgotPasswordPage navigate={navigate} />;
    if (route === "/reset-password") return <ResetPasswordPage navigate={navigate} />;
    if (route === "/request-access") return <RequestAccessPage navigate={navigate} />;
    if (route === "/" || route === "/home") return <PublicHome navigate={navigate} />;
    return <LoginPage onLogin={handleLogin} navigate={navigate} />;
  }

  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          <HeartPulse size={24} />
          <div>
            <strong>Clinical Donor</strong>
            <span>Current app: Clinical</span>
          </div>
        </div>
        <div className="portfolio-nav" aria-label="Portfolio navigation">
          {visiblePortfolioLinks(user).map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.label} href={item.href} className={item.label === "Clinical" ? "active" : ""}>
                <Icon size={15} />
                {item.label}
              </a>
            );
          })}
        </div>
        <nav>
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={cx(active === section.id && "active")}
                onClick={() => navigate(section.route)}
                type="button"
              >
                <Icon size={17} />
                {section.label}
              </button>
            );
          })}
          <div className="nav-divider" />
          <button className={cx(route === "/profile" && "active")} onClick={() => navigate("/profile")} type="button">
            <User size={17} />
            Profile
          </button>
          <button className={cx(route === "/preferences" && "active")} onClick={() => navigate("/preferences")} type="button">
            <Bell size={17} />
            Preferences
          </button>
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Azure-ready FastAPI + React</p>
            <h1>
              {route === "/profile"
                ? "Profile"
                : route === "/preferences"
                  ? "Notification Preferences"
                  : activeSection?.label || "Clinical Operations"}
            </h1>
          </div>
          <div className="topbar-actions">
            <button type="button" onClick={refresh}>
              <RefreshCw size={16} />
              Refresh
            </button>
            <button type="button" onClick={() => navigate("/profile")}>
              <User size={16} />
              {user?.display_name || user?.username || "Profile"}
            </button>
            <button type="button" onClick={() => navigate("/logout")}>
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
        {route === "/profile" && <ProfilePage token={token} user={user} onUserUpdate={updateUser} />}
        {route === "/preferences" && <PreferencesPage token={token} />}
        {route !== "/profile" && route !== "/preferences" && !hasRouteAccess(activeSection, user) && (
          <AccessDenied section={activeSection} user={user} />
        )}
        {route !== "/profile" && route !== "/preferences" && hasRouteAccess(activeSection, user) && (
          <SectionBody active={active || "dashboard"} status={status || {}} token={token} refresh={refresh} />
        )}
      </main>
    </div>
  );
}

export default App;
