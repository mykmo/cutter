class DummyProgress:
	def __init__(self, callback, message):
		self.callback = callback
		self.message = message

	def init(self, total):
		pass

	def update(self, value):
		pass

	def finish(self):
		self.callback(self.message + "\n")

class PercentProgress(DummyProgress):
	def __init__(self, *args):
		DummyProgress.__init__(self, *args)
		self.progress_shown = False

	def _erase(self, n):
		if not self.progress_shown:
			self.last_length = n
			self.progress_shown = True
			return 0

		prev, self.last_length = self.last_length, n
		return prev

	def _show(self, msg):
		self.callback("\b" * self._erase(len(msg)) + msg)

	def _show_percent(self):
		if self.percent > self.last_percent:
			self._show("%3d%% " % self.percent)
			self.last_percent = self.percent

	def clear(self):
		if self.last_length:
			self._show(" " * self.last_length)

	def init(self, total):
		self.total = total
		self.current = 0
		self.percent = 0
		self.last_percent = -1
		self.last_length = 0

		self._show_percent()

	def update(self, value):
		self.current += value
		percent = 100 * self.current // self.total
		self.percent = min(max(percent, 0), 100)

		self._show_percent()

	def finish(self):
		n = max(self.last_length - len(self.message), 0)
		self._show(self.message + " " * n + "\n")
