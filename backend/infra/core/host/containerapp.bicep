metadata description = 'Creates an Azure Container App.'
param name string
param location string = resourceGroup().location
param tags object = {}

param containerAppsEnvironmentId string
param containerRegistryLoginServer string
param imageName string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param targetPort int = 8000
param env array = []
param secrets array = []
param cpu string = '0.5'
param memory string = '1.0Gi'

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      secrets: secrets
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistryLoginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: imageName
          env: env
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output name string = containerApp.name
output uri string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output identityPrincipalId string = containerApp.identity.principalId
