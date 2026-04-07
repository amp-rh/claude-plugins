# AWS Resource Cleanup

Procedures for cleaning up stale AWS resources left behind by failed CI test runs.

→ **Skill**: @../../../../skills/aws-cluster-cleanup/SKILL.md

## Summary

Clean up orphaned AWS resources (EC2, VPC, ECS, ELB, Route53) from failed OpenShift CI jobs.

**When to use:**
- CI jobs fail during cluster provisioning/deprovisioning
- AWS quota errors indicate orphaned resources (`VpcLimitExceeded`, etc.)
- Performing watcher rotation cleanup
- Resources older than 24 hours

**Key points:**
- Resources must be deleted in correct order to avoid `DependencyViolation` errors
- Check both Classic ELB (`aws elb`) and ALB/NLB (`aws elbv2`) APIs
- Wait for instances to fully terminate before deleting subnets/security groups
- ECS clusters require stopping tasks → deleting services → deregistering instances → deleting cluster

## Quick Reference

**Deletion order:** EC2 → ELB → NAT Gateway → EIP → IGW → (wait for instances) → Subnets → Route Tables → Security Groups → VPC Endpoints → VPC

**Common commands:**

```bash
# List VPCs
aws ec2 describe-vpcs --region us-east-2 \
  --query 'Vpcs[*].{VpcId:VpcId,Name:Tags[?Key==`Name`].Value|[0]}' --output table

# Find instances by cluster tag
CLUSTER_TAG="ci-op-XXXXX"
aws ec2 describe-instances --region us-east-2 \
  --filters "Name=tag:kubernetes.io/cluster/$CLUSTER_TAG,Values=owned" \
  --query 'Reservations[*].Instances[*].[InstanceId,LaunchTime]' --output table
```

## Related

- @daily-triage.md — When to perform cleanup
- @../dashboards.md — Finding failed jobs
