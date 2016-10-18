#!/usr/bin/env python
# vim:ts=4:noexpandtab:sw=4

from sr.sr import ServiceRegistry
from pprint import pprint

foo = ServiceRegistry(username='pino',password='1en1em1en1e',baseurl='https://serviceregistry.test.surfconext.nl/janus/app.php/api')

#foo.list();
#foo.list(entityid='http://ste.test.iqualify.nl/SAML2')

print("\nFetching basic record\n\n")
basic = foo.get('bazo:test',)
pprint(basic)
id = basic['id']
print("Found entity with id=%u\n" % id)

print("\nFetching full record\n\n")
extended = foo.get(id)
extended['metadata']['OrganizationName'] = {"en": "Bas is erg tof"}

pprint(extended)

print("\nUpdating record\n\n")
foo.update(id,extended)

print("\nAdding record\n\n")
extended['name'] = 'bazo:test3'
newentity = foo.add(extended)

print("\nFetching full new record\n\n")
extended2 = foo.get(newentity['id'])
pprint(extended2)

print("\nRemoving entity\n\n")
foo.delete(newentity['id'])
