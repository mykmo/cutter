from formats.__base__ import *
from utils import to_bytes

import subprocess

class OggHandler(BaseHandler):
	name = "ogg"
	ext = "ogg"

	def encode(self, opt, info):
		self.add("cust ext=%s sox -" % self.ext)

		if opt.compression is not None:
			self.add("-C %d" % opt.compression)

		self.add_sox_args(opt, info)
		self.add("%f")

		return self.build()

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
