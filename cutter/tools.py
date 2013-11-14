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

def fatal(fmt, *args):
	printerr(fmt, *args)
	sys.exit(1)

def debug(fmt, *args):
	msg = fmt % args
	if msg[-1] != "\n":
		msg += "\n"
	sys.stderr.write("-- " + msg)

def msf(ts):
	m = ts / (60 * 75)
	s = ts / 75 % 60
	f = ts % 75

	return "%d:%02d.%02d" % (m, s, f)
