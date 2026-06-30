metadata description = 'Creates an Azure Static Web App.'
param name string
param location string = resourceGroup().location
param tags object = {}
param sku string = 'Free'
param appSettings object = {}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    buildProperties: {
      skipGithubActionWorkflowGeneration: true
    }
  }
}

resource appsettings 'Microsoft.Web/staticSites/config@2022-09-01' = if (!empty(appSettings)) {
  name: 'appsettings'
  parent: staticWebApp
  properties: appSettings
}

output id string = staticWebApp.id
output uri string = 'https://${staticWebApp.properties.defaultHostname}'
output name string = staticWebApp.name
output deploymentToken string = staticWebApp.listSecrets().properties.apiKey
