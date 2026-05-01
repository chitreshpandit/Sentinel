
# Step 1: Login to Azure (opens browser)
#Connect-AzAccount

# Optional: set subscription explicitly (good practice)
Set-AzContext -SubscriptionId "6874b9d3-0bbe-43fd-9182-ec44214b1b4d"


$tableParams = @'
{
    "properties": {
        "schema": {
            "name": "AwsLambdaExecutionLogs_CL",
            "columns": [
                { "name": "TimeGenerated", "type": "datetime", "description": "Event time in UTC used for querying and detection." },
                { "name": "EventEpochTime", "type": "long", "description": "Event timestamp in Unix epoch format (milliseconds)." },
                { "name": "CloudProvider", "type": "string", "description": "Cloud provider name (e.g., AWS)." },
                { "name": "AwsRegion", "type": "string", "description": "AWS region where the API call was executed." },
                { "name": "ApiService", "type": "string", "description": "AWS service associated with the API call (e.g., lambda.amazonaws.com)." },
                { "name": "ApiOperation", "type": "string", "description": "API operation invoked (e.g., Invoke, InvokeFunction, CreateFunction)." },
                { "name": "ActivityName", "type": "string", "description": "Activity name extracted from the normalized event." },
                { "name": "ActivityStatus", "type": "string", "description": "Outcome of the activity (Success/Failure) when available." },
                { "name": "Severity", "type": "string", "description": "Severity classification of the event (Informational, Warning, High, etc.)." },
                { "name": "RequestId", "type": "string", "description": "Unique request identifier used for correlation." },
                { "name": "HttpUserAgent", "type": "string", "description": "HTTP user agent associated with the API request." },
                { "name": "ActorType", "type": "string", "description": "Type of identity performing the action (AWSService, IAMUser, AssumedRole, etc.)." },
                { "name": "ActorArn", "type": "string", "description": "ARN of the actor initiating the request." },
                { "name": "ActorAccountId", "type": "string", "description": "AWS account ID of the actor making the API call." },
                { "name": "SrcIpAddress", "type": "string", "description": "Source IP address from which the API request originated." },
                { "name": "SrcDomain", "type": "string", "description": "Source domain or hostname associated with the request, if available." },
                { "name": "FunctionName", "type": "string", "description": "Name of the Lambda function targeted by the API call." },
                { "name": "LambdaArn", "type": "string", "description": "ARN of the Lambda function involved in the event." },
                { "name": "AccountId", "type": "string", "description": "AWS account ID that owns the Lambda function." },
                { "name": "ResourceType", "type": "string", "description": "Type of resource associated with the event (e.g., AWS::Lambda::Function)." },
                { "name": "Unmapped", "type": "dynamic", "description": "Original fields from the source event not explicitly mapped to structured columns." },
                { "name": "Observables", "type": "dynamic", "description": "Extracted observable entities such as IPs, resource identifiers, and indicators." },
                { "name": "Resources", "type": "dynamic", "description": "Resources referenced or affected by the event." },
                { "name": "RawData", "type": "string", "description": "Original raw JSON event payload for forensic analysis and reprocessing." },
                { "name": "Properties", "type": "dynamic", "description": "Additional event-specific metadata and attributes." }
            ]
        }
    }
}
'@



$restMethodParams = @{
    Path    = "/subscriptions/6874b9d3-0bbe-43fd-9182-ec44214b1b4d/resourcegroups/chitpa-sentinel-rg-01/providers/microsoft.operationalinsights/workspaces/sentinel-ws-sea-01/tables/AwsLambdaExecutionLogs_CL?api-version=2025-07-01"
    Method  = "PUT"
    Payload = $tableParams}

Invoke-AzRestMethod @restMethodParams