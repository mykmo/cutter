import sys
import os

progname = os.path.basename(sys.argv[0])

def quote(s, ch = '"'):
	return s if " " not in s else ch + s + ch

def printf(fmt, *args):
	out = fmt % args
	sys.stdout.write(out)

	if out[-1] != '\n':
		sys.stdout.flush()

def printerr(fmt, *args):
	msg = fmt % args
	if msg[-1] != "\n":
		msg += "\n"
	sys.stderr.write("** " + progname + ": " + msg)

def debug(fmt, *args):
	msg = fmt % args
	if msg[-1] != "\n":
		msg += "\n"
	sys.stderr.write("-- " + msg)
