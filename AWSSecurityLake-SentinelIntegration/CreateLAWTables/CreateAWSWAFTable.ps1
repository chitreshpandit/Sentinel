
# Step 1: Login to Azure (opens browser)
Connect-AzAccount

# Optional: set subscription explicitly (good practice)
Set-AzContext -SubscriptionId "<SUBSCRIPTION ID HERE>"


$tableParams = @'
{
    "properties": {
        "schema": {
            "name": "AWSWAFEvents_CL",
            "columns": [
                { "name": "Action", "type": "string", "description": "Terminating action taken by AWS WAF (ALLOW, BLOCK, CAPTCHA, or CHALLENGE)." },
                { "name": "Args", "type": "string", "description": "Query string parameters included in the request." },
                { "name": "CaptchaResponse", "type": "dynamic", "description": "Details of CAPTCHA verification status for the request." },
                { "name": "ChallengeResponse", "type": "dynamic", "description": "Details of security challenge response for the request." },
                { "name": "ClientIp", "type": "string", "description": "IP address of the client making the request." },
                { "name": "Country", "type": "string", "description": "Country of origin of the client IP address." },
                { "name": "DomainName", "type": "string", "description": "Hostname extracted from the HTTP request." },
                { "name": "ExcludedRules", "type": "dynamic", "description": "Rules excluded from evaluation within the rule group." },
                { "name": "FormatVersion", "type": "string", "description": "Version of the AWS WAF log format." },
                { "name": "Headers", "type": "dynamic", "description": "HTTP headers included in the request." },
                { "name": "HttpMethod", "type": "string", "description": "HTTP method used (GET, POST, etc.)." },
                { "name": "HttpRequest", "type": "dynamic", "description": "Metadata and details of the HTTP request." },
                { "name": "HttpSourceId", "type": "string", "description": "Identifier of the associated AWS resource (e.g., CloudFront distribution, ALB)." },
                { "name": "HttpSourceName", "type": "string", "description": "Source of the request (e.g., CloudFront, API Gateway, ALB)." },
                { "name": "HttpVersion", "type": "string", "description": "HTTP version used in the request." },
                { "name": "Ja3Fingerprint", "type": "string", "description": "JA3 fingerprint derived from the TLS client hello." },
                { "name": "Labels", "type": "dynamic", "description": "Labels applied to the request during rule evaluation." },
                { "name": "NonTerminatingMatchingRules", "type": "dynamic", "description": "Rules that matched but did not terminate the request." },
                { "name": "OversizeFields", "type": "dynamic", "description": "Request fields that exceeded AWS WAF inspection size limits." },
                { "name": "Properties", "type": "dynamic", "description": "Additional event-specific metadata." },
                { "name": "RateBasedRuleList", "type": "dynamic", "description": "List of rate-based rules evaluated for the request." },
                { "name": "RateLimit", "type": "string", "description": "Rate limit configured for the matching rule." },
                { "name": "RawData", "type": "string", "description": "Original raw WAF log event payload." },
                { "name": "RequestHeadersInserted", "type": "dynamic", "description": "Headers inserted into the request by AWS WAF." },
                { "name": "RequestId", "type": "string", "description": "Unique identifier for the request." },
                { "name": "ResponseCodeSent", "type": "int", "description": "HTTP response code returned to the client." },
                { "name": "RuleGroupId", "type": "string", "description": "Identifier of the rule group that matched." },
                { "name": "RuleGroupList", "type": "dynamic", "description": "List of rule groups evaluated for the request." },
                { "name": "TerminatingRule", "type": "dynamic", "description": "Details of the rule that terminated the request, including action and match data." },
                { "name": "TerminatingRuleId", "type": "string", "description": "Identifier of the rule that terminated the request." },
                { "name": "TerminatingRuleMatchDetails", "type": "dynamic", "description": "Detailed match information for the terminating rule." },
                { "name": "TerminatingRuleMatchDetailsConditionType", "type": "string", "description": "Condition type that triggered the terminating rule." },
                { "name": "TerminatingRuleMatchDetailsLocation", "type": "string", "description": "Request location (e.g., header, body) where the rule match occurred." },
                { "name": "TerminatingRuleType", "type": "string", "description": "Type of the rule that terminated the request." },
                { "name": "TimeGenerated", "type": "datetime", "description": "Timestamp when the WAF log event was generated." },
                { "name": "Uri", "type": "string", "description": "Request URI path." },
                { "name": "WebAclId", "type": "string", "description": "Identifier of the Web ACL applied to the request." },
                { "name": "UserAgent", "type": "string", "description": "Client user agent string from the HTTP request." }
            ]
        }
    }
}
'@



$restMethodParams = @{
    Path    = "<LAW RESOURCE ID HERE>/tables/AWSWAFEvents_CL?api-version=2025-07-01"
    Method  = "PUT"
    Payload = $tableParams}

Invoke-AzRestMethod @restMethodParams