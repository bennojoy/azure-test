#!/usr/bin/python
import az_conn
import json
from az_base import Template
from az_vnet import *
import requests

USERN     = '<email>'
PASSN     = '<pass>'
CLIENT_SECRET = 'UxxxxxxDkoicj0TCZuk='
CLIENT_ID     = 'e5f1b4b8df'
SUB_ID = 'ac0d7bc7-358a-88bb'
NAME = 'benn'
RES_GROUP = 'bentest'
put_url = 'https://management.azure.com/subscriptions/' + SUB_ID + '/resourceGroups/' + RES_GROUP + '/providers/Microsoft.ClassicNetwork/virtualNetworks/' + NAME + '?api-version=2014-06-01'
conn = az_conn.AzureConn(user=USERN, password=PASSN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

template = Template()
net1 = Vnet(name='bennn', location='eastasia', addressSpace=dict(addressprefixes=['192.168.0.0/16']), subnets=[dict(name='benno', addressprefix='192.168.1.0/24')])
template.add_resource(net1)
template.add_version()
template.add_schema()
data = json.loads(template.to_json())
vnet = data['resources'][0]
resp = conn.az_get(put_url)
#resp = conn.az_put(put_url, data=json.dumps(vnet))
if resp.status_code == 200:
    print "object exists"
    print resp.json()
else:
    print "object does not exists"
