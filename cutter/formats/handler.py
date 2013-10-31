def dev_null():
	return open("/dev/null")

class Handler:
	def __init__(self, handler):
		self.handler = handler

	def __getattr__(self, attr):
		return getattr(self.handler, attr)

from . encoder import EncoderHandler
from . decoder import DecoderHandler
