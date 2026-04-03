"""CrossGuard policy pack entry point."""

from pulumi_policy import PolicyPack

from policies.genomics_policies import policies

PolicyPack(
    name="precision-genomics-compliance",
    enforcement_level="mandatory",
    policies=policies,
)
