
# Step 1: Login to Azure (opens browser)
Connect-AzAccount

# Optional: set subscription explicitly (good practice)
Set-AzContext -SubscriptionId "6874b9d3-0bbe-43fd-9182-ec44214b1b4d"


$tableParams = @'
{
    "properties": {
        "schema": {
            "name": "AWSEKSLogs_CL",
            "columns": [
                { "name": "ActorName", "type": "string", "description": "Name of the entity (user, service account, or system) that initiated the action." },
                { "name": "ActorTypeId", "type": "int", "description": "Numeric identifier representing the type/category of the actor (e.g., user, service account, system)." },
                { "name": "ActorUid", "type": "string", "description": "Unique identifier assigned to the actor within the Kubernetes cluster or identity provider." },
                { "name": "ApiGroup", "type": "string", "description": "Kubernetes API group associated with the request (e.g., core, apps, networking.k8s.io)." },
                { "name": "ApiVersion", "type": "string", "description": "Version of the Kubernetes API used for the request (e.g., v1, v1beta1)." },
                { "name": "CloudProvider", "type": "string", "description": "Cloud environment where the Kubernetes cluster is running (e.g., AWS)." },
                { "name": "EksClusterName", "type": "string", "description": "Name of the Amazon EKS cluster where the event occurred." },
                { "name": "EKSNamespace", "type": "string", "description": "Kubernetes namespace in which the resource or action is scoped." },
                { "name": "EKSResourceName", "type": "string", "description": "Name of the Kubernetes resource targeted or affected by the operation." },
                { "name": "EKSResourceType", "type": "string", "description": "Type of Kubernetes resource involved (e.g., Pod, Deployment, Service, ConfigMap)." },
                { "name": "EKSResourceUid", "type": "string", "description": "Unique identifier assigned to the Kubernetes resource." },
                { "name": "EKSResourceVersion", "type": "string", "description": "Version identifier for the Kubernetes resource at the time of the event." },
                { "name": "Message", "type": "string", "description": "Human-readable message describing the event or operation outcome." },
                { "name": "Observables", "type": "dynamic", "description": "Collection of extracted security-relevant observables (e.g., IPs, domains, resource identifiers)." },
                { "name": "Operation", "type": "string", "description": "Action performed (e.g., create, update, delete, get, list, patch)." },
                { "name": "Properties", "type": "dynamic", "description": "Additional event-specific attributes and metadata not mapped to predefined columns." },
                { "name": "RawData", "type": "string", "description": "Original raw log payload for the event, preserved for reference and troubleshooting." },
                { "name": "Resources", "type": "dynamic", "description": "List of related resources impacted or referenced in the event." },
                { "name": "ResponseCode", "type": "int", "description": "HTTP or API response code returned for the request (e.g., 200, 403, 404)." },
                { "name": "SrcIp", "type": "string", "description": "Source IP address from which the request originated." },
                { "name": "TimeGenerated", "type": "datetime", "description": "Timestamp when the event was generated at the source system." },
                { "name": "Unmapped", "type": "dynamic", "description": "Fields from the original event that are not explicitly mapped to predefined columns." },
                { "name": "UrlPath", "type": "string", "description": "API endpoint path accessed during the request." },
                { "name": "UserAgent", "type": "string", "description": "User agent string identifying the client or tool that made the request." },
                { "name": "EventEpochTime", "type": "long", "description": "Event timestamp represented as Unix epoch time (milliseconds since January 1, 1970)." }
            ]
        }
    }
}
'@


$restMethodParams = @{
    Path    = "/subscriptions/6874b9d3-0bbe-43fd-9182-ec44214b1b4d/resourcegroups/chitpa-sentinel-rg-01/providers/microsoft.operationalinsights/workspaces/sentinel-ws-sea-01/tables/AWSEKSLogs_CL?api-version=2025-07-01"
    Method  = "PUT"
    Payload = $tableParams}

Invoke-AzRestMethod @restMethodParams