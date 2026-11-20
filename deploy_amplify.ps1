# Rebuild the demo site and (re)deploy it to AWS Amplify in one step.
# Requires the sandbox AWS profile to be active (run updatesandbox.bat first).
# Usage: powershell -ExecutionPolicy Bypass -File .\deploy_amplify.ps1
param(
  [string]$AppId = 'd3pz3oj6iuj9t4',
  [string]$ProfileName = '304507007699_AWSPowerUserAccess'
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # quiet the Compress-Archive / web progress bars

python build_home.py | Out-Null
Remove-Item _site, site.zip -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory _site | Out-Null
Copy-Item index.html, marcus_fhir.html, marcus_fusion.html, marcus_healthix.html, marcus_healtheconn.html, marcus_bronx.html, hosp_data.js, nonhosp_data.js, adt_data.js _site\
Compress-Archive -Path _site\* -DestinationPath site.zip -Force

$dep = aws amplify create-deployment --app-id $AppId --branch-name main --profile $ProfileName --output json | ConvertFrom-Json
Invoke-WebRequest -Method Put -Uri $dep.zipUploadUrl -InFile site.zip -ContentType "application/zip" -UseBasicParsing | Out-Null
aws amplify start-deployment --app-id $AppId --branch-name main --job-id $dep.jobId --profile $ProfileName | Out-Null

do {
  Start-Sleep 5
  $s = aws amplify get-job --app-id $AppId --branch-name main --job-id $dep.jobId --profile $ProfileName --query "job.summary.status" --output text
} while ($s -notin 'SUCCEED', 'FAILED', 'CANCELLED')

Write-Host "Deploy $s  ->  https://main.$AppId.amplifyapp.com"
