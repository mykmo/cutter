from . sox import *
from . command import *
from .. coding import to_bytes

class OggHandler(SoxHandler):
	name = "ogg"
	ext = "ogg"

	def encode(self, path, opt, info):
		if opt.compression is not None:
			self.set_compression(opt.compression)

		return self.sox_args(path, opt, info)

	def tag(self, path, tags):
		args = ["vorbiscomment", "--raw", "--write", path]

		proc = Command(args, stdin=PIPE)
		if not proc.ready():
			return False

		for k, v in tags.items():
			proc.stdin.write(to_bytes("%s=%s\n" % (k.upper(), v)))

		proc.stdin.close()
		proc.close()

		return proc.status is 0

def init():
	return OggHandler
