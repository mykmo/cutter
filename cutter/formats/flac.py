from . sox import *
from . command import *
from .. coding import to_bytes

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

		proc = Command(args, stdin=PIPE)
		if not proc.ready():
			return False

		for k, v in tags.items():
			proc.stdin.write(to_bytes("%s=%s\n" % (k.upper(), v)))

		proc.stdin.close()
		proc.close()

		return proc.status is 0

def init():
	return FlacHandler
