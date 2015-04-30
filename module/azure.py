import requests
import json
import sys


def azure_common_argument_spec():
    return dict(
        azure_password=dict(aliases=['password'], no_log=True),
        azure_username=dict(aliases=['username']),
    )

class AzureConn():
    url = None
    resource = None
    token =  None
    def __init__(self, url=None, resource=None, user=None, password=None, client_id=None, module=None):
        if url:
            self.url = url
        else:
            self.url = 'https://login.windows.net/common/oauth2/token'
        if resource:
            self.resource = resource
        else:
            self.resource = 'https://management.azure.com/'
        payload = { 'resource': self.resource, 'username': user, 'password': password, 'client_id': client_id, 'grant_type': 'password' }
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
