from . sox import *

class WavHandler(SoxHandler):
	name = "wav"
	ext = "wav"

	def decode(self, filename):
		return ["cat", filename]

	def encode(self, path, opt, info):
		return self.sox_args(path, opt, info)

def init():
	return WavHandler
