#!/usr/bin/python
import az_conn
import json
from az_base import Template
from az_vnet import *
import requests
import collections
import time

USERN     = 'com'
PASSN     = 'd'
CLIENT_SECRET = 'Utwm9uicj0TCZuk='
CLIENT_ID     = 'e5f1b48a08df'
SUB_ID = 'ac0d7bc7-358a-4a86-831d-571f4d0888bb'
NAME = 'bennn'
RES_GROUP = 'bentest'
put_url = 'https://management.azure.com/subscriptions/' + SUB_ID + '/resourceGroups/' + RES_GROUP + '/providers/Microsoft.ClassicNetwork/virtualNetworks/' + NAME + '?api-version=2014-06-01'
conn = az_conn.AzureConn(user=USERN, password=PASSN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def cmp_dict(dict1, dict2):
    od1 = collections.OrderedDict(sorted(dict1.items()))
    od2 = collections.OrderedDict(sorted(dict2.items()))
    return  od1 == od2

    

def resource_status(conn=None, url=None, status=None, wait_timeout=None):
    if status == 'present':
        resp = conn.az_get(url)
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            if resp_data['error']['code'] == 'ResourceNotFound':
                return False
            else:
                print resp_data['error']['code'] + ":    " + resp_data['error']['message']
                exit(1)
        if resp.status_code == 200:
            return True
        return False
    if status == 'get_json':
        resp = conn.az_get(url)
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            print resp_data['error']['code'] + ":    " + resp_data['error']['message']
            exit(1)
        return resp.json()
    if status == 'create':
        timeout = time.time() + wait_timeout
        time.sleep(1)
        while timeout > time.time():
            resp = conn.az_get(url)
            print resp.status_code
            print resp.content
            resp_data =  json.loads(resp.content)
            if 'error' in resp_data.keys():
                print resp_data['error']['code'] + ":    " + resp_data['error']['message']
                exit(1)
            if resp_data['properties']['status'] == 'Created':
                print "resource created \n"
                print json.dumps(resp_data, indent=3)
                exit(0)
            time.sleep(5)
        print "timed out waiting for resource to be created"

def create_resource(conn, url=None, data=None):
    resp = conn.az_put(put_url, data)
    if resp.status_code == 202:
            print "accepted"
            if resource_status(conn, put_url, 'create', 300):
                print "sucessfully created resource"
    else:
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            print resp_data['error']['code'] + ":    " + resp_data['error']['message']
            exit(1)
    
         
template = Template()
net1 = Vnet(name='bennn', location='eastasia', addressSpace=dict(addressPrefixes=['192.168.0.0/16']), subnets=[dict(name='benno', addressPrefix='192.168.5.0/24')])
template.add_resource(net1)
template.add_version()
template.add_schema()
data = json.loads(template.to_json())
vnet = data['resources'][0]
if not resource_status(conn, put_url, 'present'):
    create_resource(conn, put_url, json.dumps(vnet))
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
    vnet_current.pop('name')
    if cmp_dict(vnet_current, vnet_data):
        print "resource exists"
        res_json  = resource_status(conn, put_url, 'get_json')
        print json.dumps(res_json, indent=2)
    else:
        create_resource(conn, put_url, json.dumps(vnet))
        


