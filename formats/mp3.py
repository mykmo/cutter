from formats.__base__ import *
from utils import to_bytes

import subprocess
import struct
import array

def synchsafe(num):
	if num <= 0x7f:
		return num

	return synchsafe(num >> 7) << 8 | num & 0x7f

class ID3Tagger:
	# id3v2 frame mapping
	__mapping = {
		"album":	"TALB",
		"artist":	"TPE1",
		"composer":	"TCOM",
		"date":		"TDRC",
		"title":	"TIT2",
		"tracknumber":	"TRCK",
	}

	# id3v1 offsets
	__offset = {
		"title": 3,
		"artist": 33,
		"album": 63,
	}

	@staticmethod
	def header(size):
		return struct.pack(">3s3BI", b"ID3", 4, 0, 0, synchsafe(size))

	@staticmethod
	def frame(name, data):
		size = len(data) + 1
		hdr = struct.pack(">4sIHB", name, size, 0, 3)
		return hdr + data

	def __init__(self):
		self.frames = []

		self.v1 = array.array("B", b"\x00" * 128)
		struct.pack_into("3s", self.v1, 0, b"TAG")
		struct.pack_into("B", self.v1, 127, 0xff)

	def frame_size(self):
		return sum(map(len, self.frames))

	def add(self, tag, value):
		value = to_bytes(value)

		if tag in self.__mapping:
			key = to_bytes(self.__mapping[tag])
			self.frames.append(self.frame(key, value))

		off = self.__offset.get(tag)
		if off:
			struct.pack_into("30s", self.v1, off, value)
		elif tag == "date":
			struct.pack_into("4s", self.v1, 93, value)
		elif tag == "tracknumber":
			number = int(value.partition(b"/")[0])
			struct.pack_into("B", self.v1, 126, number)

	def write(self, path):
		fp = open(path, "r+b")
		data = fp.read()

		fp.seek(0)
		fp.truncate(0)

		# save id3v2
		fp.write(self.header(self.frame_size()))
		for frame in self.frames:
			fp.write(frame)

		fp.write(data)

		# save id3v1
		self.v1.tofile(fp)

		fp.close()

class Mp3Handler(BaseHandler):
	name = "mp3"
	ext = "mp3"

	def encode(self, opt, info):
		self.add("cust ext=%s sox -" % self.ext)

		if opt.bitrate is not None:
			self.add("-C %d" % opt.bitrate)

		self.add_sox_args(opt, info)
		self.add("%f")

		return self.build()

	def tag(self, path, tags):
		tagger = ID3Tagger()

		for k, v in tags.items():
			if v and k not in ("tracknumber", "tracktotal"):
				tagger.add(k, v)

		number = "%d/%d" % (tags["tracknumber"], tags["tracktotal"])
		tagger.add("tracknumber", number)

		tagger.write(path)
		return True

def init():
	return Mp3Handler
