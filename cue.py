from cchardet import detect as encoding_detect
import codecs
import sys
import re

def sort_iter(d):
	def over(d):
		for k in sorted(d.keys()):
			yield k, d[k]
	return iter(over(d))

class Track:
	def __init__(self, number, datatype):
		try:
			self.number = int(number)
		except ValueError:
			raise InvalidCommand("invalid number \"%s\"" % number)

		self.type = datatype
		self._indexes = {}
		self._attrs = {}

	def attrs(self):
		return sort_iter(self._attrs)

	def indexes(self):
		return sort_iter(self._indexes)

	def get(self, attr):
		return self._attrs.get(attr,
			None if attr in ("pregap", "postgap") else ""
		)

class File:
	def __init__(self, name, filetype):
		self.name = name
		self.type = filetype
		self._tracks = []

	def tracks(self):
		return iter(self._tracks)

	def add_track(self, track):
		self._tracks.append(track)

	def __repr__(self):
		return self.name

class Cue:
	def __init__(self):
		self._attrs = {}
		self._files = []

	def attrs(self):
		return sort_iter(self._attrs)

	def files(self):
		return iter(self._files)

	def get(self, attr):
		return self._attrs.get(attr, "")

	def add_file(self, file):
		self._files.append(file)

class CueParserError(Exception):
	pass

class UnknownCommand(CueParserError):
	pass

class InvalidCommand(CueParserError):
	pass

class InvalidContext(CueParserError):
	pass

class Context:
	(
		GENERAL,
		TRACK,
		FILE
	) = range(3)

def check(count = None, context = None):
	def deco(func):
		def method(cls, *lst):
			if count is not None:
				n = len(lst)
				if n != count:
					raise InvalidCommand(
						"%d arg%s expected, got %d" %
						(count, "s" if count > 1 else "", n)
					)
			if context is not None:
				if type(context) in (list, tuple):
					if cls.context not in context:
						raise InvalidContext
				elif cls.context != context:
					raise InvalidContext
			func(cls, *lst)
		return method
	return deco

class CueParser:
	re_timestamp = re.compile("^[\d]{1,3}:[\d]{1,2}:[\d]{1,2}$")
	rem_commands = ('genre', 'data', 'comment')

	def __init__(self):
		def do_set_attr(name, cue = False, track = False, convert = None):
			def func(*args):
				n = len(args)
				if n != 1:
					raise InvalidCommand("1 arg expected, got %d" % n)
				opt = {}
				if cue:
					opt[Context.GENERAL] = self.cue
				if track:
					opt[Context.TRACK] = self.track

				arg = convert(args[0]) if convert else args[0]
				self.set_attr(name, arg, opt)
			return func

		self.cue = Cue()
		self.context = Context.GENERAL
		self.track = None
		self.file = None

		self.commands = {
			"file": 	self.parse_file,
			"flags": 	self.parse_flags,
			"index": 	self.parse_index,
			"pregap": 	self.parse_pregap,
			"rem":		self.parse_rem,
			"track": 	self.parse_track,

			"catalog":	do_set_attr("catalog", cue = True),
			"performer":	do_set_attr("performer", cue = True, track = True),
			"postgap": 	do_set_attr("postgap", track = True, convert = self.parse_timestamp),
			"songwriter":	do_set_attr("songwriter", cue = True, track = True),
			"title": 	do_set_attr("title", cue = True, track = True),

			"cdtextfile":	self.parse_skip,
			"isrc":		self.parse_skip,
		}

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

	@staticmethod
	def parse_timestamp(time):
		if not CueParser.re_timestamp.match(time):
			raise InvalidCommand("invalid timestamp \"%s\"" % time)

		m, s, f = map(int, time.split(":"))
		return (m * 60 + s) * 75 + f

	def get_cue(self):
		return self.cue

	@check(2)
	def parse_file(self, *args):
		self.file = File(*args)
		self.cue.add_file(self.file)
		self.context = Context.FILE

	@check(2, (Context.FILE, Context.TRACK))
	def parse_track(self, *args):
		self.track = Track(*args)
		self.file.add_track(self.track)
		self.context = Context.TRACK

	@check(2, Context.TRACK)
	def parse_index(self, number, time):
		if "postgap" in self.track._attrs:
			raise InvalidCommand("after POSTGAP")
		try:
			number = int(number)
		except ValueError:
			raise InvalidCommand("invalid number \"%s\"" % number)
		if number is 0 and "pregap" in self.track._attrs:
			raise InvalidCommand("conflict with previous PREGAP")
		if number in self.track._indexes:
		 	raise InvalidCommand("duplicate index number %d" % number)

		self.track._indexes[number] = self.parse_timestamp(time)

	@check(1, Context.TRACK)
	def parse_pregap(self, time):
		if self.track._indexes:
			raise InvalidCommand("must appear before any INDEX commands for the current track")
		self.set_attr("pregap", self.parse_timestamp(time), obj = self.track)

	def set_attr(self, attr, value, opt = None, obj = None):
		if opt is not None:
			obj = opt.get(self.context)
			if obj is None:
				raise InvalidContext
		elif obj is None:
			raise CueParserError("CueParserError.set_attr: invalid usage")

		if attr in obj._attrs:
			raise InvalidCommand("duplicate")

		obj._attrs[attr] = value

	@check(context = Context.TRACK)
	def parse_flags(self, *flags):
		if self.track._indexes:
			raise InvalidCommand("must appear before any INDEX commands")

	def parse_rem(self, opt, value = None, *args):
		cmd = opt.lower()
		if value and cmd in self.rem_commands:
			if len(args):
				raise InvalidCommand("extra arguments for \"%s\"" % opt)
			self.set_attr(cmd, value, obj = self.cue)

	def parse_skip(self, *args):
		pass

	def parse_default(self, *args):
		raise UnknownCommand

	def parse(self, cmd, arg):
		self.commands.get(cmd.lower(), self.parse_default)(*self.split_args(arg))

def __read_file(filename):
	f = open(filename, "rb")
	data = f.read()
	f.close()

	encoded = None
	try:
		encoded = data.decode("utf-8-sig")
	except UnicodeDecodeError:
		pass

	if encoded is None:
		enc = encoding_detect(data)
		if enc is None:
			raise Exception("autodetect failed")
		encoding = enc["encoding"]
		try:
			encoded = data.decode(encoding)
		except UnicodeDecodeError:
			raise Exception("autodetect failed: invalid encoding %s" % encoding)

	return encoded

def read_cue(filename, on_error = None):
	if on_error:
		def msg(fmt, *args):
			err = CueParserError(fmt % args)
			err.line = nline
			on_error(err)
	else:
		msg = lambda *args: None

	cuefile = __read_file(filename)
	parser = CueParser()

	nline = 0

	for line in cuefile.split("\n"):
		nline = nline + 1
		s = line.strip()
		if not len(s):
			continue

		data = s.split(None, 1)
		if len(data) is 1:
			msg("invalid command \"%s\": arg missed", data[0])
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

	return parser.get_cue()
