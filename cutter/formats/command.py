from .. coding import to_unicode

import subprocess
import signal

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT

def strsignal(sig):
	for k, v in signal.__dict__.items():
		if k.startswith("SIG") and not k.startswith("SIG_"):
			if v == sig:
				return k

	return "signal(%d)" % sig

class CommandError(Exception):
	pass

class Command:
	def __init__(self, args, stdin=None, stdout=None, stderr=None):
		self.proc = None
		self.status = None
		self.status_msg = ""

		try:
			self.proc = subprocess.Popen(args,
				stdin=stdin, stdout=stdout, stderr=stderr)
		except OSError as err:
			self.status = "not started"
			self.status_msg = err.strerror

	def ready(self):
		return self.proc is not None

	def get_status(self):
		return self.status, self.status_msg

	def close(self, msg=""):
		if self.proc is None:
			return

		self.status = self.proc.wait()
		if self.status and self.proc.stderr:
			self.status_msg = to_unicode(self.proc.stderr.read())

		if msg and not self.status_msg:
			self.status_msg = msg

		if self.status < 0:
			self.status = strsignal(-self.status)

		self.proc = None

	def __getattr__(self, attr):
		if self.proc is None:
			raise CommandError("command not started")

		if attr not in ("stdin", "stdout", "stderr"):
			raise CommandError("unknown attribute '%s'" % attr)

		return getattr(self.proc, attr)
