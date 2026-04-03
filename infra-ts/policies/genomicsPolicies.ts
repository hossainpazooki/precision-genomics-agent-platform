import { PolicyPackConfig, ResourceValidationPolicy } from "@pulumi/policy";

export const genomicsPolicies: ResourceValidationPolicy[] = [
  {
    name: "cloud-sql-pitr-enabled",
    description: "All Cloud SQL instances must have point-in-time recovery enabled",
    enforcementLevel: "mandatory",
    validateResource: (args, reportViolation) => {
      if (args.type === "gcp:sql/databaseInstance:DatabaseInstance") {
        const settings = args.props?.settings;
        const backup = settings?.backupConfiguration;
        if (!backup?.pointInTimeRecoveryEnabled) {
          reportViolation("Cloud SQL must have point-in-time recovery enabled for genomics data lineage");
        }
      }
    },
  },
  {
    name: "gcs-versioning-enabled",
    description: "All GCS buckets must have versioning enabled",
    enforcementLevel: "mandatory",
    validateResource: (args, reportViolation) => {
      if (args.type === "gcp:storage/bucket:Bucket") {
        const versioning = args.props?.versioning;
        if (!versioning?.enabled) {
          reportViolation("GCS buckets must have versioning enabled for data lineage");
        }
      }
    },
  },
  {
    name: "cloud-sql-deletion-protection",
    description: "Cloud SQL instances must have deletion protection enabled",
    enforcementLevel: "mandatory",
    validateResource: (args, reportViolation) => {
      if (args.type === "gcp:sql/databaseInstance:DatabaseInstance") {
        if (!args.props?.deletionProtection) {
          reportViolation("Cloud SQL must have deletion protection enabled");
        }
      }
    },
  },
  {
    name: "resource-labeling",
    description: "All resources must have data-classification and hipaa-scope labels",
    enforcementLevel: "advisory",
    validateResource: (args, reportViolation) => {
      if (args.type === "gcp:storage/bucket:Bucket") {
        const labels = args.props?.labels ?? {};
        if (!labels["data-classification"]) {
          reportViolation("GCS bucket missing 'data-classification' label");
        }
        if (!labels["hipaa-scope"]) {
          reportViolation("GCS bucket missing 'hipaa-scope' label");
        }
      }
    },
  },
];
