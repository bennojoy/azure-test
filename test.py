from azure import Template
from vnet import *

template = Template()
net1 = Vnet(name='bennn', location='usa', addressSpace=dict(addressprefixes=['192.168.1.0/24']), subnets=[dict(name='benno', addressprefix='192.168.1.0/24')])
template.add_resource(net1)
template.add_version()
template.add_schema()
print template.to_json()
