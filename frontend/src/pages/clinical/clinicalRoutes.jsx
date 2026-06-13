import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Database,
  FileCheck2,
  HeartPulse,
  ShieldCheck,
  UploadCloud,
  User,
  UserPlus,
} from "lucide-react";

function normalizeClinicalRoute(route) {
  const withSlash = route?.startsWith("/") ? route : `/${route || ""}`;
  const clean = withSlash.replace(/\/+$/, "");
  return clean || "/";
}

export function clinicalPatientId(route) {
  const match = normalizeClinicalRoute(route).match(/^\/clinical\/patients\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

export const clinicalSections = [
  {
    id: "clinical_dashboard",
    label: "Clinical Dashboard",
    route: "/clinical/dashboard",
    icon: HeartPulse,
    status: "Foundation pending",
    workflows: ["Operational overview", "Workflow operation activity"],
  },
  {
    id: "clinical_patients",
    label: "Patients / Donors",
    route: "/clinical/patients",
    icon: UserPlus,
    status: "Active",
    workflows: ["Create patient/donor", "Edit demographics", "Capture consent"],
  },
  {
    id: "clinical_scheduling",
    label: "Scheduling",
    route: "/clinical/scheduling",
    icon: CalendarDays,
    status: "Active",
    workflows: ["Book appointment", "Reschedule appointment", "Cancel appointment", "Check in appointment", "Mark no-show"],
  },
  {
    id: "clinical_screening",
    label: "Donor Screening",
    route: "/clinical/screening",
    icon: CheckCircle2,
    status: "Active",
    workflows: ["Start screening", "Commit questionnaire", "Capture vitals", "Preview eligibility", "Commit result", "Supervisor override"],
  },
  {
    id: "clinical_encounters",
    label: "Encounters",
    route: "/clinical/encounters",
    icon: FileCheck2,
    status: "Active",
    workflows: ["Create encounter", "Save draft note", "Sign and lock note", "Amend signed note", "Add diagnosis/problem", "Add allergy", "Add medication"],
  },
  {
    id: "clinical_orders",
    label: "Orders / Results",
    route: "/clinical/orders",
    icon: UploadCloud,
    status: "Active",
    workflows: ["Create order", "Receive result", "Correct result", "Acknowledge critical result", "Cancel order"],
  },
  {
    id: "clinical_care_plans",
    label: "Care Plans",
    route: "/clinical/care-plans",
    icon: Activity,
    status: "Active",
    workflows: ["Create care plan", "Add goal", "Add intervention", "Add task", "Update progress", "Close care plan"],
  },
  {
    id: "clinical_billing",
    label: "Billing",
    route: "/clinical/billing",
    icon: Database,
    status: "Active",
    workflows: ["Verify insurance", "Capture charge", "Create claim draft", "Post payment", "Capture denial"],
  },
  {
    id: "clinical_quality",
    label: "Quality",
    route: "/clinical/quality",
    icon: AlertTriangle,
    status: "Active",
    workflows: ["Create quality event", "Create adverse event", "Add investigation", "Link CAPA", "Close quality event", "Export audit evidence"],
  },
  {
    id: "clinical_reports",
    label: "Reports",
    route: "/clinical/reports",
    icon: BarChart3,
    status: "Active",
    workflows: [
      "Dashboard aggregates",
      "Patient throughput",
      "Scheduling utilization",
      "Screening outcomes",
      "Deferral trends",
      "Encounter volume",
      "Orders and results",
      "Care plan aging",
      "Billing work queue",
      "Quality trends",
      "Audit activity",
      "Analytics export preview",
      "Analytics export commit",
    ],
  },
  {
    id: "clinical_admin",
    label: "Clinical Admin",
    route: "/clinical/admin",
    icon: ShieldCheck,
    status: "Active",
    workflows: [
      "Manage appointment types",
      "Manage provider schedule templates",
      "Version screening templates and rules",
      "Manage note templates and order catalog",
      "Manage billing codes and quality categories",
      "Manage approval paths and notification templates",
      "Review RBAC overview",
    ],
  },
];

export const clinicalPatientDetailSection = {
  id: "clinical_patient_detail",
  label: "Patient / Donor Detail",
  route: "/clinical/patients/:id",
  icon: User,
  status: "Foundation pending",
  workflows: ["Profile review", "Consent timeline", "Workflow audit"],
};
