class WavpackHandler:
	name = "wavpack"
	ext = "wv"
	cmd = "wvunpack"

	def decode(self, filename):
		return [self.cmd, "-q", filename, "-o", "-"]

def init():
	return WavpackHandler
