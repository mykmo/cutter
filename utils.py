import sys

if sys.version_info.major == 2:
	def is_python_v2():
		return True

	def to_unicode(buf):
		if type(buf) is unicode:
			return buf
		return buf.decode("utf-8")

	class Encoded:
		def __init__(self, stream):
			self.stream = stream

		def write(self, msg):
			if type(msg) is unicode:
				self.stream.write(msg.encode("utf-8"))
			else:
				self.stream.write(msg)

		def __getattr__(self, attr):
			return getattr(self.stream, attr)

	sys.stdout = Encoded(sys.stdout)
	sys.stderr = Encoded(sys.stderr)
else:
	def is_python_v2():
		return False

	def to_unicode(buf):
		return buf
