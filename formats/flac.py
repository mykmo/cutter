from formats.__base__ import *
from coding import to_bytes

import subprocess

class FlacHandler(BaseHandler):
	name = "flac"
	ext = "flac"

	def encode(self, opt, info):
		self.add("flac sox -")

		if opt.compression is not None:
			self.add("-C %d" % opt.compression)

		self.add_sox_args(opt, info)
		self.add("%f")

		return self.build()

	def tag(self, path, tags):
		args = ["metaflac", "--remove-all-tags", "--import-tags-from=-", path]

		proc = subprocess.Popen(args, stdin = subprocess.PIPE)
		for k, v in tags.items():
			if v is not "":
				proc.stdin.write(to_bytes("%s=%s\n" % (k.upper(), v)))
		proc.stdin.close()

		return proc.wait() is 0

def init():
	return FlacHandler
