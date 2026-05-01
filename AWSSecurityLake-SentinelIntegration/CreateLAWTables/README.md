# AWS Security Lake → Microsoft Sentinel Integration (Custom Table Creation)

This repository contains PowerShell scripts to create custom Log Analytics tables (for example, `AWSEKSLogs_CL`) using Azure REST APIs. These tables can be used for ingesting transformed AWS Security Lake logs into Microsoft Sentinel.

---

## 📌 Prerequisites

### ✅ Permissions (Minimum Required)
The following Azure RBAC roles are required:
- **Log Analytics Contributor**
- **Microsoft Sentinel Contributor**

These permissions are required to create and manage custom tables in the Log Analytics workspace.

---

## ▶️ Where can you run the script?

You can execute the provided script from:

- ✅ **Windows PowerShell**
- ✅ **Visual Studio Code (with Azure PowerShell extension)**
- ✅ **Azure Cloud Shell (PowerShell)**

---

## ⚠️ Important Notes

- If running in **local PowerShell / VS Code**, keep:
  ```powershell
  Connect-AzAccount
  ```
- If running in **Azure Cloud Shell**, **comment out**:
  ```powershell
  # Connect-AzAccount
  ```
  👉 Authentication is already handled automatically in Azure Cloud Shell.

---

## 🚀 Steps to Run from Local PowerShell / VS Code

1. Install Azure PowerShell module (if not installed):
   ```powershell
   Install-Module Az -Scope CurrentUser -Repository PSGallery -Force
   ```

2. Authenticate:
   ```powershell
   Connect-AzAccount
   ```

3. Set the subscription context in the script:
   ```powershell
   Set-AzContext -SubscriptionId "<your-subscription-id>"
   ```

4. Run the script:
   ```powershell
   Invoke-AzRestMethod @restMethodParams
   ```

---

## ☁️ Steps to Run from Azure Cloud Shell

### Step-by-step:

1. Go to **Azure Portal**
2. Click on **Cloud Shell** (top-right toolbar)
3. Select **PowerShell**

4. Upload the script:
   - Click **Upload/Download files**
   - Upload your `.ps1` file

5. Edit the script (important):
   - Comment the login line:
     ```powershell
     # Connect-AzAccount
     ```

6. Set subscription context (if needed):
   ```powershell
   Set-AzContext -SubscriptionId "<your-subscription-id>"
   ```

7. Execute the script:
   ```powershell
   ./your-script-name.ps1
   ```

---

## 📂 Script Overview

The script performs the following:

- Defines a custom schema (`AWSEKSLogs_CL`)
- Creates a Log Analytics custom table using the **2025-07-01 API**
- Uses `Invoke-AzRestMethod` for direct REST interaction

---

## 💡 Design Considerations

- Custom tables follow Azure naming convention: `<TableName>_CL`
- Schema supports structured + dynamic fields for flexibility
- Raw data is preserved (`RawData`) for troubleshooting
- Supports normalized fields for Sentinel analytics

---

## 📊 Optional – Screenshots (Recommended for README)

You can enhance this README by adding:

- Azure Portal → Log Analytics Workspace → Tables view
- Custom table creation success
- Data ingestion validation in Logs

Example (add images):
```markdown
![Table Created](./images/table-created.png)
![Logs View](./images/logs-view.png)
```

---

## ✅ Output

After successful execution:

- Custom table will be created in Log Analytics workspace
- Ready for ingestion via Data Collection Endpoint / Event Hub pipeline

---

## 🔗 Next Steps

- Integrate with Event Hub ingestion pipeline
- Add DCR (Data Collection Rule) for ingestion
- Build KQL parsers and analytics rules

---

## ⚠️ Troubleshooting

| Issue | Resolution |
|------|-----------|
| 403 Forbidden | Check RBAC roles (Sentinel Contributor / LA Contributor) |
| Script fails in Cloud Shell | Ensure Connect-AzAccount is commented |
| Table not visible | Refresh workspace or wait few minutes |

---

## 📢 Notes

- This approach avoids ARM templates and uses direct REST API for flexibility
- Recommended for automation scenarios (CI/CD, pipelines, bulk schema creation)

---

