#
# Errors for use with SR module
#
# vim:ts=4:noexpandtab:sw=4

from __future__ import print_function
from __future__ import with_statement


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

