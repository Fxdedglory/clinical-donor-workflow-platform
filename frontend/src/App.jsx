import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bell,
  CalendarDays,
  CheckCircle2,
  Clock,
  CreditCard,
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
  ReceiptText,
  ShieldCheck,
  Square,
  UploadCloud,
  User,
  UserPlus,
  XCircle,
} from "lucide-react";
import { isValidElement, useEffect, useMemo, useState } from "react";

import { ClinicalRedactedValue } from "./pages/clinical/ClinicalRedactedValue";
import { ClinicalShellPlaceholder } from "./pages/clinical/ClinicalShellPlaceholder";
import { ClinicalSuppressedMetric } from "./pages/clinical/ClinicalSuppressedMetric";
import {
  EXPORT_PROFILE_OPTIONS,
  clinicalPrivacyMode,
  displayClinicalValue,
  exportProfileInfo,
  isSuppressedCell,
  suppressionSummary,
} from "./pages/clinical/clinicalPrivacyDisplay";
import { clinicalPatientDetailSection, clinicalPatientId, clinicalSections } from "./pages/clinical/clinicalRoutes";

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

const navigationSections = [...sections, ...clinicalSections];
const routeToSection = Object.fromEntries(navigationSections.map((section) => [section.route, section.id]));
const sectionById = Object.fromEntries(
  [...navigationSections, clinicalPatientDetailSection].map((section) => [section.id, section]),
);

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

async function apiRequest(path, { token, method = "GET", body, headers: customHeaders = {} } = {}) {
  const headers = { ...customHeaders };
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

function formatMoney(value) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(Number(value || 0));
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

function ClinicalPrivacyIndicator({ user }) {
  const mode = clinicalPrivacyMode(user);
  return (
    <div className="privacy-indicator" aria-label="Clinical privacy display mode">
      <span>PHI protected</span>
      <strong>{mode.label}</strong>
    </div>
  );
}

function ExportProfileIndicator({ profile = "aggregate_safe", suppression }) {
  const info = exportProfileInfo(profile);
  const summary = suppressionSummary(suppression);
  return (
    <div className="export-profile-indicator" aria-label="Export profile protections">
      <StatusPill status={info.label} />
      <span>{info.redactionActive ? "PHI/ePHI redaction active" : "Detail visibility restricted"}</span>
      <span>{info.suppressionActive ? "Small-cell suppression active" : "Small-cell suppression inactive"}</span>
      {summary.threshold && <span>Threshold {summary.threshold}</span>}
      {summary.applied && <span>{summary.suppressedCells} suppressed</span>}
    </div>
  );
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

function renderedFieldName(row, column) {
  if (column === "value" && row?.field) return row.field;
  return column;
}

function TableCellValue({ value, field, user, sensitiveColumns = [] }) {
  if (isValidElement(value)) return value;
  if (Array.isArray(value)) return value.length;
  const display = displayClinicalValue(value, field, user, {
    sensitive: sensitiveColumns.includes(field) ? true : undefined,
  });
  if (display.kind === "suppressed") return <ClinicalSuppressedMetric cell={value} />;
  if (display.kind === "redacted") return <ClinicalRedactedValue indicator={display.indicator} />;
  if (display.kind === "empty") return "";
  return String(display.value ?? "");
}

function clinicalDisplayText(value, field, user) {
  const display = displayClinicalValue(value, field, user);
  if (display.kind === "suppressed") {
    const threshold = display.threshold ? ` < ${display.threshold}` : "";
    return `${display.label} (${display.badge}${threshold})`;
  }
  if (display.kind === "redacted") return `${display.label} (${display.indicator})`;
  if (display.kind === "empty") return "";
  return String(display.value ?? "");
}

function Table({ rows, columns, user, sensitiveColumns = [] }) {
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
                <td key={column}>
                  <TableCellValue
                    value={row[column]}
                    field={renderedFieldName(row, column)}
                    user={user}
                    sensitiveColumns={sensitiveColumns}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const patientStatusOptions = ["active", "inactive", "deferred", "deceased"];
const futurePatientWorkflows = [
  { label: "Schedule Visit", route: "/clinical/scheduling", status: "Active" },
  { label: "Start Screening", route: "/clinical/screening", status: "Active" },
  { label: "Open Encounter", route: "/clinical/encounters", status: "Active" },
  { label: "Create Order", route: "/clinical/orders", status: "Active" },
  { label: "Billing Review", route: "/clinical/billing", status: "Planned" },
];

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function patientDisplayName(patient) {
  return [patient?.first_name, patient?.middle_name, patient?.last_name].filter(Boolean).join(" ") || "Unnamed patient";
}

function defaultPatientForm(type, patient) {
  if (type === "edit") {
    return {
      donor_reference: patient?.donor_reference || "",
      first_name: patient?.first_name || "",
      middle_name: patient?.middle_name || "",
      last_name: patient?.last_name || "",
      date_of_birth: patient?.date_of_birth || "",
      sex_at_birth: patient?.sex_at_birth || "",
      gender_identity: patient?.gender_identity || "",
      preferred_language: patient?.preferred_language || "",
      phone: patient?.phone || "",
      email: patient?.email || "",
      address_line1: patient?.address_line1 || "",
      city: patient?.city || "",
      state: patient?.state || "",
      postal_code: patient?.postal_code || "",
      status: patient?.status || "active",
    };
  }
  if (type === "contact") {
    return { contact_type: "emergency", full_name: "", relationship: "", phone: "", email: "", is_primary: false, status: "active" };
  }
  if (type === "insurance") {
    return { payer_name: "", member_id: "", group_number: "", plan_type: "", priority: "primary", eligibility_status: "not_verified", status: "active" };
  }
  if (type === "consent") {
    return { consent_type: "Treatment", consent_status: "captured", captured_by_name: "", notes: "" };
  }
  return {
    donor_reference: "",
    first_name: "",
    middle_name: "",
    last_name: "",
    date_of_birth: "",
    sex_at_birth: "",
    gender_identity: "",
    preferred_language: "",
    phone: "",
    email: "",
    address_line1: "",
    city: "",
    state: "",
    postal_code: "",
    status: "active",
  };
}

function compactPayload(form) {
  return Object.fromEntries(
    Object.entries(form).filter(([, value]) => value !== "" && value !== null && value !== undefined),
  );
}

function workflowTitle(type) {
  return {
    create: "Create Patient / Donor",
    edit: "Edit Demographics",
    contact: "Add Contact",
    insurance: "Add Insurance",
    consent: "Capture Consent",
  }[type];
}

function validatePatientWorkflow(type, form) {
  const issues = [];
  if (["create", "edit"].includes(type)) {
    for (const field of ["first_name", "last_name", "date_of_birth", "sex_at_birth"]) {
      if (!form[field]) issues.push(`${field.replaceAll("_", " ")} is required.`);
    }
  }
  if (type === "contact" && !form.full_name) issues.push("Contact full name is required.");
  if (type === "insurance" && !form.payer_name) issues.push("Payer name is required.");
  if (type === "consent" && !form.consent_type) issues.push("Consent type is required.");
  return issues;
}

function previewEndpoint(type, patientId) {
  if (type === "create") return "/api/clinical/patients/preview";
  if (type === "edit") return `/api/clinical/patients/${patientId}/edit/preview`;
  if (type === "contact") return `/api/clinical/patients/${patientId}/contacts/preview`;
  if (type === "insurance") return `/api/clinical/patients/${patientId}/insurance/preview`;
  return `/api/clinical/patients/${patientId}/consents/preview`;
}

function commitEndpoint(type, patientId) {
  if (type === "create") return { path: "/api/clinical/patients", method: "POST" };
  if (type === "edit") return { path: `/api/clinical/patients/${patientId}`, method: "PATCH" };
  if (type === "contact") return { path: `/api/clinical/patients/${patientId}/contacts`, method: "POST" };
  if (type === "insurance") return { path: `/api/clinical/patients/${patientId}/insurance`, method: "POST" };
  return { path: `/api/clinical/patients/${patientId}/consents`, method: "POST" };
}

function PatientWorkflowModal({ type, patient, token, user, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultPatientForm(type, patient));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validatePatientWorkflow(type, form);
  const patientId = patient?.patient_id;

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(previewEndpoint(type, patientId), {
        token,
        method: "POST",
        body: compactPayload(form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    const { path, method } = commitEndpoint(type, patientId);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...compactPayload(form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={workflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{workflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>
            Close
          </button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {["create", "edit"].includes(type) && (
              <div className="form-grid">
                <label>First name<input value={form.first_name} onChange={(event) => updateField("first_name", event.target.value)} /></label>
                <label>Middle name<input value={form.middle_name} onChange={(event) => updateField("middle_name", event.target.value)} /></label>
                <label>Last name<input value={form.last_name} onChange={(event) => updateField("last_name", event.target.value)} /></label>
                <label>Date of birth<input type="date" value={form.date_of_birth} onChange={(event) => updateField("date_of_birth", event.target.value)} /></label>
                <label>Sex at birth<input value={form.sex_at_birth} onChange={(event) => updateField("sex_at_birth", event.target.value)} /></label>
                <label>Gender identity<input value={form.gender_identity} onChange={(event) => updateField("gender_identity", event.target.value)} /></label>
                <label>Donor reference<input value={form.donor_reference} onChange={(event) => updateField("donor_reference", event.target.value)} /></label>
                <label>Preferred language<input value={form.preferred_language} onChange={(event) => updateField("preferred_language", event.target.value)} /></label>
                <label>Phone<input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} /></label>
                <label>Email<input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} /></label>
                <label>Address<input value={form.address_line1} onChange={(event) => updateField("address_line1", event.target.value)} /></label>
                <label>City<input value={form.city} onChange={(event) => updateField("city", event.target.value)} /></label>
                <label>State<input value={form.state} onChange={(event) => updateField("state", event.target.value)} /></label>
                <label>Postal code<input value={form.postal_code} onChange={(event) => updateField("postal_code", event.target.value)} /></label>
                <label>Status<select value={form.status} onChange={(event) => updateField("status", event.target.value)}>{patientStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
              </div>
            )}
            {type === "contact" && (
              <div className="form-grid">
                <label>Contact type<input value={form.contact_type} onChange={(event) => updateField("contact_type", event.target.value)} /></label>
                <label>Full name<input value={form.full_name} onChange={(event) => updateField("full_name", event.target.value)} /></label>
                <label>Relationship<input value={form.relationship} onChange={(event) => updateField("relationship", event.target.value)} /></label>
                <label>Phone<input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} /></label>
                <label>Email<input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} /></label>
                <label className="checkbox-row"><input type="checkbox" checked={form.is_primary} onChange={(event) => updateField("is_primary", event.target.checked)} /> Primary contact</label>
              </div>
            )}
            {type === "insurance" && (
              <div className="form-grid">
                <label>Payer name<input value={form.payer_name} onChange={(event) => updateField("payer_name", event.target.value)} /></label>
                <label>Member ID<input value={form.member_id} onChange={(event) => updateField("member_id", event.target.value)} /></label>
                <label>Group number<input value={form.group_number} onChange={(event) => updateField("group_number", event.target.value)} /></label>
                <label>Plan type<input value={form.plan_type} onChange={(event) => updateField("plan_type", event.target.value)} /></label>
                <label>Priority<select value={form.priority} onChange={(event) => updateField("priority", event.target.value)}><option>primary</option><option>secondary</option></select></label>
                <label>Eligibility status<input value={form.eligibility_status} onChange={(event) => updateField("eligibility_status", event.target.value)} /></label>
              </div>
            )}
            {type === "consent" && (
              <div className="form-grid">
                <label>Consent type<input value={form.consent_type} onChange={(event) => updateField("consent_type", event.target.value)} /></label>
                <label>Consent status<select value={form.consent_status} onChange={(event) => updateField("consent_status", event.target.value)}><option>captured</option><option>declined</option><option>revoked</option></select></label>
                <label>Captured by<input value={form.captured_by_name} onChange={(event) => updateField("captured_by_name", event.target.value)} /></label>
                <label>Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? (
              <div className="error-state">{validationIssues.join(" ")}</div>
            ) : (
              <div className="notice-state">Required fields are complete. Preview will check backend rules and duplicate risk.</div>
            )}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>
              {busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}
              Generate preview
            </button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className="notice-state">{preview.summary}</div>
            <Table rows={[{ field: "Preview hash", value: preview.preview_hash }, { field: "Validation", value: preview.validation_status }]} columns={["field", "value"]} />
            {preview.duplicate_warnings?.length > 0 && (
              <div className="error-state">
                Duplicate risk: {preview.duplicate_warnings.map((warning) => `${clinicalDisplayText(warning.patient_id, "patient_id", user)} (${warning.matched_fields.join(", ")})`).join("; ")}
              </div>
            )}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true and append a workflow operation audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>
              {busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}
              Commit workflow
            </button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Workflow committed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalPatientsPage({ token, navigate, user }) {
  const [patients, setPatients] = useState([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [modalType, setModalType] = useState("");

  async function loadPatients() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (statusFilter) params.set("status", statusFilter);
    try {
      const payload = await apiRequest(`/api/clinical/patients${params.toString() ? `?${params}` : ""}`, { token });
      setPatients(payload?.patients || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadPatients();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadPatients();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Patient / donor registration</p>
          <h2>Patients / Donors</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("create")}>
            <UserPlus size={16} />
            Create Patient / Donor
          </button>
          <button type="button" className="secondary-button" onClick={loadPatients}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </section>
      <section>
        <form className="patient-filter" onSubmit={submitSearch}>
          <label>Search<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, phone, email, or patient ID" /></label>
          <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{patientStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
          <button type="submit"><FileCheck2 size={16} />Apply</button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading patient/donor records...</div>}
      {!loading && !patients.length && <div className="empty-state">No patient or donor profiles found.</div>}
      {!!patients.length && (
        <section>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Patient ID</th><th>Name</th><th>DOB</th><th>Contact</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>
                {patients.map((patient) => (
                  <tr key={patient.patient_id}>
                    <td><TableCellValue value={patient.patient_id} field="patient_id" user={user} /></td>
                    <td><TableCellValue value={patientDisplayName(patient)} field="patient_name" user={user} /></td>
                    <td><TableCellValue value={formatDate(patient.date_of_birth)} field="date_of_birth" user={user} /></td>
                    <td><TableCellValue value={patient.phone || patient.email || ""} field="contact" user={user} /></td>
                    <td><StatusPill status={patient.status} /></td>
                    <td><button type="button" className="table-action" onClick={() => navigate(`/clinical/patients/${patient.patient_id}`)}>Open</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {modalType && (
        <PatientWorkflowModal
          type={modalType}
          token={token}
          user={user}
          onClose={() => setModalType("")}
          onSuccess={(payload) => {
            loadPatients();
            if (payload?.patient?.patient_id) navigate(`/clinical/patients/${payload.patient.patient_id}`);
          }}
        />
      )}
    </div>
  );
}

function ClinicalPatientDetailPage({ token, route, navigate, user }) {
  const patientId = clinicalPatientId(route);
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [modalType, setModalType] = useState("");

  async function loadPatient() {
    if (!patientId) return;
    setLoading(true);
    setError("");
    try {
      setPatient(await apiRequest(`/api/clinical/patients/${patientId}`, { token }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadPatient();
  }, [token, patientId]);

  if (loading) return <div className="notice-state">Loading patient/donor profile...</div>;
  if (error) return <div className="error-state">{error}</div>;
  if (!patient) return <div className="empty-state">Patient/donor profile unavailable.</div>;

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow"><TableCellValue value={patient.patient_id} field="patient_id" user={user} /></p>
          <h2><TableCellValue value={patientDisplayName(patient)} field="patient_name" user={user} /></h2>
          <StatusPill status={patient.status} />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("edit")}><FileCheck2 size={16} />Edit Demographics</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/patients")}><ArrowLeft size={16} />Back to List</button>
        </div>
      </section>
      <div className="split">
        <section>
          <h3>Demographics</h3>
          <Table rows={[
            { field: "Date of birth", value: formatDate(patient.date_of_birth) },
            { field: "Sex at birth", value: patient.sex_at_birth },
            { field: "Gender identity", value: patient.gender_identity || "" },
            { field: "Preferred language", value: patient.preferred_language || "" },
            { field: "Phone", value: patient.phone || "" },
            { field: "Email", value: patient.email || "" },
            { field: "Donor reference", value: patient.donor_reference || "" },
          ]} columns={["field", "value"]} user={user} />
        </section>
        <section>
          <h3>Planned Future Workflows</h3>
          <div className="workflow-list">
            {futurePatientWorkflows.map((workflow) => (
              <div className="workflow-row" key={workflow.label}>
                <button type="button" className="secondary-button" onClick={() => navigate(workflow.route)}>{workflow.label}</button>
                <StatusPill status={workflow.status} />
              </div>
            ))}
          </div>
        </section>
      </div>
      <div className="split">
        <section>
          <div className="section-heading-row"><h3>Contacts</h3><button type="button" onClick={() => setModalType("contact")}>Add</button></div>
          <Table rows={patient.contacts || []} columns={["contact_type", "full_name", "relationship", "phone", "email"]} user={user} />
        </section>
        <section>
          <div className="section-heading-row"><h3>Insurance</h3><button type="button" onClick={() => setModalType("insurance")}>Add</button></div>
          <Table rows={patient.insurance_profiles || []} columns={["priority", "payer_name", "member_id", "eligibility_status"]} user={user} />
        </section>
      </div>
      <div className="split">
        <section>
          <div className="section-heading-row"><h3>Consents</h3><button type="button" onClick={() => setModalType("consent")}>Capture</button></div>
          <Table rows={patient.consents || []} columns={["consent_type", "consent_status", "captured_by_name", "notes"]} user={user} />
        </section>
        <section>
          <h3>Recent Workflow Activity</h3>
          <Table rows={[
            { event: "Profile created", timestamp: formatDateTime(patient.created_at), source: patient.source },
            { event: "Profile updated", timestamp: formatDateTime(patient.updated_at), source: `Version ${patient.version}` },
          ]} columns={["event", "timestamp", "source"]} />
        </section>
      </div>
      {modalType && (
        <PatientWorkflowModal
          type={modalType}
          patient={patient}
          token={token}
          user={user}
          onClose={() => setModalType("")}
          onSuccess={(payload) => setPatient(payload?.patient || patient)}
        />
      )}
    </div>
  );
}

const appointmentStatusOptions = ["scheduled", "rescheduled", "checked_in", "cancelled", "no_show"];

function toDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function defaultDateTimeLocal(minutesAhead = 60) {
  const date = new Date(Date.now() + minutesAhead * 60000);
  const roundedMinutes = Math.ceil(date.getMinutes() / 15) * 15;
  date.setMinutes(roundedMinutes, 0, 0);
  return toDateTimeLocal(date.toISOString());
}

function localDateTimeToIso(value) {
  return value ? new Date(value).toISOString() : undefined;
}

function appointmentLabel(appointment) {
  return appointment?.appointment_number || `Appointment ${appointment?.appointment_id || ""}`;
}

function patientOptionLabel(patient, user) {
  const patientId = clinicalDisplayText(patient?.patient_id, "patient_id", user);
  const name = clinicalDisplayText(patientDisplayName(patient), "patient_name", user);
  return patientId && patientId !== name ? `${patientId} - ${name}` : name || "Patient";
}

function defaultSchedulingForm(type, appointment, resources, appointmentTypes, patients) {
  const firstProvider = resources?.providers?.[0]?.id || "";
  const firstRoom = resources?.rooms?.[0]?.id || "";
  const firstAppointmentType = appointmentTypes?.[0]?.appointment_type_id || "";
  const firstPatient = patients?.[0]?.patient_id || "";
  if (type === "reschedule") {
    return {
      provider_id: appointment?.provider_id || firstProvider,
      room_id: appointment?.room_id || firstRoom,
      appointment_type_id: appointment?.appointment_type_id || firstAppointmentType,
      scheduled_start: toDateTimeLocal(appointment?.scheduled_start) || defaultDateTimeLocal(60),
      scheduled_end: toDateTimeLocal(appointment?.scheduled_end) || defaultDateTimeLocal(120),
      equipment_ids: appointment?.equipment_ids || [],
      reason: "Reschedule appointment",
    };
  }
  if (type === "cancel") return { cancellation_reason: "" };
  if (type === "checkin") return { check_in_time: defaultDateTimeLocal(0), reason: "Check in appointment" };
  if (type === "noshow") return { no_show_reason: "" };
  return {
    patient_id: appointment?.patient_id || firstPatient,
    provider_id: appointment?.provider_id || firstProvider,
    room_id: appointment?.room_id || firstRoom,
    appointment_type_id: appointment?.appointment_type_id || firstAppointmentType,
    scheduled_start: defaultDateTimeLocal(60),
    scheduled_end: defaultDateTimeLocal(120),
    reason: "Donor intake visit",
    equipment_ids: [],
  };
}

function schedulingWorkflowTitle(type) {
  return {
    book: "Book Appointment",
    reschedule: "Reschedule Appointment",
    cancel: "Cancel Appointment",
    checkin: "Check In Appointment",
    noshow: "Mark No-show",
  }[type];
}

function validateSchedulingWorkflow(type, form) {
  const issues = [];
  if (["book", "reschedule"].includes(type)) {
    for (const field of ["provider_id", "appointment_type_id", "scheduled_start", "scheduled_end"]) {
      if (!form[field]) issues.push(`${field.replaceAll("_", " ")} is required.`);
    }
    if (type === "book" && !form.patient_id) issues.push("patient id is required.");
    if (!form.reason) issues.push("reason is required.");
    if (form.scheduled_start && form.scheduled_end && new Date(form.scheduled_end) <= new Date(form.scheduled_start)) {
      issues.push("scheduled end must be after scheduled start.");
    }
  }
  if (type === "cancel" && !form.cancellation_reason) issues.push("cancellation reason is required.");
  if (type === "noshow" && !form.no_show_reason) issues.push("no-show reason is required.");
  return issues;
}

function schedulingPreviewEndpoint(type, appointmentId) {
  if (type === "book") return "/api/clinical/scheduling/appointments/preview";
  if (type === "reschedule") return `/api/clinical/scheduling/${appointmentId}/reschedule/preview`;
  if (type === "cancel") return `/api/clinical/scheduling/${appointmentId}/cancel/preview`;
  if (type === "checkin") return `/api/clinical/scheduling/${appointmentId}/check-in/preview`;
  return `/api/clinical/scheduling/${appointmentId}/no-show/preview`;
}

function schedulingCommitEndpoint(type, appointmentId) {
  if (type === "book") return { path: "/api/clinical/scheduling/appointments", method: "POST" };
  if (type === "reschedule") return { path: `/api/clinical/scheduling/${appointmentId}/reschedule`, method: "POST" };
  if (type === "cancel") return { path: `/api/clinical/scheduling/${appointmentId}/cancel`, method: "POST" };
  if (type === "checkin") return { path: `/api/clinical/scheduling/${appointmentId}/check-in`, method: "POST" };
  return { path: `/api/clinical/scheduling/${appointmentId}/no-show`, method: "POST" };
}

function schedulingPayload(type, form) {
  if (["book", "reschedule"].includes(type)) {
    const payload = {
      provider_id: Number(form.provider_id),
      appointment_type_id: Number(form.appointment_type_id),
      scheduled_start: localDateTimeToIso(form.scheduled_start),
      scheduled_end: localDateTimeToIso(form.scheduled_end),
      reason: form.reason,
      equipment_ids: (form.equipment_ids || []).map(Number),
    };
    if (type === "book") payload.patient_id = form.patient_id;
    if (form.room_id) payload.room_id = Number(form.room_id);
    return payload;
  }
  if (type === "cancel") return { cancellation_reason: form.cancellation_reason };
  if (type === "checkin") {
    return {
      check_in_time: form.check_in_time ? localDateTimeToIso(form.check_in_time) : undefined,
      reason: form.reason || "Check in appointment",
    };
  }
  return { no_show_reason: form.no_show_reason };
}

function SchedulingWorkflowModal({
  type,
  appointment,
  token,
  user,
  resources,
  appointmentTypes,
  patients,
  onClose,
  onSuccess,
}) {
  const [form, setForm] = useState(() => defaultSchedulingForm(type, appointment, resources, appointmentTypes, patients));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateSchedulingWorkflow(type, form);
  const appointmentId = appointment?.appointment_id;
  const hasBlockingConflicts = preview?.conflicts?.some((conflict) => conflict.blocking);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(schedulingPreviewEndpoint(type, appointmentId), {
        token,
        method: "POST",
        body: schedulingPayload(type, form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    const { path, method } = schedulingCommitEndpoint(type, appointmentId);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...schedulingPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={schedulingWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{schedulingWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>
            Close
          </button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {["book", "reschedule"].includes(type) && (
              <div className="form-grid">
                {type === "book" && (
                  <label>
                    Patient / donor
                    <select value={form.patient_id} onChange={(event) => updateField("patient_id", event.target.value)}>
                      <option value="">Select patient</option>
                      {patients.map((patient) => (
                        <option key={patient.patient_id} value={patient.patient_id}>
                          {patientOptionLabel(patient, user)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  Provider
                  <select value={form.provider_id} onChange={(event) => updateField("provider_id", event.target.value)}>
                    <option value="">Select provider</option>
                    {resources.providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Room
                  <select value={form.room_id} onChange={(event) => updateField("room_id", event.target.value)}>
                    <option value="">No room</option>
                    {resources.rooms.map((room) => (
                      <option key={room.id} value={room.id}>
                        {room.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Appointment type
                  <select value={form.appointment_type_id} onChange={(event) => updateField("appointment_type_id", event.target.value)}>
                    <option value="">Select type</option>
                    {appointmentTypes.map((appointmentType) => (
                      <option key={appointmentType.appointment_type_id} value={appointmentType.appointment_type_id}>
                        {appointmentType.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Start
                  <input type="datetime-local" value={form.scheduled_start} onChange={(event) => updateField("scheduled_start", event.target.value)} />
                </label>
                <label>
                  End
                  <input type="datetime-local" value={form.scheduled_end} onChange={(event) => updateField("scheduled_end", event.target.value)} />
                </label>
                <label>
                  Equipment
                  <select
                    multiple
                    value={(form.equipment_ids || []).map(String)}
                    onChange={(event) =>
                      updateField(
                        "equipment_ids",
                        Array.from(event.target.selectedOptions).map((option) => Number(option.value)),
                      )
                    }
                  >
                    {resources.equipment.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Reason
                  <textarea value={form.reason} rows="3" onChange={(event) => updateField("reason", event.target.value)} />
                </label>
              </div>
            )}
            {type === "cancel" && (
              <div className="form-grid">
                <label>
                  Cancellation reason
                  <textarea value={form.cancellation_reason} rows="4" onChange={(event) => updateField("cancellation_reason", event.target.value)} />
                </label>
              </div>
            )}
            {type === "checkin" && (
              <div className="form-grid">
                <label>
                  Check-in time
                  <input type="datetime-local" value={form.check_in_time} onChange={(event) => updateField("check_in_time", event.target.value)} />
                </label>
                <label>
                  Reason
                  <input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} />
                </label>
              </div>
            )}
            {type === "noshow" && (
              <div className="form-grid">
                <label>
                  No-show reason
                  <textarea value={form.no_show_reason} rows="4" onChange={(event) => updateField("no_show_reason", event.target.value)} />
                </label>
              </div>
            )}
            {appointment && (
              <div className="notice-state">
                Workflow target: {appointmentLabel(appointment)} for <TableCellValue value={appointment.patient_name || appointment.patient_id} field="patient" user={user} />.
              </div>
            )}
            <button type="button" onClick={() => setStep("validation")}>
              Continue to validation
            </button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? (
              <div className="error-state">{validationIssues.join(" ")}</div>
            ) : (
              <div className="notice-state">Required fields are complete. Preview will check patient, provider, room, equipment, and transition rules.</div>
            )}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>
              Back to form
            </button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>
              {busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}
              Generate preview
            </button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className={hasBlockingConflicts ? "error-state" : "notice-state"}>{preview.summary}</div>
            <Table
              rows={[
                { field: "Preview hash", value: preview.preview_hash },
                { field: "Validation", value: preview.validation_status },
                { field: "Patient", value: preview.selected_patient || "" },
                { field: "Provider", value: preview.selected_provider || "" },
                { field: "Room", value: preview.selected_room || "No room" },
                { field: "Start", value: formatDateTime(preview.scheduled_start) },
                { field: "End", value: formatDateTime(preview.scheduled_end) },
              ]}
              columns={["field", "value"]}
            />
            {!!preview.selected_equipment?.length && (
              <Table rows={preview.selected_equipment.map((name) => ({ equipment: name }))} columns={["equipment"]} />
            )}
            {!!preview.conflicts?.length && (
              <div className="conflict-list">
                {preview.conflicts.map((conflict) => (
                  <div className="conflict-row blocking" key={`${conflict.conflict_type}-${conflict.entity_id}`}>
                    <XCircle size={16} />
                    <span>{conflict.message}</span>
                  </div>
                ))}
              </div>
            )}
            {!!preview.warnings?.length && (
              <div className="conflict-list">
                {preview.warnings.map((warning) => (
                  <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}>
                    <AlertTriangle size={16} />
                    <span>{warning.message}</span>
                  </div>
                ))}
              </div>
            )}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>
              Back to form
            </button>
            <button type="button" disabled={hasBlockingConflicts} onClick={() => setStep("confirm")}>
              Continue to commit confirmation
            </button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true and append a scheduling workflow audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>
              Back to preview
            </button>
            <button type="button" disabled={busy} onClick={runCommit}>
              {busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}
              Commit workflow
            </button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Scheduling workflow committed successfully.</div>
            <button type="button" onClick={onClose}>
              Done
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalSchedulingPage({ token, navigate, user }) {
  const [appointments, setAppointments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [resources, setResources] = useState({ providers: [], rooms: [], equipment: [] });
  const [appointmentTypes, setAppointmentTypes] = useState([]);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadScheduling() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (dateFilter) params.set("date", dateFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (providerFilter) params.set("provider_id", providerFilter);
    try {
      const [appointmentPayload, resourcePayload, typePayload, patientPayload] = await Promise.all([
        apiRequest(`/api/clinical/scheduling/appointments${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/scheduling/resources", { token }),
        apiRequest("/api/clinical/scheduling/appointment-types", { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
      ]);
      const nextAppointments = appointmentPayload?.appointments || [];
      setAppointments(nextAppointments);
      setResources(resourcePayload || { providers: [], rooms: [], equipment: [] });
      setAppointmentTypes(typePayload || []);
      setPatients(patientPayload?.patients || []);
      setSelectedAppointment((current) => {
        if (!nextAppointments.length) return null;
        if (!current) return nextAppointments[0];
        return nextAppointments.find((appointment) => appointment.appointment_id === current.appointment_id) || nextAppointments[0];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadScheduling();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadScheduling();
  }

  function workflowSuccess(payload) {
    if (payload?.appointment) setSelectedAppointment(payload.appointment);
    loadScheduling();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Clinical scheduling</p>
          <h2>Appointments</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("book")}>
            <CalendarDays size={16} />
            Book Appointment
          </button>
          <button type="button" className="secondary-button" onClick={loadScheduling}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/patients")}>
            <UserPlus size={16} />
            Patients
          </button>
        </div>
      </section>
      <section>
        <form className="scheduling-filter" onSubmit={submitSearch}>
          <label>
            Search
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Appointment, patient, or donor" />
          </label>
          <label>
            Date
            <input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
          </label>
          <label>
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">All</option>
              {appointmentStatusOptions.map((statusName) => (
                <option key={statusName} value={statusName}>
                  {statusName}
                </option>
              ))}
            </select>
          </label>
          <label>
            Provider
            <select value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}>
              <option value="">All</option>
              {resources.providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </label>
          <button type="submit">
            <FileCheck2 size={16} />
            Apply
          </button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading appointment schedule...</div>}
      {!loading && !appointments.length && <div className="empty-state">No appointments match the current filters.</div>}
      {!!appointments.length && (
        <div className="split schedule-layout">
          <section>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Appointment</th>
                    <th>Patient / Donor</th>
                    <th>Provider</th>
                    <th>Start</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appointment) => (
                    <tr key={appointment.appointment_id}>
                      <td>{appointment.appointment_number}</td>
                      <td><TableCellValue value={appointment.patient_name || appointment.patient_id} field="patient" user={user} /></td>
                      <td>{appointment.provider_name}</td>
                      <td>{formatDateTime(appointment.scheduled_start)}</td>
                      <td>
                        <StatusPill status={appointment.status} />
                      </td>
                      <td>
                        <button type="button" className="table-action" onClick={() => setSelectedAppointment(appointment)}>
                          Open
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="appointment-detail-panel">
            {selectedAppointment ? (
              <>
                <div className="section-heading-row">
                  <div>
                    <p className="eyebrow">{selectedAppointment.appointment_number}</p>
                    <h3><TableCellValue value={selectedAppointment.patient_name || selectedAppointment.patient_id} field="patient" user={user} /></h3>
                  </div>
                  <StatusPill status={selectedAppointment.status} />
                </div>
                <Table
                  rows={[
                    { field: "Provider", value: selectedAppointment.provider_name },
                    { field: "Room", value: selectedAppointment.room_name || "No room" },
                    { field: "Type", value: selectedAppointment.appointment_type_name },
                    { field: "Start", value: formatDateTime(selectedAppointment.scheduled_start) },
                    { field: "End", value: formatDateTime(selectedAppointment.scheduled_end) },
                    { field: "Reason", value: selectedAppointment.reason },
                    { field: "Cancellation reason", value: selectedAppointment.cancellation_reason || "" },
                    { field: "No-show reason", value: selectedAppointment.no_show_reason || "" },
                    { field: "Check-in", value: formatDateTime(selectedAppointment.check_in_time) },
                  ]}
                  columns={["field", "value"]}
                  user={user}
                />
                <div className="clinical-actions detail-actions">
                  <button type="button" onClick={() => setModalType("reschedule")}>
                    <Clock size={16} />
                    Reschedule
                  </button>
                  <button type="button" onClick={() => setModalType("checkin")}>
                    <CheckCircle2 size={16} />
                    Check In
                  </button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("cancel")}>
                    <XCircle size={16} />
                    Cancel
                  </button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("noshow")}>
                    <AlertTriangle size={16} />
                    No-show
                  </button>
                </div>
              </>
            ) : (
              <div className="empty-state">Select an appointment to review details.</div>
            )}
          </section>
        </div>
      )}
      {modalType && (
        <SchedulingWorkflowModal
          type={modalType}
          appointment={modalType === "book" ? null : selectedAppointment}
          token={token}
          user={user}
          resources={resources}
          appointmentTypes={appointmentTypes}
          patients={patients}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const screeningStatusOptions = [
  "not_started",
  "in_progress",
  "pending_eligibility",
  "requires_supervisor_review",
  "eligible",
  "eligible_with_conditions",
  "temporarily_deferred",
  "permanently_deferred",
  "cancelled",
];
const screeningOutcomeOptions = [
  "eligible",
  "eligible_with_conditions",
  "temporarily_deferred",
  "permanently_deferred",
  "requires_supervisor_review",
];

function answerMapFromSession(session) {
  return Object.fromEntries(
    (session?.answers || []).map((answer) => [answer.question_key, answer.answer_value?.value ?? ""]),
  );
}

function latestSessionVitals(session) {
  return [...(session?.vitals || [])].sort((left, right) => new Date(right.captured_at) - new Date(left.captured_at))[0] || null;
}

function defaultScreeningForm(type, session, patients, appointments) {
  if (type === "start") {
    return {
      patient_id: patients?.[0]?.patient_id || "",
      appointment_id: appointments?.[0]?.appointment_id || "",
      reason: "Start donor screening session",
    };
  }
  if (type === "questionnaire") {
    return { answers: answerMapFromSession(session), notes: "" };
  }
  if (type === "vitals") {
    const vitals = latestSessionVitals(session);
    return {
      height_cm: vitals?.height_cm || "",
      weight_kg: vitals?.weight_kg || "",
      temperature_c: vitals?.temperature_c || "",
      blood_pressure_systolic: vitals?.blood_pressure_systolic || "",
      blood_pressure_diastolic: vitals?.blood_pressure_diastolic || "",
      pulse: vitals?.pulse || "",
      respiration_rate: vitals?.respiration_rate || "",
      oxygen_saturation: vitals?.oxygen_saturation || "",
      notes: "",
    };
  }
  if (type === "eligibility") return { category: "", reason: "Preview donor eligibility" };
  if (type === "result") {
    return {
      outcome: session?.current_outcome || "eligible",
      reason: "Commit screening result",
      deferral_type: "",
      deferral_ends_at: "",
    };
  }
  return {
    original_outcome: session?.current_outcome || "requires_supervisor_review",
    override_outcome: "eligible_with_conditions",
    reason: "",
  };
}

function screeningWorkflowTitle(type) {
  return {
    start: "Start Screening Session",
    questionnaire: "Complete Questionnaire",
    vitals: "Capture Vitals",
    eligibility: "Preview Eligibility",
    result: "Commit Screening Result",
    override: "Supervisor Override",
  }[type];
}

function validateScreeningWorkflow(type, form, template) {
  const issues = [];
  if (type === "start" && !form.patient_id) issues.push("patient/donor is required.");
  if (type === "questionnaire") {
    const required = template?.questions?.filter((question) => question.required) || [];
    for (const question of required) {
      const value = form.answers?.[question.question_key];
      if (value === "" || value === undefined || value === null) issues.push(`${question.label} is required.`);
    }
  }
  if (type === "vitals") {
    for (const field of ["weight_kg", "temperature_c", "blood_pressure_systolic", "blood_pressure_diastolic", "pulse"]) {
      if (!form[field]) issues.push(`${field.replaceAll("_", " ")} is required.`);
    }
  }
  if (type === "result" && !form.reason) issues.push("result reason is required.");
  if (type === "override") {
    if (!form.reason) issues.push("override reason is required.");
    if (!form.original_outcome || !form.override_outcome) issues.push("original and override outcomes are required.");
  }
  return issues;
}

function screeningPreviewEndpoint(type, sessionId) {
  if (type === "start") return "/api/clinical/screening/sessions/preview";
  if (type === "questionnaire") return `/api/clinical/screening/sessions/${sessionId}/questionnaire/preview`;
  if (type === "vitals") return `/api/clinical/screening/sessions/${sessionId}/vitals/preview`;
  if (type === "override") return `/api/clinical/screening/sessions/${sessionId}/override/preview`;
  return `/api/clinical/screening/sessions/${sessionId}/eligibility/preview`;
}

function screeningCommitEndpoint(type, sessionId) {
  if (type === "start") return { path: "/api/clinical/screening/sessions", method: "POST" };
  if (type === "questionnaire") return { path: `/api/clinical/screening/sessions/${sessionId}/questionnaire`, method: "POST" };
  if (type === "vitals") return { path: `/api/clinical/screening/sessions/${sessionId}/vitals`, method: "POST" };
  if (type === "result") return { path: `/api/clinical/screening/sessions/${sessionId}/result`, method: "POST" };
  return { path: `/api/clinical/screening/sessions/${sessionId}/override`, method: "POST" };
}

function numericOrUndefined(value) {
  return value === "" || value === null || value === undefined ? undefined : Number(value);
}

function screeningPayload(type, form) {
  if (type === "start") {
    const payload = { patient_id: form.patient_id, reason: form.reason || "Start donor screening session" };
    if (form.appointment_id) payload.appointment_id = Number(form.appointment_id);
    return payload;
  }
  if (type === "questionnaire") return { answers: form.answers || {}, notes: form.notes || "" };
  if (type === "vitals") {
    return {
      height_cm: numericOrUndefined(form.height_cm),
      weight_kg: numericOrUndefined(form.weight_kg),
      temperature_c: numericOrUndefined(form.temperature_c),
      blood_pressure_systolic: numericOrUndefined(form.blood_pressure_systolic),
      blood_pressure_diastolic: numericOrUndefined(form.blood_pressure_diastolic),
      pulse: numericOrUndefined(form.pulse),
      respiration_rate: numericOrUndefined(form.respiration_rate),
      oxygen_saturation: numericOrUndefined(form.oxygen_saturation),
      notes: form.notes || "",
    };
  }
  if (type === "eligibility") return compactPayload(form);
  if (type === "result") {
    const payload = { outcome: form.outcome, reason: form.reason };
    if (form.deferral_type) payload.deferral_type = form.deferral_type;
    if (form.deferral_ends_at) payload.deferral_ends_at = localDateTimeToIso(form.deferral_ends_at);
    return payload;
  }
  return {
    original_outcome: form.original_outcome,
    override_outcome: form.override_outcome,
    reason: form.reason,
  };
}

function ScreeningWorkflowModal({
  type,
  session,
  token,
  user,
  template,
  patients,
  appointments,
  onClose,
  onSuccess,
}) {
  const [form, setForm] = useState(() => defaultScreeningForm(type, session, patients, appointments));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateScreeningWorkflow(type, form, template);
  const blockingIssues = preview?.blocking_issues || [];
  const sessionId = session?.session_id;

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateAnswer(key, value) {
    setForm((current) => ({ ...current, answers: { ...(current.answers || {}), [key]: value } }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(screeningPreviewEndpoint(type === "result" ? "eligibility" : type, sessionId), {
        token,
        method: "POST",
        body: screeningPayload(type === "result" ? "eligibility" : type, form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    if (type === "eligibility") {
      setStep("success");
      onSuccess({ eligibilityPreview: preview });
      return;
    }
    setBusy(true);
    setError("");
    const { path, method } = screeningCommitEndpoint(type, sessionId);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...screeningPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={screeningWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{screeningWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {type === "start" && (
              <div className="form-grid">
                <label>Patient / donor<select value={form.patient_id} onChange={(event) => updateField("patient_id", event.target.value)}><option value="">Select patient</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
                <label>Appointment context<select value={form.appointment_id} onChange={(event) => updateField("appointment_id", event.target.value)}><option value="">No appointment</option>{appointments.map((appointment) => <option key={appointment.appointment_id} value={appointment.appointment_id}>{appointment.appointment_number} - {clinicalDisplayText(appointment.patient_name || appointment.patient_id, "patient", user)}</option>)}</select></label>
                <label>Reason<textarea value={form.reason} rows="3" onChange={(event) => updateField("reason", event.target.value)} /></label>
              </div>
            )}
            {type === "questionnaire" && (
              <div className="workflow-list">
                {(template?.questions || []).map((question) => (
                  <label className="workflow-row screening-question-row" key={question.question_key}>
                    <span>{question.label}</span>
                    <select value={String(form.answers?.[question.question_key] ?? "")} onChange={(event) => updateAnswer(question.question_key, event.target.value === "" ? "" : event.target.value === "true")}>
                      <option value="">Select</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </label>
                ))}
                <label>Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "vitals" && (
              <div className="form-grid">
                <label>Height cm<input type="number" value={form.height_cm} onChange={(event) => updateField("height_cm", event.target.value)} /></label>
                <label>Weight kg<input type="number" value={form.weight_kg} onChange={(event) => updateField("weight_kg", event.target.value)} /></label>
                <label>Temperature C<input type="number" step="0.1" value={form.temperature_c} onChange={(event) => updateField("temperature_c", event.target.value)} /></label>
                <label>Systolic<input type="number" value={form.blood_pressure_systolic} onChange={(event) => updateField("blood_pressure_systolic", event.target.value)} /></label>
                <label>Diastolic<input type="number" value={form.blood_pressure_diastolic} onChange={(event) => updateField("blood_pressure_diastolic", event.target.value)} /></label>
                <label>Pulse<input type="number" value={form.pulse} onChange={(event) => updateField("pulse", event.target.value)} /></label>
                <label>Respiration rate<input type="number" value={form.respiration_rate} onChange={(event) => updateField("respiration_rate", event.target.value)} /></label>
                <label>Oxygen saturation<input type="number" value={form.oxygen_saturation} onChange={(event) => updateField("oxygen_saturation", event.target.value)} /></label>
                <label>Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "eligibility" && (
              <div className="form-grid">
                <label>Rule category<input value={form.category} onChange={(event) => updateField("category", event.target.value)} placeholder="Optional existing engine category" /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
              </div>
            )}
            {type === "result" && (
              <div className="form-grid">
                <label>Outcome<select value={form.outcome} onChange={(event) => updateField("outcome", event.target.value)}>{screeningOutcomeOptions.map((outcome) => <option key={outcome}>{outcome}</option>)}</select></label>
                <label>Reason<textarea value={form.reason} rows="3" onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label>Deferral type<select value={form.deferral_type} onChange={(event) => updateField("deferral_type", event.target.value)}><option value="">None</option><option value="temporary">temporary</option><option value="permanent">permanent</option></select></label>
                <label>Temporary deferral ends<input type="datetime-local" value={form.deferral_ends_at} onChange={(event) => updateField("deferral_ends_at", event.target.value)} /></label>
              </div>
            )}
            {type === "override" && (
              <div className="form-grid">
                <label>Original outcome<select value={form.original_outcome} onChange={(event) => updateField("original_outcome", event.target.value)}>{screeningOutcomeOptions.map((outcome) => <option key={outcome}>{outcome}</option>)}</select></label>
                <label>Override outcome<select value={form.override_outcome} onChange={(event) => updateField("override_outcome", event.target.value)}>{screeningOutcomeOptions.map((outcome) => <option key={outcome}>{outcome}</option>)}</select></label>
                <label>Reason<textarea value={form.reason} rows="4" onChange={(event) => updateField("reason", event.target.value)} /></label>
              </div>
            )}
            {session && <div className="notice-state">Workflow target: {session.session_number} for <TableCellValue value={session.patient_name || session.patient_id} field="patient" user={user} />.</div>}
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? <div className="error-state">{validationIssues.join(" ")}</div> : <div className="notice-state">Required fields are complete. Preview will run clinical screening checks.</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>{busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}Generate preview</button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className={blockingIssues.length ? "error-state" : "notice-state"}>{preview.summary}</div>
            <Table rows={[
              { field: "Preview hash", value: preview.preview_hash },
              { field: "Validation", value: preview.validation_status },
              { field: "Proposed outcome", value: preview.proposed_outcome || "" },
              { field: "Supervisor review", value: preview.supervisor_review_required ? "Required" : "Not required" },
              { field: "Deferral recommendation", value: preview.recommended_deferral_type || "" },
            ]} columns={["field", "value"]} />
            {!!preview.blocking_issues?.length && <div className="conflict-list">{preview.blocking_issues.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}><XCircle size={16} /><span>{issue.message}</span></div>)}</div>}
            {!!preview.warnings?.length && <div className="conflict-list">{preview.warnings.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}><AlertTriangle size={16} /><span>{warning.message}</span></div>)}</div>}
            {!!preview.rules_evaluated?.length && <Table rows={preview.rules_evaluated.map((rule) => ({ rule: rule.rule_name, category: rule.rule_category, outcome: rule.outcome, explanation: rule.explanation }))} columns={["rule", "category", "outcome", "explanation"]} />}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={blockingIssues.length > 0 && type !== "eligibility"} onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">{type === "eligibility" ? "Eligibility preview is non-mutating; the durable action is Commit Screening Result." : "Commit will send X-Confirm-Generation: true and append a screening workflow audit entry."}</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>{busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}{type === "eligibility" ? "Use preview" : "Commit workflow"}</button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Screening workflow completed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalScreeningPage({ token, navigate, user }) {
  const [sessions, setSessions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [rules, setRules] = useState([]);
  const [deferrals, setDeferrals] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [eligibilityPreview, setEligibilityPreview] = useState(null);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [appointmentContext, setAppointmentContext] = useState("");
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const template = templates[0] || { questions: [] };

  async function loadScreening() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (dateFilter) params.set("date", dateFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (appointmentContext) params.set("appointment_context", appointmentContext);
    try {
      const [sessionPayload, templatePayload, rulePayload, deferralPayload, patientPayload, appointmentPayload] = await Promise.all([
        apiRequest(`/api/clinical/screening/sessions${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/screening/templates", { token }),
        apiRequest("/api/clinical/screening/rules", { token }),
        apiRequest("/api/clinical/screening/deferrals", { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
        apiRequest("/api/clinical/scheduling/appointments?limit=500", { token }).catch(() => ({ appointments: [] })),
      ]);
      const nextSessions = sessionPayload?.sessions || [];
      setSessions(nextSessions);
      setTemplates(templatePayload || []);
      setRules(rulePayload || []);
      setDeferrals(deferralPayload || []);
      setPatients(patientPayload?.patients || []);
      setAppointments(appointmentPayload?.appointments || []);
      setSelectedSession((current) => {
        if (!nextSessions.length) return null;
        if (!current) return nextSessions[0];
        return nextSessions.find((session) => session.session_id === current.session_id) || nextSessions[0];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadScreening();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadScreening();
  }

  function workflowSuccess(payload) {
    if (payload?.eligibilityPreview) setEligibilityPreview(payload.eligibilityPreview);
    if (payload?.session) setSelectedSession(payload.session);
    loadScreening();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Donor screening / eligibility</p>
          <h2>Screening Queue</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("start")}><CheckCircle2 size={16} />Start Screening</button>
          <button type="button" className="secondary-button" onClick={loadScreening}><RefreshCw size={16} />Refresh</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/encounters")}><FileCheck2 size={16} />Encounters Planned</button>
        </div>
      </section>
      <section>
        <form className="screening-filter" onSubmit={submitSearch}>
          <label>Search<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Session, patient, or donor" /></label>
          <label>Date<input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} /></label>
          <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{screeningStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
          <label>Appointment<select value={appointmentContext} onChange={(event) => setAppointmentContext(event.target.value)}><option value="">All</option><option value="true">With appointment</option><option value="false">Without appointment</option></select></label>
          <button type="submit"><FileCheck2 size={16} />Apply</button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading screening queue...</div>}
      {!loading && !sessions.length && <div className="empty-state">No screening sessions match the current filters.</div>}
      {!!sessions.length && (
        <div className="split screening-layout">
          <section>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Session</th><th>Patient / Donor</th><th>Appointment</th><th>Outcome</th><th>Status</th><th>Action</th></tr></thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr key={session.session_id}>
                      <td>{session.session_number}</td>
                      <td><TableCellValue value={session.patient_name || session.patient_id} field="patient" user={user} /></td>
                      <td>{session.appointment_number || "No appointment"}</td>
                      <td>{session.current_outcome || ""}</td>
                      <td><StatusPill status={session.status} /></td>
                      <td><button type="button" className="table-action" onClick={() => setSelectedSession(session)}>Open</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="appointment-detail-panel">
            {selectedSession ? (
              <>
                <div className="section-heading-row">
                  <div>
                    <p className="eyebrow">{selectedSession.session_number}</p>
                    <h3><TableCellValue value={selectedSession.patient_name || selectedSession.patient_id} field="patient" user={user} /></h3>
                  </div>
                  <StatusPill status={selectedSession.status} />
                </div>
                <Table rows={[
                  { field: "Patient ID", value: selectedSession.patient_id },
                  { field: "Appointment", value: selectedSession.appointment_number || "No appointment" },
                  { field: "Template", value: selectedSession.template_id },
                  { field: "Current outcome", value: selectedSession.current_outcome || "" },
                  { field: "Supervisor review", value: selectedSession.supervisor_review_required ? "Required" : "Not required" },
                  { field: "Started", value: formatDateTime(selectedSession.started_at) },
                  { field: "Completed", value: formatDateTime(selectedSession.completed_at) },
                ]} columns={["field", "value"]} user={user} />
                <div className="clinical-actions detail-actions">
                  <button type="button" onClick={() => setModalType("questionnaire")}><FileCheck2 size={16} />Questionnaire</button>
                  <button type="button" onClick={() => setModalType("vitals")}><HeartPulse size={16} />Vitals</button>
                  <button type="button" onClick={() => setModalType("eligibility")}><ShieldCheck size={16} />Preview Eligibility</button>
                  <button type="button" onClick={() => setModalType("result")}><CheckCircle2 size={16} />Commit Result</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("override")}><AlertTriangle size={16} />Override</button>
                </div>
              </>
            ) : <div className="empty-state">Select a screening session to review details.</div>}
          </section>
        </div>
      )}
      {selectedSession && (
        <div className="screening-detail-grid">
          <section><h3>Questionnaire</h3><Table rows={(selectedSession.answers || []).map((answer) => ({ question: answer.question_key, answer: String(answer.answer_value?.value ?? ""), notes: answer.notes }))} columns={["question", "answer", "notes"]} user={user} /></section>
          <section><h3>Vitals</h3><Table rows={(selectedSession.vitals || []).map((vitals) => ({ captured_at: formatDateTime(vitals.captured_at), weight_kg: vitals.weight_kg, temperature_c: vitals.temperature_c, bp: `${vitals.blood_pressure_systolic}/${vitals.blood_pressure_diastolic}`, pulse: vitals.pulse }))} columns={["captured_at", "weight_kg", "temperature_c", "bp", "pulse"]} user={user} /></section>
          <section><h3>Eligibility Preview</h3>{eligibilityPreview ? <Table rows={[{ field: "Proposed outcome", value: eligibilityPreview.proposed_outcome }, { field: "Supervisor review", value: eligibilityPreview.supervisor_review_required ? "Required" : "Not required" }, { field: "Deferral", value: eligibilityPreview.recommended_deferral_type || "" }]} columns={["field", "value"]} user={user} /> : <div className="empty-state">No eligibility preview generated in this session view.</div>}</section>
          <section><h3>Deferrals</h3><Table rows={(selectedSession.deferrals || []).map((deferral) => ({ deferral: deferral.deferral_number, type: deferral.deferral_type, status: deferral.status, reason: deferral.reason }))} columns={["deferral", "type", "status", "reason"]} user={user} /></section>
          <section><h3>Supervisor Override</h3><Table rows={(selectedSession.outcomes || []).filter((outcome) => outcome.override_outcome).map((outcome) => ({ original: outcome.original_outcome, override: outcome.override_outcome, reason: outcome.reason, at: formatDateTime(outcome.created_at) }))} columns={["original", "override", "reason", "at"]} user={user} /></section>
          <section><h3>Recent Audit Activity</h3><Table rows={(selectedSession.outcomes || []).map((outcome) => ({ event: outcome.override_outcome ? "Override" : "Result", outcome: outcome.committed_outcome || outcome.override_outcome || outcome.proposed_outcome, at: formatDateTime(outcome.created_at) }))} columns={["event", "outcome", "at"]} /></section>
        </div>
      )}
      <div className="split">
        <section><h3>Screening Rules</h3><Table rows={rules.map((rule) => ({ rule: rule.rule_name, category: rule.rule_category, outcome: rule.outcome, explanation: rule.explanation }))} columns={["rule", "category", "outcome", "explanation"]} /></section>
        <section><h3>Active Deferrals</h3><Table rows={deferrals.map((deferral) => ({ deferral: deferral.deferral_number, patient: deferral.patient_id, type: deferral.deferral_type, status: deferral.status }))} columns={["deferral", "patient", "type", "status"]} user={user} /></section>
      </div>
      {modalType && (
        <ScreeningWorkflowModal
          type={modalType}
          session={modalType === "start" ? null : selectedSession}
          token={token}
          user={user}
          template={template}
          patients={patients}
          appointments={appointments}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const encounterStatusOptions = ["draft", "in_progress", "ready_for_signature", "signed", "amended", "cancelled"];

function latestUnsignedEncounterNote(encounter) {
  return [...(encounter?.notes || [])]
    .filter((note) => !["signed", "amended"].includes(note.status))
    .sort((left, right) => new Date(right.updated_at || right.created_at) - new Date(left.updated_at || left.created_at))[0] || null;
}

function latestSignedEncounterNote(encounter) {
  return [...(encounter?.notes || [])]
    .filter((note) => ["signed", "amended"].includes(note.status))
    .sort((left, right) => new Date(right.signed_at || right.updated_at || right.created_at) - new Date(left.signed_at || left.updated_at || left.created_at))[0] || null;
}

function checkedInAppointments(appointments) {
  return (appointments || []).filter((appointment) => appointment.status === "checked_in");
}

function encounterWorkflowTitle(type) {
  return {
    create: "Create Encounter",
    note: "Save Draft Note",
    sign: "Sign Note",
    amend: "Amend Signed Note",
    diagnosis: "Add Diagnosis / Problem",
    allergy: "Add Allergy",
    medication: "Add Medication",
  }[type];
}

function defaultEncounterForm(type, encounter, patients, appointments, sessions, templates) {
  const unsignedNote = latestUnsignedEncounterNote(encounter);
  const signedNote = latestSignedEncounterNote(encounter);
  const firstTemplate = templates?.[0];
  const firstCheckedInAppointment = checkedInAppointments(appointments)?.[0] || appointments?.[0];
  if (type === "create") {
    return {
      patient_id: encounter?.patient_id || patients?.[0]?.patient_id || "",
      appointment_id: firstCheckedInAppointment?.appointment_id || "",
      screening_session_id: sessions?.[0]?.session_id || "",
      encounter_type: "donor_screening",
      chief_complaint: "Donor screening review",
      started_at: defaultDateTimeLocal(0),
      reason: "Create clinical encounter",
    };
  }
  if (type === "note") {
    return {
      note_id: unsignedNote?.note_id || "",
      template_id: unsignedNote?.template_id || firstTemplate?.template_id || "",
      note_type: unsignedNote?.note_type || firstTemplate?.note_type || "clinical_note",
      title: unsignedNote?.title || "Clinical encounter note",
      content: unsignedNote?.content || firstTemplate?.body || "Subjective:\n\nObjective:\n\nAssessment:\n\nPlan:\n",
      reason: "Save draft encounter note",
    };
  }
  if (type === "sign") {
    return {
      note_id: unsignedNote?.note_id || "",
      attestation: "I attest this encounter note is accurate and complete.",
      reason: "Sign encounter note",
    };
  }
  if (type === "amend") {
    return {
      note_id: signedNote?.note_id || "",
      title: "Encounter note addendum",
      amendment_text: "",
      reason: "Late clinical clarification",
    };
  }
  if (type === "diagnosis") {
    return { code: "", display: "", diagnosis_type: "problem", status: "active", onset_date: "", notes: "", reason: "Add encounter diagnosis/problem" };
  }
  if (type === "allergy") {
    return { allergen: "", reaction: "", severity: "unknown", status: "active", onset_date: "", notes: "", reason: "Add patient allergy" };
  }
  return {
    medication_name: "",
    dose: "",
    route: "",
    frequency: "",
    status: "active",
    start_date: "",
    end_date: "",
    indication: "",
    notes: "",
    reason: "Add patient medication",
  };
}

function validateEncounterWorkflow(type, form, encounter) {
  const issues = [];
  if (type === "create") {
    if (!form.patient_id) issues.push("Patient/donor is required.");
    if (!form.reason?.trim()) issues.push("Reason is required.");
  }
  if (type === "note") {
    if (!form.title?.trim()) issues.push("Note title is required.");
    if (!form.content?.trim()) issues.push("Note content is required.");
  }
  if (type === "sign") {
    if (!form.note_id) issues.push("Select a draft or ready note to sign.");
    if (!form.attestation?.trim()) issues.push("Attestation is required.");
  }
  if (type === "amend") {
    if (!form.note_id) issues.push("Select a signed note to amend.");
    if (!form.amendment_text?.trim()) issues.push("Amendment text is required.");
    if (!form.reason?.trim()) issues.push("Amendment reason is required.");
  }
  if (type === "diagnosis") {
    if (!form.code?.trim()) issues.push("Diagnosis/problem code is required.");
    if (!form.display?.trim()) issues.push("Diagnosis/problem display is required.");
  }
  if (type === "allergy" && !form.allergen?.trim()) issues.push("Allergen is required.");
  if (type === "medication" && !form.medication_name?.trim()) issues.push("Medication name is required.");
  if (["note", "sign", "amend", "diagnosis", "allergy", "medication"].includes(type) && !encounter) issues.push("Select an encounter first.");
  return issues;
}

function encounterPayload(type, form) {
  const payload = compactPayload(form);
  for (const field of ["appointment_id", "screening_session_id", "template_id", "note_id"]) {
    if (payload[field] !== undefined) payload[field] = Number(payload[field]);
  }
  if (payload.started_at) payload.started_at = localDateTimeToIso(payload.started_at);
  return payload;
}

function encounterPreviewEndpoint(type, encounter, patientId) {
  if (type === "create") return "/api/clinical/encounters/preview";
  if (type === "note") return `/api/clinical/encounters/${encounter.encounter_id}/notes/preview`;
  if (type === "sign") return `/api/clinical/encounters/${encounter.encounter_id}/sign/preview`;
  if (type === "amend") return `/api/clinical/encounters/${encounter.encounter_id}/amend/preview`;
  if (type === "diagnosis") return `/api/clinical/encounters/${encounter.encounter_id}/diagnoses/preview`;
  if (type === "allergy") return `/api/clinical/patients/${patientId}/allergies/preview`;
  return `/api/clinical/patients/${patientId}/medications/preview`;
}

function encounterCommitEndpoint(type, encounter, patientId) {
  if (type === "create") return { path: "/api/clinical/encounters", method: "POST" };
  if (type === "note") return { path: `/api/clinical/encounters/${encounter.encounter_id}/notes`, method: "POST" };
  if (type === "sign") return { path: `/api/clinical/encounters/${encounter.encounter_id}/sign`, method: "POST" };
  if (type === "amend") return { path: `/api/clinical/encounters/${encounter.encounter_id}/amend`, method: "POST" };
  if (type === "diagnosis") return { path: `/api/clinical/encounters/${encounter.encounter_id}/diagnoses`, method: "POST" };
  if (type === "allergy") return { path: `/api/clinical/patients/${patientId}/allergies`, method: "POST" };
  return { path: `/api/clinical/patients/${patientId}/medications`, method: "POST" };
}

function EncounterWorkflowModal({ type, encounter, token, user, patients, appointments, sessions, templates, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultEncounterForm(type, encounter, patients, appointments, sessions, templates));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateEncounterWorkflow(type, form, encounter);
  const blockingIssues = preview?.blocking_issues || [];
  const warningRows = preview?.warnings || [];
  const patientId = encounter?.patient_id || form.patient_id;
  const unsignedNotes = (encounter?.notes || []).filter((note) => !["signed", "amended"].includes(note.status));
  const signedNotes = (encounter?.notes || []).filter((note) => ["signed", "amended"].includes(note.status));

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateTemplate(templateId) {
    const template = templates.find((item) => String(item.template_id) === String(templateId));
    setForm((current) => ({
      ...current,
      template_id: templateId,
      note_type: template?.note_type || current.note_type,
      content: current.content?.trim() ? current.content : template?.body || current.content,
    }));
  }

  function updateSelectedNote(noteId) {
    const note = [...unsignedNotes, ...signedNotes].find((item) => String(item.note_id) === String(noteId));
    setForm((current) => ({
      ...current,
      note_id: noteId,
      title: note?.title || current.title,
      content: type === "note" ? note?.content || current.content : current.content,
      template_id: type === "note" ? note?.template_id || current.template_id : current.template_id,
    }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(encounterPreviewEndpoint(type, encounter, patientId), {
        token,
        method: "POST",
        body: encounterPayload(type, form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    const { path, method } = encounterCommitEndpoint(type, encounter, patientId);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...encounterPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={encounterWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{encounterWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {type === "create" && (
              <div className="form-grid">
                <label>Patient / donor<select value={form.patient_id} onChange={(event) => updateField("patient_id", event.target.value)}><option value="">Select patient</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
                <label>Checked-in appointment<select value={form.appointment_id} onChange={(event) => updateField("appointment_id", event.target.value)}><option value="">No appointment</option>{appointments.map((appointment) => <option key={appointment.appointment_id} value={appointment.appointment_id}>{appointment.appointment_number} - {clinicalDisplayText(appointment.patient_name || appointment.patient_id, "patient", user)} ({appointment.status})</option>)}</select></label>
                <label>Screening context<select value={form.screening_session_id} onChange={(event) => updateField("screening_session_id", event.target.value)}><option value="">No screening session</option>{sessions.map((session) => <option key={session.session_id} value={session.session_id}>{session.session_number} - {clinicalDisplayText(session.patient_name || session.patient_id, "patient", user)}</option>)}</select></label>
                <label>Encounter type<input value={form.encounter_type} onChange={(event) => updateField("encounter_type", event.target.value)} /></label>
                <label>Started<input type="datetime-local" value={form.started_at} onChange={(event) => updateField("started_at", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label>Chief complaint<textarea value={form.chief_complaint} rows="3" onChange={(event) => updateField("chief_complaint", event.target.value)} /></label>
              </div>
            )}
            {type === "note" && (
              <div className="form-grid">
                <label>Draft note<select value={form.note_id} onChange={(event) => updateSelectedNote(event.target.value)}><option value="">New draft note</option>{unsignedNotes.map((note) => <option key={note.note_id} value={note.note_id}>{note.title} - {note.status}</option>)}</select></label>
                <label>Template<select value={form.template_id} onChange={(event) => updateTemplate(event.target.value)}><option value="">No template</option>{templates.map((template) => <option key={template.template_id} value={template.template_id}>{template.name}</option>)}</select></label>
                <label>Note type<input value={form.note_type} onChange={(event) => updateField("note_type", event.target.value)} /></label>
                <label>Title<input value={form.title} onChange={(event) => updateField("title", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Draft note<textarea value={form.content} rows="12" onChange={(event) => updateField("content", event.target.value)} /></label>
              </div>
            )}
            {type === "sign" && (
              <div className="form-grid">
                <label>Note to sign<select value={form.note_id} onChange={(event) => updateSelectedNote(event.target.value)}><option value="">Select note</option>{unsignedNotes.map((note) => <option key={note.note_id} value={note.note_id}>{note.title} - {note.status}</option>)}</select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Attestation<textarea value={form.attestation} rows="3" onChange={(event) => updateField("attestation", event.target.value)} /></label>
              </div>
            )}
            {type === "amend" && (
              <div className="form-grid">
                <label>Signed note<select value={form.note_id} onChange={(event) => updateSelectedNote(event.target.value)}><option value="">Select signed note</option>{signedNotes.map((note) => <option key={note.note_id} value={note.note_id}>{note.title} - v{note.version}</option>)}</select></label>
                <label>Title<input value={form.title} onChange={(event) => updateField("title", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Amendment text<textarea value={form.amendment_text} rows="8" onChange={(event) => updateField("amendment_text", event.target.value)} /></label>
              </div>
            )}
            {type === "diagnosis" && (
              <div className="form-grid">
                <label>Code<input value={form.code} onChange={(event) => updateField("code", event.target.value)} /></label>
                <label>Display<input value={form.display} onChange={(event) => updateField("display", event.target.value)} /></label>
                <label>Type<input value={form.diagnosis_type} onChange={(event) => updateField("diagnosis_type", event.target.value)} /></label>
                <label>Status<input value={form.status} onChange={(event) => updateField("status", event.target.value)} /></label>
                <label>Onset date<input type="date" value={form.onset_date} onChange={(event) => updateField("onset_date", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="4" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "allergy" && (
              <div className="form-grid">
                <label>Allergen<input value={form.allergen} onChange={(event) => updateField("allergen", event.target.value)} /></label>
                <label>Reaction<input value={form.reaction} onChange={(event) => updateField("reaction", event.target.value)} /></label>
                <label>Severity<input value={form.severity} onChange={(event) => updateField("severity", event.target.value)} /></label>
                <label>Status<input value={form.status} onChange={(event) => updateField("status", event.target.value)} /></label>
                <label>Onset date<input type="date" value={form.onset_date} onChange={(event) => updateField("onset_date", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="4" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "medication" && (
              <div className="form-grid">
                <label>Medication<input value={form.medication_name} onChange={(event) => updateField("medication_name", event.target.value)} /></label>
                <label>Dose<input value={form.dose} onChange={(event) => updateField("dose", event.target.value)} /></label>
                <label>Route<input value={form.route} onChange={(event) => updateField("route", event.target.value)} /></label>
                <label>Frequency<input value={form.frequency} onChange={(event) => updateField("frequency", event.target.value)} /></label>
                <label>Status<input value={form.status} onChange={(event) => updateField("status", event.target.value)} /></label>
                <label>Start date<input type="date" value={form.start_date} onChange={(event) => updateField("start_date", event.target.value)} /></label>
                <label>End date<input type="date" value={form.end_date} onChange={(event) => updateField("end_date", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Indication<textarea value={form.indication} rows="3" onChange={(event) => updateField("indication", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {encounter && <div className="notice-state">Workflow target: {encounter.encounter_number} for <TableCellValue value={encounter.patient_name || encounter.patient_id} field="patient" user={user} />.</div>}
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? <div className="error-state">{validationIssues.join(" ")}</div> : <div className="notice-state">Required fields are complete. Preview will run encounter workflow checks.</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>{busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}Generate preview</button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className={blockingIssues.length ? "error-state" : "notice-state"}>{preview.summary}</div>
            <Table rows={[{ field: "Preview hash", value: preview.preview_hash }, { field: "Validation", value: preview.validation_status }, { field: "Workflow", value: preview.workflow }]} columns={["field", "value"]} />
            {!!blockingIssues.length && <div className="conflict-list">{blockingIssues.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}><XCircle size={16} /><span>{issue.message}</span></div>)}</div>}
            {!!warningRows.length && <div className="conflict-list">{warningRows.map((warning) => <div className="conflict-row warning" key={`${warning.issue_type}-${warning.field}`}><AlertTriangle size={16} /><span>{warning.message}</span></div>)}</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={blockingIssues.length > 0} onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true and append an encounter workflow audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>{busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}Commit workflow</button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Encounter workflow completed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalEncountersPage({ token, navigate, user }) {
  const [encounters, setEncounters] = useState([]);
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedEncounter, setSelectedEncounter] = useState(null);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [appointmentContext, setAppointmentContext] = useState("");
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const latestDraft = latestUnsignedEncounterNote(selectedEncounter);
  const latestSigned = latestSignedEncounterNote(selectedEncounter);

  async function loadEncounters() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (dateFilter) params.set("date", dateFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (appointmentContext) params.set("appointment_context", appointmentContext);
    try {
      const [encounterPayload, templatePayload, patientPayload, appointmentPayload, screeningPayload] = await Promise.all([
        apiRequest(`/api/clinical/encounters${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/encounters/templates", { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
        apiRequest("/api/clinical/scheduling/appointments?limit=500", { token }).catch(() => ({ appointments: [] })),
        apiRequest("/api/clinical/screening/sessions?limit=500", { token }).catch(() => ({ sessions: [] })),
      ]);
      const nextEncounters = encounterPayload?.encounters || [];
      setEncounters(nextEncounters);
      setTemplates(templatePayload || []);
      setPatients(patientPayload?.patients || []);
      setAppointments(appointmentPayload?.appointments || []);
      setSessions(screeningPayload?.sessions || []);
      setSelectedEncounter((current) => {
        if (!nextEncounters.length) return null;
        if (!current) return nextEncounters[0];
        return nextEncounters.find((encounter) => encounter.encounter_id === current.encounter_id) || nextEncounters[0];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadEncounters();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadEncounters();
  }

  function workflowSuccess(payload) {
    if (payload?.encounter) setSelectedEncounter(payload.encounter);
    loadEncounters();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">EMR / encounters</p>
          <h2>Encounter Worklist</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("create")}><FileCheck2 size={16} />Create Encounter</button>
          <button type="button" className="secondary-button" onClick={loadEncounters}><RefreshCw size={16} />Refresh</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/screening")}><CheckCircle2 size={16} />Screening</button>
        </div>
      </section>
      <section>
        <form className="encounter-filter" onSubmit={submitSearch}>
          <label>Search<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Encounter, patient, or donor" /></label>
          <label>Date<input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} /></label>
          <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{encounterStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
          <label>Appointment<select value={appointmentContext} onChange={(event) => setAppointmentContext(event.target.value)}><option value="">All</option><option value="true">With appointment</option><option value="false">Without appointment</option></select></label>
          <button type="submit"><FileCheck2 size={16} />Apply</button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading encounter worklist...</div>}
      {!loading && !encounters.length && <div className="empty-state">No encounters match the current filters.</div>}
      {!!encounters.length && (
        <div className="split encounter-layout">
          <section>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Encounter</th><th>Patient / Donor</th><th>Context</th><th>Started</th><th>Status</th><th>Action</th></tr></thead>
                <tbody>
                  {encounters.map((encounter) => (
                    <tr key={encounter.encounter_id}>
                      <td>{encounter.encounter_number}</td>
                      <td><TableCellValue value={encounter.patient_name || encounter.patient_id} field="patient" user={user} /></td>
                      <td>{encounter.appointment_number || encounter.screening_session_number || "Direct"}</td>
                      <td>{formatDateTime(encounter.started_at)}</td>
                      <td><StatusPill status={encounter.status} /></td>
                      <td><button type="button" className="table-action" onClick={() => setSelectedEncounter(encounter)}>Open</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="appointment-detail-panel">
            {selectedEncounter ? (
              <>
                <div className="section-heading-row">
                  <div>
                    <p className="eyebrow">{selectedEncounter.encounter_number}</p>
                    <h3><TableCellValue value={selectedEncounter.patient_name || selectedEncounter.patient_id} field="patient" user={user} /></h3>
                  </div>
                  <StatusPill status={selectedEncounter.status} />
                </div>
                <Table rows={[
                  { field: "Patient ID", value: selectedEncounter.patient_id },
                  { field: "Appointment", value: selectedEncounter.appointment_number || "No appointment" },
                  { field: "Screening", value: selectedEncounter.screening_session_number || "No screening session" },
                  { field: "Type", value: selectedEncounter.encounter_type },
                  { field: "Chief complaint", value: selectedEncounter.chief_complaint },
                  { field: "Started", value: formatDateTime(selectedEncounter.started_at) },
                  { field: "Signed", value: formatDateTime(selectedEncounter.signed_at) },
                ]} columns={["field", "value"]} user={user} />
                <div className="clinical-actions detail-actions">
                  <button type="button" onClick={() => setModalType("note")}><FileCheck2 size={16} />Save Draft Note</button>
                  <button type="button" onClick={() => setModalType("sign")}><ShieldCheck size={16} />Sign Note</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("amend")}><AlertTriangle size={16} />Amend</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("diagnosis")}><HeartPulse size={16} />Diagnosis</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("allergy")}><XCircle size={16} />Allergy</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("medication")}><Activity size={16} />Medication</button>
                </div>
              </>
            ) : <div className="empty-state">Select an encounter to review details.</div>}
          </section>
        </div>
      )}
      {selectedEncounter && (
        <>
          <div className="encounter-detail-grid">
            <section>
              <h3>Clinical Summary</h3>
              <Table rows={[
                { field: "Draft note", value: latestDraft ? `${latestDraft.title} (${latestDraft.status})` : "No active draft" },
                { field: "Latest signed", value: latestSigned ? `${latestSigned.title} v${latestSigned.version}` : "No signed note" },
                { field: "Diagnoses/problems", value: (selectedEncounter.diagnoses || []).length },
                { field: "Allergies", value: (selectedEncounter.allergies || []).length },
                { field: "Medications", value: (selectedEncounter.medications || []).length },
              ]} columns={["field", "value"]} user={user} />
            </section>
            <section>
              <h3>Draft Note Workspace</h3>
              {latestDraft ? (
                <Table rows={[{ title: latestDraft.title, status: latestDraft.status, template: latestDraft.template_name || "No template", updated: formatDateTime(latestDraft.updated_at) }]} columns={["title", "status", "template", "updated"]} user={user} />
              ) : (
                <div className="empty-state">No draft note is active for this encounter.</div>
              )}
            </section>
            <section>
              <h3>Downstream Actions</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/orders")}><span>Orders / Results</span><StatusPill status="Active" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/care-plans")}><span>Care Plans</span><StatusPill status="Foundation pending" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/billing")}><span>Billing</span><StatusPill status="Planned workflow" /></button>
              </div>
            </section>
          </div>
          <div className="encounter-detail-grid">
            <section><h3>Notes</h3><Table rows={(selectedEncounter.notes || []).map((note) => ({ title: note.title, status: note.status, version: note.version, locked: note.locked ? "Read-only" : "Editable draft", signed: formatDateTime(note.signed_at), addendum: note.is_addendum ? "Yes" : "No" }))} columns={["title", "status", "version", "locked", "signed", "addendum"]} user={user} /></section>
            <section><h3>Diagnoses / Problems</h3><Table rows={(selectedEncounter.diagnoses || []).map((diagnosis) => ({ code: diagnosis.code, display: diagnosis.display, type: diagnosis.diagnosis_type, status: diagnosis.status }))} columns={["code", "display", "type", "status"]} user={user} /></section>
            <section><h3>Allergies</h3><Table rows={(selectedEncounter.allergies || []).map((allergy) => ({ allergen: allergy.allergen, reaction: allergy.reaction, severity: allergy.severity, status: allergy.status }))} columns={["allergen", "reaction", "severity", "status"]} user={user} /></section>
            <section><h3>Medications</h3><Table rows={(selectedEncounter.medications || []).map((medication) => ({ medication: medication.medication_name, dose: medication.dose, route: medication.route, frequency: medication.frequency, status: medication.status }))} columns={["medication", "dose", "route", "frequency", "status"]} user={user} /></section>
            <section><h3>Version / Addendum History</h3><Table rows={(selectedEncounter.notes || []).map((note) => ({ note: note.title, version: note.version, status: note.status, amendment_reason: note.amendment_reason || "", from_note: note.amended_from_note_id || "" }))} columns={["note", "version", "status", "amendment_reason", "from_note"]} user={user} /></section>
            <section><h3>Recent Audit Activity</h3><Table rows={(selectedEncounter.status_history || []).map((history) => ({ status: `${history.from_status || "new"} -> ${history.to_status}`, reason: history.reason, notes: history.notes, at: formatDateTime(history.changed_at) }))} columns={["status", "reason", "notes", "at"]} user={user} /></section>
          </div>
        </>
      )}
      {modalType && (
        <EncounterWorkflowModal
          type={modalType}
          encounter={modalType === "create" ? null : selectedEncounter}
          token={token}
          user={user}
          patients={patients}
          appointments={appointments}
          sessions={sessions}
          templates={templates}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const orderStatusOptions = ["draft", "ordered", "in_progress", "resulted", "cancelled"];
const orderPriorityOptions = ["routine", "urgent", "stat"];
const orderResultFlagOptions = ["pending", "normal", "abnormal", "critical"];
const orderResultStatusOptions = ["normal", "abnormal", "critical", "corrected", "cancelled"];

function ResultFlagPill({ flag }) {
  const normalized = flag || "pending";
  const tone = normalized === "critical" ? "danger" : normalized === "abnormal" ? "warning" : normalized === "normal" ? "success" : "neutral";
  return <span className={cx("status-pill", tone)}>{normalized}</span>;
}

function acknowledgedResultIds(order) {
  return new Set((order?.acknowledgements || []).filter((ack) => ack.result_id).map((ack) => ack.result_id));
}

function criticalUnacknowledgedResults(order) {
  const acknowledged = acknowledgedResultIds(order);
  const orderAcknowledged = (order?.acknowledgements || []).some((ack) => !ack.result_id);
  if (orderAcknowledged) return [];
  return (order?.results || []).filter(
    (result) => result.critical_flag && result.result_status !== "cancelled" && !acknowledged.has(result.result_id),
  );
}

function latestOrderResult(order) {
  return [...(order?.results || [])].sort((left, right) => new Date(right.resulted_at) - new Date(left.resulted_at))[0] || null;
}

function orderWorkflowTitle(type) {
  return {
    create: "Create Order",
    result: "Enter Result",
    acknowledge: "Acknowledge Critical Result",
    cancel: "Cancel Order",
  }[type];
}

function defaultOrderForm(type, order, patients, encounters, sessions, appointments, catalog) {
  const firstCatalog = catalog?.[0];
  const firstPatient = order?.patient_id || patients?.[0]?.patient_id || "";
  if (type === "create") {
    return {
      patient_id: firstPatient,
      encounter_id: encounters?.[0]?.encounter_id || "",
      screening_session_id: sessions?.[0]?.session_id || "",
      appointment_id: appointments?.[0]?.appointment_id || "",
      catalog_item_id: firstCatalog?.catalog_item_id || "",
      priority: firstCatalog?.default_priority || "routine",
      clinical_indication: "Donor screening order",
      ordering_provider: "",
      ordered_at: defaultDateTimeLocal(0),
      reason: "Create clinical order",
    };
  }
  if (type === "result") {
    return {
      result_name: order?.catalog_name || "Order result",
      result_value: "",
      result_unit: "",
      reference_range: "",
      result_status: "normal",
      abnormal_flag: false,
      critical_flag: false,
      resulted_at: defaultDateTimeLocal(0),
      notes: "",
      corrected_from_result_id: "",
      reason: "Enter order result",
    };
  }
  if (type === "acknowledge") {
    return {
      result_id: criticalUnacknowledgedResults(order)?.[0]?.result_id || "",
      acknowledgement_note: "",
      reason: "Acknowledge critical result",
    };
  }
  return {
    cancellation_reason: "",
    reason: "Cancel clinical order",
  };
}

function validateOrderWorkflow(type, form, order) {
  const issues = [];
  if (type === "create") {
    if (!form.patient_id) issues.push("Patient/donor is required.");
    if (!form.catalog_item_id) issues.push("Catalog item is required.");
    if (!form.priority?.trim()) issues.push("Priority is required.");
  }
  if (type === "result") {
    if (!order) issues.push("Select an order first.");
    if (!form.result_name?.trim()) issues.push("Result name is required.");
    if (!form.result_value?.trim()) issues.push("Result value is required.");
    if (!form.reason?.trim()) issues.push("Result reason is required.");
  }
  if (type === "acknowledge") {
    if (!order) issues.push("Select an order first.");
    if (!form.reason?.trim()) issues.push("Acknowledgement reason is required.");
    if (!criticalUnacknowledgedResults(order).length) issues.push("No unacknowledged critical result is present.");
  }
  if (type === "cancel") {
    if (!order) issues.push("Select an order first.");
    if (!form.cancellation_reason?.trim()) issues.push("Cancellation reason is required.");
  }
  return issues;
}

function orderPayload(type, form) {
  const payload = compactPayload(form);
  for (const field of ["catalog_item_id", "encounter_id", "screening_session_id", "appointment_id", "result_id", "corrected_from_result_id"]) {
    if (payload[field] !== undefined) payload[field] = Number(payload[field]);
  }
  if (payload.ordered_at) payload.ordered_at = localDateTimeToIso(payload.ordered_at);
  if (payload.resulted_at) payload.resulted_at = localDateTimeToIso(payload.resulted_at);
  if (type === "result" && payload.result_status === "critical") payload.critical_flag = true;
  if (type === "result" && ["abnormal", "critical"].includes(payload.result_status)) payload.abnormal_flag = true;
  return payload;
}

function orderPreviewEndpoint(type, order) {
  if (type === "create") return "/api/clinical/orders/preview";
  if (type === "result") return `/api/clinical/orders/${order.order_id}/results/preview`;
  if (type === "acknowledge") return `/api/clinical/orders/${order.order_id}/acknowledge/preview`;
  return `/api/clinical/orders/${order.order_id}/cancel/preview`;
}

function orderCommitEndpoint(type, order) {
  if (type === "create") return { path: "/api/clinical/orders", method: "POST" };
  if (type === "result") return { path: `/api/clinical/orders/${order.order_id}/results`, method: "POST" };
  if (type === "acknowledge") return { path: `/api/clinical/orders/${order.order_id}/acknowledge`, method: "POST" };
  return { path: `/api/clinical/orders/${order.order_id}/cancel`, method: "POST" };
}

function orderContextLabel(order) {
  return order?.encounter_number || order?.screening_session_number || order?.appointment_number || "Direct order";
}

function OrderWorkflowModal({ type, order, token, user, patients, encounters, sessions, appointments, catalog, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultOrderForm(type, order, patients, encounters, sessions, appointments, catalog));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateOrderWorkflow(type, form, order);
  const blockingIssues = preview?.blocking_issues || [];
  const warningRows = preview?.warnings || [];
  const unacknowledged = criticalUnacknowledgedResults(order);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateCatalog(catalogItemId) {
    const item = catalog.find((catalogItem) => String(catalogItem.catalog_item_id) === String(catalogItemId));
    setForm((current) => ({
      ...current,
      catalog_item_id: catalogItemId,
      priority: item?.default_priority || current.priority,
    }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(orderPreviewEndpoint(type, order), {
        token,
        method: "POST",
        body: orderPayload(type, form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    const { path, method } = orderCommitEndpoint(type, order);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...orderPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={orderWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{orderWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {type === "create" && (
              <div className="form-grid">
                <label>Patient / donor<select value={form.patient_id} onChange={(event) => updateField("patient_id", event.target.value)}><option value="">Select patient</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
                <label>Catalog<select value={form.catalog_item_id} onChange={(event) => updateCatalog(event.target.value)}><option value="">Select order</option>{catalog.map((item) => <option key={item.catalog_item_id} value={item.catalog_item_id}>{item.code} - {item.name}</option>)}</select></label>
                <label>Priority<select value={form.priority} onChange={(event) => updateField("priority", event.target.value)}>{orderPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
                <label>Encounter<select value={form.encounter_id} onChange={(event) => updateField("encounter_id", event.target.value)}><option value="">No encounter</option>{encounters.map((encounter) => <option key={encounter.encounter_id} value={encounter.encounter_id}>{encounter.encounter_number} - {clinicalDisplayText(encounter.patient_name || encounter.patient_id, "patient", user)}</option>)}</select></label>
                <label>Screening<select value={form.screening_session_id} onChange={(event) => updateField("screening_session_id", event.target.value)}><option value="">No screening</option>{sessions.map((session) => <option key={session.session_id} value={session.session_id}>{session.session_number} - {clinicalDisplayText(session.patient_name || session.patient_id, "patient", user)}</option>)}</select></label>
                <label>Appointment<select value={form.appointment_id} onChange={(event) => updateField("appointment_id", event.target.value)}><option value="">No appointment</option>{appointments.map((appointment) => <option key={appointment.appointment_id} value={appointment.appointment_id}>{appointment.appointment_number} - {clinicalDisplayText(appointment.patient_name || appointment.patient_id, "patient", user)}</option>)}</select></label>
                <label>Ordered at<input type="datetime-local" value={form.ordered_at} onChange={(event) => updateField("ordered_at", event.target.value)} /></label>
                <label>Ordering provider<input value={form.ordering_provider} onChange={(event) => updateField("ordering_provider", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Clinical indication<textarea value={form.clinical_indication} rows="3" onChange={(event) => updateField("clinical_indication", event.target.value)} /></label>
              </div>
            )}
            {type === "result" && (
              <div className="form-grid">
                <label>Result name<input value={form.result_name} onChange={(event) => updateField("result_name", event.target.value)} /></label>
                <label>Value<input value={form.result_value} onChange={(event) => updateField("result_value", event.target.value)} /></label>
                <label>Unit<input value={form.result_unit} onChange={(event) => updateField("result_unit", event.target.value)} /></label>
                <label>Reference range<input value={form.reference_range} onChange={(event) => updateField("reference_range", event.target.value)} /></label>
                <label>Status<select value={form.result_status} onChange={(event) => updateField("result_status", event.target.value)}>{orderResultStatusOptions.map((resultStatus) => <option key={resultStatus}>{resultStatus}</option>)}</select></label>
                <label>Resulted at<input type="datetime-local" value={form.resulted_at} onChange={(event) => updateField("resulted_at", event.target.value)} /></label>
                <label>Corrects result<select value={form.corrected_from_result_id} onChange={(event) => updateField("corrected_from_result_id", event.target.value)}><option value="">No correction</option>{(order?.results || []).map((result) => <option key={result.result_id} value={result.result_id}>{result.result_name} - {clinicalDisplayText(result.result_value, "result_value", user)} ({formatDateTime(result.resulted_at)})</option>)}</select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="checkbox-row"><input type="checkbox" checked={Boolean(form.abnormal_flag)} onChange={() => updateField("abnormal_flag", !form.abnormal_flag)} />Abnormal</label>
                <label className="checkbox-row"><input type="checkbox" checked={Boolean(form.critical_flag)} onChange={() => updateField("critical_flag", !form.critical_flag)} />Critical</label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="4" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "acknowledge" && (
              <div className="form-grid">
                <label>Critical result<select value={form.result_id} onChange={(event) => updateField("result_id", event.target.value)}><option value="">Select critical result</option>{unacknowledged.map((result) => <option key={result.result_id} value={result.result_id}>{result.result_name} - {clinicalDisplayText(result.result_value, "result_value", user)}</option>)}</select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Acknowledgement note<textarea value={form.acknowledgement_note} rows="4" onChange={(event) => updateField("acknowledgement_note", event.target.value)} /></label>
              </div>
            )}
            {type === "cancel" && (
              <div className="form-grid">
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Cancellation reason<textarea value={form.cancellation_reason} rows="5" onChange={(event) => updateField("cancellation_reason", event.target.value)} /></label>
              </div>
            )}
            {order && <div className="notice-state">Workflow target: {order.order_number} for <TableCellValue value={order.patient_name || order.patient_id} field="patient" user={user} />.</div>}
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? <div className="error-state">{validationIssues.join(" ")}</div> : <div className="notice-state">Required fields are complete. Preview will run orders/results checks.</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>{busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}Generate preview</button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className={blockingIssues.length ? "error-state" : "notice-state"}>{preview.summary}</div>
            <Table rows={[{ field: "Preview hash", value: preview.preview_hash }, { field: "Validation", value: preview.validation_status }, { field: "Workflow", value: preview.workflow }]} columns={["field", "value"]} />
            {!!blockingIssues.length && <div className="conflict-list">{blockingIssues.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}><XCircle size={16} /><span>{issue.message}</span></div>)}</div>}
            {!!warningRows.length && <div className="conflict-list">{warningRows.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}><AlertTriangle size={16} /><span>{warning.message}</span></div>)}</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={blockingIssues.length > 0} onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true and append an orders/results workflow audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>{busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}Commit workflow</button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Orders/results workflow completed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalOrdersPage({ token, navigate, user }) {
  const [orders, setOrders] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [patients, setPatients] = useState([]);
  const [encounters, setEncounters] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [patientFilter, setPatientFilter] = useState("");
  const [encounterFilter, setEncounterFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [resultFlagFilter, setResultFlagFilter] = useState("");
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const latestResult = latestOrderResult(selectedOrder);
  const unacknowledged = criticalUnacknowledgedResults(selectedOrder);

  async function loadOrders() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (dateFilter) params.set("date", dateFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (patientFilter) params.set("patient_id", patientFilter);
    if (encounterFilter) params.set("encounter_id", encounterFilter);
    if (priorityFilter) params.set("priority", priorityFilter);
    if (resultFlagFilter) params.set("result_flag", resultFlagFilter);
    try {
      const [orderPayload, catalogPayload, patientPayload, encounterPayload, screeningPayload, appointmentPayload] = await Promise.all([
        apiRequest(`/api/clinical/orders${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/orders/catalog", { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
        apiRequest("/api/clinical/encounters?limit=500", { token }).catch(() => ({ encounters: [] })),
        apiRequest("/api/clinical/screening/sessions?limit=500", { token }).catch(() => ({ sessions: [] })),
        apiRequest("/api/clinical/scheduling/appointments?limit=500", { token }).catch(() => ({ appointments: [] })),
      ]);
      const nextOrders = orderPayload?.orders || [];
      setOrders(nextOrders);
      setCatalog(catalogPayload || []);
      setPatients(patientPayload?.patients || []);
      setEncounters(encounterPayload?.encounters || []);
      setSessions(screeningPayload?.sessions || []);
      setAppointments(appointmentPayload?.appointments || []);
      setSelectedOrder((current) => {
        if (!nextOrders.length) return null;
        if (!current) return nextOrders[0];
        return nextOrders.find((order) => order.order_id === current.order_id) || nextOrders[0];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadOrders();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadOrders();
  }

  function workflowSuccess(payload) {
    if (payload?.order) setSelectedOrder(payload.order);
    loadOrders();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Orders / results</p>
          <h2>Orders Worklist</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("create")}><UploadCloud size={16} />Create Order</button>
          <button type="button" className="secondary-button" onClick={loadOrders}><RefreshCw size={16} />Refresh</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/encounters")}><FileCheck2 size={16} />Encounters</button>
        </div>
      </section>
      <section>
        <form className="orders-filter" onSubmit={submitSearch}>
          <label>Search<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Order, patient, indication" /></label>
          <label>Date<input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} /></label>
          <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{orderStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
          <label>Patient<select value={patientFilter} onChange={(event) => setPatientFilter(event.target.value)}><option value="">All</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
          <label>Encounter<select value={encounterFilter} onChange={(event) => setEncounterFilter(event.target.value)}><option value="">All</option>{encounters.map((encounter) => <option key={encounter.encounter_id} value={encounter.encounter_id}>{encounter.encounter_number}</option>)}</select></label>
          <label>Priority<select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="">All</option>{orderPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
          <label>Result<select value={resultFlagFilter} onChange={(event) => setResultFlagFilter(event.target.value)}><option value="">All</option>{orderResultFlagOptions.map((flag) => <option key={flag}>{flag}</option>)}</select></label>
          <button type="submit"><FileCheck2 size={16} />Apply</button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading orders worklist...</div>}
      {!loading && !orders.length && <div className="empty-state">No orders match the current filters.</div>}
      {!!orders.length && (
        <div className="split orders-layout">
          <section>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Order</th><th>Patient / Donor</th><th>Catalog</th><th>Priority</th><th>Status</th><th>Result</th><th>Action</th></tr></thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.order_id} className={order.has_critical_unacknowledged ? "order-critical-row" : ""}>
                      <td>{order.order_number}</td>
                      <td><TableCellValue value={order.patient_name || order.patient_id} field="patient" user={user} /></td>
                      <td>{order.catalog_code || order.catalog_name}</td>
                      <td>{order.priority}</td>
                      <td><StatusPill status={order.status} /></td>
                      <td><ResultFlagPill flag={order.result_flag} /></td>
                      <td><button type="button" className="table-action" onClick={() => setSelectedOrder(order)}>Open</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="appointment-detail-panel">
            {selectedOrder ? (
              <>
                <div className="section-heading-row">
                  <div>
                    <p className="eyebrow">{selectedOrder.order_number}</p>
                    <h3><TableCellValue value={selectedOrder.patient_name || selectedOrder.patient_id} field="patient" user={user} /></h3>
                  </div>
                  <ResultFlagPill flag={selectedOrder.result_flag} />
                </div>
                <Table rows={[
                  { field: "Patient ID", value: selectedOrder.patient_id },
                  { field: "Catalog", value: `${selectedOrder.catalog_code} - ${selectedOrder.catalog_name}` },
                  { field: "Context", value: orderContextLabel(selectedOrder) },
                  { field: "Priority", value: selectedOrder.priority },
                  { field: "Status", value: selectedOrder.status },
                  { field: "Ordered", value: formatDateTime(selectedOrder.ordered_at) },
                  { field: "Critical ack", value: unacknowledged.length ? "Required" : "Current" },
                ]} columns={["field", "value"]} user={user} />
                <div className="clinical-actions detail-actions">
                  <button type="button" onClick={() => setModalType("result")}><Activity size={16} />Enter Result</button>
                  <button type="button" onClick={() => setModalType("acknowledge")}><ShieldCheck size={16} />Acknowledge</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("cancel")}><XCircle size={16} />Cancel</button>
                </div>
              </>
            ) : <div className="empty-state">Select an order to review details.</div>}
          </section>
        </div>
      )}
      {selectedOrder && (
        <>
          <div className="orders-detail-grid">
            <section>
              <h3>Patient / Encounter Context</h3>
              <Table rows={[
                { field: "Patient", value: selectedOrder.patient_name || selectedOrder.patient_id },
                { field: "Encounter", value: selectedOrder.encounter_number || "No encounter" },
                { field: "Screening", value: selectedOrder.screening_session_number || "No screening" },
                { field: "Appointment", value: selectedOrder.appointment_number || "No appointment" },
                { field: "Indication", value: selectedOrder.clinical_indication },
              ]} columns={["field", "value"]} user={user} />
            </section>
            <section>
              <h3>Result Summary</h3>
              <Table rows={[
                { field: "Latest result", value: latestResult ? `${latestResult.result_name}: ${latestResult.result_value}` : "Pending" },
                { field: "Unit / range", value: latestResult ? `${latestResult.result_unit || ""} ${latestResult.reference_range || ""}`.trim() : "" },
                { field: "Flag", value: selectedOrder.result_flag },
                { field: "Critical unacknowledged", value: unacknowledged.length },
                { field: "Resulted", value: formatDateTime(latestResult?.resulted_at) },
              ]} columns={["field", "value"]} user={user} />
            </section>
            <section>
              <h3>Downstream Actions</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/care-plans")}><span>Care Plans</span><StatusPill status="Active" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/billing")}><span>Billing</span><StatusPill status="Planned workflow" /></button>
              </div>
            </section>
          </div>
          <div className="orders-detail-grid">
            <section className="orders-wide-section">
              <h3>Results</h3>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Name</th><th>Value</th><th>Unit</th><th>Range</th><th>Status</th><th>Ack</th><th>Resulted</th></tr></thead>
                  <tbody>
                    {(selectedOrder.results || []).map((result) => (
                      <tr key={result.result_id} className={result.critical_flag ? "order-critical-row" : result.abnormal_flag ? "order-abnormal-row" : ""}>
                        <td>{result.result_name}</td>
                        <td><TableCellValue value={result.result_value} field="result_value" user={user} /></td>
                        <td>{result.result_unit || ""}</td>
                        <td>{result.reference_range || ""}</td>
                        <td><ResultFlagPill flag={result.critical_flag ? "critical" : result.abnormal_flag ? "abnormal" : result.result_status} /></td>
                        <td>{result.requires_acknowledgement && !acknowledgedResultIds(selectedOrder).has(result.result_id) ? "Required" : "Current"}</td>
                        <td>{formatDateTime(result.resulted_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!(selectedOrder.results || []).length && <div className="empty-state">No results entered for this order.</div>}
              </div>
            </section>
            <section>
              <h3>Correction History</h3>
              <Table rows={(selectedOrder.results || []).filter((result) => result.corrected_from_result_id).map((result) => ({ result: result.result_name, value: result.result_value, corrects: result.corrected_from_result_id, at: formatDateTime(result.resulted_at) }))} columns={["result", "value", "corrects", "at"]} user={user} />
            </section>
            <section>
              <h3>Recent Audit / Status</h3>
              <Table rows={(selectedOrder.status_history || []).map((history) => ({ status: `${history.from_status || "new"} -> ${history.to_status}`, reason: history.reason, notes: history.notes, at: formatDateTime(history.changed_at) }))} columns={["status", "reason", "notes", "at"]} user={user} />
            </section>
          </div>
          <section>
            <h3>Catalog</h3>
            <Table rows={catalog.map((item) => ({ code: item.code, name: item.name, type: item.order_type, priority: item.default_priority, specimen: item.specimen_type || "" }))} columns={["code", "name", "type", "priority", "specimen"]} />
          </section>
        </>
      )}
      {modalType && (
        <OrderWorkflowModal
          type={modalType}
          order={modalType === "create" ? null : selectedOrder}
          token={token}
          user={user}
          patients={patients}
          encounters={encounters}
          sessions={sessions}
          appointments={appointments}
          catalog={catalog}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const carePlanStatusOptions = ["draft", "active", "on_hold", "completed", "cancelled", "closed"];
const carePlanPriorityOptions = ["routine", "urgent", "stat"];
const carePlanResultFlagOptions = ["none", "pending", "normal", "abnormal", "critical"];

function defaultDateInput(daysAhead = 0) {
  const date = new Date(Date.now() + daysAhead * 24 * 60 * 60 * 1000);
  return date.toISOString().slice(0, 10);
}

function PriorityChip({ priority }) {
  const normalized = priority || "routine";
  const tone = normalized === "stat" ? "danger" : normalized === "urgent" ? "warning" : "neutral";
  return <span className={cx("priority-chip", tone)}>{normalized}</span>;
}

function latestCarePlanProgress(carePlan) {
  return [...(carePlan?.progress_notes || [])].sort((left, right) => new Date(right.created_at) - new Date(left.created_at))[0] || null;
}

function carePlanOrderResults(orders, orderId) {
  const order = (orders || []).find((item) => String(item.order_id) === String(orderId));
  return order?.results || [];
}

function carePlanWorkflowTitle(type) {
  return {
    create: "Create Care Plan",
    goal: "Add Goal",
    intervention: "Add Intervention",
    task: "Add Task",
    progress: "Add Progress Update",
    close: "Close Care Plan",
  }[type];
}

function defaultCarePlanForm(type, carePlan, patients, encounters, sessions, orders) {
  const firstOrder = orders?.[0];
  const firstResult = firstOrder?.results?.[0];
  if (type === "create") {
    return {
      patient_id: patients?.[0]?.patient_id || "",
      encounter_id: encounters?.[0]?.encounter_id || "",
      screening_session_id: sessions?.[0]?.session_id || "",
      order_id: firstOrder?.order_id || "",
      order_result_id: firstResult?.result_id || "",
      title: firstResult?.critical_flag ? "Critical result follow-up plan" : "Care coordination plan",
      plan_type: "case_management",
      priority: firstResult?.critical_flag ? "urgent" : "routine",
      start_date: defaultDateInput(0),
      target_date: defaultDateInput(14),
      team_member_name: "",
      team_member_role: "Care Coordinator",
      reason: "Create care plan",
    };
  }
  if (type === "goal") {
    return { goal: "", target_date: defaultDateInput(30), status: "active", priority: carePlan?.priority || "routine", notes: "", reason: "Add care plan goal" };
  }
  if (type === "intervention") {
    return { intervention: "", intervention_type: "follow_up", owner: "", due_date: defaultDateInput(7), status: "planned", notes: "", reason: "Add care plan intervention" };
  }
  if (type === "task") {
    return { title: "", description: "", owner: "", due_date: defaultDateInput(7), priority: carePlan?.priority || "routine", status: "open", notes: "", reason: "Add care plan task" };
  }
  if (type === "progress") {
    return { progress_note: "", status_update: "", reason: "Add care plan progress update" };
  }
  return { outcome_summary: "", closure_reason: "", reason: "Close care plan" };
}

function validateCarePlanWorkflow(type, form, carePlan) {
  const issues = [];
  if (type === "create") {
    if (!form.patient_id) issues.push("Patient/donor is required.");
    if (!form.title?.trim()) issues.push("Title is required.");
    if (!form.plan_type?.trim()) issues.push("Plan type is required.");
    if (!form.priority?.trim()) issues.push("Priority is required.");
  }
  if (type === "goal" && !form.goal?.trim()) issues.push("Goal is required.");
  if (type === "intervention") {
    if (!form.intervention?.trim()) issues.push("Intervention is required.");
    if (!form.intervention_type?.trim()) issues.push("Intervention type is required.");
  }
  if (type === "task") {
    if (!form.title?.trim()) issues.push("Task title is required.");
    if (!form.owner?.trim()) issues.push("Task owner is required.");
    if (!form.due_date) issues.push("Task due date is required.");
  }
  if (type === "progress" && !form.progress_note?.trim()) issues.push("Progress note is required.");
  if (type === "close") {
    if (!form.outcome_summary?.trim()) issues.push("Outcome summary is required.");
    if (!form.closure_reason?.trim()) issues.push("Closure reason is required.");
  }
  if (type !== "create" && !carePlan) issues.push("Select a care plan first.");
  return issues;
}

function carePlanPayload(type, form) {
  const payload = compactPayload(form);
  for (const field of ["encounter_id", "screening_session_id", "order_id", "order_result_id"]) {
    if (payload[field] !== undefined) payload[field] = Number(payload[field]);
  }
  return payload;
}

function carePlanPreviewEndpoint(type, carePlan) {
  if (type === "create") return "/api/clinical/care-plans/preview";
  if (type === "goal") return `/api/clinical/care-plans/${carePlan.care_plan_id}/goals/preview`;
  if (type === "intervention") return `/api/clinical/care-plans/${carePlan.care_plan_id}/interventions/preview`;
  if (type === "task") return `/api/clinical/care-plans/${carePlan.care_plan_id}/tasks/preview`;
  if (type === "progress") return `/api/clinical/care-plans/${carePlan.care_plan_id}/progress/preview`;
  return `/api/clinical/care-plans/${carePlan.care_plan_id}/close/preview`;
}

function carePlanCommitEndpoint(type, carePlan) {
  if (type === "create") return { path: "/api/clinical/care-plans", method: "POST" };
  if (type === "goal") return { path: `/api/clinical/care-plans/${carePlan.care_plan_id}/goals`, method: "POST" };
  if (type === "intervention") return { path: `/api/clinical/care-plans/${carePlan.care_plan_id}/interventions`, method: "POST" };
  if (type === "task") return { path: `/api/clinical/care-plans/${carePlan.care_plan_id}/tasks`, method: "POST" };
  if (type === "progress") return { path: `/api/clinical/care-plans/${carePlan.care_plan_id}/progress`, method: "POST" };
  return { path: `/api/clinical/care-plans/${carePlan.care_plan_id}/close`, method: "POST" };
}

function carePlanContextLabel(carePlan) {
  return carePlan?.order_number || carePlan?.encounter_number || carePlan?.screening_session_number || "Direct care plan";
}

function CarePlanWorkflowModal({ type, carePlan, token, user, patients, encounters, sessions, orders, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultCarePlanForm(type, carePlan, patients, encounters, sessions, orders));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateCarePlanWorkflow(type, form, carePlan);
  const blockingIssues = preview?.blocking_issues || [];
  const warningRows = preview?.warnings || [];
  const linkedOrderResults = carePlanOrderResults(orders, form.order_id);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateOrder(orderId) {
    const results = carePlanOrderResults(orders, orderId);
    setForm((current) => ({ ...current, order_id: orderId, order_result_id: results?.[0]?.result_id || "" }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(carePlanPreviewEndpoint(type, carePlan), {
        token,
        method: "POST",
        body: carePlanPayload(type, form),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    const { path, method } = carePlanCommitEndpoint(type, carePlan);
    try {
      const payload = await apiRequest(path, {
        token,
        method,
        headers: { "X-Confirm-Generation": "true" },
        body: { ...carePlanPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={carePlanWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{carePlanWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            {type === "create" && (
              <div className="form-grid">
                <label>Patient / donor<select value={form.patient_id} onChange={(event) => updateField("patient_id", event.target.value)}><option value="">Select patient</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
                <label>Encounter<select value={form.encounter_id} onChange={(event) => updateField("encounter_id", event.target.value)}><option value="">No encounter</option>{encounters.map((encounter) => <option key={encounter.encounter_id} value={encounter.encounter_id}>{encounter.encounter_number} - {clinicalDisplayText(encounter.patient_name || encounter.patient_id, "patient", user)}</option>)}</select></label>
                <label>Screening<select value={form.screening_session_id} onChange={(event) => updateField("screening_session_id", event.target.value)}><option value="">No screening</option>{sessions.map((session) => <option key={session.session_id} value={session.session_id}>{session.session_number} - {clinicalDisplayText(session.patient_name || session.patient_id, "patient", user)}</option>)}</select></label>
                <label>Order<select value={form.order_id} onChange={(event) => updateOrder(event.target.value)}><option value="">No order</option>{orders.map((order) => <option key={order.order_id} value={order.order_id}>{order.order_number} - {clinicalDisplayText(order.patient_name || order.patient_id, "patient", user)} ({order.result_flag})</option>)}</select></label>
                <label>Order result<select value={form.order_result_id} onChange={(event) => updateField("order_result_id", event.target.value)}><option value="">No result</option>{linkedOrderResults.map((result) => <option key={result.result_id} value={result.result_id}>{result.result_name} - {clinicalDisplayText(result.result_value, "result_value", user)}{result.critical_flag ? " (critical)" : result.abnormal_flag ? " (abnormal)" : ""}</option>)}</select></label>
                <label>Plan type<input value={form.plan_type} onChange={(event) => updateField("plan_type", event.target.value)} /></label>
                <label>Priority<select value={form.priority} onChange={(event) => updateField("priority", event.target.value)}>{carePlanPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
                <label>Start date<input type="date" value={form.start_date} onChange={(event) => updateField("start_date", event.target.value)} /></label>
                <label>Target date<input type="date" value={form.target_date} onChange={(event) => updateField("target_date", event.target.value)} /></label>
                <label>Team member<input value={form.team_member_name} onChange={(event) => updateField("team_member_name", event.target.value)} /></label>
                <label>Team role<input value={form.team_member_role} onChange={(event) => updateField("team_member_role", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Title<textarea value={form.title} rows="3" onChange={(event) => updateField("title", event.target.value)} /></label>
              </div>
            )}
            {type === "goal" && (
              <div className="form-grid">
                <label>Target date<input type="date" value={form.target_date} onChange={(event) => updateField("target_date", event.target.value)} /></label>
                <label>Status<input value={form.status} onChange={(event) => updateField("status", event.target.value)} /></label>
                <label>Priority<select value={form.priority} onChange={(event) => updateField("priority", event.target.value)}><option value="">None</option>{carePlanPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Goal<textarea value={form.goal} rows="4" onChange={(event) => updateField("goal", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "intervention" && (
              <div className="form-grid">
                <label>Type<input value={form.intervention_type} onChange={(event) => updateField("intervention_type", event.target.value)} /></label>
                <label>Owner<input value={form.owner} onChange={(event) => updateField("owner", event.target.value)} /></label>
                <label>Due date<input type="date" value={form.due_date} onChange={(event) => updateField("due_date", event.target.value)} /></label>
                <label>Status<input value={form.status} onChange={(event) => updateField("status", event.target.value)} /></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Intervention<textarea value={form.intervention} rows="4" onChange={(event) => updateField("intervention", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "task" && (
              <div className="form-grid">
                <label>Title<input value={form.title} onChange={(event) => updateField("title", event.target.value)} /></label>
                <label>Owner<input value={form.owner} onChange={(event) => updateField("owner", event.target.value)} /></label>
                <label>Due date<input type="date" value={form.due_date} onChange={(event) => updateField("due_date", event.target.value)} /></label>
                <label>Priority<select value={form.priority} onChange={(event) => updateField("priority", event.target.value)}>{carePlanPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
                <label>Status<select value={form.status} onChange={(event) => updateField("status", event.target.value)}><option>open</option><option>in_progress</option><option>completed</option><option>cancelled</option></select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Description<textarea value={form.description} rows="3" onChange={(event) => updateField("description", event.target.value)} /></label>
                <label className="wide-field">Notes<textarea value={form.notes} rows="3" onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
            )}
            {type === "progress" && (
              <div className="form-grid">
                <label>Status update<select value={form.status_update} onChange={(event) => updateField("status_update", event.target.value)}><option value="">No status change</option><option value="active">active</option><option value="on_hold">on_hold</option><option value="draft">draft</option></select></label>
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Progress note<textarea value={form.progress_note} rows="6" onChange={(event) => updateField("progress_note", event.target.value)} /></label>
              </div>
            )}
            {type === "close" && (
              <div className="form-grid">
                <label>Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
                <label className="wide-field">Outcome summary<textarea value={form.outcome_summary} rows="5" onChange={(event) => updateField("outcome_summary", event.target.value)} /></label>
                <label className="wide-field">Closure reason<textarea value={form.closure_reason} rows="4" onChange={(event) => updateField("closure_reason", event.target.value)} /></label>
              </div>
            )}
            {carePlan && <div className="notice-state">Workflow target: {carePlan.care_plan_number} for <TableCellValue value={carePlan.patient_name || carePlan.patient_id} field="patient" user={user} />.</div>}
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? <div className="error-state">{validationIssues.join(" ")}</div> : <div className="notice-state">Required fields are complete. Preview will run care plan checks.</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>{busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}Generate preview</button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className={blockingIssues.length ? "error-state" : "notice-state"}>{preview.summary}</div>
            <Table rows={[{ field: "Preview hash", value: preview.preview_hash }, { field: "Validation", value: preview.validation_status }, { field: "Workflow", value: preview.workflow }]} columns={["field", "value"]} />
            {!!blockingIssues.length && <div className="conflict-list">{blockingIssues.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}><XCircle size={16} /><span>{issue.message}</span></div>)}</div>}
            {!!warningRows.length && <div className="conflict-list">{warningRows.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}><AlertTriangle size={16} /><span>{warning.message}</span></div>)}</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={blockingIssues.length > 0} onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true and append a care plan workflow audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>{busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}Commit workflow</button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Care plan workflow completed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function ClinicalCarePlansPage({ token, navigate, user }) {
  const [carePlans, setCarePlans] = useState([]);
  const [patients, setPatients] = useState([]);
  const [encounters, setEncounters] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [selectedCarePlan, setSelectedCarePlan] = useState(null);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [patientFilter, setPatientFilter] = useState("");
  const [encounterFilter, setEncounterFilter] = useState("");
  const [orderContextFilter, setOrderContextFilter] = useState("");
  const [resultFlagFilter, setResultFlagFilter] = useState("");
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const latestProgress = latestCarePlanProgress(selectedCarePlan);

  async function loadCarePlans() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (dateFilter) params.set("date", dateFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (priorityFilter) params.set("priority", priorityFilter);
    if (patientFilter) params.set("patient_id", patientFilter);
    if (encounterFilter) params.set("encounter_id", encounterFilter);
    if (orderContextFilter) params.set("order_context", orderContextFilter);
    if (resultFlagFilter) params.set("result_flag", resultFlagFilter);
    try {
      const [carePlanPayload, patientPayload, encounterPayload, screeningPayload, orderPayload] = await Promise.all([
        apiRequest(`/api/clinical/care-plans${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
        apiRequest("/api/clinical/encounters?limit=500", { token }).catch(() => ({ encounters: [] })),
        apiRequest("/api/clinical/screening/sessions?limit=500", { token }).catch(() => ({ sessions: [] })),
        apiRequest("/api/clinical/orders?limit=500", { token }).catch(() => ({ orders: [] })),
      ]);
      const nextCarePlans = carePlanPayload?.care_plans || [];
      setCarePlans(nextCarePlans);
      setPatients(patientPayload?.patients || []);
      setEncounters(encounterPayload?.encounters || []);
      setSessions(screeningPayload?.sessions || []);
      setOrders(orderPayload?.orders || []);
      setSelectedCarePlan((current) => {
        if (!nextCarePlans.length) return null;
        if (!current) return nextCarePlans[0];
        return nextCarePlans.find((carePlan) => carePlan.care_plan_id === current.care_plan_id) || nextCarePlans[0];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadCarePlans();
  }, [token]);

  function submitSearch(event) {
    event.preventDefault();
    loadCarePlans();
  }

  function workflowSuccess(payload) {
    if (payload?.care_plan) setSelectedCarePlan(payload.care_plan);
    loadCarePlans();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Care plans / case management</p>
          <h2>Care Plan Worklist</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("create")}><Activity size={16} />Create Care Plan</button>
          <button type="button" className="secondary-button" onClick={loadCarePlans}><RefreshCw size={16} />Refresh</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/orders")}><UploadCloud size={16} />Orders</button>
        </div>
      </section>
      <section>
        <form className="care-plan-filter" onSubmit={submitSearch}>
          <label>Search<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Care plan or patient" /></label>
          <label>Start date<input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} /></label>
          <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{carePlanStatusOptions.map((statusName) => <option key={statusName}>{statusName}</option>)}</select></label>
          <label>Priority<select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="">All</option>{carePlanPriorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
          <label>Patient<select value={patientFilter} onChange={(event) => setPatientFilter(event.target.value)}><option value="">All</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>)}</select></label>
          <label>Encounter<select value={encounterFilter} onChange={(event) => setEncounterFilter(event.target.value)}><option value="">All</option>{encounters.map((encounter) => <option key={encounter.encounter_id} value={encounter.encounter_id}>{encounter.encounter_number}</option>)}</select></label>
          <label>Order context<select value={orderContextFilter} onChange={(event) => setOrderContextFilter(event.target.value)}><option value="">All</option><option value="true">With order/result</option><option value="false">Without order</option></select></label>
          <label>Result<select value={resultFlagFilter} onChange={(event) => setResultFlagFilter(event.target.value)}><option value="">All</option>{carePlanResultFlagOptions.map((flag) => <option key={flag}>{flag}</option>)}</select></label>
          <button type="submit"><FileCheck2 size={16} />Apply</button>
        </form>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading && <div className="notice-state">Loading care plan worklist...</div>}
      {!loading && !carePlans.length && <div className="empty-state">No care plans match the current filters.</div>}
      {!!carePlans.length && (
        <div className="split care-plan-layout">
          <section>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Care plan</th><th>Patient / Donor</th><th>Context</th><th>Priority</th><th>Status</th><th>Result</th><th>Target</th><th>Action</th></tr></thead>
                <tbody>
                  {carePlans.map((carePlan) => (
                    <tr key={carePlan.care_plan_id} className={carePlan.has_critical_unacknowledged ? "order-critical-row" : ""}>
                      <td>{carePlan.care_plan_number}</td>
                      <td><TableCellValue value={carePlan.patient_name || carePlan.patient_id} field="patient" user={user} /></td>
                      <td>{carePlanContextLabel(carePlan)}</td>
                      <td><PriorityChip priority={carePlan.priority} /></td>
                      <td><StatusPill status={carePlan.status} /></td>
                      <td><ResultFlagPill flag={carePlan.result_flag} /></td>
                      <td>{formatDate(carePlan.target_date)}</td>
                      <td><button type="button" className="table-action" onClick={() => setSelectedCarePlan(carePlan)}>Open</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="appointment-detail-panel">
            {selectedCarePlan ? (
              <>
                <div className="section-heading-row">
                  <div>
                    <p className="eyebrow">{selectedCarePlan.care_plan_number}</p>
                    <h3>{selectedCarePlan.title}</h3>
                  </div>
                  <StatusPill status={selectedCarePlan.status} />
                </div>
                <Table rows={[
                  { field: "Patient", value: selectedCarePlan.patient_name || selectedCarePlan.patient_id },
                  { field: "Context", value: carePlanContextLabel(selectedCarePlan) },
                  { field: "Priority", value: selectedCarePlan.priority },
                  { field: "Result flag", value: selectedCarePlan.result_flag },
                  { field: "Critical ack", value: selectedCarePlan.has_critical_unacknowledged ? "Required" : "Current" },
                  { field: "Latest progress", value: latestProgress ? formatDateTime(latestProgress.created_at) : "No progress note" },
                ]} columns={["field", "value"]} user={user} />
                <div className="clinical-actions detail-actions">
                  <button type="button" onClick={() => setModalType("goal")}><CheckCircle2 size={16} />Goal</button>
                  <button type="button" onClick={() => setModalType("intervention")}><Activity size={16} />Intervention</button>
                  <button type="button" onClick={() => setModalType("task")}><Clock size={16} />Task</button>
                  <button type="button" onClick={() => setModalType("progress")}><FileCheck2 size={16} />Progress</button>
                  <button type="button" className="secondary-button" onClick={() => setModalType("close")}><XCircle size={16} />Close</button>
                </div>
              </>
            ) : <div className="empty-state">Select a care plan to review details.</div>}
          </section>
        </div>
      )}
      {selectedCarePlan && (
        <>
          <div className="care-plan-detail-grid">
            <section>
              <h3>Patient / Clinical Context</h3>
              <Table rows={[
                { field: "Patient ID", value: selectedCarePlan.patient_id },
                { field: "Encounter", value: selectedCarePlan.encounter_number || "No encounter" },
                { field: "Screening", value: selectedCarePlan.screening_session_number || "No screening" },
                { field: "Order", value: selectedCarePlan.order_number || "No order" },
                { field: "Order result", value: selectedCarePlan.order_result_summary || "No linked result" },
              ]} columns={["field", "value"]} user={user} />
            </section>
            <section>
              <h3>Plan Summary</h3>
              <Table rows={[
                { field: "Type", value: selectedCarePlan.plan_type },
                { field: "Start", value: formatDate(selectedCarePlan.start_date) },
                { field: "Target", value: formatDate(selectedCarePlan.target_date) },
                { field: "Reason", value: selectedCarePlan.reason },
                { field: "Closed", value: formatDateTime(selectedCarePlan.closed_at) },
              ]} columns={["field", "value"]} user={user} />
            </section>
            <section>
              <h3>Downstream Actions</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/billing")}><span>Billing Review</span><StatusPill status="Planned workflow" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/quality")}><span>Quality Review</span><StatusPill status="Foundation pending" /></button>
              </div>
            </section>
          </div>
          <div className="care-plan-detail-grid">
            <section><h3>Goals</h3><Table rows={(selectedCarePlan.goals || []).map((goal) => ({ goal: goal.goal, status: goal.status, priority: goal.priority || "", target: formatDate(goal.target_date), notes: goal.notes || "" }))} columns={["goal", "status", "priority", "target", "notes"]} user={user} /></section>
            <section><h3>Interventions</h3><Table rows={(selectedCarePlan.interventions || []).map((intervention) => ({ intervention: intervention.intervention, type: intervention.intervention_type, owner: intervention.owner || "", due: formatDate(intervention.due_date), status: intervention.status }))} columns={["intervention", "type", "owner", "due", "status"]} user={user} /></section>
            <section><h3>Tasks</h3><Table rows={(selectedCarePlan.tasks || []).map((task) => ({ title: task.title, owner: task.owner, due: formatDate(task.due_date), priority: task.priority, status: task.status, completed: formatDateTime(task.completed_at) }))} columns={["title", "owner", "due", "priority", "status", "completed"]} user={user} /></section>
            <section><h3>Care Team</h3><Table rows={(selectedCarePlan.team_members || []).map((member) => ({ member: member.member_name, role: member.role, primary: member.is_primary ? "Yes" : "No" }))} columns={["member", "role", "primary"]} user={user} /></section>
            <section className="care-plan-wide-section"><h3>Progress Timeline</h3><Table rows={(selectedCarePlan.progress_notes || []).map((note) => ({ at: formatDateTime(note.created_at), status_update: note.status_update || "", note: note.progress_note }))} columns={["at", "status_update", "note"]} user={user} /></section>
            <section><h3>Closure</h3><Table rows={[
              { field: "Status", value: selectedCarePlan.status },
              { field: "Closed at", value: formatDateTime(selectedCarePlan.closed_at) },
              { field: "Closure reason", value: selectedCarePlan.closure_reason || "" },
              { field: "Outcome summary", value: selectedCarePlan.outcome_summary || "" },
            ]} columns={["field", "value"]} user={user} /></section>
            <section><h3>Recent Audit / Status</h3><Table rows={(selectedCarePlan.status_history || []).map((history) => ({ status: `${history.from_status || "new"} -> ${history.to_status}`, reason: history.reason, notes: history.notes, at: formatDateTime(history.changed_at) }))} columns={["status", "reason", "notes", "at"]} user={user} /></section>
          </div>
        </>
      )}
      {modalType && (
        <CarePlanWorkflowModal
          type={modalType}
          carePlan={modalType === "create" ? null : selectedCarePlan}
          token={token}
          user={user}
          patients={patients}
          encounters={encounters}
          sessions={sessions}
          orders={orders}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const billingStatusOptions = ["open", "closed"];
const billingClaimStatusOptions = ["ready_for_review", "partially_paid", "paid", "denied"];
const billingDenialStatusOptions = ["open", "resolved"];

function billingWorkflowTitle(type) {
  return {
    verify: "Verify Insurance",
    charge: "Capture Charge",
    claim: "Create Claim Draft",
    payment: "Post Payment",
    denial: "Capture Denial",
  }[type];
}

function defaultBillingForm(type, account, patients, queue) {
  const patient = account?.patient_id || patients[0]?.patient_id || "";
  const insurance = patients.find((item) => item.patient_id === patient)?.insurance_profiles?.[0]?.insurance_id || "";
  if (type === "verify") {
    return { patient_id: patient, patient_insurance_id: insurance, verification_status: "verified", notes: "" };
  }
  if (type === "charge") {
    return {
      patient_id: patient,
      encounter_id: "",
      order_id: "",
      order_result_id: "",
      care_plan_id: "",
      care_plan_task_id: "",
      service_date: defaultDateInput(),
      code: "",
      code_type: "internal",
      description: "",
      quantity: "1",
      unit_amount: "",
      status: "captured",
    };
  }
  if (type === "claim") {
    return { patient_id: patient, patient_insurance_id: insurance, charge_ids: [], status: "ready_for_review", diagnosis_code: "" };
  }
  if (type === "payment") {
    return { claim_id: queue?.claims?.[0]?.claim_id || "", payment_amount: "", adjustment_amount: "0", payment_method: "eft", payer_type: "insurance", reference_number: "", notes: "" };
  }
  return { claim_id: queue?.claims?.[0]?.claim_id || "", claim_line_id: "", denial_code: "", denial_reason: "", status: "open", assigned_to: "", due_date: "" };
}

function billingPreviewEndpoint(type) {
  return {
    verify: "/api/clinical/billing/insurance-verifications/preview",
    charge: "/api/clinical/billing/charges/preview",
    claim: "/api/clinical/billing/claims/preview",
    payment: "/api/clinical/billing/payments/preview",
    denial: "/api/clinical/billing/denials/preview",
  }[type];
}

function billingCommitEndpoint(type) {
  return {
    verify: "/api/clinical/billing/insurance-verifications",
    charge: "/api/clinical/billing/charges",
    claim: "/api/clinical/billing/claims",
    payment: "/api/clinical/billing/payments",
    denial: "/api/clinical/billing/denials",
  }[type];
}

function numberOrUndefined(value) {
  return value === "" || value === null || value === undefined ? undefined : Number(value);
}

function billingPayload(type, form) {
  if (type === "verify") {
    return compactPayload({
      patient_id: form.patient_id,
      patient_insurance_id: numberOrUndefined(form.patient_insurance_id),
      verification_status: form.verification_status,
      notes: form.notes,
    });
  }
  if (type === "charge") {
    return compactPayload({
      patient_id: form.patient_id,
      encounter_id: numberOrUndefined(form.encounter_id),
      order_id: numberOrUndefined(form.order_id),
      order_result_id: numberOrUndefined(form.order_result_id),
      care_plan_id: numberOrUndefined(form.care_plan_id),
      care_plan_task_id: numberOrUndefined(form.care_plan_task_id),
      service_date: form.service_date,
      code: form.code,
      code_type: form.code_type,
      description: form.description,
      quantity: Number(form.quantity || 0),
      unit_amount: Number(form.unit_amount || 0),
      status: form.status,
    });
  }
  if (type === "claim") {
    return compactPayload({
      patient_id: form.patient_id,
      patient_insurance_id: numberOrUndefined(form.patient_insurance_id),
      charge_ids: form.charge_ids.map((chargeId) => Number(chargeId)),
      status: form.status,
      diagnosis_code: form.diagnosis_code,
    });
  }
  if (type === "payment") {
    return compactPayload({
      claim_id: Number(form.claim_id),
      payment_amount: Number(form.payment_amount || 0),
      adjustment_amount: Number(form.adjustment_amount || 0),
      payment_method: form.payment_method,
      payer_type: form.payer_type,
      reference_number: form.reference_number,
      notes: form.notes,
    });
  }
  return compactPayload({
    claim_id: Number(form.claim_id),
    claim_line_id: numberOrUndefined(form.claim_line_id),
    denial_code: form.denial_code,
    denial_reason: form.denial_reason,
    status: form.status,
    assigned_to: form.assigned_to,
    due_date: form.due_date,
  });
}

function validateBillingWorkflow(type, form) {
  const issues = [];
  if (["verify", "charge", "claim"].includes(type) && !form.patient_id) issues.push("Patient is required.");
  if (type === "charge") {
    if (!form.service_date) issues.push("Service date is required.");
    if (!form.code) issues.push("Code is required.");
    if (!form.description) issues.push("Description is required.");
    if (Number(form.quantity || 0) <= 0) issues.push("Quantity must be greater than zero.");
    if (form.unit_amount === "" || Number(form.unit_amount) < 0) issues.push("Unit amount is required.");
  }
  if (type === "claim" && !form.charge_ids.length) issues.push("Select at least one charge.");
  if (type === "payment") {
    if (!form.claim_id) issues.push("Claim is required.");
    if (Number(form.payment_amount || 0) + Number(form.adjustment_amount || 0) <= 0) issues.push("Payment or adjustment amount is required.");
  }
  if (type === "denial") {
    if (!form.claim_id) issues.push("Claim is required.");
    if (!form.denial_reason) issues.push("Denial reason is required.");
  }
  return issues;
}

function patientInsuranceOptions(patients, patientId) {
  return patients.find((patient) => patient.patient_id === patientId)?.insurance_profiles || [];
}

function claimLineOptions(queue, claimId) {
  return queue?.claims?.find((claim) => String(claim.claim_id) === String(claimId))?.lines || [];
}

function BillingWorkflowModal({ type, token, user, account, patients, encounters, orders, carePlans, queue, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultBillingForm(type, account, patients, queue));
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const validationIssues = validateBillingWorkflow(type, form);
  const insuranceOptions = patientInsuranceOptions(patients, form.patient_id);
  const patientEncounters = encounters.filter((encounter) => encounter.patient_id === form.patient_id);
  const patientOrders = orders.filter((order) => order.patient_id === form.patient_id);
  const patientCarePlans = carePlans.filter((carePlan) => carePlan.patient_id === form.patient_id);
  const eligibleCharges = (queue?.charges || []).filter(
    (charge) => charge.patient_id === form.patient_id && !["voided", "cancelled", "claimed"].includes(charge.status),
  );
  const selectedClaimLines = claimLineOptions(queue, form.claim_id);

  async function previewWorkflow(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (validationIssues.length) return;
    try {
      const payload = await apiRequest(billingPreviewEndpoint(type), {
        token,
        method: "POST",
        body: billingPayload(type, form),
      });
      setPreview(payload);
      setMessage(payload.validation_status === "failed" ? "Preview has blocking issues." : "Preview ready for confirmation.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function commitWorkflow() {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiRequest(billingCommitEndpoint(type), {
        token,
        method: "POST",
        headers: { "X-Confirm-Generation": "true" },
        body: { ...billingPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setMessage(`Committed ${result.operation_id}.`);
      onSuccess(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleCharge(chargeId) {
    const value = String(chargeId);
    setForm((current) => ({
      ...current,
      charge_ids: current.charge_ids.includes(value)
        ? current.charge_ids.filter((item) => item !== value)
        : [...current.charge_ids, value],
    }));
  }

  return (
    <div className="modal-backdrop">
      <section className="workflow-modal billing-modal">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Billing workflow</p>
            <h3>{billingWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        <form className="stacked-form" onSubmit={previewWorkflow}>
          {["verify", "charge", "claim"].includes(type) && (
            <label>
              Patient
              <select value={form.patient_id} onChange={(event) => setForm({ ...form, patient_id: event.target.value, patient_insurance_id: "", charge_ids: [] })}>
                <option value="">Select patient</option>
                {patients.map((patient) => (
                  <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>
                ))}
              </select>
            </label>
          )}
          {["verify", "claim"].includes(type) && (
            <label>
              Insurance
              <select value={form.patient_insurance_id} onChange={(event) => setForm({ ...form, patient_insurance_id: event.target.value })}>
                <option value="">Manual or self-pay</option>
                {insuranceOptions.map((insurance) => (
                  <option key={insurance.insurance_id} value={insurance.insurance_id}>{clinicalDisplayText(insurance.payer_name, "payer_name", user)} - {insurance.member_id ? clinicalDisplayText(insurance.member_id, "member_id", user) : "member pending"}</option>
                ))}
              </select>
            </label>
          )}
          {type === "verify" && (
            <>
              <label>
                Verification status
                <select value={form.verification_status} onChange={(event) => setForm({ ...form, verification_status: event.target.value })}>
                  {["verified", "not_verified", "needs_review", "inactive"].map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </label>
              <label>
                Notes
                <textarea rows="3" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
              </label>
            </>
          )}
          {type === "charge" && (
            <>
              <div className="form-grid">
                <label>
                  Encounter
                  <select value={form.encounter_id} onChange={(event) => setForm({ ...form, encounter_id: event.target.value })}>
                    <option value="">None</option>
                    {patientEncounters.map((encounter) => <option key={encounter.encounter_id} value={encounter.encounter_id}>{encounter.encounter_number} - {encounter.status}</option>)}
                  </select>
                </label>
                <label>
                  Order
                  <select value={form.order_id} onChange={(event) => setForm({ ...form, order_id: event.target.value, order_result_id: "" })}>
                    <option value="">None</option>
                    {patientOrders.map((order) => <option key={order.order_id} value={order.order_id}>{order.order_number} - {order.status}</option>)}
                  </select>
                </label>
                <label>
                  Order result
                  <select value={form.order_result_id} onChange={(event) => setForm({ ...form, order_result_id: event.target.value })}>
                    <option value="">None</option>
                    {patientOrders.find((order) => String(order.order_id) === String(form.order_id))?.results?.map((result) => (
                      <option key={result.result_id} value={result.result_id}>{result.result_name} - {result.result_status}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Care plan
                  <select value={form.care_plan_id} onChange={(event) => setForm({ ...form, care_plan_id: event.target.value, care_plan_task_id: "" })}>
                    <option value="">None</option>
                    {patientCarePlans.map((carePlan) => <option key={carePlan.care_plan_id} value={carePlan.care_plan_id}>{carePlan.care_plan_number} - {carePlan.status}</option>)}
                  </select>
                </label>
                <label>
                  Care plan task
                  <select value={form.care_plan_task_id} onChange={(event) => setForm({ ...form, care_plan_task_id: event.target.value })}>
                    <option value="">None</option>
                    {patientCarePlans.find((carePlan) => String(carePlan.care_plan_id) === String(form.care_plan_id))?.tasks?.map((task) => (
                      <option key={task.task_id} value={task.task_id}>{clinicalDisplayText(task.title, "title", user)} - {task.status}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Service date
                  <input type="date" value={form.service_date} onChange={(event) => setForm({ ...form, service_date: event.target.value })} />
                </label>
              </div>
              <div className="form-grid">
                <label>
                  Code
                  <input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} />
                </label>
                <label>
                  Code type
                  <select value={form.code_type} onChange={(event) => setForm({ ...form, code_type: event.target.value })}>
                    {["internal", "cpt", "hcpcs"].map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Quantity
                  <input type="number" min="0.01" step="0.01" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
                </label>
                <label>
                  Unit amount
                  <input type="number" min="0" step="0.01" value={form.unit_amount} onChange={(event) => setForm({ ...form, unit_amount: event.target.value })} />
                </label>
              </div>
              <label>
                Description
                <textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
              </label>
            </>
          )}
          {type === "claim" && (
            <>
              <label>
                Claim status
                <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                  {["ready_for_review", "draft"].map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </label>
              <label>
                Diagnosis code
                <input value={form.diagnosis_code} onChange={(event) => setForm({ ...form, diagnosis_code: event.target.value })} />
              </label>
              <div className="charge-picker">
                {eligibleCharges.length ? eligibleCharges.map((charge) => (
                  <label key={charge.charge_id} className="checkbox-row">
                    <input type="checkbox" checked={form.charge_ids.includes(String(charge.charge_id))} onChange={() => toggleCharge(charge.charge_id)} />
                    {charge.charge_number} - {charge.code} - {formatMoney(charge.total_amount)}
                  </label>
                )) : <div className="empty-state">No eligible captured charges for this patient.</div>}
              </div>
            </>
          )}
          {type === "payment" && (
            <div className="form-grid">
              <label>
                Claim
                <select value={form.claim_id} onChange={(event) => setForm({ ...form, claim_id: event.target.value })}>
                  <option value="">Select claim</option>
                  {(queue?.claims || []).map((claim) => <option key={claim.claim_id} value={claim.claim_id}>{claim.claim_number} - {formatMoney(claim.balance)}</option>)}
                </select>
              </label>
              <label>
                Payment amount
                <input type="number" min="0" step="0.01" value={form.payment_amount} onChange={(event) => setForm({ ...form, payment_amount: event.target.value })} />
              </label>
              <label>
                Adjustment
                <input type="number" min="0" step="0.01" value={form.adjustment_amount} onChange={(event) => setForm({ ...form, adjustment_amount: event.target.value })} />
              </label>
              <label>
                Method
                <select value={form.payment_method} onChange={(event) => setForm({ ...form, payment_method: event.target.value })}>
                  {["eft", "check", "card", "cash"].map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label>
                Payer type
                <select value={form.payer_type} onChange={(event) => setForm({ ...form, payer_type: event.target.value })}>
                  {["insurance", "patient", "adjustment"].map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label>
                Reference
                <input value={form.reference_number} onChange={(event) => setForm({ ...form, reference_number: event.target.value })} />
              </label>
            </div>
          )}
          {type === "denial" && (
            <>
              <div className="form-grid">
                <label>
                  Claim
                  <select value={form.claim_id} onChange={(event) => setForm({ ...form, claim_id: event.target.value, claim_line_id: "" })}>
                    <option value="">Select claim</option>
                    {(queue?.claims || []).map((claim) => <option key={claim.claim_id} value={claim.claim_id}>{claim.claim_number} - {claim.status}</option>)}
                  </select>
                </label>
                <label>
                  Claim line
                  <select value={form.claim_line_id} onChange={(event) => setForm({ ...form, claim_line_id: event.target.value })}>
                    <option value="">Whole claim</option>
                    {selectedClaimLines.map((line) => <option key={line.line_id} value={line.line_id}>Line {line.line_number} - {line.code}</option>)}
                  </select>
                </label>
                <label>
                  Denial code
                  <input value={form.denial_code} onChange={(event) => setForm({ ...form, denial_code: event.target.value })} />
                </label>
                <label>
                  Assigned to
                  <input value={form.assigned_to} onChange={(event) => setForm({ ...form, assigned_to: event.target.value })} />
                </label>
                <label>
                  Due date
                  <input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} />
                </label>
              </div>
              <label>
                Denial reason
                <textarea rows="3" value={form.denial_reason} onChange={(event) => setForm({ ...form, denial_reason: event.target.value })} />
              </label>
            </>
          )}
          {validationIssues.length > 0 && <div className="error-state">{validationIssues.join(" ")}</div>}
          {preview && (
            <div className="preview-panel">
              <StatusPill status={preview.validation_status} />
              <p>{preview.summary}</p>
              {preview.blocking_issues?.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}>{issue.message}</div>)}
              {preview.warnings?.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}>{warning.message}</div>)}
            </div>
          )}
          {message && <div className="notice-state">{message}</div>}
          {error && <div className="error-state">{error}</div>}
          <div className="modal-actions">
            <button type="submit" disabled={Boolean(validationIssues.length)}>
              <FileCheck2 size={16} />
              Preview
            </button>
            <button type="button" className="secondary-button" disabled={!preview || preview.validation_status === "failed" || submitting} onClick={commitWorkflow}>
              <CheckCircle2 size={16} />
              Confirm
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function ClinicalBillingPage({ token, navigate, user }) {
  const [queue, setQueue] = useState({ accounts: [], charges: [], claims: [], payments: [], denials: [], insurance_verifications: [] });
  const [patients, setPatients] = useState([]);
  const [encounters, setEncounters] = useState([]);
  const [orders, setOrders] = useState([]);
  const [carePlans, setCarePlans] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [filters, setFilters] = useState({ q: "", status: "", patient_id: "", payer: "", date: "", claim_status: "", denial_status: "" });
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const selectedAccount = queue.accounts.find((account) => account.account_id === selectedAccountId) || queue.accounts[0];
  const openDenials = queue.denials.filter((denial) => denial.status === "open");
  const totalBalance = queue.accounts.reduce((total, account) => total + Number(account.balance || 0), 0);
  const totalCharges = queue.charges.reduce((total, charge) => total + Number(charge.total_amount || 0), 0);
  const claimBalance = queue.claims.reduce((total, claim) => total + Number(claim.balance || 0), 0);

  async function loadBilling() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    try {
      const [workQueue, patientPayload, encounterPayload, orderPayload, carePlanPayload] = await Promise.all([
        apiRequest(`/api/clinical/billing/work-queue?${params.toString()}`, { token }),
        apiRequest("/api/clinical/patients?limit=200", { token }),
        apiRequest("/api/clinical/encounters?limit=200", { token }),
        apiRequest("/api/clinical/orders?limit=200", { token }),
        apiRequest("/api/clinical/care-plans?limit=200", { token }),
      ]);
      setQueue(workQueue);
      setPatients(patientPayload.patients || []);
      setEncounters(encounterPayload.encounters || []);
      setOrders(orderPayload.orders || []);
      setCarePlans(carePlanPayload.care_plans || []);
      setSelectedAccountId((current) => current || workQueue.accounts?.[0]?.account_id || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBilling();
  }, [token]);

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function workflowSuccess() {
    loadBilling();
  }

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Revenue cycle foundation</p>
          <h2>Billing / Insurance</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalType("verify")}><ShieldCheck size={16} />Verify Insurance</button>
          <button type="button" onClick={() => setModalType("charge")}><ReceiptText size={16} />Create Charge</button>
          <button type="button" onClick={() => setModalType("claim")}><FileCheck2 size={16} />Create Claim</button>
          <button type="button" onClick={() => setModalType("payment")}><CreditCard size={16} />Post Payment</button>
          <button type="button" onClick={() => setModalType("denial")}><AlertTriangle size={16} />Capture Denial</button>
        </div>
      </section>
      <section>
        <div className="billing-filter">
          <label>Search<input value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} placeholder="Patient, account, claim, charge" /></label>
          <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All</option>{billingStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Patient<select value={filters.patient_id} onChange={(event) => updateFilter("patient_id", event.target.value)}><option value="">All</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{clinicalDisplayText(patient.patient_id, "patient_id", user)}</option>)}</select></label>
          <label>Payer<input value={filters.payer} onChange={(event) => updateFilter("payer", event.target.value)} /></label>
          <label>Date<input type="date" value={filters.date} onChange={(event) => updateFilter("date", event.target.value)} /></label>
          <label>Claim<select value={filters.claim_status} onChange={(event) => updateFilter("claim_status", event.target.value)}><option value="">All</option>{billingClaimStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Denial<select value={filters.denial_status} onChange={(event) => updateFilter("denial_status", event.target.value)}><option value="">Open</option>{billingDenialStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <button type="button" onClick={loadBilling}><RefreshCw size={16} />Apply</button>
        </div>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading ? <div className="notice-state">Loading billing work queue...</div> : (
        <>
          <div className="content-grid">
            <MetricCard label="Account Balance" value={formatMoney(totalBalance)} tone={totalBalance > 0 ? "warning" : "neutral"} />
            <MetricCard label="Captured Charges" value={formatMoney(totalCharges)} />
            <MetricCard label="Claim Balance" value={formatMoney(claimBalance)} tone={claimBalance > 0 ? "warning" : "neutral"} />
            <MetricCard label="Open Denials" value={formatNumber(openDenials.length)} tone={openDenials.length ? "warning" : "neutral"} />
          </div>
          <div className="split billing-layout">
            <section>
              <h3>Billing Work Queue</h3>
              <div className="workflow-list">
                {queue.accounts.length ? queue.accounts.map((account) => (
                  <button type="button" className="workflow-row" key={account.account_id} onClick={() => setSelectedAccountId(account.account_id)}>
                    <span>{account.account_number} - <TableCellValue value={account.patient_name} field="patient_name" user={user} /></span>
                    <span>{formatMoney(account.balance)}</span>
                    <StatusPill status={account.status} />
                  </button>
                )) : <div className="empty-state">No billing accounts match the current filters.</div>}
              </div>
            </section>
            <section>
              <h3>Account Summary</h3>
              {selectedAccount ? (
                <div className="info-list compact">
                  <p><strong>{selectedAccount.account_number}</strong></p>
                  <p><TableCellValue value={selectedAccount.patient_id} field="patient_id" user={user} /> - <TableCellValue value={selectedAccount.patient_name} field="patient_name" user={user} /></p>
                  <p><TableCellValue value={selectedAccount.payer_name || "No payer selected"} field="payer_name" user={user} /></p>
                  <div className="summary-grid">
                    <span>Charges <strong>{formatMoney(selectedAccount.total_charges)}</strong></span>
                    <span>Payments <strong>{formatMoney(selectedAccount.total_payments)}</strong></span>
                    <span>Adjustments <strong>{formatMoney(selectedAccount.total_adjustments)}</strong></span>
                    <span>Balance <strong>{formatMoney(selectedAccount.balance)}</strong></span>
                  </div>
                </div>
              ) : <div className="empty-state">Select or create a billing account.</div>}
            </section>
          </div>
          <div className="billing-detail-grid">
            <section>
              <h3>Insurance Verification</h3>
              <Table rows={queue.insurance_verifications.slice(0, 6)} columns={["patient_id", "payer_name", "verification_status", "verified_at"]} user={user} />
            </section>
            <section>
              <h3>Charges</h3>
              <Table rows={queue.charges.slice(0, 8)} columns={["charge_number", "patient_id", "code", "total_amount", "status"]} user={user} />
            </section>
            <section>
              <h3>Claims</h3>
              <Table rows={queue.claims.slice(0, 8)} columns={["claim_number", "patient_id", "payer_name", "balance", "status"]} user={user} />
            </section>
            <section>
              <h3>Payments</h3>
              <Table rows={queue.payments.slice(0, 8)} columns={["claim_number", "payment_amount", "adjustment_amount", "payment_method", "posted_at"]} />
            </section>
            <section>
              <h3>Denial / Rework</h3>
              <Table rows={queue.denials.slice(0, 8)} columns={["claim_number", "denial_code", "denial_reason", "status", "due_date"]} user={user} />
            </section>
            <section>
              <h3>Handoffs</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/quality")}><span>Quality / Compliance</span><StatusPill status="Planned" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/reports")}><span>Reporting</span><StatusPill status="Active" /></button>
              </div>
            </section>
          </div>
        </>
      )}
      {modalType && (
        <BillingWorkflowModal
          type={modalType}
          token={token}
          user={user}
          account={selectedAccount}
          patients={patients}
          encounters={encounters}
          orders={orders}
          carePlans={carePlans}
          queue={queue}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const qualityStatusOptions = ["open", "under_review", "investigation", "capa_required", "pending_approval", "closed", "cancelled"];
const qualitySeverityOptions = ["low", "medium", "high", "severe", "critical"];
const qualityCategoryOptions = ["process_deviation", "patient_safety", "documentation", "billing", "screening", "encounter", "order_result", "care_plan", "compliance"];
const qualitySourceModuleOptions = ["clinical_quality", "clinical_screening", "clinical_encounters", "clinical_orders", "clinical_care_plans", "clinical_billing"];
const qualityExportModuleOptions = ["quality", "screening", "encounters", "orders", "care_plans", "billing"];

function QualitySeverityChip({ severity }) {
  const normalized = severity || "medium";
  const lower = normalized.toLowerCase();
  const tone = lower === "critical" || lower === "severe" ? "danger" : lower === "high" ? "warning" : "neutral";
  return <span className={cx("priority-chip", tone)}>{normalized}</span>;
}

function qualityWorkflowTitle(type) {
  return {
    event: "Create Quality Event",
    adverse: "Create Adverse Event",
    investigation: "Add Investigation",
    capa: "Link / Plan CAPA",
    close: "Close Quality Event",
    export: "Generate Compliance Export",
  }[type];
}

function defaultQualityForm(type, selectedEvent, patients) {
  const patient = selectedEvent?.patient_id || patients?.[0]?.patient_id || "";
  if (type === "event") {
    return {
      patient_id: patient,
      category: "process_deviation",
      severity: "medium",
      status: "open",
      owner: "",
      due_date: defaultDateInput(14),
      source_module: "clinical_quality",
      description: "",
      appointment_id: "",
      screening_session_id: "",
      encounter_id: "",
      order_id: "",
      order_result_id: "",
      care_plan_id: "",
      charge_id: "",
      claim_id: "",
      payment_id: "",
      denial_id: "",
      deviation_id: "",
      capa_id: "",
    };
  }
  if (type === "adverse") {
    return {
      patient_id: patient,
      quality_event_id: selectedEvent?.event_id || "",
      event_type: "patient_safety",
      severity: selectedEvent?.severity || "medium",
      event_at: new Date().toISOString().slice(0, 16),
      description: "",
      immediate_action_taken: "",
      reporter: "",
      follow_up_required: false,
      status: "open",
      screening_session_id: "",
      encounter_id: selectedEvent?.encounter_id || "",
      order_id: selectedEvent?.order_id || "",
      order_result_id: selectedEvent?.order_result_id || "",
      care_plan_id: selectedEvent?.care_plan_id || "",
    };
  }
  if (type === "investigation") {
    return {
      note: "",
      evidence_summary: "",
      owner: selectedEvent?.owner || "",
      finding: "",
      root_cause_category: "",
      corrective_action_recommendation: "",
      follow_up_due_date: defaultDateInput(7),
      status_after: "investigation",
    };
  }
  if (type === "capa") {
    return {
      existing_capa_id: selectedEvent?.capa_id || "",
      create_planned_capa: !selectedEvent?.capa_id,
      root_cause: "",
      corrective_action_owner: selectedEvent?.owner || "",
      due_date: defaultDateInput(30),
    };
  }
  if (type === "close") {
    return {
      resolution_summary: "",
      closure_reason: "",
    };
  }
  return {
    date_from: "",
    date_to: defaultDateInput(0),
    modules: ["quality"],
    actor: "",
    workflow: "",
    entity_type: "",
    entity_id: "",
    export_profile: "compliance_evidence",
    include_quality_history: true,
  };
}

function qualityPreviewEndpoint(type, selectedEvent) {
  return {
    event: "/api/clinical/quality/events/preview",
    adverse: "/api/clinical/quality/adverse-events/preview",
    investigation: `/api/clinical/quality/events/${selectedEvent?.event_id}/investigation/preview`,
    capa: `/api/clinical/quality/events/${selectedEvent?.event_id}/capa/preview`,
    close: `/api/clinical/quality/events/${selectedEvent?.event_id}/close/preview`,
    export: "/api/clinical/quality/compliance-exports/preview",
  }[type];
}

function qualityCommitEndpoint(type, selectedEvent) {
  return {
    event: "/api/clinical/quality/events",
    adverse: "/api/clinical/quality/adverse-events",
    investigation: `/api/clinical/quality/events/${selectedEvent?.event_id}/investigation`,
    capa: `/api/clinical/quality/events/${selectedEvent?.event_id}/capa`,
    close: `/api/clinical/quality/events/${selectedEvent?.event_id}/close`,
    export: "/api/clinical/quality/compliance-exports",
  }[type];
}

function qualityPayload(type, form) {
  if (type === "event") {
    return compactPayload({
      patient_id: form.patient_id,
      category: form.category,
      severity: form.severity,
      status: form.status,
      owner: form.owner,
      due_date: form.due_date,
      source_module: form.source_module,
      description: form.description,
      appointment_id: numberOrUndefined(form.appointment_id),
      screening_session_id: numberOrUndefined(form.screening_session_id),
      encounter_id: numberOrUndefined(form.encounter_id),
      order_id: numberOrUndefined(form.order_id),
      order_result_id: numberOrUndefined(form.order_result_id),
      care_plan_id: numberOrUndefined(form.care_plan_id),
      charge_id: numberOrUndefined(form.charge_id),
      claim_id: numberOrUndefined(form.claim_id),
      payment_id: numberOrUndefined(form.payment_id),
      denial_id: numberOrUndefined(form.denial_id),
      deviation_id: numberOrUndefined(form.deviation_id),
      capa_id: numberOrUndefined(form.capa_id),
    });
  }
  if (type === "adverse") {
    return compactPayload({
      patient_id: form.patient_id,
      quality_event_id: numberOrUndefined(form.quality_event_id),
      event_type: form.event_type,
      severity: form.severity,
      event_at: form.event_at,
      description: form.description,
      immediate_action_taken: form.immediate_action_taken,
      reporter: form.reporter,
      follow_up_required: Boolean(form.follow_up_required),
      status: form.status,
      screening_session_id: numberOrUndefined(form.screening_session_id),
      encounter_id: numberOrUndefined(form.encounter_id),
      order_id: numberOrUndefined(form.order_id),
      order_result_id: numberOrUndefined(form.order_result_id),
      care_plan_id: numberOrUndefined(form.care_plan_id),
    });
  }
  if (type === "investigation") {
    return compactPayload({
      note: form.note,
      evidence_summary: form.evidence_summary,
      owner: form.owner,
      finding: form.finding,
      root_cause_category: form.root_cause_category,
      corrective_action_recommendation: form.corrective_action_recommendation,
      follow_up_due_date: form.follow_up_due_date,
      status_after: form.status_after,
    });
  }
  if (type === "capa") {
    return compactPayload({
      existing_capa_id: numberOrUndefined(form.existing_capa_id),
      create_planned_capa: Boolean(form.create_planned_capa),
      root_cause: form.root_cause,
      corrective_action_owner: form.corrective_action_owner,
      due_date: form.due_date,
    });
  }
  if (type === "close") {
    return compactPayload({
      resolution_summary: form.resolution_summary,
      closure_reason: form.closure_reason,
    });
  }
  return compactPayload({
    date_from: form.date_from,
    date_to: form.date_to,
    modules: form.modules,
    actor: form.actor,
    workflow: form.workflow,
    entity_type: form.entity_type,
    entity_id: form.entity_id,
    export_profile: form.export_profile,
    include_quality_history: Boolean(form.include_quality_history),
  });
}

function validateQualityWorkflow(type, form, selectedEvent) {
  const issues = [];
  if (["investigation", "capa", "close"].includes(type) && !selectedEvent) issues.push("Select a quality event.");
  if (type === "event") {
    for (const field of ["category", "severity", "status", "source_module", "description"]) {
      if (!form[field]) issues.push(`${field.replaceAll("_", " ")} is required.`);
    }
  }
  if (type === "adverse") {
    for (const field of ["patient_id", "event_type", "severity", "event_at", "description", "reporter"]) {
      if (!form[field]) issues.push(`${field.replaceAll("_", " ")} is required.`);
    }
  }
  if (type === "investigation" && !form.note) issues.push("Investigation note is required.");
  if (type === "capa" && !form.existing_capa_id && !form.create_planned_capa) issues.push("Select an existing CAPA or create a planned CAPA link.");
  if (type === "close") {
    if (!form.resolution_summary) issues.push("Resolution summary is required.");
    if (!form.closure_reason) issues.push("Closure reason is required.");
  }
  return issues;
}

function qualityPatientContextRows(event) {
  if (!event) return [];
  return [
    { context: "Patient", value: event.patient_id ? `${event.patient_id} - ${event.patient_name || ""}` : "Not linked" },
    { context: "Appointment", value: event.appointment_number || event.appointment_id || "" },
    { context: "Screening", value: event.screening_session_number || event.screening_session_id || "" },
    { context: "Encounter", value: event.encounter_number || event.encounter_id || "" },
    { context: "Order", value: event.order_number || event.order_id || "" },
    { context: "Result", value: event.order_result_summary || event.order_result_id || "" },
    { context: "Care Plan", value: event.care_plan_number || event.care_plan_id || "" },
    { context: "Charge", value: event.charge_number || event.charge_id || "" },
    { context: "Claim", value: event.claim_number || event.claim_id || "" },
    { context: "Payment", value: event.payment_reference || event.payment_id || "" },
    { context: "Denial", value: event.denial_code || event.denial_id || "" },
    { context: "Deviation", value: event.deviation_code || event.deviation_id || "" },
    { context: "CAPA", value: event.capa_code || event.capa_id || "" },
  ].filter((row) => row.value);
}

function QualityWorkflowModal({ type, token, user, selectedEvent, patients, appointments, sessions, encounters, orders, carePlans, billingQueue, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultQualityForm(type, selectedEvent, patients));
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const validationIssues = validateQualityWorkflow(type, form, selectedEvent);
  const patientAppointments = appointments.filter((item) => item.patient_id === form.patient_id);
  const patientSessions = sessions.filter((item) => item.patient_id === form.patient_id);
  const patientEncounters = encounters.filter((item) => item.patient_id === form.patient_id);
  const patientOrders = orders.filter((item) => item.patient_id === form.patient_id);
  const patientCarePlans = carePlans.filter((item) => item.patient_id === form.patient_id);
  const patientCharges = (billingQueue?.charges || []).filter((item) => item.patient_id === form.patient_id);
  const patientClaims = (billingQueue?.claims || []).filter((item) => item.patient_id === form.patient_id);
  const patientPayments = (billingQueue?.payments || []).filter((item) => item.patient_id === form.patient_id);
  const patientDenials = (billingQueue?.denials || []).filter((item) => {
    const claim = patientClaims.find((claimItem) => claimItem.claim_id === item.claim_id);
    return Boolean(claim);
  });
  const selectedOrderResults = patientOrders.find((order) => String(order.order_id) === String(form.order_id))?.results || [];

  function toggleModule(module) {
    setForm((current) => ({
      ...current,
      modules: current.modules.includes(module)
        ? current.modules.filter((item) => item !== module)
        : [...current.modules, module],
    }));
  }

  async function previewWorkflow(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (validationIssues.length) return;
    try {
      const payload = await apiRequest(qualityPreviewEndpoint(type, selectedEvent), {
        token,
        method: "POST",
        body: qualityPayload(type, form),
      });
      setPreview(payload);
      setMessage(payload.validation_status === "failed" ? "Preview has blocking issues." : "Preview ready for confirmation.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function commitWorkflow() {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiRequest(qualityCommitEndpoint(type, selectedEvent), {
        token,
        method: "POST",
        headers: { "X-Confirm-Generation": "true" },
        body: { ...qualityPayload(type, form), preview_hash: preview?.preview_hash },
      });
      setMessage(`Committed ${result.operation_id}.`);
      onSuccess(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <section className="workflow-modal quality-modal">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Quality workflow</p>
            <h3>{qualityWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        <form className="stacked-form" onSubmit={previewWorkflow}>
          {["event", "adverse"].includes(type) && (
            <label>
              Patient
              <select value={form.patient_id} onChange={(event) => setForm({ ...form, patient_id: event.target.value, appointment_id: "", screening_session_id: "", encounter_id: "", order_id: "", order_result_id: "", care_plan_id: "", charge_id: "", claim_id: "", payment_id: "", denial_id: "" })}>
                <option value="">Select patient</option>
                {patients.map((patient) => (
                  <option key={patient.patient_id} value={patient.patient_id}>{patientOptionLabel(patient, user)}</option>
                ))}
              </select>
            </label>
          )}
          {type === "event" && (
            <>
              <div className="form-grid">
                <label>Category<select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{qualityCategoryOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Severity<select value={form.severity} onChange={(event) => setForm({ ...form, severity: event.target.value })}>{qualitySeverityOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>{qualityStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Source module<select value={form.source_module} onChange={(event) => setForm({ ...form, source_module: event.target.value })}>{qualitySourceModuleOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Owner<input value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })} /></label>
                <label>Due date<input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} /></label>
              </div>
              <div className="form-grid">
                <label>Appointment<select value={form.appointment_id} onChange={(event) => setForm({ ...form, appointment_id: event.target.value })}><option value="">None</option>{patientAppointments.map((item) => <option key={item.appointment_id} value={item.appointment_id}>{item.appointment_number} - {item.status}</option>)}</select></label>
                <label>Screening<select value={form.screening_session_id} onChange={(event) => setForm({ ...form, screening_session_id: event.target.value })}><option value="">None</option>{patientSessions.map((item) => <option key={item.session_id} value={item.session_id}>{item.session_number} - {item.status}</option>)}</select></label>
                <label>Encounter<select value={form.encounter_id} onChange={(event) => setForm({ ...form, encounter_id: event.target.value })}><option value="">None</option>{patientEncounters.map((item) => <option key={item.encounter_id} value={item.encounter_id}>{item.encounter_number} - {item.status}</option>)}</select></label>
                <label>Order<select value={form.order_id} onChange={(event) => setForm({ ...form, order_id: event.target.value, order_result_id: "" })}><option value="">None</option>{patientOrders.map((item) => <option key={item.order_id} value={item.order_id}>{item.order_number} - {item.status}</option>)}</select></label>
                <label>Order result<select value={form.order_result_id} onChange={(event) => setForm({ ...form, order_result_id: event.target.value })}><option value="">None</option>{selectedOrderResults.map((item) => <option key={item.result_id} value={item.result_id}>{item.result_name} - {item.result_status}</option>)}</select></label>
                <label>Care plan<select value={form.care_plan_id} onChange={(event) => setForm({ ...form, care_plan_id: event.target.value })}><option value="">None</option>{patientCarePlans.map((item) => <option key={item.care_plan_id} value={item.care_plan_id}>{item.care_plan_number} - {item.status}</option>)}</select></label>
                <label>Charge<select value={form.charge_id} onChange={(event) => setForm({ ...form, charge_id: event.target.value })}><option value="">None</option>{patientCharges.map((item) => <option key={item.charge_id} value={item.charge_id}>{item.charge_number} - {item.status}</option>)}</select></label>
                <label>Claim<select value={form.claim_id} onChange={(event) => setForm({ ...form, claim_id: event.target.value })}><option value="">None</option>{patientClaims.map((item) => <option key={item.claim_id} value={item.claim_id}>{item.claim_number} - {item.status}</option>)}</select></label>
                <label>Payment<select value={form.payment_id} onChange={(event) => setForm({ ...form, payment_id: event.target.value })}><option value="">None</option>{patientPayments.map((item) => <option key={item.payment_id} value={item.payment_id}>{item.claim_number} - {formatMoney(item.payment_amount)}</option>)}</select></label>
                <label>Denial<select value={form.denial_id} onChange={(event) => setForm({ ...form, denial_id: event.target.value })}><option value="">None</option>{patientDenials.map((item) => <option key={item.denial_id} value={item.denial_id}>{item.denial_code || item.denial_id} - {item.status}</option>)}</select></label>
                <label>Deviation ID<input value={form.deviation_id} onChange={(event) => setForm({ ...form, deviation_id: event.target.value })} /></label>
                <label>CAPA ID<input value={form.capa_id} onChange={(event) => setForm({ ...form, capa_id: event.target.value })} /></label>
              </div>
              <label>Description<textarea rows="4" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            </>
          )}
          {type === "adverse" && (
            <>
              <div className="form-grid">
                <label>Quality event<input value={form.quality_event_id} onChange={(event) => setForm({ ...form, quality_event_id: event.target.value })} /></label>
                <label>Event type<input value={form.event_type} onChange={(event) => setForm({ ...form, event_type: event.target.value })} /></label>
                <label>Severity<select value={form.severity} onChange={(event) => setForm({ ...form, severity: event.target.value })}>{qualitySeverityOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Event time<input type="datetime-local" value={form.event_at} onChange={(event) => setForm({ ...form, event_at: event.target.value })} /></label>
                <label>Reporter<input value={form.reporter} onChange={(event) => setForm({ ...form, reporter: event.target.value })} /></label>
                <label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>{qualityStatusOptions.filter((item) => item !== "closed").map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              </div>
              <label className="checkbox-row"><input type="checkbox" checked={form.follow_up_required} onChange={(event) => setForm({ ...form, follow_up_required: event.target.checked })} />Follow-up required</label>
              <div className="form-grid">
                <label>Screening<select value={form.screening_session_id} onChange={(event) => setForm({ ...form, screening_session_id: event.target.value })}><option value="">None</option>{patientSessions.map((item) => <option key={item.session_id} value={item.session_id}>{item.session_number}</option>)}</select></label>
                <label>Encounter<select value={form.encounter_id} onChange={(event) => setForm({ ...form, encounter_id: event.target.value })}><option value="">None</option>{patientEncounters.map((item) => <option key={item.encounter_id} value={item.encounter_id}>{item.encounter_number}</option>)}</select></label>
                <label>Order<select value={form.order_id} onChange={(event) => setForm({ ...form, order_id: event.target.value, order_result_id: "" })}><option value="">None</option>{patientOrders.map((item) => <option key={item.order_id} value={item.order_id}>{item.order_number}</option>)}</select></label>
                <label>Order result<select value={form.order_result_id} onChange={(event) => setForm({ ...form, order_result_id: event.target.value })}><option value="">None</option>{selectedOrderResults.map((item) => <option key={item.result_id} value={item.result_id}>{item.result_name}</option>)}</select></label>
                <label>Care plan<select value={form.care_plan_id} onChange={(event) => setForm({ ...form, care_plan_id: event.target.value })}><option value="">None</option>{patientCarePlans.map((item) => <option key={item.care_plan_id} value={item.care_plan_id}>{item.care_plan_number}</option>)}</select></label>
              </div>
              <label>Description<textarea rows="4" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
              <label>Immediate action taken<textarea rows="3" value={form.immediate_action_taken} onChange={(event) => setForm({ ...form, immediate_action_taken: event.target.value })} /></label>
            </>
          )}
          {type === "investigation" && (
            <>
              <label>Investigation note<textarea rows="4" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} /></label>
              <div className="form-grid">
                <label>Owner<input value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })} /></label>
                <label>Follow-up due<input type="date" value={form.follow_up_due_date} onChange={(event) => setForm({ ...form, follow_up_due_date: event.target.value })} /></label>
                <label>Status after<select value={form.status_after} onChange={(event) => setForm({ ...form, status_after: event.target.value })}>{["under_review", "investigation", "capa_required", "pending_approval"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label>Root cause category<input value={form.root_cause_category} onChange={(event) => setForm({ ...form, root_cause_category: event.target.value })} /></label>
              </div>
              <label>Evidence summary<textarea rows="3" value={form.evidence_summary} onChange={(event) => setForm({ ...form, evidence_summary: event.target.value })} /></label>
              <label>Finding<textarea rows="3" value={form.finding} onChange={(event) => setForm({ ...form, finding: event.target.value })} /></label>
              <label>Corrective action recommendation<textarea rows="3" value={form.corrective_action_recommendation} onChange={(event) => setForm({ ...form, corrective_action_recommendation: event.target.value })} /></label>
            </>
          )}
          {type === "capa" && (
            <>
              <div className="form-grid">
                <label>Existing CAPA ID<input value={form.existing_capa_id} onChange={(event) => setForm({ ...form, existing_capa_id: event.target.value })} /></label>
                <label>Due date<input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} /></label>
                <label>Corrective action owner<input value={form.corrective_action_owner} onChange={(event) => setForm({ ...form, corrective_action_owner: event.target.value })} /></label>
              </div>
              <label className="checkbox-row"><input type="checkbox" checked={form.create_planned_capa} onChange={(event) => setForm({ ...form, create_planned_capa: event.target.checked })} />Create planned CAPA link</label>
              <label>Root cause<textarea rows="3" value={form.root_cause} onChange={(event) => setForm({ ...form, root_cause: event.target.value })} /></label>
            </>
          )}
          {type === "close" && (
            <>
              <label>Resolution summary<textarea rows="4" value={form.resolution_summary} onChange={(event) => setForm({ ...form, resolution_summary: event.target.value })} /></label>
              <label>Closure reason<textarea rows="3" value={form.closure_reason} onChange={(event) => setForm({ ...form, closure_reason: event.target.value })} /></label>
            </>
          )}
          {type === "export" && (
            <>
              <div className="form-grid">
                <label>Date from<input type="date" value={form.date_from} onChange={(event) => setForm({ ...form, date_from: event.target.value })} /></label>
                <label>Date to<input type="date" value={form.date_to} onChange={(event) => setForm({ ...form, date_to: event.target.value })} /></label>
                <label>Workflow<input value={form.workflow} onChange={(event) => setForm({ ...form, workflow: event.target.value })} placeholder="quality.event_create" /></label>
                <label>Actor<input value={form.actor} onChange={(event) => setForm({ ...form, actor: event.target.value })} /></label>
                <label>Entity type<input value={form.entity_type} onChange={(event) => setForm({ ...form, entity_type: event.target.value })} /></label>
                <label>Entity ID<input value={form.entity_id} onChange={(event) => setForm({ ...form, entity_id: event.target.value })} /></label>
                <label>Export profile<select value={form.export_profile} onChange={(event) => setForm({ ...form, export_profile: event.target.value })}>{EXPORT_PROFILE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
              </div>
              <div className="preference-list">
                {qualityExportModuleOptions.map((module) => (
                  <label className="checkbox-row" key={module}>
                    <input type="checkbox" checked={form.modules.includes(module)} onChange={() => toggleModule(module)} />
                    {module.replaceAll("_", " ")}
                  </label>
                ))}
                <label className="checkbox-row"><input type="checkbox" checked={form.include_quality_history} onChange={(event) => setForm({ ...form, include_quality_history: event.target.checked })} />Include quality status history</label>
              </div>
              <ExportProfileIndicator profile={form.export_profile} />
              {exportProfileInfo(form.export_profile).warning && (
                <div className="notice-state">{exportProfileInfo(form.export_profile).warning}</div>
              )}
            </>
          )}
          {validationIssues.length > 0 && <div className="error-state">{validationIssues.join(" ")}</div>}
          {preview && (
            <div className="notice-state">
              <strong>{preview.validation_status}</strong> - {preview.summary}
              <Table rows={[
                { field: "Preview hash", value: preview.preview_hash },
                { field: "Export profile", value: preview.changes?.export_profile || form.export_profile },
                { field: "Workflow operations", value: preview.changes?.evidence_summary?.workflow_operation_count ?? "" },
              ]} columns={["field", "value"]} />
              {preview.blocking_issues?.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}>{issue.message}</div>)}
              {preview.warnings?.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}>{warning.message}</div>)}
            </div>
          )}
          {message && <div className="message">{message}</div>}
          {error && <div className="error-state">{error}</div>}
          <button type="submit"><FileCheck2 size={16} />Preview</button>
          <button type="button" onClick={commitWorkflow} disabled={!preview || preview.validation_status === "failed" || submitting}>
            <ShieldCheck size={16} />
            Commit
          </button>
          <div className="notice-state">Commit will send X-Confirm-Generation: true and append a quality workflow audit entry.</div>
        </form>
      </section>
    </div>
  );
}

function ClinicalQualityPage({ token, navigate, user }) {
  const [filters, setFilters] = useState({ q: "", status: "", severity: "", category: "", owner: "", source_module: "", patient_id: "", date_from: "", date_to: "" });
  const [dashboard, setDashboard] = useState(null);
  const [events, setEvents] = useState([]);
  const [adverseEvents, setAdverseEvents] = useState([]);
  const [auditEvidence, setAuditEvidence] = useState({ operations: [], quality_status_history: [], compliance_exports: [] });
  const [exports, setExports] = useState([]);
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [encounters, setEncounters] = useState([]);
  const [orders, setOrders] = useState([]);
  const [carePlans, setCarePlans] = useState([]);
  const [billingQueue, setBillingQueue] = useState({ charges: [], claims: [], payments: [], denials: [] });
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedEvent = events.find((event) => event.event_id === selectedEventId) || events[0] || null;

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function openWorkflow(type) {
    setError("");
    if (["investigation", "capa", "close"].includes(type) && !selectedEvent) {
      setError("Select a quality event before using this workflow.");
      return;
    }
    setModalType(type);
  }

  async function loadQuality() {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    try {
      const [
        dashboardPayload,
        eventPayload,
        adversePayload,
        evidencePayload,
        exportPayload,
        patientPayload,
        appointmentPayload,
        sessionPayload,
        encounterPayload,
        orderPayload,
        carePlanPayload,
        billingPayload,
      ] = await Promise.all([
        apiRequest("/api/clinical/quality/dashboard", { token }),
        apiRequest(`/api/clinical/quality/events${params.toString() ? `?${params}` : ""}`, { token }),
        apiRequest("/api/clinical/quality/adverse-events", { token }),
        apiRequest("/api/clinical/quality/audit-evidence?module=quality", { token }),
        apiRequest("/api/clinical/quality/compliance-exports", { token }),
        apiRequest("/api/clinical/patients?limit=500", { token }),
        apiRequest("/api/clinical/scheduling/appointments?limit=500", { token }).catch(() => ({ appointments: [] })),
        apiRequest("/api/clinical/screening/sessions?limit=500", { token }).catch(() => ({ sessions: [] })),
        apiRequest("/api/clinical/encounters?limit=500", { token }).catch(() => ({ encounters: [] })),
        apiRequest("/api/clinical/orders?limit=500", { token }).catch(() => ({ orders: [] })),
        apiRequest("/api/clinical/care-plans?limit=500", { token }).catch(() => ({ care_plans: [] })),
        apiRequest("/api/clinical/billing/work-queue", { token }).catch(() => ({ charges: [], claims: [], payments: [], denials: [] })),
      ]);
      const nextEvents = eventPayload.events || [];
      setDashboard(dashboardPayload);
      setEvents(nextEvents);
      setAdverseEvents(adversePayload.adverse_events || []);
      setAuditEvidence(evidencePayload);
      setExports(exportPayload.exports || []);
      setPatients(patientPayload.patients || []);
      setAppointments(appointmentPayload.appointments || []);
      setSessions(sessionPayload.sessions || []);
      setEncounters(encounterPayload.encounters || []);
      setOrders(orderPayload.orders || []);
      setCarePlans(carePlanPayload.care_plans || []);
      setBillingQueue(billingPayload);
      setSelectedEventId((current) => (nextEvents.some((event) => event.event_id === current) ? current : nextEvents[0]?.event_id || null));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQuality();
  }, [token]);

  function workflowSuccess() {
    loadQuality();
  }

  const operations = (auditEvidence.operations || []).slice(-8).reverse().map((operation) => ({
    workflow: operation.workflow,
    entity_type: operation.entity_type,
    entity_id: operation.entity_id,
    actor: operation.actor,
    timestamp: operation.timestamp,
  }));

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Quality / Compliance expansion</p>
          <h2>Quality</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => openWorkflow("event")}><AlertTriangle size={16} />Create Quality Event</button>
          <button type="button" onClick={() => openWorkflow("adverse")}><HeartPulse size={16} />Create Adverse Event</button>
          <button type="button" onClick={() => openWorkflow("investigation")}><FileCheck2 size={16} />Add Investigation</button>
          <button type="button" onClick={() => openWorkflow("capa")}><ShieldCheck size={16} />Link CAPA</button>
          <button type="button" onClick={() => openWorkflow("close")}><CheckCircle2 size={16} />Close Event</button>
          <button type="button" onClick={() => openWorkflow("export")}><UploadCloud size={16} />Export Evidence</button>
        </div>
      </section>
      <section>
        <div className="quality-filter">
          <label>Search<input value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} placeholder="Event, patient, CAPA, deviation" /></label>
          <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All</option>{qualityStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Severity<select value={filters.severity} onChange={(event) => updateFilter("severity", event.target.value)}><option value="">All</option>{qualitySeverityOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Category<select value={filters.category} onChange={(event) => updateFilter("category", event.target.value)}><option value="">All</option>{qualityCategoryOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Owner<input value={filters.owner} onChange={(event) => updateFilter("owner", event.target.value)} /></label>
          <label>Source<select value={filters.source_module} onChange={(event) => updateFilter("source_module", event.target.value)}><option value="">All</option>{qualitySourceModuleOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Patient<select value={filters.patient_id} onChange={(event) => updateFilter("patient_id", event.target.value)}><option value="">All</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{clinicalDisplayText(patient.patient_id, "patient_id", user)}</option>)}</select></label>
          <button type="button" onClick={loadQuality}><RefreshCw size={16} />Apply</button>
        </div>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading ? <div className="notice-state">Loading quality work queue...</div> : (
        <>
          <ExportProfileIndicator profile={auditEvidence.export_profile || "audit_metadata"} />
          <div className="notice-state">{exportProfileInfo(auditEvidence.export_profile || "audit_metadata").warning}</div>
          <div className="content-grid">
            <MetricCard label="Open Events" value={formatNumber(dashboard?.open_events)} tone={dashboard?.open_events ? "warning" : "neutral"} />
            <MetricCard label="Overdue" value={formatNumber(dashboard?.overdue_events)} tone={dashboard?.overdue_events ? "warning" : "neutral"} />
            <MetricCard label="Adverse Open" value={formatNumber(dashboard?.adverse_events_open)} tone={dashboard?.adverse_events_open ? "warning" : "neutral"} />
            <MetricCard label="Exports" value={formatNumber(dashboard?.compliance_exports)} />
          </div>
          <div className="split quality-layout">
            <section>
              <h3>Quality Event Worklist</h3>
              <div className="workflow-list">
                {events.length ? events.map((event) => (
                  <button type="button" className="workflow-row" key={event.event_id} onClick={() => setSelectedEventId(event.event_id)}>
                    <span>{event.event_number} - {event.category}<br /><span className="muted"><TableCellValue value={event.patient_id || "No patient"} field="patient_id" user={user} /> {event.owner ? `- ${event.owner}` : ""}</span></span>
                    <span className="chip-list"><QualitySeverityChip severity={event.severity} /><StatusPill status={event.status} /></span>
                  </button>
                )) : <div className="empty-state">No quality events match the current filters.</div>}
              </div>
            </section>
            <section>
              <h3>Event Detail</h3>
              {selectedEvent ? (
                <div className="info-list compact">
                  <p><strong>{selectedEvent.event_number}</strong></p>
                  <p><TableCellValue value={selectedEvent.description} field="description" user={user} /></p>
                  <div className="chip-list"><QualitySeverityChip severity={selectedEvent.severity} /><StatusPill status={selectedEvent.status} /></div>
                  <div className="summary-grid">
                    <span>Owner <strong>{selectedEvent.owner || "Unassigned"}</strong></span>
                    <span>Due <strong>{selectedEvent.due_date ? formatDate(selectedEvent.due_date) : "None"}</strong></span>
                    <span>Source <strong>{selectedEvent.source_module}</strong></span>
                    <span>CAPA <strong>{selectedEvent.capa_code || selectedEvent.capa_id || "None"}</strong></span>
                  </div>
                </div>
              ) : <div className="empty-state">Select or create a quality event.</div>}
            </section>
          </div>
          <div className="quality-detail-grid">
            <section>
              <h3>Linked Context</h3>
              <Table rows={qualityPatientContextRows(selectedEvent)} columns={["context", "value"]} user={user} />
            </section>
            <section>
              <h3>Investigation Timeline</h3>
              <Table rows={(selectedEvent?.investigations || []).map((item) => ({ created_at: formatDateTime(item.created_at), owner: item.owner || "", note: item.note, root_cause: item.root_cause_category || "" }))} columns={["created_at", "owner", "note", "root_cause"]} user={user} />
            </section>
            <section>
              <h3>Status History</h3>
              <Table rows={(selectedEvent?.status_history || []).map((item) => ({ changed_at: formatDateTime(item.changed_at), from: item.from_status || "", to: item.to_status, reason: item.reason }))} columns={["changed_at", "from", "to", "reason"]} user={user} />
            </section>
            <section>
              <h3>Adverse Events</h3>
              <Table rows={adverseEvents.slice(0, 8).map((event) => ({ event: event.adverse_event_number, patient: event.patient_id, type: event.event_type, severity: event.severity, status: event.status }))} columns={["event", "patient", "type", "severity", "status"]} user={user} />
            </section>
            <section>
              <h3>Audit Evidence</h3>
              <Table rows={operations} columns={["workflow", "entity_type", "entity_id", "actor", "timestamp"]} user={user} />
            </section>
            <section>
              <h3>Compliance Exports</h3>
              <Table rows={exports.slice(0, 8).map((item) => ({ export: item.export_number, status: item.status, generated_at: formatDateTime(item.generated_at), profile: item.export_profile, evidence: item.evidence_summary?.workflow_operation_count || 0 }))} columns={["export", "status", "generated_at", "profile", "evidence"]} />
            </section>
            <section>
              <h3>CAPA / Deviation Links</h3>
              <Table rows={(selectedEvent?.links || []).map((link) => ({ type: link.entity_type, id: link.entity_id, label: link.label || "" }))} columns={["type", "id", "label"]} />
            </section>
            <section>
              <h3>Handoffs</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/admin")}><span>Quality categories and approval paths</span><StatusPill status="Planned workflow" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/reports")}><span>Quality compliance reports</span><StatusPill status="Active" /></button>
              </div>
            </section>
          </div>
        </>
      )}
      {modalType && (
        <QualityWorkflowModal
          type={modalType}
          token={token}
          user={user}
          selectedEvent={selectedEvent}
          patients={patients}
          appointments={appointments}
          sessions={sessions}
          encounters={encounters}
          orders={orders}
          carePlans={carePlans}
          billingQueue={billingQueue}
          onClose={() => setModalType("")}
          onSuccess={workflowSuccess}
        />
      )}
    </div>
  );
}

const reportModuleOptions = [
  { key: "patient_throughput", label: "Patient Throughput", endpoint: "/api/clinical/reports/patient-throughput" },
  { key: "scheduling_utilization", label: "Scheduling Utilization", endpoint: "/api/clinical/reports/scheduling-utilization" },
  { key: "screening_outcomes", label: "Screening Outcomes", endpoint: "/api/clinical/reports/screening-outcomes" },
  { key: "deferrals", label: "Deferrals", endpoint: "/api/clinical/reports/deferrals" },
  { key: "encounter_volume", label: "Encounter Volume", endpoint: "/api/clinical/reports/encounter-volume" },
  { key: "orders_results", label: "Orders / Results", endpoint: "/api/clinical/reports/orders-results" },
  { key: "care_plan_aging", label: "Care Plan Aging", endpoint: "/api/clinical/reports/care-plan-aging" },
  { key: "billing_work_queue", label: "Billing Work Queue", endpoint: "/api/clinical/reports/billing-work-queue" },
  { key: "quality_trends", label: "Quality Trends", endpoint: "/api/clinical/reports/quality-trends" },
  { key: "audit_activity", label: "Audit Activity", endpoint: "/api/clinical/reports/audit-activity" },
];

const reportStatusOptions = [
  "active",
  "scheduled",
  "checked_in",
  "in_progress",
  "completed",
  "open",
  "generated",
  "closed",
  "cancelled",
];

function reportModuleLabel(key) {
  return reportModuleOptions.find((item) => item.key === key)?.label || String(key || "").replaceAll("_", " ");
}

function reportMetricValue(metric) {
  if (isSuppressedCell(metric?.value)) return <ClinicalSuppressedMetric cell={metric.value} />;
  const value = Number(metric?.value || 0);
  const label = String(metric?.label || "").toLowerCase();
  if (metric?.unit === "currency" || ["balance", "charges", "payment", "adjustment", "amount"].some((term) => label.includes(term))) {
    return formatMoney(value);
  }
  return Number.isInteger(value) ? formatNumber(value) : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function countSortValue(count) {
  if (isSuppressedCell(count)) return -1;
  return Number(count || 0);
}

function visibleReportCount(count) {
  if (isSuppressedCell(count)) return 0;
  return Number(count || 0);
}

function countRows(counts, labelColumn = "category") {
  return Object.entries(counts || {})
    .map(([label, count]) => ({ [labelColumn]: label, count }))
    .sort((left, right) => countSortValue(right.count) - countSortValue(left.count));
}

function reportTableConfig(definition, report) {
  if (!report) return { rows: [], columns: ["metric", "value"] };
  if (definition.key === "patient_throughput") {
    return { rows: countRows(report.status_counts, "status"), columns: ["status", "count"] };
  }
  if (definition.key === "scheduling_utilization") {
    const rows = (report.provider_utilization || []).map((item) => ({
      provider_id: item.provider_id || "Unassigned",
      appointments: item.appointments || 0,
      scheduled_minutes: item.scheduled_minutes || 0,
    }));
    return rows.length
      ? { rows, columns: ["provider_id", "appointments", "scheduled_minutes"] }
      : { rows: countRows(report.appointment_type_breakdown, "appointment_type"), columns: ["appointment_type", "count"] };
  }
  if (definition.key === "screening_outcomes") {
    return { rows: countRows(report.outcome_counts, "outcome"), columns: ["outcome", "count"] };
  }
  if (definition.key === "deferrals") {
    const rows = report.patient_context?.length ? report.patient_context : countRows(report.type_counts, "deferral_type");
    return { rows, columns: rows[0] ? Object.keys(rows[0]) : ["deferral_type", "count"] };
  }
  if (definition.key === "encounter_volume") {
    const rows = [
      ...countRows(report.status_counts, "label").map((row) => ({ type: "encounter", ...row })),
      ...countRows(report.note_status_counts, "label").map((row) => ({ type: "note", ...row })),
    ];
    return { rows, columns: ["type", "label", "count"] };
  }
  if (definition.key === "orders_results") {
    const rows = [
      ...countRows(report.order_status_counts, "label").map((row) => ({ type: "order", ...row })),
      ...countRows(report.result_status_counts, "label").map((row) => ({ type: "result", ...row })),
    ];
    return { rows, columns: ["type", "label", "count"] };
  }
  if (definition.key === "care_plan_aging") {
    const rows = [
      ...countRows(report.status_counts, "label").map((row) => ({ type: "plan", ...row })),
      ...countRows(report.task_status_counts, "label").map((row) => ({ type: "task", ...row })),
      ...countRows(report.priority_counts, "label").map((row) => ({ type: "priority", ...row })),
    ];
    return { rows, columns: ["type", "label", "count"] };
  }
  if (definition.key === "billing_work_queue") {
    const rows = Object.entries(report.balances || {}).map(([metric, value]) => ({ metric, value: formatMoney(value) }));
    return { rows, columns: ["metric", "value"] };
  }
  if (definition.key === "quality_trends") {
    const rows = [
      ...countRows(report.severity_counts, "label").map((row) => ({ type: "severity", ...row })),
      ...countRows(report.status_counts, "label").map((row) => ({ type: "status", ...row })),
      ...countRows(report.category_counts, "label").map((row) => ({ type: "category", ...row })),
    ];
    return { rows, columns: ["type", "label", "count"] };
  }
  if (definition.key === "audit_activity") {
    const rows = [...(report.operations || [])].reverse().map((operation) => ({
      workflow: operation.workflow,
      entity: `${operation.entity_type || ""}:${operation.entity_id || ""}`,
      actor: operation.actor,
      timestamp: formatDateTime(operation.timestamp),
    }));
    return { rows, columns: ["workflow", "entity", "actor", "timestamp"] };
  }
  return { rows: [], columns: ["metric", "value"] };
}

function ReportPanel({ definition, report, user }) {
  const config = reportTableConfig(definition, report);
  return (
    <section>
      <div className="section-heading-row">
        <h3>{definition.label}</h3>
        <StatusPill status="Active" />
      </div>
      <div className="summary-grid report-summary-grid">
        {(report?.metrics || []).slice(0, 4).map((metric) => (
          <span key={metric.label}>{metric.label}<strong>{reportMetricValue(metric)}</strong></span>
        ))}
      </div>
      <Table rows={config.rows.slice(0, 10)} columns={config.columns} user={user} />
      {(report?.warnings || []).map((warning) => (
        <div className="notice-state compact-notice" key={`${definition.key}-${warning.warning_type}`}>{warning.message}</div>
      ))}
    </section>
  );
}

function ReportsExportModal({ token, filters, onClose, onSuccess }) {
  const [form, setForm] = useState(() => ({
    modules: reportModuleOptions.map((item) => item.key),
    export_format: "json",
    export_profile: filters.export_profile || "aggregate_safe",
    include_detail: false,
    date_from: filters.date_from,
    date_to: filters.date_to,
    status: filters.status,
    module: filters.module,
    actor: filters.actor,
    workflow: filters.workflow,
    entity_type: "",
    entity_id: "",
    reason: "Generate analytics export",
  }));
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const validationIssues = [];
  if (!form.modules.length) validationIssues.push("Select at least one report module.");
  if (!form.reason.trim()) validationIssues.push("Reason is required.");

  function toggleModule(module) {
    setForm((current) => ({
      ...current,
      modules: current.modules.includes(module)
        ? current.modules.filter((item) => item !== module)
        : [...current.modules, module],
    }));
  }

  function payload() {
    return compactPayload({
      modules: form.modules,
      export_format: form.export_format,
      include_detail: Boolean(form.include_detail),
      date_from: form.date_from,
      date_to: form.date_to,
      status: form.status,
      module: form.module,
      actor: form.actor,
      workflow: form.workflow,
      entity_type: form.entity_type,
      entity_id: form.entity_id,
      export_profile: form.export_profile,
      reason: form.reason,
    });
  }

  async function previewExport(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (validationIssues.length) return;
    try {
      const result = await apiRequest("/api/clinical/reports/analytics-exports/preview", {
        token,
        method: "POST",
        body: payload(),
      });
      setPreview(result);
      setMessage(result.blocking_issues?.length ? "Preview has blocking issues." : "Preview ready for confirmation.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function commitExport() {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiRequest("/api/clinical/reports/analytics-exports", {
        token,
        method: "POST",
        headers: { "X-Confirm-Generation": "true" },
        body: { ...payload(), preview_hash: preview?.preview_hash },
      });
      setMessage(`Committed ${result.operation_id}.`);
      onSuccess(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const rowCounts = Object.entries(preview?.row_counts || {}).map(([module, row_count]) => ({
    module: reportModuleLabel(module),
    row_count,
  }));

  return (
    <div className="modal-backdrop">
      <section className="workflow-modal reports-modal" role="dialog" aria-modal="true" aria-label="Generate analytics export">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Reporting analytics</p>
            <h3>Generate Analytics Export</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        <form className="stacked-form" onSubmit={previewExport}>
          <div className="form-grid">
            <label>Date from<input type="date" value={form.date_from} onChange={(event) => setForm({ ...form, date_from: event.target.value })} /></label>
            <label>Date to<input type="date" value={form.date_to} onChange={(event) => setForm({ ...form, date_to: event.target.value })} /></label>
            <label>Format<select value={form.export_format} onChange={(event) => setForm({ ...form, export_format: event.target.value })}><option value="json">JSON</option><option value="csv">CSV</option></select></label>
            <label>Export profile<select value={form.export_profile} onChange={(event) => setForm({ ...form, export_profile: event.target.value })}>{EXPORT_PROFILE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}><option value="">All</option>{reportStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label>Audit module<select value={form.module} onChange={(event) => setForm({ ...form, module: event.target.value })}><option value="">All</option>{reportModuleOptions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
            <label>Workflow<input value={form.workflow} onChange={(event) => setForm({ ...form, workflow: event.target.value })} placeholder="reports.analytics_export" /></label>
            <label>Actor<input value={form.actor} onChange={(event) => setForm({ ...form, actor: event.target.value })} /></label>
            <label>Entity type<input value={form.entity_type} onChange={(event) => setForm({ ...form, entity_type: event.target.value })} /></label>
            <label>Entity ID<input value={form.entity_id} onChange={(event) => setForm({ ...form, entity_id: event.target.value })} /></label>
          </div>
          <div className="preference-list report-module-picker">
            {reportModuleOptions.map((module) => (
              <label className="checkbox-row" key={module.key}>
                <input type="checkbox" checked={form.modules.includes(module.key)} onChange={() => toggleModule(module.key)} />
                {module.label}
              </label>
            ))}
            <label className="checkbox-row">
              <input type="checkbox" checked={form.include_detail} onChange={(event) => setForm({ ...form, include_detail: event.target.checked })} />
              Include detail metadata
            </label>
          </div>
          <label>Reason<textarea rows="3" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
          <ExportProfileIndicator profile={form.export_profile} suppression={preview?.suppression} />
          {exportProfileInfo(form.export_profile).warning && (
            <div className="notice-state">{exportProfileInfo(form.export_profile).warning}</div>
          )}
          {validationIssues.length > 0 && <div className="error-state">{validationIssues.join(" ")}</div>}
          {preview && (
            <div className="preview-panel">
              <StatusPill status={preview.blocking_issues?.length ? "failed" : "passed"} />
              <p>{preview.summary}</p>
              <Table rows={rowCounts} columns={["module", "row_count"]} />
              {preview.blocking_issues?.map((issue) => <div className="conflict-row blocking" key={`${issue.issue_type}-${issue.field}`}>{issue.message}</div>)}
              {preview.warnings?.map((warning) => <div className="conflict-row warning" key={`${warning.warning_type}-${warning.field}`}>{warning.message}</div>)}
            </div>
          )}
          {message && <div className="notice-state">{message}</div>}
          {error && <div className="error-state">{error}</div>}
          <div className="modal-actions">
            <button type="submit" disabled={Boolean(validationIssues.length)}><FileCheck2 size={16} />Preview</button>
            <button type="button" className="secondary-button" disabled={!preview || preview.blocking_issues?.length || submitting} onClick={commitExport}>
              <CheckCircle2 size={16} />
              Confirm
            </button>
          </div>
          <div className="notice-state">Commit sends X-Confirm-Generation: true and appends a workflow audit operation.</div>
        </form>
      </section>
    </div>
  );
}

function ClinicalReportsPage({ token, navigate, user }) {
  const [filters, setFilters] = useState({
    date_from: defaultDateInput(-30),
    date_to: defaultDateInput(0),
    status: "",
    module: "",
    actor: "",
    workflow: "",
    export_profile: "aggregate_safe",
  });
  const [dashboard, setDashboard] = useState(null);
  const [reports, setReports] = useState({});
  const [exports, setExports] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function queryString() {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    return params.toString();
  }

  async function loadReports() {
    setLoading(true);
    setError("");
    const qs = queryString();
    try {
      const [dashboardPayload, exportsPayload, ...reportPayloads] = await Promise.all([
        apiRequest(`/api/clinical/reports/dashboard${qs ? `?${qs}` : ""}`, { token }),
        apiRequest("/api/clinical/reports/analytics-exports", { token }),
        ...reportModuleOptions.map((definition) => apiRequest(`${definition.endpoint}${qs ? `?${qs}` : ""}`, { token })),
      ]);
      setDashboard(dashboardPayload);
      setExports(exportsPayload || []);
      setReports(Object.fromEntries(reportModuleOptions.map((definition, index) => [definition.key, reportPayloads[index]])));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadReports();
  }, [token]);

  const exportRows = exports.slice(0, 10).map((item) => ({
    export: item.export_number,
    status: item.status,
    modules: (item.modules || []).length,
    rows: Object.values(item.row_counts || {}).reduce((total, count) => total + visibleReportCount(count), 0),
    profile: item.payload_metadata?.export_profile || item.export_profile || "aggregate_safe",
    format: item.export_format,
    generated_at: formatDateTime(item.generated_at),
  }));

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Reporting / analytics readiness</p>
          <h2>Reports</h2>
          <StatusPill status="Active" />
          <ClinicalPrivacyIndicator user={user} />
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => setModalOpen(true)}><BarChart3 size={16} />Generate Export</button>
          <button type="button" className="secondary-button" onClick={loadReports}><RefreshCw size={16} />Refresh</button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/quality")}><ShieldCheck size={16} />Quality</button>
        </div>
      </section>
      <section>
        <div className="reports-filter">
          <label>Date from<input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} /></label>
          <label>Date to<input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} /></label>
          <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All</option>{reportStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Export profile<select value={filters.export_profile} onChange={(event) => updateFilter("export_profile", event.target.value)}>{EXPORT_PROFILE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label>Audit module<select value={filters.module} onChange={(event) => updateFilter("module", event.target.value)}><option value="">All</option>{reportModuleOptions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
          <label>Workflow<input value={filters.workflow} onChange={(event) => updateFilter("workflow", event.target.value)} /></label>
          <label>Actor<input value={filters.actor} onChange={(event) => updateFilter("actor", event.target.value)} /></label>
          <button type="button" onClick={loadReports}><FileCheck2 size={16} />Apply</button>
        </div>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading ? <div className="notice-state">Loading reporting datasets...</div> : (
        <>
          <ExportProfileIndicator profile={filters.export_profile} suppression={dashboard?.suppression} />
          {exportProfileInfo(filters.export_profile).warning && (
            <div className="notice-state">{exportProfileInfo(filters.export_profile).warning}</div>
          )}
          <div className="content-grid">
            {(dashboard?.metrics || []).map((metric) => (
              <MetricCard key={metric.label} label={metric.label} value={reportMetricValue(metric)} tone={metric.tone} />
            ))}
          </div>
          <div className="reports-detail-grid">
            {reportModuleOptions.map((definition) => (
              <ReportPanel key={definition.key} definition={definition} report={reports[definition.key]} user={user} />
            ))}
            <section>
              <div className="section-heading-row">
                <h3>Analytics Exports</h3>
                <button type="button" onClick={() => setModalOpen(true)}><UploadCloud size={15} />New Export</button>
              </div>
              <Table rows={exportRows} columns={["export", "status", "modules", "rows", "profile", "format", "generated_at"]} />
            </section>
            <section>
              <h3>Recent Audit</h3>
              <Table rows={(dashboard?.recent_audit_operations || []).map((operation) => ({ workflow: operation.workflow, entity_type: operation.entity_type, entity_id: operation.entity_id, actor: operation.actor, timestamp: formatDateTime(operation.timestamp) }))} columns={["workflow", "entity_type", "entity_id", "actor", "timestamp"]} user={user} />
            </section>
            <section>
              <h3>Handoffs</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/admin")}><span>Report permissions and catalogs</span><StatusPill status="Active" /></button>
                <div className="workflow-row"><span>Power BI / Snowflake delivery</span><StatusPill status="Planned workflow" /></div>
                <div className="workflow-row"><span>FHIR / HL7 analytics extract</span><StatusPill status="Foundation pending" /></div>
                <div className="workflow-row"><span>Production audit storage policy</span><StatusPill status="Planned workflow" /></div>
              </div>
            </section>
          </div>
        </>
      )}
      {modalOpen && <ReportsExportModal token={token} filters={filters} onClose={() => setModalOpen(false)} onSuccess={loadReports} />}
    </div>
  );
}

const adminWorkflowDefinitions = [
  { type: "appointment_type", label: "Appointment Type", endpoint: "/api/clinical/admin/appointment-types", listKey: "appointmentTypes", columns: ["type_code", "name", "category", "default_duration_minutes", "status", "version"] },
  { type: "provider_schedule", label: "Provider Schedule", endpoint: "/api/clinical/admin/provider-schedules", listKey: "providerSchedules", columns: ["provider_id", "weekday", "date_pattern", "start_time", "end_time", "active", "version"] },
  { type: "screening_template", label: "Screening Template", endpoint: "/api/clinical/admin/screening-templates", listKey: "screeningTemplates", columns: ["template_key", "template_name", "version", "active", "reason"] },
  { type: "eligibility_rule", label: "Eligibility Rule", endpoint: "/api/clinical/admin/eligibility-rules", listKey: "eligibilityRules", columns: ["rule_key", "rule_name", "rule_type", "severity", "active", "version"] },
  { type: "deferral_rule", label: "Deferral Rule", endpoint: "/api/clinical/admin/deferral-rules", listKey: "deferralRules", columns: ["rule_key", "rule_name", "rule_type", "severity", "active", "version"] },
  { type: "note_template", label: "Note Template", endpoint: "/api/clinical/admin/note-templates", listKey: "noteTemplates", columns: ["template_key", "name", "note_type", "status", "version"] },
  { type: "order_catalog", label: "Order Catalog Item", endpoint: "/api/clinical/admin/order-catalog", listKey: "orderCatalog", columns: ["code", "name", "order_type", "default_priority", "active", "version"] },
  { type: "billing_code", label: "Billing Code", endpoint: "/api/clinical/admin/billing-codes", listKey: "billingCodes", columns: ["code", "code_type", "description", "default_amount", "active", "version"] },
  { type: "quality_category", label: "Quality Category", endpoint: "/api/clinical/admin/quality-categories", listKey: "qualityCategories", columns: ["category_key", "category", "closure_approval_required", "approval_required", "active", "version"] },
  { type: "approval_path", label: "Approval Path", endpoint: "/api/clinical/admin/approval-paths", listKey: "approvalPaths", columns: ["workflow", "path_name", "version", "active", "steps"] },
  { type: "notification_template", label: "Notification Template", endpoint: "/api/clinical/admin/notification-templates", listKey: "notificationTemplates", columns: ["workflow", "channel", "subject", "active", "version"] },
];

function adminWorkflowTitle(type) {
  return adminWorkflowDefinitions.find((item) => item.type === type)?.label || "Clinical Admin Workflow";
}

function adminWorkflowEndpoint(type, suffix = "") {
  const definition = adminWorkflowDefinitions.find((item) => item.type === type);
  return definition ? `${definition.endpoint}${suffix}` : "/api/clinical/admin";
}

function defaultAdminForm(type) {
  if (type === "appointment_type") {
    return { type_code: "", name: "", duration_minutes: 60, category: "general", description: "", requires_room: true, active: true, reason: "Update appointment type configuration" };
  }
  if (type === "provider_schedule") {
    return { provider_id: "", weekday: "1", date_pattern: "weekly", start_time: "08:00", end_time: "17:00", location: "", room_id: "", active: true, reason: "Update provider schedule template" };
  }
  if (type === "screening_template") {
    return { template_key: "", template_name: "", required_questions_json: '[{"key":"question_1","label":"Required screening question","required":true}]', active: true, reason: "Create screening template version" };
  }
  if (type === "eligibility_rule") {
    return { rule_key: "", rule_name: "", rule_type: "eligibility", severity: "medium", expression: "", criteria_json: '{"all":[]}', explanation: "", active: true, reason: "Create eligibility rule version" };
  }
  if (type === "deferral_rule") {
    return { rule_key: "", rule_name: "", rule_type: "deferral", severity: "medium", expression: "", criteria_json: '{"all":[]}', explanation: "", active: true, reason: "Create deferral rule version" };
  }
  if (type === "note_template") {
    return { template_key: "", name: "", note_type: "clinical_note", body: "", sections_json: '[{"title":"Assessment","required":true}]', active: true, reason: "Update note template configuration" };
  }
  if (type === "order_catalog") {
    return { code: "", name: "", order_type: "laboratory", description: "", default_priority: "routine", specimen_type: "", active: true, reason: "Update order catalog item" };
  }
  if (type === "billing_code") {
    return { code: "", code_type: "internal", description: "", default_amount: "0.00", active: true, reason: "Update billing code catalog" };
  }
  if (type === "quality_category") {
    return { category_key: "", category: "", severity_mapping_json: '{"default":"medium"}', closure_required: false, approval_required: false, active: true, reason: "Update quality category configuration" };
  }
  if (type === "approval_path") {
    return { workflow: "quality.event_close", path_name: "", steps_json: '[{"step_order":1,"role":"Quality Assurance Specialist","permission":"quality.close","required":true,"active":true}]', active: true, reason: "Create approval path version" };
  }
  return { workflow: "", channel: "in_app", subject: "", body: "", active: true, reason: "Update notification template" };
}

function parseAdminJson(value, fallback) {
  if (!value) return fallback;
  return JSON.parse(value);
}

function adminNumberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  return Number(value);
}

function adminPayload(type, form) {
  if (type === "screening_template") {
    return { template_key: form.template_key, template_name: form.template_name, required_questions: parseAdminJson(form.required_questions_json, []), active: form.active, reason: form.reason };
  }
  if (["eligibility_rule", "deferral_rule"].includes(type)) {
    return { rule_key: form.rule_key, rule_name: form.rule_name, rule_type: form.rule_type, severity: form.severity, expression: form.expression, criteria: parseAdminJson(form.criteria_json, {}), explanation: form.explanation, active: form.active, reason: form.reason };
  }
  if (type === "note_template") {
    return { template_key: form.template_key, name: form.name, note_type: form.note_type, body: form.body, sections: parseAdminJson(form.sections_json, []), active: form.active, reason: form.reason };
  }
  if (type === "quality_category") {
    return { category_key: form.category_key, category: form.category, severity_mapping: parseAdminJson(form.severity_mapping_json, {}), closure_required: form.closure_required, approval_required: form.approval_required, active: form.active, reason: form.reason };
  }
  if (type === "approval_path") {
    return { workflow: form.workflow, path_name: form.path_name, steps: parseAdminJson(form.steps_json, []), active: form.active, reason: form.reason };
  }
  if (type === "provider_schedule") {
    return { provider_id: Number(form.provider_id), weekday: adminNumberOrNull(form.weekday), date_pattern: form.date_pattern, start_time: form.start_time, end_time: form.end_time, location: form.location, room_id: adminNumberOrNull(form.room_id), active: form.active, reason: form.reason };
  }
  if (type === "appointment_type") {
    return { type_code: form.type_code, name: form.name, duration_minutes: Number(form.duration_minutes), category: form.category, description: form.description, requires_room: form.requires_room, active: form.active, reason: form.reason };
  }
  if (type === "billing_code") {
    return { code: form.code, code_type: form.code_type, description: form.description, default_amount: Number(form.default_amount || 0), active: form.active, reason: form.reason };
  }
  if (type === "notification_template") {
    return { workflow: form.workflow, channel: form.channel, subject: form.subject, body: form.body, active: form.active, reason: form.reason };
  }
  return { code: form.code, name: form.name, order_type: form.order_type, description: form.description, default_priority: form.default_priority, specimen_type: form.specimen_type, active: form.active, reason: form.reason };
}

function validateAdminWorkflow(type, form) {
  const requiredByType = {
    appointment_type: ["type_code", "name", "category"],
    provider_schedule: ["provider_id", "date_pattern", "start_time", "end_time"],
    screening_template: ["template_key", "template_name"],
    eligibility_rule: ["rule_key", "rule_name", "rule_type", "severity"],
    deferral_rule: ["rule_key", "rule_name", "rule_type", "severity"],
    note_template: ["template_key", "name", "note_type"],
    order_catalog: ["code", "name", "order_type", "default_priority"],
    billing_code: ["code", "code_type", "description"],
    quality_category: ["category_key", "category"],
    approval_path: ["workflow", "path_name"],
    notification_template: ["workflow", "channel", "subject", "body"],
  };
  const issues = [];
  for (const field of requiredByType[type] || []) {
    if (!String(form[field] ?? "").trim()) issues.push(`${field.replaceAll("_", " ")} is required.`);
  }
  if (type === "provider_schedule" && form.start_time && form.end_time && form.end_time <= form.start_time) {
    issues.push("End time must be after start time.");
  }
  try {
    adminPayload(type, form);
  } catch (err) {
    issues.push(`JSON field is invalid: ${err.message}`);
  }
  return issues;
}

function AdminWorkflowFields({ type, form, updateField }) {
  if (type === "appointment_type") {
    return (
      <div className="form-grid">
        <label>Type code<input value={form.type_code} onChange={(event) => updateField("type_code", event.target.value)} /></label>
        <label>Name<input value={form.name} onChange={(event) => updateField("name", event.target.value)} /></label>
        <label>Duration minutes<input type="number" min="1" value={form.duration_minutes} onChange={(event) => updateField("duration_minutes", event.target.value)} /></label>
        <label>Category<input value={form.category} onChange={(event) => updateField("category", event.target.value)} /></label>
        <label className="wide-field">Description<textarea rows="3" value={form.description} onChange={(event) => updateField("description", event.target.value)} /></label>
        <label className="checkbox-row"><input type="checkbox" checked={form.requires_room} onChange={(event) => updateField("requires_room", event.target.checked)} /> Requires room</label>
        <label className="checkbox-row"><input type="checkbox" checked={form.active} onChange={(event) => updateField("active", event.target.checked)} /> Active</label>
      </div>
    );
  }
  if (type === "provider_schedule") {
    return (
      <div className="form-grid">
        <label>Provider ID<input type="number" value={form.provider_id} onChange={(event) => updateField("provider_id", event.target.value)} /></label>
        <label>Weekday<select value={form.weekday} onChange={(event) => updateField("weekday", event.target.value)}><option value="">Any</option><option value="0">Sunday</option><option value="1">Monday</option><option value="2">Tuesday</option><option value="3">Wednesday</option><option value="4">Thursday</option><option value="5">Friday</option><option value="6">Saturday</option></select></label>
        <label>Date pattern<input value={form.date_pattern} onChange={(event) => updateField("date_pattern", event.target.value)} /></label>
        <label>Location<input value={form.location} onChange={(event) => updateField("location", event.target.value)} /></label>
        <label>Start<input type="time" value={form.start_time} onChange={(event) => updateField("start_time", event.target.value)} /></label>
        <label>End<input type="time" value={form.end_time} onChange={(event) => updateField("end_time", event.target.value)} /></label>
        <label>Room ID<input type="number" value={form.room_id} onChange={(event) => updateField("room_id", event.target.value)} /></label>
        <label className="checkbox-row"><input type="checkbox" checked={form.active} onChange={(event) => updateField("active", event.target.checked)} /> Active</label>
      </div>
    );
  }
  if (["screening_template", "eligibility_rule", "deferral_rule", "note_template", "quality_category", "approval_path"].includes(type)) {
    return (
      <div className="form-grid">
        {type === "screening_template" && (
          <>
            <label>Template key<input value={form.template_key} onChange={(event) => updateField("template_key", event.target.value)} /></label>
            <label>Template name<input value={form.template_name} onChange={(event) => updateField("template_name", event.target.value)} /></label>
            <label className="wide-field">Required questions JSON<textarea rows="7" value={form.required_questions_json} onChange={(event) => updateField("required_questions_json", event.target.value)} /></label>
          </>
        )}
        {["eligibility_rule", "deferral_rule"].includes(type) && (
          <>
            <label>Rule key<input value={form.rule_key} onChange={(event) => updateField("rule_key", event.target.value)} /></label>
            <label>Rule name<input value={form.rule_name} onChange={(event) => updateField("rule_name", event.target.value)} /></label>
            <label>Rule type<input value={form.rule_type} onChange={(event) => updateField("rule_type", event.target.value)} /></label>
            <label>Severity<select value={form.severity} onChange={(event) => updateField("severity", event.target.value)}><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label>
            <label className="wide-field">Expression<textarea rows="3" value={form.expression} onChange={(event) => updateField("expression", event.target.value)} /></label>
            <label className="wide-field">Criteria JSON<textarea rows="6" value={form.criteria_json} onChange={(event) => updateField("criteria_json", event.target.value)} /></label>
            <label className="wide-field">Explanation<textarea rows="3" value={form.explanation} onChange={(event) => updateField("explanation", event.target.value)} /></label>
          </>
        )}
        {type === "note_template" && (
          <>
            <label>Template key<input value={form.template_key} onChange={(event) => updateField("template_key", event.target.value)} /></label>
            <label>Name<input value={form.name} onChange={(event) => updateField("name", event.target.value)} /></label>
            <label>Note type<input value={form.note_type} onChange={(event) => updateField("note_type", event.target.value)} /></label>
            <label className="wide-field">Body<textarea rows="5" value={form.body} onChange={(event) => updateField("body", event.target.value)} /></label>
            <label className="wide-field">Sections JSON<textarea rows="5" value={form.sections_json} onChange={(event) => updateField("sections_json", event.target.value)} /></label>
          </>
        )}
        {type === "quality_category" && (
          <>
            <label>Category key<input value={form.category_key} onChange={(event) => updateField("category_key", event.target.value)} /></label>
            <label>Category<input value={form.category} onChange={(event) => updateField("category", event.target.value)} /></label>
            <label className="wide-field">Severity mapping JSON<textarea rows="5" value={form.severity_mapping_json} onChange={(event) => updateField("severity_mapping_json", event.target.value)} /></label>
            <label className="checkbox-row"><input type="checkbox" checked={form.closure_required} onChange={(event) => updateField("closure_required", event.target.checked)} /> Closure approval required</label>
            <label className="checkbox-row"><input type="checkbox" checked={form.approval_required} onChange={(event) => updateField("approval_required", event.target.checked)} /> Approval required</label>
          </>
        )}
        {type === "approval_path" && (
          <>
            <label>Workflow<input value={form.workflow} onChange={(event) => updateField("workflow", event.target.value)} /></label>
            <label>Path name<input value={form.path_name} onChange={(event) => updateField("path_name", event.target.value)} /></label>
            <label className="wide-field">Steps JSON<textarea rows="7" value={form.steps_json} onChange={(event) => updateField("steps_json", event.target.value)} /></label>
          </>
        )}
        <label className="checkbox-row"><input type="checkbox" checked={form.active} onChange={(event) => updateField("active", event.target.checked)} /> Active</label>
      </div>
    );
  }
  return (
    <div className="form-grid">
      {type === "order_catalog" && (
        <>
          <label>Code<input value={form.code} onChange={(event) => updateField("code", event.target.value)} /></label>
          <label>Name<input value={form.name} onChange={(event) => updateField("name", event.target.value)} /></label>
          <label>Order type<input value={form.order_type} onChange={(event) => updateField("order_type", event.target.value)} /></label>
          <label>Default priority<input value={form.default_priority} onChange={(event) => updateField("default_priority", event.target.value)} /></label>
          <label>Specimen type<input value={form.specimen_type} onChange={(event) => updateField("specimen_type", event.target.value)} /></label>
          <label className="wide-field">Description<textarea rows="3" value={form.description} onChange={(event) => updateField("description", event.target.value)} /></label>
        </>
      )}
      {type === "billing_code" && (
        <>
          <label>Code<input value={form.code} onChange={(event) => updateField("code", event.target.value)} /></label>
          <label>Code type<input value={form.code_type} onChange={(event) => updateField("code_type", event.target.value)} /></label>
          <label>Default amount<input type="number" min="0" step="0.01" value={form.default_amount} onChange={(event) => updateField("default_amount", event.target.value)} /></label>
          <label className="wide-field">Description<textarea rows="3" value={form.description} onChange={(event) => updateField("description", event.target.value)} /></label>
        </>
      )}
      {type === "notification_template" && (
        <>
          <label>Workflow<input value={form.workflow} onChange={(event) => updateField("workflow", event.target.value)} /></label>
          <label>Channel<select value={form.channel} onChange={(event) => updateField("channel", event.target.value)}><option>in_app</option><option>email</option><option>sms</option></select></label>
          <label className="wide-field">Subject<input value={form.subject} onChange={(event) => updateField("subject", event.target.value)} /></label>
          <label className="wide-field">Body<textarea rows="6" value={form.body} onChange={(event) => updateField("body", event.target.value)} /></label>
        </>
      )}
      <label className="checkbox-row"><input type="checkbox" checked={form.active} onChange={(event) => updateField("active", event.target.checked)} /> Active</label>
    </div>
  );
}

function AdminWorkflowModal({ type, token, onClose, onSuccess }) {
  const [form, setForm] = useState(() => defaultAdminForm(type));
  const [step, setStep] = useState("form");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const validationIssues = validateAdminWorkflow(type, form);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function runPreview() {
    setBusy(true);
    setError("");
    try {
      const payload = await apiRequest(adminWorkflowEndpoint(type, "/preview"), {
        token,
        method: "POST",
        body: compactPayload(adminPayload(type, form)),
      });
      setPreview(payload);
      setStep("preview");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setBusy(true);
    setError("");
    try {
      await apiRequest(adminWorkflowEndpoint(type), {
        token,
        method: "POST",
        headers: { "X-Confirm-Generation": "true" },
        body: { ...compactPayload(adminPayload(type, form)), preview_hash: preview?.preview_hash },
      });
      setStep("success");
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const currentRows = Object.entries(preview?.current_config || {}).map(([field, value]) => ({ field, value: typeof value === "object" ? JSON.stringify(value) : value }));
  const proposedRows = Object.entries(preview?.proposed_config || {}).map(([field, value]) => ({ field, value: typeof value === "object" ? JSON.stringify(value) : value }));

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workflow-modal admin-modal" role="dialog" aria-modal="true" aria-label={adminWorkflowTitle(type)}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{step.replaceAll("_", " ")}</p>
            <h3>{adminWorkflowTitle(type)}</h3>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Close</button>
        </div>
        {error && <div className="error-state">{error}</div>}
        {step === "form" && (
          <div className="stacked-form">
            <AdminWorkflowFields type={type} form={form} updateField={updateField} />
            <label className="wide-field">Reason<input value={form.reason} onChange={(event) => updateField("reason", event.target.value)} /></label>
            <button type="button" onClick={() => setStep("validation")}>Continue to validation</button>
          </div>
        )}
        {step === "validation" && (
          <div className="stacked-form">
            {validationIssues.length ? <div className="error-state">{validationIssues.join(" ")}</div> : <div className="notice-state">Required fields are complete. Preview will compare current and proposed configuration.</div>}
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={busy || validationIssues.length > 0} onClick={runPreview}>{busy ? <RefreshCw size={16} /> : <FileCheck2 size={16} />}Generate preview</button>
          </div>
        )}
        {step === "preview" && preview && (
          <div className="stacked-form">
            <div className="notice-state">{preview.summary}</div>
            <Table rows={[{ field: "Preview hash", value: preview.preview_hash }, { field: "Changed fields", value: preview.changed_fields.join(", ") || "None" }, { field: "Affected modules", value: preview.affected_modules.join(", ") }]} columns={["field", "value"]} />
            {preview.warnings?.length > 0 && <Table rows={preview.warnings} columns={["warning_type", "field", "message"]} />}
            {preview.blocking_issues?.length > 0 && <div className="error-state">{preview.blocking_issues.map((issue) => issue.message).join(" ")}</div>}
            <div className="admin-preview-grid">
              <section><h3>Current</h3><Table rows={currentRows} columns={["field", "value"]} /></section>
              <section><h3>Proposed</h3><Table rows={proposedRows} columns={["field", "value"]} /></section>
            </div>
            <button type="button" className="secondary-button" onClick={() => setStep("form")}>Back to form</button>
            <button type="button" disabled={preview.blocking_issues?.length > 0} onClick={() => setStep("confirm")}>Continue to commit confirmation</button>
          </div>
        )}
        {step === "confirm" && (
          <div className="stacked-form">
            <div className="notice-state">Commit will send X-Confirm-Generation: true, create or preserve a configuration version, and append a workflow operation audit entry.</div>
            <button type="button" className="secondary-button" onClick={() => setStep("preview")}>Back to preview</button>
            <button type="button" disabled={busy} onClick={runCommit}>{busy ? <RefreshCw size={16} /> : <CheckCircle2 size={16} />}Commit workflow</button>
          </div>
        )}
        {step === "success" && (
          <div className="stacked-form">
            <div className="notice-state">Configuration workflow committed successfully.</div>
            <button type="button" onClick={onClose}>Done</button>
          </div>
        )}
      </section>
    </div>
  );
}

function adminRowText(row) {
  return Object.values(row || {}).map((value) => (typeof value === "object" ? JSON.stringify(value) : String(value ?? ""))).join(" ").toLowerCase();
}

function ClinicalAdminPage({ token, navigate, user }) {
  const [dashboard, setDashboard] = useState(null);
  const [configVersions, setConfigVersions] = useState([]);
  const [rbac, setRbac] = useState({ roles: [] });
  const [lists, setLists] = useState({});
  const [filters, setFilters] = useState({ q: "", status: "" });
  const [modalType, setModalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadAdmin() {
    setLoading(true);
    setError("");
    try {
      const [dashboardPayload, versionPayload, rbacPayload, ...listPayloads] = await Promise.all([
        apiRequest("/api/clinical/admin/dashboard", { token }),
        apiRequest("/api/clinical/admin/config-versions", { token }),
        apiRequest("/api/clinical/admin/rbac", { token }),
        ...adminWorkflowDefinitions.map((definition) => apiRequest(definition.endpoint, { token }).catch(() => [])),
      ]);
      const nextLists = {};
      adminWorkflowDefinitions.forEach((definition, index) => {
        nextLists[definition.listKey] = listPayloads[index] || [];
      });
      setDashboard(dashboardPayload);
      setConfigVersions(versionPayload || []);
      setRbac(rbacPayload || { roles: [] });
      setLists(nextLists);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadAdmin();
  }, [token]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function filteredRows(rows) {
    return (rows || []).filter((row) => {
      const statusValue = String(row.status ?? (row.active === false ? "inactive" : row.active === true ? "active" : "")).toLowerCase();
      const matchesStatus = !filters.status || statusValue === filters.status;
      const matchesQuery = !filters.q || adminRowText(row).includes(filters.q.toLowerCase());
      return matchesStatus && matchesQuery;
    });
  }

  const totalConfigs = adminWorkflowDefinitions.reduce((total, definition) => total + (lists[definition.listKey]?.length || 0), 0);
  const activeConfigs = adminWorkflowDefinitions.reduce((total, definition) => total + (lists[definition.listKey] || []).filter((row) => row.active === true || row.status === "active").length, 0);
  const recentOps = (dashboard?.recent_audit_operations || []).slice().reverse().map((operation) => ({ workflow: operation.workflow, entity_type: operation.entity_type, entity_id: operation.entity_id, actor: operation.actor, timestamp: formatDateTime(operation.timestamp) }));

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div>
          <p className="eyebrow">Clinical administration</p>
          <h2>Clinical Admin</h2>
          <StatusPill status="Active" />
        </div>
        <div className="clinical-actions">
          {adminWorkflowDefinitions.slice(0, 6).map((definition) => (
            <button type="button" key={definition.type} onClick={() => setModalType(definition.type)}><ShieldCheck size={16} />{definition.label}</button>
          ))}
        </div>
      </section>
      <section>
        <div className="admin-filter">
          <label>Search<input value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} placeholder="Template, rule, code, workflow" /></label>
          <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All</option><option value="active">Active</option><option value="inactive">Inactive</option></select></label>
          <button type="button" onClick={loadAdmin}><RefreshCw size={16} />Refresh</button>
        </div>
      </section>
      {error && <div className="error-state">{error}</div>}
      {loading ? <div className="notice-state">Loading clinical administration configuration...</div> : (
        <>
          <div className="content-grid">
            <MetricCard label="Config Versions" value={formatNumber(dashboard?.total_config_versions || configVersions.length)} />
            <MetricCard label="Active Versions" value={formatNumber(dashboard?.active_config_versions || activeConfigs)} />
            <MetricCard label="Config Records" value={formatNumber(totalConfigs)} />
            <MetricCard label="Admin Audit Ops" value={formatNumber(dashboard?.recent_audit_operations?.length || 0)} />
          </div>
          <div className="admin-detail-grid">
            <section>
              <div className="section-heading-row"><h3>Config Version History</h3><StatusPill status="Append only" /></div>
              <Table rows={configVersions.slice(0, 8).map((item) => ({ config_type: item.config_type, config_key: item.config_key, version: item.version, status: item.status, created_at: formatDateTime(item.created_at), reason: item.reason }))} columns={["config_type", "config_key", "version", "status", "created_at", "reason"]} />
            </section>
            <section>
              <div className="section-heading-row"><h3>RBAC Overview</h3><StatusPill status="Internal only" /></div>
              <Table rows={(rbac.roles || []).map((role) => ({ role: role.role, read: role.can_read_admin, manage: role.can_manage_admin, external: role.external }))} columns={["role", "read", "manage", "external"]} />
            </section>
            {adminWorkflowDefinitions.map((definition) => {
              const rows = filteredRows(lists[definition.listKey] || []).slice(0, 8);
              return (
                <section key={definition.type}>
                  <div className="section-heading-row">
                    <h3>{definition.label}</h3>
                    <button type="button" onClick={() => setModalType(definition.type)}><FileCheck2 size={15} />Configure</button>
                  </div>
                  <Table rows={rows} columns={definition.columns} />
                </section>
              );
            })}
            <section>
              <h3>Recent Admin Audit</h3>
              <Table rows={recentOps} columns={["workflow", "entity_type", "entity_id", "actor", "timestamp"]} />
            </section>
            <section>
              <h3>Handoffs</h3>
              <div className="workflow-list">
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/quality")}><span>Quality categories and approval-controlled closure</span><StatusPill status="Active" /></button>
                <button type="button" className="workflow-row" onClick={() => navigate("/clinical/reports")}><span>Reporting / analytics configuration consumers</span><StatusPill status="Active" /></button>
              </div>
            </section>
          </div>
        </>
      )}
      {modalType && <AdminWorkflowModal type={modalType} token={token} onClose={() => setModalType("")} onSuccess={loadAdmin} />}
    </div>
  );
}

function ClinicalModuleSection({ section, route, token, navigate, user }) {
  if (section.id === "clinical_admin") {
    return <ClinicalAdminPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_quality") {
    return <ClinicalQualityPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_reports") {
    return <ClinicalReportsPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_billing") {
    return <ClinicalBillingPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_care_plans") {
    return <ClinicalCarePlansPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_orders") {
    return <ClinicalOrdersPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_encounters") {
    return <ClinicalEncountersPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_patients") {
    return <ClinicalPatientsPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_scheduling") {
    return <ClinicalSchedulingPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_screening") {
    return <ClinicalScreeningPage token={token} navigate={navigate} user={user} />;
  }
  if (section.id === "clinical_patient_detail") {
    return <ClinicalPatientDetailPage token={token} route={route} navigate={navigate} user={user} />;
  }
  return (
    <ClinicalShellPlaceholder
      section={section}
      route={route}
      navigate={navigate}
      StatusPill={StatusPill}
      Table={Table}
    />
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

function SectionBody({ active, activeSection, route, status, token, user, refresh, navigate }) {
  const validation = status?.latest_validation || {};
  const manifest = status?.latest_export_manifest || {};
  const freshness = status?.source_freshness?.freshness || [];
  const runs = status?.recent_runs || [];

  if (active?.startsWith("clinical_")) {
    return <ClinicalModuleSection section={activeSection} route={route} token={token} user={user} navigate={navigate} />;
  }
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
  const active =
    routeToSection[route] || (clinicalPatientId(route) ? "clinical_patient_detail" : route === "/" && token ? "dashboard" : "");
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
          <span className="nav-label">Clinical Platform</span>
          {clinicalSections.map((section) => {
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
          <SectionBody
            active={active || "dashboard"}
            activeSection={activeSection}
            route={route}
            status={status || {}}
            token={token}
            user={user}
            refresh={refresh}
            navigate={navigate}
          />
        )}
      </main>
    </div>
  );
}

export default App;
