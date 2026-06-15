import { HeartPulse, User, UserPlus } from "lucide-react";

import { clinicalPatientId } from "./clinicalRoutes";

export function ClinicalShellPlaceholder({ section, route, navigate, StatusPill, Table }) {
  const patientId = clinicalPatientId(route);
  const moduleRoute = patientId ? "/clinical/patients" : section.route;
  const detailRows = patientId
    ? [
        { field: "Record", value: patientId },
        { field: "Status", value: "Foundation pending" },
        { field: "Commit Guard", value: "X-Confirm-Generation: true" },
      ]
    : [
        { field: "Route", value: moduleRoute },
        { field: "Status", value: section.status },
        { field: "API", value: "/api/clinical" },
      ];

  return (
    <div className="clinical-shell">
      <section className="clinical-hero">
        <div className="clinical-title-block">
          <p className="eyebrow">Clinical platform shell</p>
          <h2>{section.label}</h2>
          <div className="clinical-meta-row">
            <span className="route-chip">{moduleRoute}</span>
            <StatusPill status={section.status} />
          </div>
          <p className="clinical-helper-text">
            Foundation route is visible and navigable while backend-specific dashboard workflow data is pending.
          </p>
        </div>
        <div className="clinical-actions">
          <button type="button" onClick={() => navigate("/clinical/dashboard")}>
            <HeartPulse size={16} />
            Dashboard
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/clinical/patients")}>
            <UserPlus size={16} />
            Patients
          </button>
          {section.id === "clinical_patients" && (
            <button type="button" className="secondary-button" onClick={() => navigate("/clinical/patients/PT-000001")}>
              <User size={16} />
              Sample Detail
            </button>
          )}
        </div>
      </section>
      <div className="split">
        <section>
          <h3>Workflow Readiness</h3>
          <div className="workflow-list">
            {section.workflows.map((workflow) => (
              <div className="workflow-row" key={workflow}>
                <span>{workflow}</span>
                <StatusPill status="Planned workflow" />
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3>Foundation Contract</h3>
          <Table rows={detailRows} columns={["field", "value"]} />
        </section>
      </div>
      {patientId && (
        <section>
          <h3>Patient / Donor Snapshot</h3>
          <Table
            rows={[
              { field: "Demographics", value: "Foundation pending" },
              { field: "Consent", value: "Planned workflow" },
              { field: "Duplicate Review", value: "Planned workflow" },
            ]}
            columns={["field", "value"]}
          />
        </section>
      )}
    </div>
  );
}
