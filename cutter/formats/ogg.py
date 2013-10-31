from . sox import *
from .. coding import to_bytes

import subprocess

class OggHandler(SoxHandler):
	name = "ogg"
	ext = "ogg"

	def encode(self, path, opt, info):
		if opt.compression is not None:
			self.set_compression(opt.compression)

		return self.sox_args(path, opt, info)

	def tag(self, path, tags):
		args = ["vorbiscomment", "--raw", "--write", path]

		proc = subprocess.Popen(args, stdin = subprocess.PIPE)
		for k, v in tags.items():
			if v is not "":
				proc.stdin.write(to_bytes("%s=%s\n" % (k.upper(), v)))
		proc.stdin.close()

		return proc.wait() is 0

def init():
	return OggHandler
