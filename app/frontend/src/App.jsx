import React, { useEffect, useMemo, useState } from "react";
import {
  CLINICAL_USER_ID,
  getClinicalHealth,
  getClinicalRecentEvents,
  sendClinicalEvent
} from "./api";
import "./styles.css";

const portfolioNavItems = [
  {
    "label": "Home",
    "href": "https://teemails.com/"
  },
  {
    "label": "ERP",
    "href": "https://teemails.com/ERP"
  },
  {
    "label": "HR",
    "href": "https://teemails.com/HR"
  },
  {
    "label": "Clinical",
    "href": "https://teemails.com/Clinical"
  },
  {
    "label": "Monitor",
    "href": "https://teemails.com/Monitor"
  },
  {
    "label": "Analytics",
    "href": "https://teemails.com/Analytics"
  },
  {
    "label": "About-me",
    "href": "https://teemails.com/about-me"
  }
];
const appNavItems = [
  {
    "label": "Command Center",
    "path": "/Clinical/",
    "key": "dashboard"
  },
  {
    "label": "Intake",
    "path": "/Clinical/intake",
    "key": "intake"
  },
  {
    "label": "Screening",
    "path": "/Clinical/screening",
    "key": "screening"
  },
  {
    "label": "Scheduling",
    "path": "/Clinical/scheduling",
    "key": "scheduling"
  },
  {
    "label": "Clinical Review",
    "path": "/Clinical/review",
    "key": "review"
  },
  {
    "label": "Quality",
    "path": "/Clinical/quality",
    "key": "quality"
  },
  {
    "label": "Vendor Ops",
    "path": "/Clinical/vendor-ops",
    "key": "vendorOps"
  },
  {
    "label": "Reports",
    "path": "/Clinical/reports",
    "key": "reports"
  },
  {
    "label": "Administration",
    "path": "/Clinical/administration",
    "key": "administration"
  }
];
const moduleConfigs = {
  "dashboard": {
    "eyebrow": "Meridian Clinical",
    "title": "Donor services command center.",
    "description": "Manage donor intake, screening, scheduling, clinical review, QA release evidence, vendor operations, and analytics readiness in an Evergen-aligned workflow.",
    "panelTitle": "Operating model",
    "panelText": "Donor Services \u00b7 Quality Workflow \u00b7 Technology Analyst View",
    "panelStatus": "Clinical rebuild active",
    "primaryTable": "screening",
    "secondaryTable": "quality",
    "workbenchTitle": "Eligibility Workbench",
    "rolesTitle": "Evergen-Aligned Roles"
  },
  "intake": {
    "title": "Intake",
    "eyebrow": "Referral registration, demographics, consent",
    "description": "Capture donor referral packets, demographics, contact details, consent state, intake notes, and case readiness.",
    "idPrefix": "DON",
    "owner": "Intake Coordinator",
    "rows": [
      {
        "id": "DON-10481",
        "description": "New referral packet",
        "status": "Intake Review",
        "owner": "Intake Coordinator"
      },
      {
        "id": "DON-10482",
        "description": "Consent verification",
        "status": "Needs Outreach",
        "owner": "Intake Coordinator"
      },
      {
        "id": "DON-10483",
        "description": "Demographics update",
        "status": "Ready",
        "owner": "Technology Analyst"
      },
      {
        "id": "DON-10484",
        "description": "Insurance/contact validation",
        "status": "In Progress",
        "owner": "Intake Coordinator"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.donor_intake.created",
        "label": "Create Donor Intake",
        "idPrefix": "DON",
        "rowDescription": "Donor intake case",
        "rowStatus": "Created",
        "owner": "Intake Coordinator",
        "fields": [
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-AUTO",
            "required": true
          },
          {
            "name": "referralSource",
            "label": "Referral Source",
            "type": "text",
            "default": "Partner referral",
            "required": true
          },
          {
            "name": "donorDisplayName",
            "label": "Demo Donor Label",
            "type": "text",
            "default": "Demo Donor",
            "required": true
          },
          {
            "name": "contactStatus",
            "label": "Contact Status",
            "type": "select",
            "default": "Contacted",
            "required": true,
            "options": [
              "New",
              "Contacted",
              "Needs Outreach"
            ]
          },
          {
            "name": "consentStatus",
            "label": "Consent Status",
            "type": "select",
            "default": "Pending",
            "required": true,
            "options": [
              "Pending",
              "Verified",
              "Declined"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "Intake Review",
              "Ready"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.consent.verified",
        "label": "Verify Consent",
        "idPrefix": "CONS",
        "rowDescription": "Consent verification",
        "rowStatus": "Verified",
        "owner": "Intake Coordinator",
        "fields": [
          {
            "name": "consentId",
            "label": "Consent ID",
            "type": "text",
            "default": "CONS-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10482",
            "required": true
          },
          {
            "name": "consentType",
            "label": "Consent Type",
            "type": "select",
            "default": "Donor services consent",
            "required": true,
            "options": [
              "Donor services consent",
              "Screening consent",
              "Vendor release"
            ]
          },
          {
            "name": "verifiedBy",
            "label": "Verified By",
            "type": "text",
            "default": "Intake Coordinator",
            "required": true
          },
          {
            "name": "verificationStatus",
            "label": "Verification Status",
            "type": "select",
            "default": "Verified",
            "required": true,
            "options": [
              "Verified",
              "Needs Outreach",
              "Declined"
            ]
          },
          {
            "name": "notes",
            "label": "Notes",
            "type": "textarea",
            "default": "Consent verified in demo workflow",
            "required": true
          }
        ]
      },
      {
        "eventType": "clinical.demographics.updated",
        "label": "Update Demographics",
        "idPrefix": "DEM",
        "rowDescription": "Demographic update",
        "rowStatus": "Updated",
        "owner": "Technology Analyst",
        "fields": [
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10483",
            "required": true
          },
          {
            "name": "ageBand",
            "label": "Age Band",
            "type": "select",
            "default": "35-44",
            "required": true,
            "options": [
              "18-24",
              "25-34",
              "35-44",
              "45-54",
              "55+"
            ]
          },
          {
            "name": "region",
            "label": "Region",
            "type": "text",
            "default": "Southeast",
            "required": true
          },
          {
            "name": "contactPreference",
            "label": "Contact Preference",
            "type": "select",
            "default": "Phone",
            "required": true,
            "options": [
              "Phone",
              "Email",
              "Portal"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Updated",
            "required": true,
            "options": [
              "Updated",
              "Ready",
              "Needs Review"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.intake.packet.completed",
        "label": "Complete Intake Packet",
        "idPrefix": "PKT",
        "rowDescription": "Intake packet completion",
        "rowStatus": "Completed",
        "owner": "Intake Coordinator",
        "fields": [
          {
            "name": "packetId",
            "label": "Packet ID",
            "type": "text",
            "default": "PKT-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "checklistStatus",
            "label": "Checklist Status",
            "type": "select",
            "default": "Complete",
            "required": true,
            "options": [
              "Complete",
              "Missing Items",
              "Needs Review"
            ]
          },
          {
            "name": "missingItems",
            "label": "Missing Items",
            "type": "textarea",
            "default": "",
            "required": false
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Completed",
            "required": true,
            "options": [
              "Completed",
              "Ready",
              "Needs Review"
            ]
          }
        ]
      }
    ]
  },
  "screening": {
    "title": "Screening",
    "eyebrow": "Eligibility, medical history, deferrals",
    "description": "Review eligibility criteria, deferral rules, infectious disease readiness, and evidence gaps.",
    "idPrefix": "SCR",
    "owner": "Clinical Reviewer",
    "rows": [
      {
        "id": "SCR-77811",
        "description": "Medical history questionnaire",
        "status": "Clinical Review",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "SCR-77812",
        "description": "Eligibility criteria check",
        "status": "Exception",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "SCR-77813",
        "description": "Infectious disease readiness",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "SCR-77814",
        "description": "Deferral rule review",
        "status": "Needs Evidence",
        "owner": "Clinical Reviewer"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.screening.started",
        "label": "Start Screening",
        "idPrefix": "SCR",
        "rowDescription": "Screening workflow",
        "rowStatus": "Started",
        "owner": "Clinical Reviewer",
        "fields": [
          {
            "name": "screeningId",
            "label": "Screening ID",
            "type": "text",
            "default": "SCR-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "screener",
            "label": "Screener",
            "type": "text",
            "default": "Clinical Reviewer",
            "required": true
          },
          {
            "name": "screeningType",
            "label": "Screening Type",
            "type": "select",
            "default": "Initial",
            "required": true,
            "options": [
              "Initial",
              "Follow-up",
              "Exception Review"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Started",
            "required": true,
            "options": [
              "Started",
              "Clinical Review",
              "Ready"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.eligibility.checked",
        "label": "Run Eligibility Check",
        "idPrefix": "ELG",
        "rowDescription": "Eligibility check",
        "rowStatus": "Checked",
        "owner": "Clinical Reviewer",
        "fields": [
          {
            "name": "eligibilityId",
            "label": "Eligibility ID",
            "type": "text",
            "default": "ELG-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "criteriaSet",
            "label": "Criteria Set",
            "type": "text",
            "default": "Evergen donor services demo",
            "required": true
          },
          {
            "name": "outcome",
            "label": "Outcome",
            "type": "select",
            "default": "Eligible",
            "required": true,
            "options": [
              "Eligible",
              "Needs Evidence",
              "Deferred",
              "Exception"
            ]
          },
          {
            "name": "evidenceStatus",
            "label": "Evidence Status",
            "type": "select",
            "default": "Ready",
            "required": true,
            "options": [
              "Ready",
              "Needs Evidence",
              "Exception"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.deferral.flagged",
        "label": "Flag Deferral",
        "idPrefix": "DEF",
        "rowDescription": "Deferral flag",
        "rowStatus": "Flagged",
        "owner": "Clinical Reviewer",
        "fields": [
          {
            "name": "deferralId",
            "label": "Deferral ID",
            "type": "text",
            "default": "DEF-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10482",
            "required": true
          },
          {
            "name": "deferralReason",
            "label": "Deferral Reason",
            "type": "text",
            "default": "Eligibility exception",
            "required": true
          },
          {
            "name": "severity",
            "label": "Severity",
            "type": "select",
            "default": "Moderate",
            "required": true,
            "options": [
              "Low",
              "Moderate",
              "High"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Flagged",
            "required": true,
            "options": [
              "Flagged",
              "Needs Evidence",
              "Resolved"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.evidence.requested",
        "label": "Request Evidence",
        "idPrefix": "EVD",
        "rowDescription": "Evidence request",
        "rowStatus": "Requested",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "evidenceId",
            "label": "Evidence ID",
            "type": "text",
            "default": "EVD-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10484",
            "required": true
          },
          {
            "name": "evidenceType",
            "label": "Evidence Type",
            "type": "select",
            "default": "Clinical documentation",
            "required": true,
            "options": [
              "Clinical documentation",
              "Consent",
              "Vendor document",
              "QA evidence"
            ]
          },
          {
            "name": "requestedFrom",
            "label": "Requested From",
            "type": "text",
            "default": "Vendor Operations",
            "required": true
          },
          {
            "name": "dueDate",
            "label": "Due Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Requested",
            "required": true,
            "options": [
              "Requested",
              "Received",
              "Overdue"
            ]
          }
        ]
      }
    ]
  },
  "scheduling": {
    "title": "Scheduling",
    "eyebrow": "Appointments, review slots, vendor windows",
    "description": "Coordinate donor appointments, provider reviews, vendor windows, and follow-up tasks.",
    "idPrefix": "APT",
    "owner": "Scheduling",
    "rows": [
      {
        "id": "APT-55021",
        "description": "Donor screening appointment",
        "status": "Confirmed",
        "owner": "Scheduling"
      },
      {
        "id": "APT-55022",
        "description": "Provider review slot",
        "status": "Pending",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "APT-55023",
        "description": "Vendor collection window",
        "status": "At Risk",
        "owner": "Vendor Operations"
      },
      {
        "id": "APT-55024",
        "description": "Follow-up review",
        "status": "Scheduled",
        "owner": "Operations Manager"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.appointment.scheduled",
        "label": "Schedule Appointment",
        "idPrefix": "APT",
        "rowDescription": "Donor appointment",
        "rowStatus": "Scheduled",
        "owner": "Scheduling",
        "fields": [
          {
            "name": "appointmentId",
            "label": "Appointment ID",
            "type": "text",
            "default": "APT-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "appointmentType",
            "label": "Appointment Type",
            "type": "select",
            "default": "Screening",
            "required": true,
            "options": [
              "Screening",
              "Provider Review",
              "Follow-up"
            ]
          },
          {
            "name": "appointmentDate",
            "label": "Appointment Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "provider",
            "label": "Provider",
            "type": "text",
            "default": "Clinical Reviewer",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Scheduled",
            "required": true,
            "options": [
              "Scheduled",
              "Confirmed",
              "Cancelled"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.appointment.rescheduled",
        "label": "Reschedule",
        "idPrefix": "APT",
        "rowDescription": "Appointment reschedule",
        "rowStatus": "Rescheduled",
        "owner": "Scheduling",
        "fields": [
          {
            "name": "appointmentId",
            "label": "Appointment ID",
            "type": "text",
            "default": "APT-55021",
            "required": true
          },
          {
            "name": "newDate",
            "label": "New Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "reason",
            "label": "Reason",
            "type": "textarea",
            "default": "Donor requested reschedule",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Rescheduled",
            "required": true,
            "options": [
              "Rescheduled",
              "Confirmed",
              "Cancelled"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.vendor_window.confirmed",
        "label": "Confirm Vendor Window",
        "idPrefix": "VEN",
        "rowDescription": "Vendor collection window",
        "rowStatus": "Confirmed",
        "owner": "Vendor Operations",
        "fields": [
          {
            "name": "vendorWindowId",
            "label": "Vendor Window ID",
            "type": "text",
            "default": "VEN-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "windowDate",
            "label": "Window Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "site",
            "label": "Site",
            "type": "text",
            "default": "Partner collection site",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Confirmed",
            "required": true,
            "options": [
              "Pending",
              "Confirmed",
              "At Risk"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.followup.created",
        "label": "Create Follow-up",
        "idPrefix": "FUP",
        "rowDescription": "Follow-up task",
        "rowStatus": "Created",
        "owner": "Operations Manager",
        "fields": [
          {
            "name": "followUpId",
            "label": "Follow-up ID",
            "type": "text",
            "default": "FUP-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "assignedTo",
            "label": "Assigned To",
            "type": "text",
            "default": "Operations Manager",
            "required": true
          },
          {
            "name": "dueDate",
            "label": "Due Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "reason",
            "label": "Reason",
            "type": "textarea",
            "default": "Follow-up review required",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "Scheduled",
              "Completed"
            ]
          }
        ]
      }
    ]
  },
  "review": {
    "title": "Clinical Review",
    "eyebrow": "Disposition, notes, lab readiness",
    "description": "Support clinical eligibility disposition, lab readiness, clinical notes, escalations, and signoff evidence.",
    "idPrefix": "REV",
    "owner": "Clinical Reviewer",
    "rows": [
      {
        "id": "REV-30210",
        "description": "Eligibility disposition",
        "status": "Pending Signoff",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "REV-30211",
        "description": "Clinical notes review",
        "status": "In Progress",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "REV-30212",
        "description": "Lab readiness evidence",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "REV-30213",
        "description": "Escalated case review",
        "status": "Urgent",
        "owner": "Operations Manager"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.review.opened",
        "label": "Open Review",
        "idPrefix": "REV",
        "rowDescription": "Clinical review opened",
        "rowStatus": "Opened",
        "owner": "Clinical Reviewer",
        "fields": [
          {
            "name": "reviewId",
            "label": "Review ID",
            "type": "text",
            "default": "REV-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "reviewer",
            "label": "Reviewer",
            "type": "text",
            "default": "Clinical Reviewer",
            "required": true
          },
          {
            "name": "priority",
            "label": "Priority",
            "type": "select",
            "default": "Standard",
            "required": true,
            "options": [
              "Standard",
              "Urgent",
              "Escalated"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Opened",
            "required": true,
            "options": [
              "Opened",
              "In Progress",
              "Pending Signoff"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.disposition.recorded",
        "label": "Record Disposition",
        "idPrefix": "DSP",
        "rowDescription": "Eligibility disposition",
        "rowStatus": "Recorded",
        "owner": "Clinical Reviewer",
        "fields": [
          {
            "name": "dispositionId",
            "label": "Disposition ID",
            "type": "text",
            "default": "DSP-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "disposition",
            "label": "Disposition",
            "type": "select",
            "default": "Eligible",
            "required": true,
            "options": [
              "Eligible",
              "Deferred",
              "Needs Evidence",
              "Escalated"
            ]
          },
          {
            "name": "reviewer",
            "label": "Reviewer",
            "type": "text",
            "default": "Clinical Reviewer",
            "required": true
          },
          {
            "name": "notes",
            "label": "Notes",
            "type": "textarea",
            "default": "Disposition recorded in demo workflow",
            "required": true
          }
        ]
      },
      {
        "eventType": "clinical.lab_readiness.confirmed",
        "label": "Confirm Lab Readiness",
        "idPrefix": "LAB",
        "rowDescription": "Lab readiness confirmation",
        "rowStatus": "Confirmed",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "labReadinessId",
            "label": "Lab Readiness ID",
            "type": "text",
            "default": "LAB-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "labPanel",
            "label": "Lab Panel",
            "type": "text",
            "default": "Donor services readiness panel",
            "required": true
          },
          {
            "name": "readinessStatus",
            "label": "Readiness Status",
            "type": "select",
            "default": "Confirmed",
            "required": true,
            "options": [
              "Confirmed",
              "Needs Evidence",
              "Exception"
            ]
          },
          {
            "name": "reviewedBy",
            "label": "Reviewed By",
            "type": "text",
            "default": "QA Specialist",
            "required": true
          }
        ]
      },
      {
        "eventType": "clinical.case.escalated",
        "label": "Escalate Case",
        "idPrefix": "ESC",
        "rowDescription": "Escalated clinical case",
        "rowStatus": "Escalated",
        "owner": "Operations Manager",
        "fields": [
          {
            "name": "escalationId",
            "label": "Escalation ID",
            "type": "text",
            "default": "ESC-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10482",
            "required": true
          },
          {
            "name": "reason",
            "label": "Reason",
            "type": "textarea",
            "default": "Eligibility review requires escalation",
            "required": true
          },
          {
            "name": "severity",
            "label": "Severity",
            "type": "select",
            "default": "High",
            "required": true,
            "options": [
              "Moderate",
              "High",
              "Critical"
            ]
          },
          {
            "name": "assignedTo",
            "label": "Assigned To",
            "type": "text",
            "default": "Operations Manager",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Escalated",
            "required": true,
            "options": [
              "Escalated",
              "In Review",
              "Resolved"
            ]
          }
        ]
      }
    ]
  },
  "quality": {
    "title": "Quality",
    "eyebrow": "QA audit, deviations, CAPA, release evidence",
    "description": "Manage QA release readiness, documentation audits, deviations, CAPA follow-up, and compliance sampling.",
    "idPrefix": "QA",
    "owner": "QA Specialist",
    "rows": [
      {
        "id": "QA-8011",
        "description": "Release evidence audit",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "QA-8012",
        "description": "Deviation review",
        "status": "CAPA Open",
        "owner": "QA Specialist"
      },
      {
        "id": "QA-8013",
        "description": "Document completeness",
        "status": "Pass",
        "owner": "Technology Analyst"
      },
      {
        "id": "QA-8014",
        "description": "Compliance sampling",
        "status": "Scheduled",
        "owner": "QA Specialist"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.qa.audit.started",
        "label": "Start QA Audit",
        "idPrefix": "QA",
        "rowDescription": "QA audit",
        "rowStatus": "Started",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "auditId",
            "label": "Audit ID",
            "type": "text",
            "default": "QA-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "auditScope",
            "label": "Audit Scope",
            "type": "select",
            "default": "Release evidence",
            "required": true,
            "options": [
              "Release evidence",
              "Documentation",
              "Deviation",
              "Compliance sample"
            ]
          },
          {
            "name": "auditor",
            "label": "Auditor",
            "type": "text",
            "default": "QA Specialist",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Started",
            "required": true,
            "options": [
              "Started",
              "In Progress",
              "Ready"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.deviation.created",
        "label": "Create Deviation",
        "idPrefix": "DEV",
        "rowDescription": "Deviation record",
        "rowStatus": "Created",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "deviationId",
            "label": "Deviation ID",
            "type": "text",
            "default": "DEV-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10482",
            "required": true
          },
          {
            "name": "deviationType",
            "label": "Deviation Type",
            "type": "select",
            "default": "Documentation",
            "required": true,
            "options": [
              "Documentation",
              "Process",
              "Vendor",
              "Clinical"
            ]
          },
          {
            "name": "severity",
            "label": "Severity",
            "type": "select",
            "default": "Moderate",
            "required": true,
            "options": [
              "Low",
              "Moderate",
              "High"
            ]
          },
          {
            "name": "description",
            "label": "Description",
            "type": "textarea",
            "default": "Deviation recorded for QA review",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "CAPA Open",
              "Closed"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.capa.updated",
        "label": "Update CAPA",
        "idPrefix": "CAPA",
        "rowDescription": "CAPA update",
        "rowStatus": "Updated",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "capaId",
            "label": "CAPA ID",
            "type": "text",
            "default": "CAPA-AUTO",
            "required": true
          },
          {
            "name": "owner",
            "label": "Owner",
            "type": "text",
            "default": "QA Specialist",
            "required": true
          },
          {
            "name": "actionPlan",
            "label": "Action Plan",
            "type": "textarea",
            "default": "Corrective action plan updated",
            "required": true
          },
          {
            "name": "dueDate",
            "label": "Due Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Updated",
            "required": true,
            "options": [
              "Updated",
              "In Progress",
              "Closed"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.release_evidence.approved",
        "label": "Approve Release Evidence",
        "idPrefix": "REL",
        "rowDescription": "Release evidence approval",
        "rowStatus": "Approved",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "releaseId",
            "label": "Release ID",
            "type": "text",
            "default": "REL-AUTO",
            "required": true
          },
          {
            "name": "donorCaseId",
            "label": "Donor Case ID",
            "type": "text",
            "default": "DON-10481",
            "required": true
          },
          {
            "name": "evidencePackage",
            "label": "Evidence Package",
            "type": "text",
            "default": "Release evidence packet",
            "required": true
          },
          {
            "name": "approver",
            "label": "Approver",
            "type": "text",
            "default": "QA Specialist",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Approved",
            "required": true,
            "options": [
              "Approved",
              "Needs Review",
              "Rejected"
            ]
          }
        ]
      }
    ]
  },
  "vendorOps": {
    "title": "Vendor Operations",
    "eyebrow": "Supplier portal, SLA, partner coordination",
    "description": "Coordinate partner document requests, SLA exceptions, collection confirmations, and supplier portal readiness.",
    "idPrefix": "VEN",
    "owner": "Vendor Operations",
    "rows": [
      {
        "id": "VEN-2001",
        "description": "Partner document request",
        "status": "Pending Vendor",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2002",
        "description": "Supplier SLA exception",
        "status": "Escalated",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2003",
        "description": "Collection confirmation",
        "status": "Confirmed",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2004",
        "description": "Portal access review",
        "status": "Needs Admin",
        "owner": "System Administrator"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.vendor.document_requested",
        "label": "Request Vendor Document",
        "idPrefix": "VEN",
        "rowDescription": "Vendor document request",
        "rowStatus": "Requested",
        "owner": "Vendor Operations",
        "fields": [
          {
            "name": "requestId",
            "label": "Request ID",
            "type": "text",
            "default": "VEN-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "documentType",
            "label": "Document Type",
            "type": "select",
            "default": "Clinical evidence",
            "required": true,
            "options": [
              "Clinical evidence",
              "Collection confirmation",
              "SLA evidence",
              "Portal access evidence"
            ]
          },
          {
            "name": "dueDate",
            "label": "Due Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Requested",
            "required": true,
            "options": [
              "Requested",
              "Pending Vendor",
              "Received"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.vendor.sla_exception.created",
        "label": "Create SLA Exception",
        "idPrefix": "SLA",
        "rowDescription": "Vendor SLA exception",
        "rowStatus": "Created",
        "owner": "Vendor Operations",
        "fields": [
          {
            "name": "exceptionId",
            "label": "Exception ID",
            "type": "text",
            "default": "SLA-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "exceptionType",
            "label": "Exception Type",
            "type": "select",
            "default": "Late response",
            "required": true,
            "options": [
              "Late response",
              "Missing document",
              "Collection delay"
            ]
          },
          {
            "name": "impact",
            "label": "Impact",
            "type": "select",
            "default": "Moderate",
            "required": true,
            "options": [
              "Low",
              "Moderate",
              "High"
            ]
          },
          {
            "name": "owner",
            "label": "Owner",
            "type": "text",
            "default": "Vendor Operations",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "Escalated",
              "Resolved"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.collection.confirmed",
        "label": "Confirm Collection",
        "idPrefix": "COL",
        "rowDescription": "Collection confirmation",
        "rowStatus": "Confirmed",
        "owner": "Vendor Operations",
        "fields": [
          {
            "name": "collectionId",
            "label": "Collection ID",
            "type": "text",
            "default": "COL-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "collectionDate",
            "label": "Collection Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "site",
            "label": "Site",
            "type": "text",
            "default": "Partner collection site",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Confirmed",
            "required": true,
            "options": [
              "Confirmed",
              "At Risk",
              "Cancelled"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.vendor_portal.access_reviewed",
        "label": "Review Portal Access",
        "idPrefix": "PORT",
        "rowDescription": "Vendor portal access review",
        "rowStatus": "Reviewed",
        "owner": "System Administrator",
        "fields": [
          {
            "name": "accessReviewId",
            "label": "Access Review ID",
            "type": "text",
            "default": "PORT-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "userGroup",
            "label": "User Group",
            "type": "text",
            "default": "Vendor Operations",
            "required": true
          },
          {
            "name": "reviewOutcome",
            "label": "Review Outcome",
            "type": "select",
            "default": "Approved",
            "required": true,
            "options": [
              "Approved",
              "Revoked",
              "Needs Admin"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Reviewed",
            "required": true,
            "options": [
              "Reviewed",
              "Needs Admin",
              "Updated"
            ]
          }
        ]
      }
    ]
  },
  "reports": {
    "title": "Reports",
    "eyebrow": "Clinical analytics readiness",
    "description": "Prepare donor services analytics for cycle time, eligibility outcomes, QA readiness, and vendor SLA.",
    "idPrefix": "RPT",
    "owner": "Technology Analyst",
    "rows": [
      {
        "id": "RPT-CLIN-001",
        "description": "Donor services executive summary",
        "status": "Ready",
        "owner": "Power BI"
      },
      {
        "id": "RPT-CLIN-002",
        "description": "Eligibility outcomes",
        "status": "Ready",
        "owner": "Snowflake"
      },
      {
        "id": "RPT-QA-003",
        "description": "QA release readiness",
        "status": "Draft",
        "owner": "Power BI"
      },
      {
        "id": "RPT-VEN-004",
        "description": "Vendor SLA exceptions",
        "status": "Draft",
        "owner": "Snowflake"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.report.run",
        "label": "Run Report",
        "idPrefix": "RPT",
        "rowDescription": "Clinical report run",
        "rowStatus": "Run",
        "owner": "Technology Analyst",
        "fields": [
          {
            "name": "reportId",
            "label": "Report ID",
            "type": "text",
            "default": "RPT-AUTO",
            "required": true
          },
          {
            "name": "reportName",
            "label": "Report Name",
            "type": "text",
            "default": "Donor services executive summary",
            "required": true
          },
          {
            "name": "dateRange",
            "label": "Date Range",
            "type": "text",
            "default": "June 2026",
            "required": true
          },
          {
            "name": "audience",
            "label": "Audience",
            "type": "select",
            "default": "Operations Manager",
            "required": true,
            "options": [
              "Operations Manager",
              "QA Specialist",
              "Technology Analyst",
              "Executive"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Run",
            "required": true,
            "options": [
              "Run",
              "Ready",
              "Failed"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.report.exported",
        "label": "Export Report",
        "idPrefix": "EXP",
        "rowDescription": "Clinical report export",
        "rowStatus": "Exported",
        "owner": "Technology Analyst",
        "fields": [
          {
            "name": "exportId",
            "label": "Export ID",
            "type": "text",
            "default": "EXP-AUTO",
            "required": true
          },
          {
            "name": "reportName",
            "label": "Report Name",
            "type": "text",
            "default": "Eligibility outcomes",
            "required": true
          },
          {
            "name": "format",
            "label": "Format",
            "type": "select",
            "default": "CSV",
            "required": true,
            "options": [
              "CSV",
              "XLSX",
              "PDF"
            ]
          },
          {
            "name": "destination",
            "label": "Destination",
            "type": "text",
            "default": "SharePoint Clinical Reports",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Exported",
            "required": true,
            "options": [
              "Exported",
              "Failed"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.analytics.snapshot.created",
        "label": "Create Snapshot",
        "idPrefix": "SNAP",
        "rowDescription": "Clinical analytics snapshot",
        "rowStatus": "Created",
        "owner": "Data Engineering",
        "fields": [
          {
            "name": "snapshotId",
            "label": "Snapshot ID",
            "type": "text",
            "default": "SNAP-AUTO",
            "required": true
          },
          {
            "name": "subjectArea",
            "label": "Subject Area",
            "type": "select",
            "default": "Eligibility",
            "required": true,
            "options": [
              "Eligibility",
              "Quality",
              "Vendor SLA",
              "Operations"
            ]
          },
          {
            "name": "asOfDate",
            "label": "As Of Date",
            "type": "date",
            "default": "",
            "required": true
          },
          {
            "name": "warehouse",
            "label": "Target Warehouse",
            "type": "text",
            "default": "Snowflake MARTS_DEV",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "Published"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.quality_dashboard.refreshed",
        "label": "Refresh Quality Dashboard",
        "idPrefix": "DASH",
        "rowDescription": "Quality dashboard refresh",
        "rowStatus": "Refreshed",
        "owner": "Technology Analyst",
        "fields": [
          {
            "name": "dashboardId",
            "label": "Dashboard ID",
            "type": "text",
            "default": "DASH-AUTO",
            "required": true
          },
          {
            "name": "dashboardName",
            "label": "Dashboard Name",
            "type": "text",
            "default": "QA release readiness",
            "required": true
          },
          {
            "name": "refreshReason",
            "label": "Refresh Reason",
            "type": "textarea",
            "default": "Post-action quality dashboard refresh",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Refreshed",
            "required": true,
            "options": [
              "Refreshed",
              "Failed"
            ]
          }
        ]
      }
    ]
  },
  "administration": {
    "title": "Administration",
    "eyebrow": "Roles, security, integrations, audit evidence",
    "description": "Configure clinical roles, supplier access, audit settings, data lake telemetry, and technology analyst controls.",
    "idPrefix": "ADM",
    "owner": "System Administrator",
    "rows": [
      {
        "id": "ROLE-INTAKE",
        "description": "Intake Coordinator",
        "status": "Active",
        "owner": "Donor intake"
      },
      {
        "id": "ROLE-CLINICAL",
        "description": "Clinical Reviewer",
        "status": "Active",
        "owner": "Eligibility review"
      },
      {
        "id": "ROLE-QA",
        "description": "QA Specialist",
        "status": "Active",
        "owner": "Release evidence"
      },
      {
        "id": "ROLE-VENDOR",
        "description": "Vendor Operations",
        "status": "Active",
        "owner": "Supplier portal"
      },
      {
        "id": "ROLE-TECH-ANALYST",
        "description": "Technology Analyst",
        "status": "Active",
        "owner": "Data quality/integration"
      },
      {
        "id": "INT-DATALAKE",
        "description": "Azure data lake event stream",
        "status": "Connected",
        "owner": "raw/apps/clinical/events"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.admin.user.created",
        "label": "Create User",
        "idPrefix": "USR",
        "rowDescription": "Clinical user account",
        "rowStatus": "Created",
        "owner": "System Administrator",
        "fields": [
          {
            "name": "userId",
            "label": "User ID",
            "type": "text",
            "default": "USR-AUTO",
            "required": true
          },
          {
            "name": "fullName",
            "label": "Full Name",
            "type": "text",
            "default": "Technology Analyst",
            "required": true
          },
          {
            "name": "email",
            "label": "Email",
            "type": "email",
            "default": "tech.analyst@meridian.example",
            "required": true
          },
          {
            "name": "role",
            "label": "Role",
            "type": "select",
            "default": "Technology Analyst",
            "required": true,
            "options": [
              "Intake Coordinator",
              "Clinical Reviewer",
              "QA Specialist",
              "Vendor Operations",
              "Operations Manager",
              "Technology Analyst",
              "System Administrator"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Created",
            "required": true,
            "options": [
              "Created",
              "Active",
              "Disabled"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.admin.role.updated",
        "label": "Update Role",
        "idPrefix": "ROLE",
        "rowDescription": "Clinical role update",
        "rowStatus": "Updated",
        "owner": "System Administrator",
        "fields": [
          {
            "name": "roleId",
            "label": "Role ID",
            "type": "text",
            "default": "ROLE-TECH-ANALYST",
            "required": true
          },
          {
            "name": "roleName",
            "label": "Role Name",
            "type": "text",
            "default": "Technology Analyst",
            "required": true
          },
          {
            "name": "permissions",
            "label": "Permissions",
            "type": "textarea",
            "default": "workflow.configure, data.quality, analytics.readiness, audit.export",
            "required": true
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Updated",
            "required": true,
            "options": [
              "Updated",
              "Pending Review"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.admin.vendor_access.updated",
        "label": "Update Vendor Access",
        "idPrefix": "VACC",
        "rowDescription": "Vendor access update",
        "rowStatus": "Updated",
        "owner": "System Administrator",
        "fields": [
          {
            "name": "accessId",
            "label": "Access ID",
            "type": "text",
            "default": "VACC-AUTO",
            "required": true
          },
          {
            "name": "vendor",
            "label": "Vendor",
            "type": "text",
            "default": "Collection Partner",
            "required": true
          },
          {
            "name": "accessScope",
            "label": "Access Scope",
            "type": "select",
            "default": "Document upload",
            "required": true,
            "options": [
              "Document upload",
              "Case status",
              "Collection confirmation",
              "SLA dashboard"
            ]
          },
          {
            "name": "decision",
            "label": "Decision",
            "type": "select",
            "default": "Approved",
            "required": true,
            "options": [
              "Approved",
              "Revoked",
              "Needs Review"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Updated",
            "required": true,
            "options": [
              "Updated",
              "Needs Admin"
            ]
          }
        ]
      },
      {
        "eventType": "clinical.admin.audit.exported",
        "label": "Export Audit Evidence",
        "idPrefix": "AUD",
        "rowDescription": "Audit evidence export",
        "rowStatus": "Exported",
        "owner": "QA Specialist",
        "fields": [
          {
            "name": "exportId",
            "label": "Export ID",
            "type": "text",
            "default": "AUD-AUTO",
            "required": true
          },
          {
            "name": "dateRange",
            "label": "Date Range",
            "type": "text",
            "default": "June 2026",
            "required": true
          },
          {
            "name": "scope",
            "label": "Scope",
            "type": "select",
            "default": "All Clinical Events",
            "required": true,
            "options": [
              "All Clinical Events",
              "Intake",
              "Screening",
              "Quality",
              "Vendor Ops"
            ]
          },
          {
            "name": "format",
            "label": "Format",
            "type": "select",
            "default": "JSON",
            "required": true,
            "options": [
              "JSON",
              "CSV",
              "PDF"
            ]
          },
          {
            "name": "status",
            "label": "Status",
            "type": "select",
            "default": "Exported",
            "required": true,
            "options": [
              "Exported",
              "Failed"
            ]
          }
        ]
      }
    ]
  }
};
const dashboardMetrics = [
  {
    "label": "Active Donor Cases",
    "value": "248",
    "delta": "+18 this week",
    "tone": "good"
  },
  {
    "label": "Eligibility Queue",
    "value": "37",
    "delta": "8 urgent",
    "tone": "warning"
  },
  {
    "label": "QA Release Ready",
    "value": "91%",
    "delta": "+4.3%",
    "tone": "good"
  },
  {
    "label": "Vendor SLA",
    "value": "96.2%",
    "delta": "2 exceptions",
    "tone": "neutral"
  }
];
const roleCards = [
  [
    "Intake Coordinator",
    "Registers donor referrals, confirms demographics, documents consents, and starts screening packets."
  ],
  [
    "Clinical Reviewer",
    "Reviews eligibility evidence, medical history, lab readiness, and clinical disposition."
  ],
  [
    "QA Specialist",
    "Audits documentation, deviations, corrective actions, and release-readiness evidence."
  ],
  [
    "Vendor Operations",
    "Coordinates supplier portals, document requests, partner follow-ups, and service-level exceptions."
  ],
  [
    "Operations Manager",
    "Monitors throughput, staffing load, cycle time, and escalation queues."
  ],
  [
    "Technology Analyst",
    "Owns workflow configuration, data quality, integrations, reporting readiness, and audit evidence."
  ]
];

const basePath = "/Clinical/";
const appName = "Meridian Clinical";
const modulePrefix = "clinical";
const classPrefix = "clinical";
const userId = CLINICAL_USER_ID;
const getHealth = getClinicalHealth;
const getRecentEvents = getClinicalRecentEvents;
const sendEvent = sendClinicalEvent;

function getCurrentPath() {
  const pathname = window.location.pathname;

  if (pathname === basePath.slice(0, -1)) {
    return basePath;
  }

  return pathname.startsWith(basePath.slice(0, -1)) ? pathname : basePath;
}

function pageKey(pathname) {
  const match = appNavItems
    .filter((item) => item.path !== basePath)
    .sort((left, right) => right.path.length - left.path.length)
    .find((item) => pathname.startsWith(item.path));

  return match?.key || "dashboard";
}

function makeId(prefix) {
  return `${prefix}-${Date.now().toString().slice(-6)}-${Math.random().toString(16).slice(2, 6)}`.toUpperCase();
}

function statusTone(status = "") {
  const normalized = String(status).toLowerCase();

  if (
    normalized.includes("ready") ||
    normalized.includes("active") ||
    normalized.includes("confirmed") ||
    normalized.includes("approved") ||
    normalized.includes("verified") ||
    normalized.includes("posted") ||
    normalized.includes("published") ||
    normalized.includes("completed") ||
    normalized.includes("exported") ||
    normalized.includes("refreshed")
  ) return "good";

  if (
    normalized.includes("urgent") ||
    normalized.includes("exception") ||
    normalized.includes("risk") ||
    normalized.includes("hold") ||
    normalized.includes("capa") ||
    normalized.includes("pending") ||
    normalized.includes("needs") ||
    normalized.includes("created") ||
    normalized.includes("requested") ||
    normalized.includes("flagged") ||
    normalized.includes("escalated")
  ) return "warning";

  return "neutral";
}

function emitDomainEvent(eventType, payload = {}) {
  sendEvent({
    eventType,
    aggregateType: payload.aggregateType || "ui",
    aggregateId: payload.aggregateId || payload.path || `${modulePrefix}-ui`,
    actorUserId: userId,
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
            onClick={() => emitDomainEvent(`${modulePrefix}.portfolio.nav_clicked`, { label: item.label, href: item.href })}
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
    <div className={`${classPrefix}-table`}>
      {rows.map((row) => (
        <div className={`${classPrefix}-table-row`} key={row.id}>
          <strong>{row.id}</strong>
          <span>{row.description}</span>
          <StatusPill tone={statusTone(row.status)}>{row.status}</StatusPill>
          <b>{row.owner}</b>
        </div>
      ))}
    </div>
  );
}

function initialValuesFor(action) {
  return Object.fromEntries(
    (action.fields || []).map((field) => {
      if (field.type === "date" && !field.default) {
        return [field.name, new Date().toISOString().slice(0, 10)];
      }

      return [field.name, field.default ?? ""];
    })
  );
}

function ModalField({ field, value, onChange }) {
  const fieldId = `field-${field.name}`;

  if (field.type === "textarea") {
    return (
      <label className="modal-field" htmlFor={fieldId}>
        <span>{field.label}</span>
        <textarea
          id={fieldId}
          required={field.required}
          value={value}
          onChange={(event) => onChange(field.name, event.target.value)}
        />
      </label>
    );
  }

  if (field.type === "select") {
    return (
      <label className="modal-field" htmlFor={fieldId}>
        <span>{field.label}</span>
        <select
          id={fieldId}
          required={field.required}
          value={value}
          onChange={(event) => onChange(field.name, event.target.value)}
        >
          {(field.options || []).map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className="modal-field" htmlFor={fieldId}>
      <span>{field.label}</span>
      <input
        id={fieldId}
        type={field.type || "text"}
        required={field.required}
        value={value}
        onChange={(event) => onChange(field.name, event.target.value)}
      />
    </label>
  );
}

function ActionFormModal({ formState, onClose, onSubmit }) {
  const [values, setValues] = useState({});

  useEffect(() => {
    if (formState?.action) {
      setValues(initialValuesFor(formState.action));
    }
  }, [formState]);

  if (!formState) {
    return null;
  }

  const { moduleConfig, action } = formState;

  function updateValue(name, value) {
    setValues((current) => ({
      ...current,
      [name]: value
    }));
  }

  function submit(event) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" role="dialog" aria-modal="true" aria-label={action.label}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">{moduleConfig.title}</p>
            <h2>{action.label}</h2>
            <span>Review and edit the data before creating the worklist row and data lake event.</span>
          </div>

          <button className="ghost-button" type="button" onClick={onClose}>Close</button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-grid">
            {(action.fields || []).map((field) => (
              <ModalField
                key={field.name}
                field={field}
                value={values[field.name] ?? ""}
                onChange={updateValue}
              />
            ))}
          </div>

          <div className="modal-actions">
            <button className="ghost-button" type="button" onClick={onClose}>Cancel</button>
            <button type="submit">Submit {action.label}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function createActionRow(action, moduleKey, moduleConfig, values) {
  const idCandidate =
    values.journalId ||
    values.invoiceNumber ||
    values.taskId ||
    values.receiptId ||
    values.requisitionId ||
    values.poNumber ||
    values.vendorId ||
    values.itemNumber ||
    values.adjustmentId ||
    values.transferId ||
    values.countId ||
    values.workOrderId ||
    values.qualityIssueId ||
    values.maintenanceId ||
    values.planId ||
    values.reportId ||
    values.exportId ||
    values.snapshotId ||
    values.reconciliationId ||
    values.userId ||
    values.roleId ||
    values.integrationId ||
    values.auditId ||
    values.donorCaseId ||
    values.consentId ||
    values.screeningId ||
    values.eligibilityId ||
    values.deferralId ||
    values.evidenceId ||
    values.appointmentId ||
    values.vendorWindowId ||
    values.followUpId ||
    values.reviewId ||
    values.dispositionId ||
    values.labReadinessId ||
    values.escalationId ||
    values.deviationId ||
    values.capaId ||
    values.releaseId ||
    values.requestId ||
    values.exceptionId ||
    values.collectionId ||
    values.accessReviewId;

  const id = String(idCandidate || "").trim() && !String(idCandidate).includes("AUTO")
    ? String(idCandidate).trim()
    : makeId(action.idPrefix || moduleConfig.idPrefix || moduleKey.toUpperCase());

  const description =
    values.description ||
    values.itemDescription ||
    values.reportName ||
    values.taskName ||
    values.vendorName ||
    values.itemName ||
    values.subject ||
    values.donorDisplayName ||
    values.referralSource ||
    values.evidenceType ||
    values.appointmentType ||
    values.disposition ||
    values.auditScope ||
    values.documentType ||
    action.rowDescription ||
    action.label;

  const status =
    values.status ||
    values.matchStatus ||
    values.decision ||
    values.reviewOutcome ||
    values.verificationStatus ||
    values.outcome ||
    values.readinessStatus ||
    action.rowStatus ||
    "Submitted";

  const owner =
    values.owner ||
    values.approver ||
    values.buyer ||
    values.requester ||
    values.verifiedBy ||
    values.reviewer ||
    values.auditor ||
    values.assignedTo ||
    values.requestedFrom ||
    values.provider ||
    action.owner ||
    moduleConfig.owner ||
    "Operations";

  return {
    id,
    description,
    status,
    owner,
    createdAt: new Date().toISOString(),
    sourceAction: action.label,
    sourceEventType: action.eventType,
    formData: values
  };
}

function DashboardPage({ worklists }) {
  const priorityRows = [
    ...(worklists[moduleConfigs.dashboard.primaryTable] || []).slice(0, 2),
    ...(worklists[moduleConfigs.dashboard.secondaryTable] || []).slice(0, 2)
  ];

  return (
    <>
      <section className="hero-card">
        <div>
          <p className="eyebrow">{moduleConfigs.dashboard.eyebrow}</p>
          <h1>{moduleConfigs.dashboard.title}</h1>
          <p>{moduleConfigs.dashboard.description}</p>
        </div>

        <div className="hero-panel">
          <strong>{moduleConfigs.dashboard.panelTitle}</strong>
          <span>{moduleConfigs.dashboard.panelText}</span>
          <StatusPill tone="good">{moduleConfigs.dashboard.panelStatus}</StatusPill>
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
        <Card title={moduleConfigs.dashboard.workbenchTitle}>
          <DataTable rows={priorityRows} />
        </Card>

        <Card title={moduleConfigs.dashboard.rolesTitle}>
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

function ModulePage({ moduleKey, config, rows, onAction }) {
  return (
    <>
      <section className="module-header-card">
        <div>
          <p className="eyebrow">{config.eyebrow}</p>
          <h1>{config.title}</h1>
          <p>{config.description}</p>
        </div>

        <div className="action-grid">
          {config.actions.map((action) => (
            <button
              key={action.eventType}
              type="button"
              onClick={() => onAction(moduleKey, action)}
            >
              {action.label}
            </button>
          ))}
        </div>
      </section>

      <Card title={`${config.title} Worklist`}>
        <DataTable rows={rows} />
      </Card>
    </>
  );
}

function AdministrationPage({ worklists, onAction }) {
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("Loading event API state");

  function refreshApiState() {
    setStatus("Loading event API state");

    Promise.allSettled([getHealth(), getRecentEvents(10)])
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
          setStatus("Event API pending");
        }
      })
      .catch(() => setStatus("Event API pending"));
  }

  useEffect(() => {
    refreshApiState();
  }, []);

  const config = moduleConfigs.administration;

  return (
    <>
      <ModulePage
        moduleKey="administration"
        config={config}
        rows={worklists.administration}
        onAction={onAction}
      />

      <Card title={`${appName} Data Lake Events`}>
        <div className="admin-api-panel">
          <div>
            <p className="muted">
              Recent {appName} domain events written to the Azure data lake through the {appName} App Service managed identity.
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
                <strong>{event.event_type || `${modulePrefix}.event`}</strong>
                <span>{event.blob_name || event.aggregate_id || event.event_id}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No recent events returned yet.</strong>
            <span>Use the action buttons to generate data lake events.</span>
          </div>
        )}
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

function initialWorklists() {
  return Object.fromEntries(
    Object.entries(moduleConfigs)
      .filter(([key]) => key !== "dashboard")
      .map(([key, config]) => [key, config.rows || []])
  );
}

function App() {
  const [path, setPath] = useState(getCurrentPath());
  const [worklists, setWorklists] = useState(initialWorklists);
  const [activeForm, setActiveForm] = useState(null);
  const [lastSubmission, setLastSubmission] = useState(null);

  const key = useMemo(() => pageKey(path), [path]);

  useEffect(() => {
    function onPopState() {
      setPath(getCurrentPath());
    }

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    emitDomainEvent(`${modulePrefix}.page.viewed`, {
      path,
      page: key,
      aggregateType: "page"
    });

    document.title = key === "dashboard" ? `${appName} | teemails` : `${appName} | ${key}`;
  }, [path, key]);

  useEffect(() => {
    const dateKey = new Date().toISOString().slice(0, 10);
    const storageKey = `${modulePrefix}-table-snapshot-forms-v2-${dateKey}`;

    if (window.localStorage.getItem(storageKey)) {
      return;
    }

    const tables = Object.fromEntries(
      Object.entries(worklists).map(([tableName, rows]) => [
        tableName,
        rows.map((row) => ({ ...row }))
      ])
    );

    emitDomainEvent(`${modulePrefix}.table.snapshot`, {
      aggregateType: "table_snapshot",
      aggregateId: `${modulePrefix}.tables.${dateKey}`,
      tables,
      tableNames: Object.keys(tables),
      schemaVersion: "forms-v2"
    });

    window.localStorage.setItem(storageKey, "true");
  }, []);

  function navigate(nextPath) {
    window.history.pushState({}, "", nextPath);
    setPath(getCurrentPath());

    emitDomainEvent(`${modulePrefix}.app.nav_clicked`, {
      path: nextPath,
      page: pageKey(nextPath)
    });
  }

  function openActionForm(moduleKey, action) {
    setActiveForm({
      moduleKey,
      moduleConfig: moduleConfigs[moduleKey],
      action
    });

    emitDomainEvent(`${modulePrefix}.form.opened`, {
      aggregateType: "form",
      aggregateId: action.eventType,
      module: moduleConfigs[moduleKey].title,
      action: action.label
    });
  }

  function submitActionForm(values) {
    if (!activeForm) return;

    const { moduleKey, moduleConfig, action } = activeForm;
    const row = createActionRow(action, moduleKey, moduleConfig, values);

    setWorklists((current) => ({
      ...current,
      [moduleKey]: [row, ...(current[moduleKey] || [])]
    }));

    emitDomainEvent(action.eventType, {
      aggregateType: moduleKey,
      aggregateId: row.id,
      module: moduleConfig.title,
      action: action.label,
      formData: values,
      row
    });

    emitDomainEvent(`${modulePrefix}.table.row.created`, {
      aggregateType: "table",
      aggregateId: `${modulePrefix}.${moduleKey}.${row.id}`,
      table: moduleKey,
      row,
      formData: values,
      schemaVersion: "forms-v2"
    });

    setLastSubmission({
      module: moduleConfig.title,
      action: action.label,
      rowId: row.id
    });

    setActiveForm(null);
  }

  let content = <DashboardPage worklists={worklists} />;

  if (key !== "dashboard" && key !== "administration") {
    content = (
      <ModulePage
        moduleKey={key}
        config={moduleConfigs[key]}
        rows={worklists[key] || []}
        onAction={openActionForm}
      />
    );
  }

  if (key === "administration") {
    content = <AdministrationPage worklists={worklists} onAction={openActionForm} />;
  }

  return (
    <>
      <PortfolioRibbon />

      <div className={`${classPrefix}-shell`}>
        <aside className={`${classPrefix}-sidebar`}>
          <div className={`${classPrefix}-product`}>
            <span className={`${classPrefix}-product-mark`}>C</span>
            <div>
              <strong>{appName}</strong>
              <small>Donor Services</small>
            </div>
          </div>

          <nav className={`${classPrefix}-nav`} aria-label={`${appName} navigation`}>
            {appNavItems.map((item) => (
              <button
                key={item.path}
                type="button"
                className={path === item.path || (item.path !== basePath && path.startsWith(item.path)) ? "active" : ""}
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

        <main className={`${classPrefix}-main`}>
          {lastSubmission && (
            <div className="submission-toast">
              <strong>{lastSubmission.action} submitted</strong>
              <span>{lastSubmission.module} row {lastSubmission.rowId} was added and written to the data lake event stream.</span>
            </div>
          )}

          {content}
        </main>
      </div>

      <ActionFormModal
        formState={activeForm}
        onClose={() => setActiveForm(null)}
        onSubmit={submitActionForm}
      />
    </>
  );
}

export default App;
