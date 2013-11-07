from . command import *
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
		self.handler = handler

		args = self.handler.encode(filename, options, reader.info())
		self.command = " ".join(map(quote, args))

		if options.dry_run:
			self.proc = None
			return

		self.proc = Command(args, stdin=PIPE)
		if not self.proc.ready():
			return

		self.reader = reader
		self.stream = self.SafeStream(self.proc.stdin)
		self.writer = wave.open(self.stream, "w")
		self.writer.setparams(reader.wave_params())

	def ready(self):
		return self.proc.ready()

	def process(self, progress):
		if not self.proc.ready():
			return

		progress.init(self.reader.size())

		data = self.reader.read(self.FRAME_BUFFER_SIZE)

		while len(data):
			self.writer.writeframesraw(data)
			progress.update(len(data))

			data = self.reader.read(self.FRAME_BUFFER_SIZE)

		progress.finish()

	def get_command(self):
		return self.command

	def get_status(self):
		return self.proc.get_status()

	def close(self):
		if self.proc is not None and self.proc.ready():
			self.writer.close()
			self.stream.close()
			self.proc.close()

	def __del__(self):
		self.close()

class EncoderHandler(Handler):
	def open(self, reader, filename, options):
		return Encoder(self.handler, reader, filename, options)

	def is_tag_supported(self):
		return hasattr(self.handler, "tag")
