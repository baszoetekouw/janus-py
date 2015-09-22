#!/usr/bin/env python

#
# Module to address SURFconext Serviceregistry
#

from __future__ import print_function
from __future__ import with_statement

import urllib.parse
import urllib3
import urllib3.util
import certifi
import json
import platform, pwd, os
from pprint import pprint


class Error(Exception):
	pass

class HttpConnectionError(Error):
	def __init__(self, status, msg):
		self.status = status
		self.msg = msg

class ServiceRegistryError(Error):
	def __init__(self, status, msg):
		self.status = status
		self.msg = msg


class ServiceRegistry:
	""" ServiceRegistry class"""
	def __init__(self,username,password,baseurl='https://serviceregistry.surfconext.nl/janus/app.php/api'):
		self._ua       = 'Python/SRlib'
		self._username = username
		self._password = password
		self._baseurl  = baseurl
		if not self._baseurl.endswith('/'): 
			self._baseurl+='/'

		self._http = urllib3.PoolManager(headers={"UserAgent": self._ua},
		                cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

	# create http request with specified parameters
	def _http_req(self,api_url,method='GET',params=None,payload=None):
		uri = '%s%s' % (self._baseurl,api_url)
		headers = urllib3.util.make_headers(basic_auth='%s:%s' % (self._username, self._password))
		body = None

		if params:
			query = urllib.parse.urlencode(params)
			uri += '?' + query

		if payload:
			body = json.dumps(payload, indent=4, sort_keys=True)
			headers['Content-type'] = 'application/json';

		#print("==> calling url '%s'" % uri)

		req = self._http.request(method, uri, headers=headers, body=body, redirect=False)
		if not 200<=req.status<400:
			raise ServiceRegistryError(req.status,"Error in http request: %s" % req.reason)

		#pprint(req.__dict__)

		decoded = None
		if req.headers['Content-Type']=='application/json':
			decoded = json.loads(req.data.decode())

		return {
			'status': req.status,
			'raw': req.data,
			'decoded': decoded
		}

	# returns list of entities with basic data
	def list(self, entityid=None):
		params = {}
		if entityid:
			params['name'] = entityid
		data = self._http_req('connections',params=params)
		#obj = json.JSONDecoder()
		return data['decoded']['connections']

	# returns list of all known eids
	def listEids(self):
		entities = self.list()
		return sorted([int(eid) for eid in entities])

	def getByEntityId(self, entityid):
		data = self.list(entityid=entityid)
		if (len(data)==0):
			return None

		eid = int( next(iter(data)) )
		entity = self.getById(eid)

		return entity

		#return list(data.values())[0]

	def getById(self, eid):
		data = self._http_req('connections/%u' % eid)
		#print("-------------\n")
		#pprint(data['decoded'])
		#print("-------------\n")
		return data['decoded']

	def updateById(self, eid, entity, note=None):
		# we need to unset some fields in the entity, if they exist
		newentity = entity
		for field in ('createdAtDate','id','isActive','parentRevision','revisionNr','updatedAtDate','updatedByUserName','updatedFromIp'):
			if field in newentity: del newentity[field]

		if note:
			newentity['revisionNote'] = note
		else:
			newentity['revisionNote'] = "Automatic change by user %s on %s" % (pwd.getpwuid(os.getuid()).pw_name,platform.node())

		for field in ('allowedConnections','blockedConnections','disableConsentConnections','arpAttributes','manipulationCode'):
			if not field in newentity:
				raise ServiceRegistryError(-1,"%s MUST be specified, otherwise the API will be silently truncate it" % field)

		result = self._http_req('connections/%u' % eid, method='PUT', payload=newentity)
		status = result['status']
		if not status==201:
			raise ServiceRegistryError(status,"Couldn't write entity %u: %u" % (eid,status))

		#print("-------------\n")
		#pprint(result['decoded'])
		#print("-------------\n")
		return result['decoded']

	def deleteById(self, eid):
		result = self._http_req('connections/%u' % eid, method='DELETE')
		status = result['status']
		if not status == 302:
			raise ServiceRegistryError(status, "Could not delete entity %u: %u" % (eid,status))

		#print("-------------\n")
		#pprint(result['decoded'])
		#print("-------------\n")
		return result['decoded']

	def add(self, entity):
		result = self._http_req('connections', method='POST', payload=entity)
		status = result['status']
		if not status==201:
			raise ServiceRegistryError(status,"Couldn't add entity")

		#print("-------------\n")
		#pprint(result['decoded'])
		#print("-------------\n")
		return result['decoded']


