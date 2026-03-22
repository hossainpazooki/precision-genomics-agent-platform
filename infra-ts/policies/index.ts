import { PolicyPack } from "@pulumi/policy";
import { genomicsPolicies } from "./genomicsPolicies";

new PolicyPack("precision-genomics-policies", {
  policies: genomicsPolicies,
});
