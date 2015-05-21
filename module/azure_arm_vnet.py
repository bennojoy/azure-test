#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: azure_arm_vnet
short_description: create, remove Virtual networks in Azure via Azure Resource Manager
description:
    - Creates or removes Virtual Networks.
version_added: "2.0"
options:
  username:
    description:
      - The email/username of the azure account
    required: false
    default: null
  password:
    description:
      - Password to the azure account
    required: false
    default: null
  client_id:
    description:
      - client_id if you are using application authentication, mutually exclusive with username.
    required: false
    default: null
  client_secret:
    description:
      - client_secret, if you are using application authentication, mutually exclusive with password.
    required: false
    default: null
  name:
    description:
      - The name of the virtual network to be created
    required: false
    default: null
  resource_group:
    description:
      - The name of the resource group where the virtual network is to be created
    required: True
  location:
    description:
      - The location where the virtual network is to be created
    required: False
    default: 'eastasia'  
  sub_id:
    description:
      - The subscription id  where the virtual network is to be created
    required: true
  state:
    description:
      - The state of the resource present/absent
    required: False
    default: 'present'   
  wait:
    description:
      - wether to wait for state of the resourse to become present/absent
    required: false
    default: 'yes'  
  wait_timeout:
    description:
      - The time in seconds for the  state of the resourse to become present/absent
    required: false
    default: 480
  s_s_vpn:
    description:
      - The Site to Site vpn configuration, see Example for usage
    required: false
    default: null
  address_spaces:
    description:
      - The main addressspaces to be used for this Virtual Network, see Example for usage
    required: false
    default: "10.0.0.0/16"
  subnets:
    description:
      - The subnets to be created for this Virtual Network, see Example for usage
    required: false
    default: "10.0.1.0/24"
  dns_servers:
    description:
      - The dns servers to be assigned  for the machines provisioned in thsi  Virtual Network, see Example for usage
    required: false
    default: null

author: benno@ansible.com
'''

EXAMPLES = '''
# Basic vnet provisioning example

- hosts: all
  connection: local
  tasks:
   - azure_arm_vnet:
       username: '<email>'
       password: '<password>'
       resource_group: bentest
       sub_id: '3f7e29ba-24e-49a14bda37'
       name: bennet
       dns_servers: ["2.2.2.2", "3.3.3.3"]
       address_spaces:
            - 192.168.0.0/16
       subnets:
         - name: ben1
           subnet: 192.168.1.0/24

#Vnet with site to site vpn configured

- hosts: all
  connection: local
  tasks:
   - azure_arm_vnet:
       username: '<email>'
       password: '<password>'
       resource_group: bentest
       sub_id: '3f70-42f6-8d9c-5bda37'
       name: bennet
       dns_servers: "2.2.2.2,3.3.3.3"
       address_spaces:
            - 192.168.0.0/16
       subnets:
         - name: ben1
           subnet: 192.168.1.0/24
         - name: GatewaySubnet
           subnet: 192.168.2.0/24
       s_s_vpn:
            site_name: "bentest"
            address_spaces: ["10.30.0.0/16"]
            gateway_ip: "3.1.1.1"


#Delete a vnet

- hosts: all
  connection: local
  tasks:
   - azure_arm_vnet:
       username: '<email>'
       password: '<password>'
       resource_group: bentest
       state: 'absent'
       sub_id: '3f0-42f6-8d9c-bda37'
       name: bennet

'''


import json
import collections
import time

VALID_SUBNET_KEYS = [ 'name', 'subnet']
VALID_SVPN_KEYS = [ 'site_name', 'address_spaces', 'gateway_ip']

from ansible.module_utils.azure import *

class Vnet(BaseAzureObject):
    props = {
        'addressSpace': (dict, False),
        'subnets': (list, False),
        'dhcpOptions': (dict, False),
        'gatewayProfile': (dict, False),
        'vpnClientAddressSpace': (dict, False)
    }


def cmp_dict(dict1, dict2):
    od1 = collections.OrderedDict(sorted(dict1.items()))
    od2 = collections.OrderedDict(sorted(dict2.items()))
    return  od1 == od2

def main():
    argument_spec = azure_common_argument_spec()
    argument_spec.update(dict(
        sub_id              = dict(required=True),
        resource_group      = dict(required=True),
        state               = dict(default='present', choices=['present', 'absent']),
        name                = dict(required=False, default='default_vnet'),
        location            = dict(required=False, default='eastasia'),
        wait                = dict(required=False, type='bool', default=True),
        wait_timeout        = dict(required=False, type='int', default=480),
        s_s_vpn             = dict(required=False, default=None),
        address_spaces      = dict(type='list',   required=False, default=['10.0.0.0/16']),
        subnets             = dict(type='list',   required=False, default=[{'name':'default', 'subnet':'10.0.1.0/24'}]),
        dns_servers         = dict(type='list',   required=False, default=None),
        )
    ) 
    module = AnsibleModule(
        argument_spec=argument_spec,
    )
    address = []
    subnets = []

    username        = module.params.get('username')
    password        = module.params.get('password')
    client_id       = module.params.get('client_id')
    client_secret   = module.params.get('client_id')
    sub_id          = module.params.get('sub_id')
    state           = module.params.get('state')
    name            = module.params.get('name')
    location        = module.params.get('location')
    address         = module.params.get('address_spaces')
    subnets         = module.params.get('subnets')
    s_vpn           = module.params.get('s_s_vpn')
    dns             = module.params.get('dns_servers')
    res_grp         = module.params.get('resource_group')
    wait            = module.params.get('wait')
    wait_tmout      = module.params.get('wait_timeout')
    if not wait:
        wait_tmout = 0
    
    #The endpoint for vnet api
    put_url        = 'https://management.azure.com/subscriptions/' + sub_id + '/resourceGroups/' + res_grp + '/providers/Microsoft.ClassicNetwork/virtualNetworks/' + name + '?api-version=2014-06-01'
    
    # Make a connection to the azure arm endpoint to get a valid token    
    conn = AzureConn(user=username, password=password, client_id=client_id, client_secret=client_secret, module=module)
    
    #Delete if state is absent
    if state == 'absent':
        if not resource_status(conn, put_url, 'present', wait_tmout, module):
            module.exit_json(changed=False, msg="Resourse does not exist")
        else:
            delete_resource(conn, put_url, wait_tmout, module)
            
    #Not delete so create or check if it exists
    address_space      = dict(addressPrefixes=address)
    if dns:
        dns            = dict(dnsServers=dns)

    # Azure expects the subnet to have the key addressPrefix, so lets substitute subnet with addressPrefix
    for idx, val in enumerate(subnets):
        for j in val.keys():
            if j not in VALID_SUBNET_KEYS:
                module.fail_json(msg = "%s is not a valid key for 'subnets' param,The valid ones are %s" %(j, VALID_SUBNET_KEYS ))
            if j == 'subnet':
                subnets[idx]['addressPrefix'] = subnets[idx]['subnet']
                subnets[idx].pop('subnet', None)

    #Lets check if site to site values are valid if provided
    if s_vpn:
        for i in s_vpn.keys():
            if i not in VALID_SVPN_KEYS:
                module.fail_json(msg = "%s is not a valid key for site vpn  param,The valid ones are %s" %(i, VALID_SVPN_KEYS ))
            if i =='address_spaces' and not isinstance(s_vpn[i], list):
                module.fail_json(msg="address_spaces in s_vpn param must be a list")
        gateway = dict(size="Small", localNetworkSites=[dict(localNetworkSiteName=s_vpn['site_name'], addressSpace=s_vpn['address_spaces'], vpnGatewayIpAddress=s_vpn['gateway_ip'], connectionTypes=['IPsec'])])
    else:
        gateway = None
    template = Template()
    net1 = Vnet(name=name, location=location, addressSpace=address_space, subnets=subnets, dhcpOptions=dns, gatewayProfile=gateway)
    template.add_resource(net1)
    data = json.loads(template.to_json())
    vnet = data['resources'][0]
    if not resource_status(conn, put_url, 'present', wait_tmout, module):
        create_resource(conn, put_url, json.dumps(vnet), wait_tmout, module)
    else:
        vnet_json = resource_status(conn, put_url, 'get_json', 0, module)
        vnet_data = json.loads(json.dumps(vnet_json))
        vnet_data.pop('id')
        vnet_data.pop('type')
        vnet_data.pop('name')
        vnet_data['properties'].pop('provisioningState')
        vnet_data['properties'].pop('siteId')
        vnet_data['properties'].pop('inUse')
        vnet_data['properties'].pop('status')
        vnet_current = data['resources'][0]
        if not dns:
            vnet_current['properties'].pop('dhcpOptions')
        if not s_vpn:
            vnet_current['properties'].pop('gatewayProfile')
#        module.exit_json(cur=vnet_current, az=vnet_data)
        if cmp_dict(vnet_current, vnet_data):
            res_json  = resource_status(conn, put_url, 'get_json', 0, module)
            module.exit_json(changed=False, res=res_json) 
        else:
            create_resource(conn, put_url, json.dumps(vnet), wait_tmout, module)

# import module snippets
from ansible.module_utils.basic import *

main()
