# Setup UTCM
Based on the docs here: https://learn.microsoft.com/en-us/graph/utcm-authentication-setup

Create an App Registration to allow connectivity to the MS Graph.
Create a secret and fill `.env` following the `.env.example`.
Give it the permission to manage configuration `ConfigurationMonitoring.ReadWrite.All`.
For the test script, also add `Organization.Read.All`.
AFAIK, this should use the service principal that we import below (`Unified Tenant Configuration Management`)

Import the Service Principal in our tenant
```PowerShell
Install-Module Microsoft.Graph.Authentication
Install-Module Microsoft.Graph.Applications

Connect-MgGraph -Scopes @('Application.ReadWrite.All', 'AppRoleAssignment.ReadWrite.All')

# This imports the Unified Tenant Configuration Management app
New-MgServicePrincipal -AppId '03b07b79-c5bc-4b5e-9bfa-13acf4a99998'
```

Give permissions to the Service Principal
```PowerShell
$permissions = @('User.ReadWrite.All', 'Policy.Read.All')
$Graph = Get-MgServicePrincipal -Filter "AppId eq '00000003-0000-0000-c000-000000000000'"
$UTCM = Get-MgServicePrincipal -Filter "AppId eq '03b07b79-c5bc-4b5e-9bfa-13acf4a99998'"

foreach ($requestedPermission in $permissions) {
    $AppRole = $Graph.AppRoles | Where-Object { $_.Value -eq $requestedPermission }
    $body = @{
        AppRoleId = $AppRole.Id
        ResourceId = $Graph.Id
        PrincipalId = $UTCM.Id
    }
    New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $UTCM.Id -BodyParameter $body
}

```