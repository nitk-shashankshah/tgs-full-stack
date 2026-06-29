targetScope = 'subscription'

// Provisions the Azure resources for the TGS backend (FastAPI on App Service).
// Adapted from the msdocs-python-fastapi-webapp-quickstart azd template.

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

// Optional parameters to override the default azd resource naming conventions.
param resourceGroupName string = ''
param appServiceName string = ''
param appServicePlanName string = ''

@description('App Service plan SKU. B1 (Basic) is recommended for the PDF/LLM workload; F1 (Free) has tight CPU/memory limits and does not support Always On.')
param appServiceSku string = 'B1'

@secure()
@description('Anthropic API key, injected as the ANTHROPIC_API_KEY app setting.')
param anthropicApiKey string

@description('Comma-separated list of extra browser origins allowed by CORS (e.g. your deployed frontend URL). Optional.')
param allowedOrigins string = ''

var abbrs = loadJsonContent('./abbreviations.json')

var tags = {
  'azd-env-name': environmentName
}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Always On is not supported on the Free (F1) tier.
var enableAlwaysOn = appServiceSku != 'F1'

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// The application App Service
module web './core/host/appservice.bicep' = {
  name: 'web'
  scope: rg
  params: {
    name: !empty(appServiceName) ? appServiceName : '${abbrs.webSitesAppService}web-${resourceToken}'
    location: location
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.13'
    appCommandLine: 'gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --timeout 600 --bind 0.0.0.0:8000'
    scmDoBuildDuringDeployment: true
    alwaysOn: enableAlwaysOn
    healthCheckPath: '/health'
    appSettings: union(
      {
        ANTHROPIC_API_KEY: anthropicApiKey
        // Give Oryx/container extra time to start under the heavier deps.
        WEBSITES_CONTAINER_START_TIME_LIMIT: '600'
      },
      empty(allowedOrigins) ? {} : { ALLOWED_ORIGINS: allowedOrigins }
    )
    tags: union(tags, { 'azd-service-name': 'web' })
  }
}

// App Service Plan
module appServicePlan './core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: appServiceSku
    }
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output WEB_URI string = web.outputs.uri
