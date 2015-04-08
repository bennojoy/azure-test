from az_base import AzureObject

class Vnet(AzureObject):
        props = {
            'addressSpace': (dict, False),
            'subnets': (list, False)
        }

