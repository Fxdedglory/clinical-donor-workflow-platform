import React, { useEffect, useMemo, useState } from "react";
import {
  CLINICAL_USER_ID,
  getClinicalHealth,
  getClinicalRecentEvents,
  sendClinicalEvent
} from "./api";
import "./styles.css";

const portfolioNavItems = [
  { label: "Home", href: "https://teemails.com/" },
  { label: "ERP", href: "https://teemails.com/ERP" },
  { label: "HR", href: "https://teemails.com/HR" },
  { label: "Clinical", href: "https://teemails.com/Clinical" },
  { label: "Monitor", href: "https://teemails.com/Monitor" },
  { label: "Analytics", href: "https://teemails.com/Analytics" },
  { label: "About-me", href: "https://teemails.com/about-me" }
];

const appNavItems = [
  { label: "Command Center", path: "/Clinical/" },
  { label: "Intake", path: "/Clinical/intake" },
  { label: "Screening", path: "/Clinical/screening" },
  { label: "Scheduling", path: "/Clinical/scheduling" },
  { label: "Clinical Review", path: "/Clinical/review" },
  { label: "Quality", path: "/Clinical/quality" },
  { label: "Vendor Ops", path: "/Clinical/vendor-ops" },
  { label: "Reports", path: "/Clinical/reports" },
  { label: "Administration", path: "/Clinical/administration" }
];

const roleCards = [
  ["Intake Coordinator", "Registers donor referrals, confirms demographics, documents consents, and starts screening packets."],
  ["Clinical Reviewer", "Reviews eligibility evidence, medical history, lab readiness, and clinical disposition."],
  ["QA Specialist", "Audits documentation, deviations, corrective actions, and release-readiness evidence."],
  ["Vendor Operations", "Coordinates supplier portals, document requests, partner follow-ups, and service-level exceptions."],
  ["Operations Manager", "Monitors throughput, staffing load, cycle time, and escalation queues."],
  ["Technology Analyst", "Owns workflow configuration, data quality, integrations, reporting readiness, and audit evidence."]
];

const dashboardMetrics = [
  { label: "Active Donor Cases", value: "248", delta: "+18 this week", tone: "good" },
  { label: "Eligibility Queue", value: "37", delta: "8 urgent", tone: "warning" },
  { label: "QA Release Ready", value: "91%", delta: "+4.3%", tone: "good" },
  { label: "Vendor SLA", value: "96.2%", delta: "2 exceptions", tone: "neutral" }
];

const intakeRows = [
  ["DON-10481", "New referral packet", "Intake Review", "Intake Coordinator"],
  ["DON-10482", "Consent verification", "Needs Outreach", "Intake Coordinator"],
  ["DON-10483", "Demographics update", "Ready", "Technology Analyst"],
  ["DON-10484", "Insurance/contact validation", "In Progress", "Intake Coordinator"]
];

const screeningRows = [
  ["SCR-77811", "Medical history questionnaire", "Clinical Review", "Clinical Reviewer"],
  ["SCR-77812", "Eligibility criteria check", "Exception", "Clinical Reviewer"],
  ["SCR-77813", "Infectious disease readiness", "Ready", "QA Specialist"],
  ["SCR-77814", "Deferral rule review", "Needs Evidence", "Clinical Reviewer"]
];

const schedulingRows = [
  ["APT-55021", "Donor screening appointment", "Confirmed", "Scheduling"],
  ["APT-55022", "Provider review slot", "Pending", "Clinical Reviewer"],
  ["APT-55023", "Vendor collection window", "At Risk", "Vendor Operations"],
  ["APT-55024", "Follow-up review", "Scheduled", "Operations Manager"]
];

const reviewRows = [
  ["REV-30210", "Eligibility disposition", "Pending Signoff", "Clinical Reviewer"],
  ["REV-30211", "Clinical notes review", "In Progress", "Clinical Reviewer"],
  ["REV-30212", "Lab readiness evidence", "Ready", "QA Specialist"],
  ["REV-30213", "Escalated case review", "Urgent", "Operations Manager"]
];

const qualityRows = [
  ["QA-8011", "Release evidence audit", "Ready", "QA Specialist"],
  ["QA-8012", "Deviation review", "CAPA Open", "QA Specialist"],
  ["QA-8013", "Document completeness", "Pass", "Technology Analyst"],
  ["QA-8014", "Compliance sampling", "Scheduled", "QA Specialist"]
];

const vendorRows = [
  ["VEN-2001", "Partner document request", "Pending Vendor", "Vendor Operations"],
  ["VEN-2002", "Supplier SLA exception", "Escalated", "Vendor Operations"],
  ["VEN-2003", "Collection confirmation", "Confirmed", "Vendor Operations"],
  ["VEN-2004", "Portal access review", "Needs Admin", "System Administrator"]
];

function getCurrentPath() {
  const pathname = window.location.pathname;

  if (pathname === "/Clinical") {
    return "/Clinical/";
  }

  return pathname.startsWith("/Clinical") ? pathname : "/Clinical/";
}

function pageKey(pathname) {
  if (pathname.includes("/intake")) return "intake";
  if (pathname.includes("/screening")) return "screening";
  if (pathname.includes("/scheduling")) return "scheduling";
  if (pathname.includes("/review")) return "review";
  if (pathname.includes("/quality")) return "quality";
  if (pathname.includes("/vendor-ops")) return "vendor-ops";
  if (pathname.includes("/reports")) return "reports";
  if (pathname.includes("/administration")) return "administration";
  return "dashboard";
}

function emitClinicalUiEvent(eventType, payload = {}) {
  sendClinicalEvent({
    eventType,
    aggregateType: payload.aggregateType || "ui",
    aggregateId: payload.aggregateId || payload.path || "clinical-ui",
    actorUserId: CLINICAL_USER_ID,
    sensitivityClassification: "public_internal",
    payload: {
      ...payload,
      emittedAt: new Date().toISOString()
    }
  });
}

function PortfolioRibbon() {
  return (
    <header className="portfolio-ribbon">
      <a className="portfolio-brand" href="https://teemails.com/">
        <span className="portfolio-mark">T</span>
        <span>
          <strong>teemails</strong>
          <small>Portfolio workspace</small>
        </span>
      </a>

      <nav className="portfolio-nav" aria-label="Portfolio navigation">
        {portfolioNavItems.map((item) => (
          <a
            key={item.label}
            className={item.label === "Clinical" ? "active" : ""}
            href={item.href}
            onClick={() => emitClinicalUiEvent("clinical.portfolio.nav_clicked", { label: item.label, href: item.href })}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
}

function StatusPill({ children, tone = "neutral" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function DataTable({ rows }) {
  return (
    <div className="clinical-table">
      {rows.map((row) => (
        <div className="clinical-table-row" key={row[0]}>
          <strong>{row[0]}</strong>
          <span>{row[1]}</span>
          <StatusPill tone={
            row[2].toLowerCase().includes("urgent") ||
            row[2].toLowerCase().includes("exception") ||
            row[2].toLowerCase().includes("risk") ||
            row[2].toLowerCase().includes("capa")
              ? "warning"
              : row[2].toLowerCase().includes("ready") ||
                row[2].toLowerCase().includes("confirmed") ||
                row[2].toLowerCase().includes("pass")
                ? "good"
                : "neutral"
          }>
            {row[2]}
          </StatusPill>
          <b>{row[3]}</b>
        </div>
      ))}
    </div>
  );
}

function ActionButton({ eventType, children, payload = {} }) {
  return (
    <button type="button" onClick={() => emitClinicalUiEvent(eventType, payload)}>
      {children}
    </button>
  );
}

function DashboardPage() {
  return (
    <>
      <section className="hero-card">
        <div>
          <p className="eyebrow">Meridian Clinical</p>
          <h1>Donor services command center.</h1>
          <p>
            Manage donor intake, screening, scheduling, clinical eligibility review, QA release evidence,
            vendor operations, and analytics readiness in an Evergen-aligned workflow.
          </p>
        </div>

        <div className="hero-panel">
          <strong>Operating model</strong>
          <span>Donor Services Â· Quality Workflow Â· Technology Analyst View</span>
          <StatusPill tone="good">Clinical rebuild active</StatusPill>
        </div>
      </section>

      <section className="metric-grid">
        {dashboardMetrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <StatusPill tone={metric.tone}>{metric.delta}</StatusPill>
          </article>
        ))}
      </section>

      <section className="two-column">
        <Card title="Eligibility Workbench">
          <DataTable rows={[screeningRows[0], screeningRows[1], reviewRows[0], reviewRows[3]]} />
        </Card>

        <Card title="Evergen-Aligned Roles">
          <div className="role-grid">
            {roleCards.map(([role, description]) => (
              <div className="role-card" key={role}>
                <strong>{role}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </>
  );
}

function IntakePage() {
  return (
    <ModulePage
      title="Intake"
      eyebrow="Referral registration, demographics, consent"
      description="Capture donor referral packets, demographics, contact details, consent state, intake notes, and case readiness for downstream screening."
      actions={[
        ["clinical.donor_intake.created", "Create Donor Intake"],
        ["clinical.consent.verified", "Verify Consent"],
        ["clinical.demographics.updated", "Update Demographics"],
        ["clinical.intake.packet.completed", "Complete Intake Packet"]
      ]}
      rows={intakeRows}
    />
  );
}

function ScreeningPage() {
  return (
    <ModulePage
      title="Screening"
      eyebrow="Eligibility, medical history, deferrals"
      description="Review medical history, eligibility criteria, deferral rules, infectious disease readiness, and evidence gaps before clinical disposition."
      actions={[
        ["clinical.screening.started", "Start Screening"],
        ["clinical.eligibility.checked", "Run Eligibility Check"],
        ["clinical.deferral.flagged", "Flag Deferral"],
        ["clinical.evidence.requested", "Request Evidence"]
      ]}
      rows={screeningRows}
    />
  );
}

function SchedulingPage() {
  return (
    <ModulePage
      title="Scheduling"
      eyebrow="Appointments, review slots, vendor windows"
      description="Coordinate donor screening appointments, provider review slots, vendor collection windows, follow-ups, and escalation windows."
      actions={[
        ["clinical.appointment.scheduled", "Schedule Appointment"],
        ["clinical.appointment.rescheduled", "Reschedule"],
        ["clinical.vendor_window.confirmed", "Confirm Vendor Window"],
        ["clinical.followup.created", "Create Follow-up"]
      ]}
      rows={schedulingRows}
    />
  );
}

function ClinicalReviewPage() {
  return (
    <ModulePage
      title="Clinical Review"
      eyebrow="Disposition, notes, lab readiness"
      description="Support clinical reviewers with eligibility disposition, lab readiness, clinical notes, escalations, and signoff evidence."
      actions={[
        ["clinical.review.opened", "Open Review"],
        ["clinical.disposition.recorded", "Record Disposition"],
        ["clinical.lab_readiness.confirmed", "Confirm Lab Readiness"],
        ["clinical.case.escalated", "Escalate Case"]
      ]}
      rows={reviewRows}
    />
  );
}

function QualityPage() {
  return (
    <ModulePage
      title="Quality"
      eyebrow="QA audit, deviations, CAPA, release evidence"
      description="Manage QA release readiness, documentation audits, deviation reviews, CAPA follow-up, and compliance sampling."
      actions={[
        ["clinical.qa.audit.started", "Start QA Audit"],
        ["clinical.deviation.created", "Create Deviation"],
        ["clinical.capa.updated", "Update CAPA"],
        ["clinical.release_evidence.approved", "Approve Release Evidence"]
      ]}
      rows={qualityRows}
    />
  );
}

function VendorOpsPage() {
  return (
    <ModulePage
      title="Vendor Operations"
      eyebrow="Supplier portal, SLA, partner coordination"
      description="Coordinate partner document requests, vendor SLA exceptions, collection confirmations, and supplier portal readiness."
      actions={[
        ["clinical.vendor.document_requested", "Request Vendor Document"],
        ["clinical.vendor.sla_exception.created", "Create SLA Exception"],
        ["clinical.collection.confirmed", "Confirm Collection"],
        ["clinical.vendor_portal.access_reviewed", "Review Portal Access"]
      ]}
      rows={vendorRows}
    />
  );
}

function ReportsPage() {
  return (
    <ModulePage
      title="Reports"
      eyebrow="Clinical analytics readiness"
      description="Prepare donor services analytics for cycle time, eligibility outcomes, QA readiness, vendor SLA, and operational throughput."
      actions={[
        ["clinical.report.run", "Run Report"],
        ["clinical.report.exported", "Export Report"],
        ["clinical.analytics.snapshot.created", "Create Snapshot"],
        ["clinical.quality_dashboard.refreshed", "Refresh Quality Dashboard"]
      ]}
      rows={[
        ["RPT-CLIN-001", "Donor services executive summary", "Ready", "Power BI"],
        ["RPT-CLIN-002", "Eligibility outcomes", "Ready", "Snowflake"],
        ["RPT-QA-003", "QA release readiness", "Draft", "Power BI"],
        ["RPT-VEN-004", "Vendor SLA exceptions", "Draft", "Snowflake"]
      ]}
    />
  );
}

function AdministrationPage() {
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("Clinical event API pending");

  function refreshApiState() {
    setStatus("Loading Clinical API state");

    Promise.allSettled([getClinicalHealth(), getClinicalRecentEvents(10)])
      .then(([healthResult, eventsResult]) => {
        if (healthResult.status === "fulfilled") {
          setHealth(healthResult.value);
        }

        if (eventsResult.status === "fulfilled") {
          setEvents(Array.isArray(eventsResult.value?.events) ? eventsResult.value.events : []);
        }

        if (healthResult.status === "fulfilled" || eventsResult.status === "fulfilled") {
          setStatus("Connected");
        } else {
          setStatus("Clinical event API pending");
        }
      })
      .catch(() => setStatus("Clinical event API pending"));
  }

  useEffect(() => {
    refreshApiState();
  }, []);

  return (
    <>
      <ModulePage
        title="Administration"
        eyebrow="Roles, security, integrations, audit evidence"
        description="Configure clinical roles, supplier access, audit settings, data lake telemetry, and technology analyst workflow controls."
        actions={[
          ["clinical.admin.user.created", "Create User"],
          ["clinical.admin.role.updated", "Update Role"],
          ["clinical.admin.vendor_access.updated", "Update Vendor Access"],
          ["clinical.admin.audit.exported", "Export Audit Evidence"]
        ]}
        rows={[
          ["ROLE-INTAKE", "Intake Coordinator", "Active", "Donor intake"],
          ["ROLE-CLINICAL", "Clinical Reviewer", "Active", "Eligibility review"],
          ["ROLE-QA", "QA Specialist", "Active", "Release evidence"],
          ["ROLE-VENDOR", "Vendor Operations", "Active", "Supplier portal"],
          ["ROLE-TECH-ANALYST", "Technology Analyst", "Active", "Data quality/integration"],
          ["INT-DATALAKE", "Azure data lake event stream", status, "raw/apps/clinical/events"]
        ]}
      />

      <Card title="Clinical Data Lake Events">
        <div className="admin-api-panel">
          <div>
            <p className="muted">
              Recent Clinical donor services events written to the Azure data lake through the Clinical App Service managed identity.
            </p>
            <StatusPill tone={status === "Connected" ? "good" : "warning"}>{status}</StatusPill>
          </div>

          <button type="button" onClick={refreshApiState}>Refresh API State</button>
        </div>

        {health && (
          <pre className="json-block">{JSON.stringify(health, null, 2)}</pre>
        )}

        {events.length > 0 ? (
          <div className="event-list">
            {events.slice(0, 8).map((event, index) => (
              <div className="event-row" key={event.event_id || event.blob_name || index}>
                <strong>{event.event_type || "clinical.event"}</strong>
                <span>{event.blob_name || event.aggregate_id || event.event_id}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No Clinical events returned yet.</strong>
            <span>Interact with Intake, Screening, Scheduling, Clinical Review, Quality, Vendor Ops, Reports, or Administration to generate Clinical events.</span>
          </div>
        )}
      </Card>
    </>
  );
}

function ModulePage({ title, eyebrow, description, actions, rows }) {
  return (
    <>
      <section className="module-header-card">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>

        <div className="action-grid">
          {actions.map(([eventType, label]) => (
            <ActionButton key={eventType} eventType={eventType} payload={{ module: title, label }}>
              {label}
            </ActionButton>
          ))}
        </div>
      </section>

      <Card title={`${title} Worklist`}>
        <DataTable rows={rows} />
      </Card>
    </>
  );
}

function Card({ title, children }) {
  return (
    <section className="card">
      <div className="card-title">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function App() {
  const [path, setPath] = useState(getCurrentPath());
  const key = useMemo(() => pageKey(path), [path]);

  useEffect(() => {
    function onPopState() {
      setPath(getCurrentPath());
    }

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    emitClinicalUiEvent("clinical.page.viewed", {
      path,
      page: key,
      aggregateType: "page"
    });

    document.title = key === "dashboard" ? "Meridian Clinical | teemails" : `Meridian Clinical | ${key}`;
  }, [path, key]);

  function navigate(nextPath) {
    window.history.pushState({}, "", nextPath);
    setPath(getCurrentPath());

    emitClinicalUiEvent("clinical.app.nav_clicked", {
      path: nextPath,
      page: pageKey(nextPath)
    });
  }

  let content = <DashboardPage />;

  if (key === "intake") content = <IntakePage />;
  if (key === "screening") content = <ScreeningPage />;
  if (key === "scheduling") content = <SchedulingPage />;
  if (key === "review") content = <ClinicalReviewPage />;
  if (key === "quality") content = <QualityPage />;
  if (key === "vendor-ops") content = <VendorOpsPage />;
  if (key === "reports") content = <ReportsPage />;
  if (key === "administration") content = <AdministrationPage />;

  return (
    <>
      <PortfolioRibbon />

      <div className="clinical-shell">
        <aside className="clinical-sidebar">
          <div className="clinical-product">
            <span className="clinical-product-mark">C</span>
            <div>
              <strong>Meridian Clinical</strong>
              <small>Donor Services</small>
            </div>
          </div>

          <nav className="clinical-nav" aria-label="Clinical navigation">
            {appNavItems.map((item) => (
              <button
                key={item.path}
                type="button"
                className={path === item.path || (item.path !== "/Clinical/" && path.startsWith(item.path)) ? "active" : ""}
                onClick={() => navigate(item.path)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="sidebar-footer">
            <span>Environment</span>
            <strong>Portfolio Dev</strong>
            <StatusPill tone="good">Events live</StatusPill>
          </div>
        </aside>

        <main className="clinical-main">
          {content}
        </main>
      </div>
    </>
  );
}

export default App;