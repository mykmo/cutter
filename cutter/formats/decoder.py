from . handler import *
from .. tools import quote
from .. coding import to_unicode

import subprocess
import wave

class DecoderError(Exception):
	pass

class StreamInfo:
	pass

class Decoder:
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

	def __init__(self, handler, filename, options=None):
		self.reader = None
		self.closed = False
		self.handler = handler

		args = self.handler.decode(filename)
		self.command = " ".join(map(quote, args))

		self.proc = subprocess.Popen(
			args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
		)

		try:
			self.reader = wave.open(self.proc.stdout, "r")
		except Exception as exc:
			self.close()
			if self.status:
				self.status_msg = to_unicode(self.proc.stderr.read())
			else:
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

	def get_command(self):
		return self.command

	def get_status(self):
		return self.status, self.status_msg

	def close(self):
		if self.closed:
			return

		if self.reader:
			self.reader.close()

		if self.proc:
			self.proc.stdout.close()
			self.status = self.proc.wait()
		else:
			self.status = 0

		self.status_msg = ""
		self.closed = True

	def __del__(self):
		self.close()

class DummyDecoder(Decoder):
	class DummyReader(Decoder.Reader):
		def __init__(self, *args):
			Decoder.Reader.__init__(self, *args)

		def info(self):
			return self.stream.info()

		def read(self, *args):
			return []

	def __init__(self, *args, **kwargs):
		Decoder.__init__(self, *args, **kwargs)

	def seek(self, *args):
		pass

	def get_reader(self, *args):
		return self.DummyReader(self, *args)

class DecoderHandler(Handler):
	def open(self, filename, options=None):
		if options and options.dry_run:
			return DummyDecoder(self.handler, filename, options)
		else:
			return Decoder(self.handler, filename, options)
