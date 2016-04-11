#!/usr/bin/env python
# vim:ts=4:noexpandtab:sw=4

#
# Module to address SURFconext Serviceregistry
#

from __future__ import print_function
from __future__ import with_statement

import urllib.parse
import urllib3
import urllib3.util
import json
import platform, pwd, os
import os.path
import site
from collections import OrderedDict
from pprint import pprint

import numpy as np
from scipy.sparse import dok_matrix

from sr.error import ServiceRegistryError


class ServiceRegistry:
	""" ServiceRegistry class"""
	def __init__(self,username,password,baseurl='https://serviceregistry.surfconext.nl/janus/app.php/api', debug=0):
		self._ua       = 'Python/SRlib'
		self._debug    = debug
		self._username = username
		self._password = password
		self._baseurl  = baseurl
		if not self._baseurl.endswith('/'): 
			self._baseurl+='/'

		self._http = urllib3.PoolManager(headers={"UserAgent": self._ua},
				cert_reqs='CERT_REQUIRED', ca_certs=self.__findcertbundle())

		self._connections = dict()

	def debug(self,dlevel,msg):
		if not ( dlevel & self._debug ):
			return

		print("--> debug %u: " % dlevel, sep='')
		if type(msg) is str:
			print(msg)
		else:
			pprint(msg)

	# return location of CA root store
	def __findcertbundle(self):
		try:
			import certifi
			return certifi.where()
		except ImportError:
			self.debug(1,"certifi package not found")

		capaths = [ 
			'/etc/ssl/certs/ca-certificates.crt',
			'/etc/ssl/certs/curl-ca-bundle.crt', 
			'/etc/pki/tls/certs/ca-bundle.crt'
		]
		for p in capaths:
			if os.path.isfile(p):
				self.debug(1,"using CA store at '%s'" % p)
				return p
		raise ServiceRegistryError(None,"Can't find CA root certificate store (try installing the certifi package)")

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
			headers['Content-type'] = 'application/json'

		self.debug(0x02,"==> calling url '%s'" % uri)

		req = self._http.request(method, uri, headers=headers, body=body, redirect=False)
		if not 200<=req.status<400:
			raise ServiceRegistryError(req.status,"Error in http request: %s" % req.reason)

		self.debug(0x03,req.__dict__)

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
		entities = data['decoded']['connections']

		# hash key will be string (damned json), so convert to integer
		entities = {int(k): v for k, v in entities.items()}
		entities_list = sorted(entities.items(), key=lambda x: x[0])
		entities = OrderedDict(entities_list)
		return entities

	def list_full(self, state):
		entities = self.list()
		for eid, entity in entities.items():
			if entity['isActive'] and entity['state']==state:
				print(eid)
				entities[eid] = self.get(eid)
		return entities

	# returns list of all known eids
	def list_eids(self):
		entities = self.list()
		return sorted([int(eid) for eid in entities])

	def get_by_entityid(self, entityid):
		data = self.list(entityid=entityid)
		if len(data) == 0:
			return None

		eid = int( next(iter(data)) )
		entity = self.get(eid)

		self.debug(0x01,entity)
		return entity

	def get(self, eid) -> dict:
		data = self._http_req('connections/%u' % eid)
		self.debug(0x01, data['decoded'])
		return data['decoded']

	def replace(self, eid, entity, note=None, force=False):
		# we need to unset some fields in the entity, if they exist
		newentity = entity
		for field in ('createdAtDate','id','isActive','parentRevision','revisionNr','updatedAtDate','updatedByUserName','updatedFromIp'):
			if field in newentity: del newentity[field]

		if note:
			newentity['revisionNote'] = note
		else:
			newentity['revisionNote'] = "Automatic change by user %s on %s" % (pwd.getpwuid(os.getuid()).pw_name,platform.node())

		if not force:
			for field in ('allowedConnections','blockedConnections','disableConsentConnections','arpAttributes','manipulationCode'):
				if not field in newentity:
					raise ServiceRegistryError(-1,"%s MUST be specified, otherwise the API will be silently truncate it" % field)

		result = self._http_req('connections/%u' % eid, method='PUT', payload=newentity)
		status = result['status']
		if not status==201:
			raise ServiceRegistryError(status,"Couldn't write entity %u: %u" % (eid,status))

		self.debug(0x01,result)
		return result['decoded']


	def update(self, eid, entity, note=None):
		# fetch the current entity
		newentity = self.get(eid)
		for field in ('createdAtDate', 'id', 'isActive', 'parentRevision', 'revisionNr', 'updatedAtDate', 'updatedByUserName','updatedFromIp'):
			if field in newentity: del newentity[field]

		# replace fields as specified in entity
		for field in entity:
			if field=='metadata':
				for mfield in entity['metadata']:
					newentity['metadata'][mfield] = entity['metadata'][mfield]
			else:
				newentity[field] = entity[field]

		result = self.replace(eid,newentity,note=note)
		return result

	def delete(self, eid):
		result = self._http_req('connections/%u' % eid, method='DELETE')
		status = result['status']
		if not status == 302:
			raise ServiceRegistryError(status, "Could not delete entity %u: %u" % (eid,status))

		self.debug(0x01,result)
		return result['decoded']

	def add(self, entity):
		result = self._http_req('connections', method='POST', payload=entity)
		status = result['status']
		if not status==201:
			raise ServiceRegistryError(status,"Couldn't add entity")

		self.debug(0x01,result)
		return result['decoded']


	def connectiontable(self, state='prodaccepted'):
		entities = self.list_full(state)

		# sort entities
		idps = OrderedDict()
		sps  = OrderedDict()
		for eid, entity in entities.items():
			if entity['isActive'] and entity['state']==state:
				if entity['type']=='saml20-idp':
					idps[eid] = entity
				elif entity['type']=='saml20-sp':
					sps[eid] = entity
				else:
					raise(ServiceRegistryError(0,"unknown type `%s' for eid=%s" % (entity['type'],entity['id'])))

		# use numpy here for the connection matrix to simplify extraction of rows and columns lateron
		max_eid = max(entities.keys())
		#print(max_eid)
		connections = dok_matrix((max_eid+1,max_eid+1), dtype=np.bool_)

		for idp_eid, idp_entity in idps.items():
			#pprint(idp_entity)
			sps_allowed = set([e['id'] for e in idp_entity['allowedConnections']])
			for sp_eid, sp_entity in sps.items():
				idps_allowed = set([ e['id'] for e in sp_entity['allowedConnections'] ])

				acl =     ( idp_entity['allowAllEntities'] or (sp_eid  in sps_allowed ) ) \
				      and ( sp_entity[ 'allowAllEntities'] or (idp_eid in idps_allowed) )
				connections[idp_eid,sp_eid] = acl

		self._connections[state] = dict()
		self._connections[state]['idp'] = idps
		self._connections[state]['sp' ] = sps
		self._connections[state]['acl'] = connections

		return connections
