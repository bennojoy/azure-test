import requests
import json
import sys
import time


def azure_common_argument_spec():
    return dict(
        azure_password=dict(aliases=['password'], no_log=True),
        azure_username=dict(aliases=['username']),
        client_id           = dict(required=False, default=None),
        client_secret       = dict(required=False, default=None, no_log=True),
    )

class AzureConn():
    url = None
    resource = None
    token =  None
    def __init__(self, url=None, resource=None, user=None, password=None, client_id=None, client_secret=None, module=None):
        if url:
            self.url = url
        else:
            self.url = 'https://login.windows.net/common/oauth2/token'
        if not client_id:
            #The xplat client id
            client_id = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
        if resource:
            self.resource = resource
        else:
            self.resource = 'https://management.azure.com/'
        if user and password:
            grant_type = 'password'
        if client_id and client_secret:
            grant_type = 'client_credentials'
        payload = { 'resource': self.resource, 'username': user, 'password': password, 'client_id': client_id, 'grant_type': grant_type }
        self.module = module
        token_dict = {}
        try:
            resp = requests.post(self.url, data=payload)
        except requests.exceptions.RequestException as e:
            module.fail_json(msg="error connecting to azure endpoint %s" %str(e))
        token_dict = json.loads(resp.content)
        if 'error' in token_dict.keys():
            module.fail_json(msg=token_dict)
        self.token = token_dict['access_token']
    
    def az_get(self, url):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.get( url, headers = header_dict)
        except requests.exceptions.RequestException as e:
            self.module_fail_json(msg="error connecting to azure endpoint for get operation for url %s" %url)
        return resp
    
    def az_delete(self, url):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.delete( url, headers = header_dict)
        except requests.exceptions.RequestException as e:
            self.module_fail_json(msg="error connecting to azure endpoint for get operation for url %s" %url)
        return resp

    def az_post(self, url, data):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.post( url, headers = header_dict, data=data)
        except requests.exceptions.RequestException as e:
            self.module_fail_json(msg="error connecting to azure endpoint for post operation for url %s" %url)
        return resp

    def az_put(self, url, data):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.put(url, headers = header_dict, data=data)
        except requests.exceptions.RequestException as e:
            self.module_fail_json(msg="error connecting to azure endpoint for put operation for url %s" %url)
        return resp

def create_resource(conn, url=None, data=None, wait_timeout=None, module=None):
    resp = conn.az_put(url, data)
    if resp.status_code == 202:
        if wait_timeout == 0:
            module.exit_json(changed=True, msg="The request for creating the resource has been submitted")
        resource_status(conn, url, 'create', wait_timeout, module)
    else:
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            module.fail_json(msg=resp_data)

def delete_resource(conn, url=None, wait_timeout=None, module=None):
    resp = conn.az_delete(url)
    if resp.status_code == 202:
        if wait_timeout == 0:
            module.exit_json(changed=True, msg="The request for Deleteing the resource has been submitted")
        resource_status(conn, url, 'delete', wait_timeout, module)
    else:
        resp_data =  json.loads(resp.content)
        if 'error' in resp_data.keys():
            module.fail_json(msg=resp_data)

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
        time.sleep(6)
        while timeout > time.time():
            resp = conn.az_get(url)
            resp_data =  json.loads(resp.content)
            if 'error' in resp_data.keys():
                module.fail_json(msg=resp_data)
            if resp_data['properties']['status'] == 'Created':
                module.exit_json(changed=True, msg=resp_data)
            time.sleep(5)
        module.fail_json(msg="timed out waiting for resource to be created")
    if status == 'delete':
        timeout = time.time() + wait_timeout
        time.sleep(1)
        while timeout > time.time():
            resp = conn.az_get(url)
            resp_data =  json.loads(resp.content)
            if 'error' in resp_data.keys():
                if resp_data['error']['code'].find('NotFound') > 0:
                    module.exit_json(changed=True, msg="Resource Deleted")
                else:
                    module.fail_json(msg=resp_data)
            time.sleep(5)
        module.fail_json(msg="timed out waiting for resource to be Deleted")


class Template(object):
    props = {
        'Resources': (list, False),
    }

    def __init__(self):
        self.resources = []

    def _update(self, d, values):
        d.update(values)
        return values

    def res_update(self, d, values):
        d.append(values)
        return values

    def add_resource(self, resource):
        return self.res_update(self.resources, resource)

    def to_json(self, indent=4, sort_keys=False, separators=(',', ': ')):
        t = {}
        t['resources'] = self.resources
        return json.dumps(t, indent=indent, cls=azureencode,
                          sort_keys=sort_keys, separators=separators)

    def JSONrepr(self):
        return [self.parameters, self.resources]

class BaseAzureObject(object):
    def __init__(self, name=None, location=None, tags=None, **kwargs):
        self.name = name
        self.propnames = self.props.keys()
        self.location = location

        # Create the list of properties set on this object by the user
        self.properties = {}
        self.resource = {
            'properties': self.properties,
        }
        self.resource['location'] = self.location
        self.__initialized = True

        # Now that it is initialized, populate it with the kwargs
        for k, v in kwargs.items():
                self.setattr(k, v)

    def JSONrepr(self):
        if self.properties:
            return self.resource
        elif hasattr(self, 'resource_type'):
            return {'Type': self.resource_type}
        else:
            return {}

    def setattr(self, name, value):
        if name in self.propnames:
            expected_type = self.props[name][0]
            if isinstance(expected_type, list):
                if not isinstance(value, list):
                    self._raise_type(name, value, expected_type)
            elif isinstance(expected_type, dict):
                if not isinstance(value, dict):
                    self._raise_type(name, value, expected_type)
            return self.properties.__setitem__(name, value)
        type_name = getattr(self, 'resource_type', self.__class__.__name__)
        raise AttributeError("%s object does not support attribute %s" %
                             (type_name, name))
    def _raise_type(self, name, value, expected_type):
        raise TypeError('%s is %s, expected %s' %
                        (name, type(value), expected_type))

class azureencode(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'JSONrepr'):
            return obj.JSONrepr()
        return json.JSONEncoder.default(self, obj)
