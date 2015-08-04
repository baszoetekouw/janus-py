#!/usr/bin/env python

from pprint import pprint
from time import sleep
from sr.sr import ServiceRegistry, ServiceRegistryError
import suds.client
from suds.transport.https import HttpAuthenticated

import logging
#logging.basicConfig(level=logging.DEBUG)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)
#logging.getLogger('suds.transport').setLevel(logging.DEBUG)
#logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
#logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)



# check entities in ServiceRegistry one by one
sr = ServiceRegistry(username='pino',password='ieniemienie',baseurl='https://serviceregistry.surfconext.nl/janus/app.php/api')

eids = sr.listEids()

for eid in eids:

	#print("fetching eid=%u" % eid)
	entity = sr.getById(eid)

	# check state
	if not entity['state']=="testaccepted": continue

	# check if this entity had an institution_id
	if not 'metadata'         in entity                    : continue
	if not 'coin'             in entity['metadata']        : continue
	if not 'institution_guid' in entity['metadata']['coin']: continue;

	print("%u" % eid)


print("----------------")


exit(0)
