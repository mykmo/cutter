from . sox import *
from .. coding import to_bytes

import subprocess

class FlacHandler(SoxHandler):
	name = "flac"
	ext = "flac"
	cmd = "flac"

	def encode(self, path, opt, info):
		if opt.compression is not None:
			self.set_compression(opt.compression)

		return self.sox_args(path, opt, info)

	def decode(self, filename):
		return [self.cmd, "-d", "-c", "-s", filename]

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
