from azure import AzureObject

class Vnet(AzureObject):
        props = {
            'addressSpace': (dict, False),
            'subnets': (list, False)
        }   

