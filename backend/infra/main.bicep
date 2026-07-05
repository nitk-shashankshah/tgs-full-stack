targetScope = 'subscription'

// Provisions the Azure resources for the TGS backend (FastAPI on Container Apps).

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param resourceGroupName string = ''
param containerAppName string = ''
param containerRegistryName string = ''

@secure()
@description('Anthropic API key, injected as the ANTHROPIC_API_KEY app setting.')
param anthropicApiKey string

@description('Comma-separated list of extra browser origins allowed by CORS. Optional.')
param allowedOrigins string = ''

@secure()
@description('Postgres connection string, injected as the DATABASE_URL app setting.')
param databaseUrl string

@secure()
@description('Azure Blob Storage connection string, injected as the AZURE_STORAGE_CONNECTION_STRING app setting.')
param storageConnectionString string

@description('Blob container name for uploaded catalogues.')
param storageContainerName string = 'tgscatalogs'

var abbrs = loadJsonContent('./abbreviations.json')

var tags = {
  'azd-env-name': environmentName
}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module containerRegistry './core/host/containerregistry.bicep' = {
  name: 'containerregistry'
  scope: rg
  params: {
    name: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
  }
}

module containerAppsEnvironment './core/host/containerapps-environment.bicep' = {
  name: 'containerapps-environment'
  scope: rg
  params: {
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    tags: tags
  }
}

module containerApp './core/host/containerapp.bicep' = {
  name: 'web'
  scope: rg
  params: {
    name: !empty(containerAppName) ? containerAppName : '${abbrs.appContainerApps}web-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    containerRegistryUsername: containerRegistry.outputs.adminUsername
    containerRegistryPassword: containerRegistry.outputs.adminPassword
    appSecrets: [
      { name: 'anthropic-api-key', value: anthropicApiKey }
      { name: 'database-url', value: databaseUrl }
      { name: 'storage-connection-string', value: storageConnectionString }
    ]
    env: union(
      [
        { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
        { name: 'DATABASE_URL', secretRef: 'database-url' }
        { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection-string' }
        { name: 'AZURE_CONTAINER_NAME', value: storageContainerName }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '600' }
      ],
      empty(allowedOrigins) ? [] : [{ name: 'ALLOWED_ORIGINS', value: allowedOrigins }]
    )
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name
output WEB_URI string = containerApp.outputs.uri
