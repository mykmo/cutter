class ApeHandler:
	name = "ape"
	ext = "ape"
	cmd = "mac"

	def decode(self, filename):
		args = [self.cmd, filename, "-", "-d"]
		return args

def init():
	return ApeHandler
