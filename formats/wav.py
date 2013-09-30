from formats.__base__ import *

class WavHandler(BaseHandler):
	name = "wav"
	ext = "wav"

	def encode(self, opt, info):
		self.add("wav sox -")
		self.add_sox_args(opt, info)
		self.add("%f")

		return self.build()

def init():
	return WavHandler
