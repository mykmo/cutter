from . handler import *
from .. tools import quote

import subprocess
import wave

class EncoderError(Exception):
	pass

class Encoder:
	FRAME_BUFFER_SIZE=0x4000

	class SafeStream:
		MIN_CHUNK_SIZE=64

		def __init__(self, fileobj):
			self.fileobj = fileobj
			self.seek_called = False
			self.written = 0

			self.buffered = b""

		def seek(self, *args):
			self.seek_called = True

		def write(self, data):
			if self.seek_called:
				return

			nbytes = len(data)
			if nbytes < self.MIN_CHUNK_SIZE:
				self.buffered += data
			else:
				if len(self.buffered):
					data = self.buffered + data
					self.buffered = b""

				self.fileobj.write(data)

			self.written += nbytes

		def tell(self):
			return self.written

		def close(self):
			if len(self.buffered):
				self.fileobj.write(self.buffered)

			self.fileobj.close()

		def __getattr__(self, attr):
			return getattr(self.fileobj, attr)

	def __init__(self, handler, reader, filename, options):
		self.closed = False
		self.handler = handler

		args = self.handler.encode(filename, options, reader.info())
		self.command = " ".join(map(quote, args))

		if options.dry_run:
			self.proc = None
			return

		self.proc = subprocess.Popen(args, stdin=subprocess.PIPE)

		self.reader = reader
		self.stream = self.SafeStream(self.proc.stdin)
		self.writer = wave.open(self.stream, "w")
		self.writer.setparams(reader.wave_params())

	def process(self):
		if self.proc is None:
			return

		while True:
			data = self.reader.read(self.FRAME_BUFFER_SIZE)
			if not len(data):
				break

			self.writer.writeframesraw(data)

	def get_command(self):
		return self.command

	def close(self):
		if self.closed or self.proc is None:
			return

		self.writer.close()
		self.stream.close()
		self.proc.wait()

	def __del__(self):
		self.close()

class EncoderHandler(Handler):
	def open(self, reader, filename, options):
		return Encoder(self.handler, reader, filename, options)

	def is_tag_supported(self):
		return hasattr(self.handler, "tag")
