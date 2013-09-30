class BaseHandler:
	def __init__(self, logger = None):
		self.logger = logger
		self.buf = []

	def log(self, fmt, *args):
		if self.logger is not None:
			self.logger(fmt, *args)

	def add(self, *args):
		self.buf.extend(args)

	def build(self, join=True):
		data = " ".join(self.buf) if join else self.buf
		self.buf = []

		return data

	def add_sox_args(self, opt, info):
		if opt.sample_rate and opt.sample_rate != info.sample_rate:
			self.add("-r %d" % opt.sample_rate)
		if opt.bits_per_sample and opt.bits_per_sample != info.bits_per_sample:
			self.add("-b %d" % opt.bits_per_sample)
		if opt.channels and opt.channels != info.channels:
			self.add("-c %d" % opt.channels)

	def is_tag_supported(self):
		return hasattr(self, "tag")
