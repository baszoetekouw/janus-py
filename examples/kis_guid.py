#!/usr/bin/env python
# vim:ts=4:noexpandtab:sw=4

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

# fetch SURFconext klanten from KIS
# create the webservice client
credentials = dict(username='pino', password='1en1em1en1e')
kistransport = HttpAuthenticated(**credentials)
kis = suds.client.Client('https://crm-ws.surfnet.nl/getKlant.svc?singlewsdl',transport=kistransport)

kisklanten = kis.service.getKlantenByDienst('SURFconext')
klanten = dict()
for k in kisklanten.Output[0]:
	klanten[k.Organisatiecode] = {
		'iafk'   : k.Organisatiecode,
		'guid'   : k.OrganisatieGUID,
		'dg_code': k.DoelgroepCode,
		'dg_val' : k.DoelgroepValue,
		'naam'   : k.Organisatienaam,
	}

pprint(klanten); exit(0)

# check entities in ServiceRegistry one by one
sr = ServiceRegistry(username='pino',password='1en1em1en1e',baseurl='https://serviceregistry.surfconext.nl/janus/app.php/api')

eids = sr.list_eids()

for eid in eids:


	#print("fetching eid=%u" % eid)
	entity = sr.get(eid)

	# check if this entity had an institution_id
	if not 'metadata'       in entity                    : continue
	if not 'coin'           in entity['metadata']        : continue
	if not 'institution_id' in entity['metadata']['coin']: continue;

	print("https://serviceregistry.surfconext.nl/simplesaml/module.php/janus/editentity.php?eid=%-2u %s %s" % (eid,entity['state'],entity['type']))
	if eid>200: exit(0)
	continue

	#if not entity['state']=='testaccepted':
	#	continue

	try:
		inst = entity['metadata']['coin']['institution_id']
	except KeyError:
		continue

	if not inst in klanten:
		print("----------------")
		print("Onbekende instelling '%s' for eid=%u" % (inst,eid))
		continue



	klant = klanten[inst]

	if 'institution_guid' in entity['metadata']['coin'] and entity['metadata']['coin']['institution_guid']==klant['guid']:
		True
		#print("guid=%s already present" % klant['guid'])
	else:
		print("----------------")
		print("eid=%u needs institution_guid for klant=%s" % (eid, inst))
		print("no guid or wrong guid, setting it to %s" % klant['guid'])

		entity['metadata']['coin']['institution_guid'] =  klant['guid'];
		try:
			result = sr.update(eid,entity,note="Automatically adding coin:institution_guid [BaZo]")
		except ServiceRegistryError as error:
			print("Request failed: %u (%s)" % (error.status,error.msg))
			exit(1)

		#pprint(result)

		sleep(1)
		#break

print("----------------")


exit(0)
