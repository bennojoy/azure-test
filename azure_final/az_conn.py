#!/usr/bin/python

import requests
import json
import sys

class AzureConn():
    url = None
    resource = None
    token =  None
    def __init__(self, url=None, resource=None, user=None, password=None, client_id=None, client_secret=None):
        
        if url:
            self.url = url
        else:
#            self.url = 'https://login.windows.net/' + sub_id + '/oauth2/token?api-version=1.0'
            self.url = 'https://login.windows.net/common/oauth2/token'
        if resource:
            self.resource = resource
        else:
            self.resource = 'https://management.azure.com/'
        
        payload = { 'resource': self.resource, 'username': user, 'password': password, 'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'password' }
        token_dict = {}
        try:
            resp = requests.post(self.url, data=payload)
        except requests.exceptions.RequestException as e:   
            print e
            sys.exit(1) 
        token_dict = json.loads(resp.content)
        self.token = token_dict['access_token']

    def az_get(self, url):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.get( url, headers = header_dict)
        except requests.exceptions.RequestException as e:    
            print e
        return resp
    
    def az_post(self, url, data):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        resp = requests.post( url, headers = header_dict, data=data)
    
    def az_put(self, url, data):
        header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        try:
            resp = requests.put(url, headers = header_dict, data=data)
        except requests.exceptions.RequestException as e:    
            print e
        return resp
