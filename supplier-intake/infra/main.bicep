targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment used to generate a short unique hash for all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param resourceGroupName string = ''
param staticWebAppName string = ''

@description('Backend API URL (Container Apps HTTPS URL). Injected as VITE_API_BASE_URL at build time.')
param backendUrl string = ''

var abbrs = {
  resourcesResourceGroups: 'rg-'
  webStaticSites: 'stapp-'
}

var tags = {
  'azd-env-name': environmentName
}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module staticWebApp 'core/staticwebapp.bicep' = {
  name: 'staticwebapp'
  scope: rg
  params: {
    name: !empty(staticWebAppName) ? staticWebAppName : '${abbrs.webStaticSites}${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    appSettings: empty(backendUrl) ? {} : {
      VITE_API_BASE_URL: backendUrl
    }
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output WEB_URI string = staticWebApp.outputs.uri
output AZURE_STATIC_WEB_APPS_API_TOKEN string = staticWebApp.outputs.deploymentToken
