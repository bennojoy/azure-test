#!/usr/bin/python

import json
import requests
import collections
import time

from ansible.module_utils.azure import *

VALID_SUBNET_KEYS = [ 'name', 'subnet']

class Vnet(BaseAzureObject):
    props = {
        'addressSpace': (dict, False),
        'subnets': (list, False),
        'dhcpOptions': (dict, False),
        'vpnClientAddressSpace': (dict, False)
    }


def cmp_dict(dict1, dict2):
    od1 = collections.OrderedDict(sorted(dict1.items()))
    od2 = collections.OrderedDict(sorted(dict2.items()))
    return  od1 == od2

def resource_status(conn=None, url=None, status=None, wait_timeout=None, module=None):
    if status == 'present':
        resp = conn.az_get(url)
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            if resp_data['error']['code'] == 'ResourceNotFound':
                return False
            else:
                module.fail_json(msg=resp_data)
        if resp.status_code == 200:
            return True
        return False
    if status == 'get_json':
        resp = conn.az_get(url)
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            module.fail_json(msg=resp_data)
        return resp.json()
    if status == 'create':
        timeout = time.time() + wait_timeout
        time.sleep(1)
        while timeout > time.time():
            resp = conn.az_get(url)
            resp_data =  json.loads(resp.content)
            if 'error' in resp_data.keys():
                module.fail_json(msg=resp_data)
            if resp_data['properties']['status'] == 'Created':
                module.exitl_json(changed=true, msg=resp_data)
            time.sleep(5)
        module.fail_json(msg="timed out waiting for resource to be created")

def create_resource(conn, url=None, data=None, wait_timeout=None, module=None):
    resp = conn.az_put(url, data)
    if resp.status_code == 202:
        if wait_timeout == 0:
            module.exit_json(changed=True, msg="The request for creating the Vnet has been submitted")
        resource_status(conn, url, 'create', wait_timeout)
    else:
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            module.fail_json(msg=resp_data)
        

def main():
    argument_spec = azure_common_argument_spec()
    argument_spec.update(dict(
        sub_id          = dict(required=True),
        resource_group  = dict(required=True),
        name            = dict(required=False, default='default_vnet'),
        location        = dict(required=False, default='eastasia'),
        wait            = dict(required=False, type='bool', default=True),
        wait_timeout    = dict(required=False, type='int', default=480),
        address_spaces  = dict(type='list',   required=False, default=['10.0.0.0/16']),
        subnets         = dict(type='list',   required=False, default=[{'name':'default', 'subnet':'10.0.1.0/24'}]),
        )
    ) 
    module = AnsibleModule(
        argument_spec=argument_spec,
    )
    address = []
    subnets = []

    username    = module.params.get('username')
    password    = module.params.get('password')
    client_id   = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
    sub_id      = module.params.get('sub_id')
    name        = module.params.get('name')
    location    = module.params.get('location')
    address     = module.params.get('address_spaces')
    subnets     = module.params.get('subnets')
    res_grp     = module.params.get('resource_group')
    wait        = module.params.get('wait')
    wait_tmout  = module.params.get('wait_timeout')
    if not wait:
        wait_tmout = 0

    address_space=dict(addressPrefixes=address)
    put_url = 'https://management.azure.com/subscriptions/' + sub_id + '/resourceGroups/' + res_grp + '/providers/Microsoft.ClassicNetwork/virtualNetworks/' + name + '?api-version=2014-06-01'

    # Azure expects the subnet to have the key addressPrefix, so lets substitute subnet with addressPrefix
    for idx, val in enumerate(subnets):
        for j in val.keys():
            if j not in VALID_SUBNET_KEYS:
                module.fail_json(msg = "%s is not a valid key for 'subnets' param,The valid ones are %s" %(j, VALID_SUBNET_KEYS ))
            if j == 'subnet':
                subnets[idx]['addressPrefix'] = subnets[idx]['subnet']
                subnets[idx].pop('subnet', None)
            
    # Make a connection to the azure arm endpoint to get a valid token    
    conn = AzureConn(user=username, password=password, client_id=client_id, module=module)

    template = Template()
    net1 = Vnet(name=name, location=location, addressSpace=address_space, subnets=subnets)
    template.add_resource(net1)
    data = json.loads(template.to_json())
    vnet = data['resources'][0]
    if not resource_status(conn, put_url, 'present', wait_tmout, module):
        create_resource(conn, put_url, json.dumps(vnet), wait_tmout, module)
    else:
        vnet_json = resource_status(conn, put_url, 'get_json')
        vnet_data = json.loads(json.dumps(vnet_json))
        vnet_data.pop('id')
        vnet_data.pop('type')
        vnet_data.pop('name')
        vnet_data['properties'].pop('provisioningState')
        vnet_data['properties'].pop('siteId')
        vnet_data['properties'].pop('inUse')
        vnet_data['properties'].pop('status')
        vnet_current = data['resources'][0]
        if cmp_dict(vnet_current, vnet_data):
            res_json  = resource_status(conn, put_url, 'get_json')
            module.exit_json(changed=False, res=res_json) 
        else:
            create_resource(conn, put_url, json.dumps(vnet), wait_tmout, module)

# import module snippets
from ansible.module_utils.basic import *

main()
