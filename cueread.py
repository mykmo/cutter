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
for key in sorted(cue.attrs.keys()):
	printf("\t%s = %s\n", key, cue.attrs[key])

for file in cue.files:
	printf("File \"%s\" %s\n", file, file.type())
	for track in file.tracks:
		printf("\tTrack %d\n", track.number)
		pregap = track.get("pregap")
		postgap = track.get("postgap")
		for key in sorted(track.attrs.keys()):
			if key not in ("pregap", "postgap"):
				printf("\t\t%s = %s\n", key, track.attrs[key])
		if pregap is not None:
			printf("\t\tPregap %s\n", msf(pregap))
		for key in sorted(track.indexes.keys()):
			printf("\t\tIndex %d %s\n", key, msf(track.indexes[key]))
		if postgap is not None:
			printf("\t\tPostgap %s\n", msf(postgap))
sys.exit(0)
