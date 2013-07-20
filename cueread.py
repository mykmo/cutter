from os.path import basename
import sys

from cue import read_cue

if sys.version_info.major == 2:
	class Encoded:
		def __init__(self, stream):
			self.stream = stream

		def write(self, msg):
			self.stream.write(msg.encode("utf-8"))

		def __getattr__(self, attr):
			return getattr(self.stream, attr)
	
	sys.stdout = Encoded(sys.stdout)

def printf(fmt, *args):
	sys.stdout.write(fmt % args)

def msf(ts):
	m = ts / (60 * 75)
	s = ts / 75 % 60
	f = ts % 75

	return "%d:%d:%d" % (m, s, f)

def quote(s):
	return s if " " not in s else "\"%s\"" % s

progname = basename(sys.argv[0])
if len(sys.argv) != 2:
	printf("Usage: %s cuefile\n", progname)
	sys.exit(1)

try:
	cue = read_cue(sys.argv[1], on_error = lambda err:\
		sys.stderr.write("** %s:%d: %s\n" % (progname, err.line, err))
	)
except Exception as err:
	printf("%s: read_cue failed: %s: %s\n", progname, err.__class__.__name__, err)
	sys.exit(1)

printf("Cue attributes:\n")
for k, v in cue.attrs():
	printf("\t%s = %s\n", k, quote(v))

for file in cue.files():
	printf("File %s %s\n", quote(file.name), file.type)
	for track in file.tracks():
		printf("\tTrack %d\n", track.number)
		pregap = track.get("pregap")
		postgap = track.get("postgap")
		for k, v in track.attrs():
			if k not in ("pregap", "postgap"):
				printf("\t\t%s = %s\n", k, quote(v))
		if pregap is not None:
			printf("\t\tPregap %s\n", msf(pregap))
		for k, v in track.indexes():
			printf("\t\tIndex %d %s\n", k, msf(v))
		if postgap is not None:
			printf("\t\tPostgap %s\n", msf(postgap))
sys.exit(0)
