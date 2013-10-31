from . sox import *

class WavHandler(SoxHandler):
	name = "wav"
	ext = "wav"

	def encode(self, path, opt, info):
		return self.sox_args(path, opt, info)

def init():
	return WavHandler
