# Step 5 - scale to all supported resources

We need to give all permissions to the UTCM app.

```PowerShell
$permissions = @("AdministrativeUnit.Read.All", "Agreement.Read.All", "Application.Read.All", "CustomSecAttributeDefinition.Read.All", "Device.Read.All", "DeviceManagementApps.Read.All", "DeviceManagementConfiguration.Read.All", "DeviceManagementManagedDevices.Read.All", "DeviceManagementRBAC.Read.All", "DeviceManagementScripts.Read.All", "DeviceManagementServiceConfig.Read.All", "Directory.Read.All", "EntitlementManagement.Read.All", "Exchange.ManageAsApp", "Group.Read.All", "GroupMember.Read.All", "IdentityProvider.Read.All", "Organization.Read.All", "Policy.Read.All", "Policy.Read.AuthenticationMethod", "Policy.Read.ConditionalAccess", "ReportSettings.Read.All", "RoleEligibilitySchedule.Read.Directory", "RoleManagement.Read.Directory", "RoleManagementPolicy.Read.Directory", "Team.ReadBasic.All", "User.EnableDisableAccount.All", "User.Read.All")
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

Also, we need to assign to the UTCM app these roles:
- Teams meeting policy: `Global Reader`
- CA / named location / app / DLP docs list `Security Reader` for read
