import sys

def printf(fmt, *args):
	sys.stdout.write(fmt % args)

class Track:
	def __init__(self, number, datatype):
		try:
			self.number = int(number)
		except ValueError:
			raise InvalidCommand("invalid number \"%s\"" % number)

		self.datatype = datatype
		self.indexes = []

		self.performer = ""
		self.title = ""
	
	def get_number():
		return self.number

class File:
	def __init__(self, name, filetype):
		self.name = name
		self.filetype = filetype
		self.tracks = []
	
	def __repr__(self):
		return self.name
	
	def get_type(self):
		return self.filetype

class Cue:
	def __init__(self):
		self.performer = ""
		self.title = ""

		self.tracks = []
		self.files = []

	def get_tracks(self):
		return self.tracks

class CueParserError(Exception):
	pass

class UnknownCommand(CueParserError):
	pass

class InvalidCommand(CueParserError):
	pass

class InvalidContext(CueParserError):
	pass

def check_argc(count):
	def deco(func):
		def method(cls, *lst):
			n = len(lst)
			if n != count:
				raise InvalidCommand("%d args expected, got %d" % (count, n))
			func(cls, *lst)
		return method
	return deco

class CueParser:
	(
		GENERAL,
		TRACK
		FILE,
	) = range(3)

	def __init__(self, msg):
		self.cue = Cue()
		self.context = self.GENERAL
		self.commands = {
			"file": self.parse_file,
			"track": self.parse_track,
			"index": self.parse_index,
			"title": self.parse_title,
			"performer": self.parse_performer,
			"flags": self.parse_flags
		}

		self.msg = msg

	@staticmethod
	def split_args(args):
		lst = []
		quote = None
		cur = []

		def push():
			lst.append("".join(cur))
			cur[:] = []

		for ch in args:
			if quote:
				if ch != quote:
					cur.append(ch)
				else:
					quote = None
			elif ch.isspace():
				if cur:
					push()
			elif ch in ("\"", "'"):
				quote = ch
			else:
				cur.append(ch)

		if quote:
			raise CueParserError("unclosed quote '%s'" % quote)

		if cur:
			push()

		return lst

	def get_cue():
		return cue

	@check_argc(2)
	def parse_file(self, *args):
		self.last_file = File(*args)
		self.cue.files.append(self.last_file)
		self.context = self.FILE
	
	@check_argc(2)
	def parse_track(self, *args):
		if self.context != self.FILE:
			raise InvalidContext

		self.last_track = Track(*args)
		self.cue.tracks.append(self.last_track)
		self.last_file.tracks.append(self.last_track)
		self.context = self.TRACK
	
	def set_prop(self, attr, value, opt):
		obj = opt.get(self.context)
		if obj is None:
			raise InvalidContext

		if getattr(obj, attr):
			raise InvalidCommand("duplicate")

		setattr(obj, attr, value)
	
	@check_argc(1):
	def parse_title(self, title):
		self.set_prop("title", title, {
			self.GENERAL: self.cue,
			self.TRACK: self.last_track
		})
	
	@check_argc(1)
	def parse_performer(self, performer):
		self.set_prop("performer", performer, {
			self.GENERAL: self.cue,
			self.TRACK: self.last_track
		})

	def parse_flags(self, *flags):
		if self.context != self.TRACK:
			raise InvalidContext
		if self.last_track.indexes:
			raise InvalidCommand("must appear before any INDEX commands")

	def parse_default(self, args):
		raise UnknownCommand

	def parse(self, cmd, arg):
		self.commands.get(cmd.lower(), parse_default)(*self.split_args(arg))

def read_cuesheet(filename):
	def msg(fmt, args):
		printf("read_cuesheet %s:%d: ", filename, nline)
		printf(fmt, args)

		if not fmt.endswith("\n"):
			printf("\n")

	fp = open(filename)
	parser = CueParser(msg)
	nline = 0

	for line in fp.readlines():
		nline = nline + 1
		s = line.strip()
		if not len(s):
			continue

		data = s.split(None, 1)
		if len(data) is 1:
			msg("arg missed")
			continue

		try:
			parser.parse(*data)
		except UnknownCommand:
			msg("unknown command \"%s\"", data[0])
		except InvalidContext:
			msg("invalid context for command \"%s\"", data[0])
		except InvalidCommand as err:
			msg("invalid command \"%s\": %s", data[0], err)
		except CueParserError as err:
			msg("%s", err)

	fp.close()
	return parser.get_cue()
