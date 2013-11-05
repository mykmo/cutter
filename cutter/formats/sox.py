class SoxHandler:
	def __init__(self):
		self.compression = None

	def set_compression(self, value):
		self.compression = value

	def sox_args(self, path, opt, info):
		args = ["sox", "-V1", "-"]

		if self.compression is not None:
			args.extend(["-C", str(self.compression)])

		if opt.sample_rate and opt.sample_rate != info.sample_rate:
			args.extend(["-r", str(opt.sample_rate)])
		if opt.bits_per_sample and opt.bits_per_sample != info.bits_per_sample:
			args.extend(["-b", str(opt.bits_per_sample)])
		if opt.channels and opt.channels != info.channels:
			args.extend(["-c", str(opt.channels)])

		args.append(path)

		return args
