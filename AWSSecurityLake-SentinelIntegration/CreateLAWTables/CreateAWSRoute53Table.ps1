
# Step 1: Login to Azure (opens browser)
Connect-AzAccount

# Optional: set subscription explicitly (good practice)
Set-AzContext -SubscriptionId "<SUBSCRIPTION ID HERE>"


$tableParams = @'
{
    "properties": {
        "schema": {
            "name": "AWSRoute53Logs_CL",
            "columns": [
                { "name": "AccountId", "type": "string", "description": "AWS account ID that owns the VPC which issued the DNS query." },
                { "name": "ActionId", "type": "string", "description": "Action identifier extracted from the log record." },
                { "name": "ActivityId", "type": "string", "description": "Activity identifier extracted from the log record." },
                { "name": "ActivityName", "type": "string", "description": "Activity name extracted from the log record." },
                { "name": "Answers", "type": "dynamic", "description": "Array of DNS response records including resolved IPs and related metadata." },
                { "name": "CategoryName", "type": "string", "description": "Category classification extracted from the log record." },
                { "name": "ClassName", "type": "string", "description": "Class classification extracted from the log record." },
                { "name": "Direction", "type": "string", "description": "Direction of the DNS query or connection (inbound/outbound)." },
                { "name": "DirectionId", "type": "string", "description": "Identifier representing the direction of the query." },
                { "name": "DstEndpoint", "type": "string", "description": "Destination endpoint identifier or DNS resolver endpoint." },
                { "name": "EventEpochTime", "type": "long", "description": "Event timestamp in Unix epoch format." },
                { "name": "FirewallDomainListId", "type": "string", "description": "ID of the DNS firewall domain list that matched the query." },
                { "name": "FirewallRule", "type": "string", "description": "DNS firewall rule details applied to the query." },
                { "name": "FirewallRuleAction", "type": "string", "description": "Action taken by the firewall rule (ALLOW, BLOCK, ALERT)." },
                { "name": "FirewallRuleGroupId", "type": "string", "description": "Identifier of the firewall rule group applied to the query." },
                { "name": "LogType", "type": "string", "description": "Type of DNS log (e.g., ResolverQueryLogs)." },
                { "name": "Observables", "type": "dynamic", "description": "Extracted observable entities such as domains, IPs, and indicators." },
                { "name": "Properties", "type": "dynamic", "description": "Additional event-specific attributes and metadata." },
                { "name": "QueryClass", "type": "string", "description": "DNS query class (typically IN for internet queries)." },
                { "name": "QueryName", "type": "string", "description": "Domain name that was queried." },
                { "name": "QueryType", "type": "string", "description": "DNS record type requested (e.g., A, AAAA, MX, TXT)." },
                { "name": "RawData", "type": "string", "description": "Original raw DNS log payload before parsing." },
                { "name": "Rcode", "type": "string", "description": "DNS response code (e.g., NOERROR, NXDOMAIN)." },
                { "name": "Region", "type": "string", "description": "AWS region where the log was generated." },
                { "name": "SourceSystem", "type": "string", "description": "Source system that generated the DNS log." },
                { "name": "SrcAddr", "type": "string", "description": "Source IP address of the client initiating the DNS query." },
                { "name": "SrcIds", "type": "dynamic", "description": "Identifiers associated with the source instance or origin of the query." },
                { "name": "SrcPort", "type": "string", "description": "Source port used by the client for the DNS query." },
                { "name": "TimeGenerated", "type": "datetime", "description": "Timestamp when the DNS query was processed by Route 53 Resolver." },
                { "name": "Transport", "type": "string", "description": "Transport protocol used (UDP, TCP, TLS)." },
                { "name": "Version", "type": "string", "description": "Version of the log format." },
                { "name": "VpcId", "type": "string", "description": "VPC identifier from which the DNS query originated." },
                { "name": "RcodeId", "type": "string", "description": "Numeric or internal identifier corresponding to the DNS response code." },
            ]
        }
    }
}
'@



$restMethodParams = @{
    Path    = "<LAW RESOURCE ID HERE>/tables/AWSRoute53Logs_CL?api-version=2025-07-01"
    Method  = "PUT"
    Payload = $tableParams}

Invoke-AzRestMethod @restMethodParams