#!/usr/bin/python

import requests
import json

URL      = 'https://login.windows.net/0b4d9aac-c9b7-4832-9013-2ab4991d5533/oauth2/token?api-version=1.0'
SUB_URL  = 'https://management.azure.com/subscriptions/ac0d7bc7-358a-4a86-831d-571f4d0888bb/resourcegroups?api-version=2015-01-01'
#SUB_URL  = 'https://management.core.windows.net/subscriptions'
USER     = '<email>'
PASS     = '<pass>'
RESOURCE = 'https://management.azure.com/'
CLIENT_SECRET = 'SECRET'
CLIENT_ID     = 'e5f1b4be-548f-43bb-a311-b801858a08df'

payload = { 'resource': RESOURCE, 'username': USER, 'password': PASS, 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'password' }

token_dict = {}
resp = requests.post(URL, data=payload)
token_dict = json.loads(resp.content)
token = token_dict['access_token']

header_dict = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
resp = requests.get( SUB_URL, headers = header_dict)
print resp.content

