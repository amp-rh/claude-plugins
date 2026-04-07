"""Pre-built LogQL queries for AWS resource analysis."""

# AWS Quota/Limit Errors - comprehensive list
AWS_QUOTA_ERRORS = r'''
{job=~".*"} |~ "VpcLimitExceeded|VpcEndpointLimitExceeded|AddressLimitExceeded|InstanceLimitExceeded|ResourceLimitExceeded|LimitExceededException|ServiceQuotaExceededException|InsufficientInstanceCapacity|InsufficientAddressCapacity|NatGatewayLimitExceeded|SubnetLimitExceeded|SecurityGroupLimitExceeded|RouteTableLimitExceeded|InternetGatewayLimitExceeded|EIPLimitExceeded|MaxIOPSLimitExceeded|VolumeLimitExceeded"
'''

# VPC-specific limit errors
VPC_LIMIT_ERRORS = r'''
{job=~".*"} |~ "VpcLimitExceeded|VpcEndpointLimitExceeded|SubnetLimitExceeded|SecurityGroupLimitExceeded|RouteTableLimitExceeded|InternetGatewayLimitExceeded|NatGatewayLimitExceeded"
'''

# Orphaned VPC Detection (deprovision failures)
ORPHANED_VPC_PATTERNS = r'''
{job=~".*deprovision.*"} |~ "failed to delete vpc|VPC.*still has dependencies|error.*deleting.*vpc|failed.*cleanup|cannot delete.*vpc|DependencyViolation"
'''

# Deprovision failures that may leave resources behind
DEPROVISION_FAILURES = r'''
{job=~".*(ipi-deprovision|aws-deprovision|deprovision).*"} |= "error" |~ "failed|delete|cleanup|timeout"
'''

# Node Availability Issues
NODE_AVAILABILITY = r'''
{job=~".*"} |~ "minimum worker replica count.*not yet met|InsufficientInstanceCapacity|Insufficient.*capacity|waiting for bootstrap|nodes are not available"
'''

# IPI Install Failures related to VPC/AWS
IPI_INSTALL_FAILURES = r'''
{job=~".*ipi-install.*"} |= "error" |~ "VpcReconciliationFailed|failed to create.*vpc|quota.*exceeded|failed.*network|ResourceInUse"
'''

# MPIIT Scope filter - jobs we care about
MPIIT_JOB_FILTER = r'''
{job=~".*(lp-interop|lp-rosa-hypershift|interop-opp|konflux).*"}
'''

# AWS Profile mentions (for tracking quota usage by account)
AWS_PROFILE_MENTIONS = r'''
{job=~".*"} |~ "aws-interop-qe|aws-cspi-qe|aws-2|aws-qe"
'''

# EC2 Instance Capacity Issues
EC2_CAPACITY_ISSUES = r'''
{job=~".*"} |~ "InsufficientInstanceCapacity|Insufficient.*capacity|InstanceLimitExceeded|MaxSpotInstanceCountExceeded"
'''

# EBS Volume Issues
EBS_ISSUES = r'''
{job=~".*"} |~ "VolumeLimitExceeded|MaxIOPSLimitExceeded|VolumeInUse|SnapshotLimitExceeded"
'''

# Elastic IP Issues
EIP_ISSUES = r'''
{job=~".*"} |~ "AddressLimitExceeded|EIPLimitExceeded|InsufficientAddressCapacity"
'''

# General AWS errors (broader catch-all)
GENERAL_AWS_ERRORS = r'''
{job=~".*"} |~ "LimitExceeded|QuotaExceeded|Insufficient.*Capacity|quota.*exceeded|ThrottlingException|RequestLimitExceeded"
'''


def build_scoped_query(base_query: str, job_filter: str | None = None) -> str:
    """Build a query with optional job scope filter.

    Args:
        base_query: The base LogQL query pattern
        job_filter: Optional job name filter regex (e.g., "lp-interop|konflux")

    Returns:
        LogQL query with job scope applied
    """
    if not job_filter:
        return base_query.strip()

    # Replace the job matcher in the base query
    # This handles the pattern {job=~".*"} → {job=~".*<filter>.*"}
    scoped = base_query.replace(
        '{job=~".*"}',
        f'{{job=~".*({job_filter}).*"}}'
    ).replace(
        '{job=~".*deprovision.*"}',
        f'{{job=~".*({job_filter}).*deprovision.*"}}'
    )

    return scoped.strip()


def get_mpiit_scoped_query(base_query: str) -> str:
    """Get a query scoped to MPIIT jobs."""
    return build_scoped_query(
        base_query,
        job_filter="lp-interop|lp-rosa-hypershift|interop-opp|konflux"
    )
