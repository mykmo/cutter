from formats.__base__ import *
from utils import to_bytes

import subprocess

class Mp3Handler(BaseHandler):
	name = "mp3"
	ext = "mp3"

	__tag_opts = {
		"album": "-a",
		"artist": "-A",
		"date": "-y",
		"title": "-t"
	}

	def encode(self, opt, info):
		self.add("cust ext=%s sox -" % self.ext)

		if opt.bitrate is not None:
			self.add("-C %d" % opt.bitrate)

		self.add_sox_args(opt, info)
		self.add("%f")

		return self.build()

	def tag(self, path, tags):
		self.add("id3v2", "--id3v1-only")

		for k, v in tags.items():
			if k in self.__tag_opts and v:
				self.add(self.__tag_opts[k])
				self.add(v)

		self.add("-T", "%d/%d" % (tags["tracknumber"], tags["tracktotal"]))
		self.add(path)

		self.log("Tag [%s] : ", path)

		if subprocess.call(self.build(False)):
			self.log("FAILED\n")
			return False

		self.log("OK\n")
		return True

def init():
	return Mp3Handler
