from . handler import *
from . command import *

from .. tools import quote
from .. coding import to_unicode

import wave

class DecoderError(Exception):
	pass

class StreamInfo:
	pass

class BaseDecoder:
	class Reader:
		def __init__(self, stream, nframes):
			self.stream = stream
			self.nframes = nframes
			self.bytes_per_frame = stream._channels * stream._bytes_per_sample
			self.nread = 0

		def info(self):
			return self.stream.info()

		def wave_params(self):
			params = list(self.stream.reader.getparams())
			params[3] = self.nframes
			return params

		def size(self):
			return self.nframes * self.bytes_per_frame

		def read(self, maxframes=None):
			if self.nread >= self.nframes:
				return []

			avail = self.nframes - self.nread
			if maxframes and maxframes < avail:
				avail = maxframes

			data = self.stream.reader.readframes(avail)
			count = len(data) // self.bytes_per_frame
			self.nread += count

			return data

	def __init__(self, handler):
		self.reader = None
		self.handler = handler

	def _init_reader(self, source):
		try:
			self.reader = wave.open(source, "r")
		except Exception as exc:
			self.close()

			self.status = "Exception"
			self.status_msg = "wave.open: %s" % exc
			return

		self._channels		= self.reader.getnchannels()
		self._bytes_per_sample	= self.reader.getsampwidth()
		self._sample_rate	= self.reader.getframerate()

	def ready(self):
		return self.reader is not None

	def channels(self):
		return self._channels

	def bits_per_sample(self):
		return self._bytes_per_sample * 8

	def sample_rate(self):
		return self._sample_rate

	def info(self):
		info = StreamInfo()

		info.channels		= self._channels
		info.bits_per_sample	= self.bits_per_sample()
		info.sample_rate	= self._sample_rate
		info.type		= self.handler.name

		return info

	def seek(self, pos):
		nframes = pos * self._sample_rate // 75 - self.reader.tell()

		if nframes:
			r = self.Reader(self, nframes)
			while len(r.read()):
				pass

		return nframes

	def get_reader(self, npsecs):
		if npsecs is None:
			nframes = self.reader.getnframes() - self.reader.tell()
		else:
			nframes = npsecs * self._sample_rate // 75

		return self.Reader(self, nframes)

	def describe(self):
		return "-"

	def get_status(self):
		if hasattr(self, "status"):
			return self.status, self.status_msg

		return None, ""

	def close(self):
		if self.reader:
			self.reader.close()
			self.reader = None

	def __del__(self):
		self.close()

class WavDecoder(BaseDecoder):
	def __init__(self, handler, filename, options=None):
		BaseDecoder.__init__(self, handler)

		self.filename = filename
		self._init_reader(filename)

	def describe(self):
		return self.filename

class AnyDecoder(BaseDecoder):
	def __init__(self, handler, filename, options=None):
		BaseDecoder.__init__(self, handler)

		args = self.handler.decode(filename)
		self.command = " ".join(map(quote, args))

		self.proc = Command(args, stdout=PIPE, stderr=PIPE)
		if not self.proc.ready():
			return

		self._init_reader(self.proc.stdout)

	def describe(self):
		return self.command

	def get_status(self):
		if self.proc.status_msg:
			return self.proc.get_status()

		return BaseDecoder.get_status(self)

	def close(self):
		if self.proc.ready():
			BaseDecoder.close(self)
			self.proc.stdout.close()
			self.proc.close()

class DummyDecoder:
	class DummyReader(BaseDecoder.Reader):
		def __init__(self, *args):
			BaseDecoder.Reader.__init__(self, *args)

		def info(self):
			return self.stream.info()

		def read(self, *args):
			return []

	def __init__(self, orig):
		self.orig = orig

	def __getattr__(self, attr):
		return getattr(self.orig, attr)

	def seek(self, *args):
		pass

	def get_reader(self, *args):
		return self.DummyReader(self, *args)

class DecoderHandler(Handler):
	def open(self, filename, options=None):
		if self.handler.name == "wav":
			cls = WavDecoder
		else:
			cls = AnyDecoder

		stream = cls(self.handler, filename, options)
		if options and options.dry_run:
			stream = DummyDecoder(stream)

		return stream
