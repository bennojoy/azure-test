import json
import re
import types


__version__ = "0.0.1"

class Template(object):
    props = {
        'AzureSchema': (basestring, False),
        'ContentVersion': (basestring, False),
        'Parameters': (dict, False),
        'Variables': (dict, False),
        'Resources': (list, False),
        'Outputs': (dict, False),
    }

    def __init__(self):
        self.azureschema = None
        self.contentversion = {}
        self.variables = {}
        self.outputs = {}
        self.parameters = {}
        self.resources = []
        self.version = None

    def add_condition(self, name, condition):
        self.conditions[name] = condition

    def _update(self, d, values):
        d.update(values)
        return values
    def res_update(self, d, values):
        d.append(values)
        return values

    def add_output(self, output):
        return self._update(self.outputs, output)

    def add_variables(self, name, mapping):
        self.mappings[name] = mapping

    def add_parameter(self, parameter):
        return self._update(self.parameters, parameter)

    def add_resource(self, resource):
        return self.res_update(self.resources, resource)

    def add_schema(self, schema=None):
        if schema:
            self.schema = schema
        else:
            self.schema = "http://schema.management.azure.com/schemas/2014-04-01-preview/deploymentTemplate.json#"
    
    def add_version(self, version=None):
        if version:
            self.version = version
        else:
            self.version = "1.0.0"

    def to_json(self, indent=4, sort_keys=False, separators=(',', ': ')):
        t = {}
        if self.variables:
            t['Variables'] = self.variables
        if self.outputs:
            t['Outputs'] = self.outputs
        if self.parameters:
            t['Parameters'] = self.parameters
        if self.schema:
            t['$schema'] = self.schema
        if self.version:
            t['ContenVersion'] = self.version
        t['resources'] = self.resources

        return json.dumps(t, indent=indent, cls=azureencode,
                          sort_keys=sort_keys, separators=separators)

    def JSONrepr(self):
        return [self.parameters, self.resources]

class BaseAzureObject(object):
    def __init__(self, name=None, apiversion="2014-04-01-preview", location=None, tags=None, 
                                                                    template=None, **kwargs):
        self.name = name
        self.template = template
        self.apiversion = apiversion
        self.location = location
        self.tags = {}
        self.tags = tags
        # Cache the keys for validity checks
        self.propnames = self.props.keys()
        self.attributes = ['dependsOn', 'DeletionPolicy',
                           'Metadata', 'UpdatePolicy',
                           'Condition', 'CreationPolicy']

        # Create the list of properties set on this object by the user
        self.properties = {}
        dictname = getattr(self, 'dictname', None)
        if dictname:
            self.resource = {
                dictname: self.properties,
            }
        else:
            self.resource = self.properties
        if hasattr(self, 'resource_type') and self.resource_type is not None:
            self.resource['type'] = self.resource_type
        self.resource['location'] = self.location
        self.resource['name'] = self.name
        self.resource['tags'] = self.tags
        self.resource['apiVersion'] = self.apiversion
        self.__initialized = True

        # Now that it is initialized, populate it with the kwargs
        for k, v in kwargs.items():
            # Special case Resource Attributes
            if k in self.attributes:
                self.resource[k] = v
            else:
                self.setattr(k, v)

        # Bound it to template if we know it
        if self.template is not None:
            self.template.add_resource(self)

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
        
class AzureObject(BaseAzureObject):
    dictname = 'properties'

class azureencode(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'JSONrepr'):
            return obj.JSONrepr()
        return json.JSONEncoder.default(self, obj)
