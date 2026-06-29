metadata description = 'Creates an Azure Container Registry.'
param name string
param location string = resourceGroup().location
param tags object = {}
param sku string = 'Basic'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: true
    anonymousPullEnabled: false
  }
}

output loginServer string = containerRegistry.properties.loginServer
output name string = containerRegistry.name
output adminUsername string = containerRegistry.listCredentials().username
@secure()
output adminPassword string = containerRegistry.listCredentials().passwords[0].value
