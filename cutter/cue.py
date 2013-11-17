import itertools
import codecs
import sys
import re

try:
	from cchardet import detect as encoding_detect
except ImportError:
	encoding_detect = None

class Track:
	def __init__(self, number, datatype):
		try:
			self.number = int(number)
		except ValueError:
			raise InvalidCommand("invalid number '%s'" % number)

		self.type = datatype
		self._indexes = {}
		self._attrs = {}

	def attrs(self):
		return sorted(self._attrs.items())

	def indexes(self):
		return sorted(self._indexes.items())

	def get(self, attr):
		return self._attrs.get(attr,
			None if attr in ("pregap", "postgap") else u""
		)

	def isaudio(self):
		return self.type == "AUDIO" and self.begin is not None

class File:
	def __init__(self, name, filetype):
		self.name = name
		self.type = filetype
		self._tracks = []

	def tracks(self, filter_audio = True):
		return filter(Track.isaudio if filter_audio else None, self._tracks)

	def add_track(self, track):
		self._tracks.append(track)

	def isaudio(self):
		return self.type in ("WAVE", "FLAC")

	def has_audio_tracks(self):
		return self.ntracks() > 0

	def ntracks(self):
		return len(list(self.tracks()))

	def split_points(self, info):
		rate = info.sample_rate * info.bits_per_sample * info.channels // 8

		for track in list(self.tracks())[1:]:
			yield rate * track.begin // 75

	def __repr__(self):
		return self.name

class Cue:
	def __init__(self):
		self._attrs = {}
		self._files = []

	def attrs(self):
		return sorted(self._attrs.items())

	def files(self, filter_audio = True):
		return filter(File.isaudio if filter_audio else None, self._files)

	def get(self, attr):
		return self._attrs.get(attr, u"")

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
	rem_commands = ('genre', 'date', 'comment')

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
			raise InvalidCommand("invalid timestamp '%s'" % time)

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
			raise InvalidCommand("invalid number '%s'" % number)
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
				raise InvalidCommand("extra arguments for '%s'" % opt)
			self.set_attr(cmd, value, obj = self.cue)

	def parse_skip(self, *args):
		pass

	def parse_default(self, *args):
		raise UnknownCommand

	def parse(self, cmd, arg):
		self.commands.get(cmd.lower(), self.parse_default)(*self.split_args(arg))

	def calc_offsets(self):
		for file in self.cue._files:
			previous = None
			for track in file._tracks:
				track.begin = None
				track.end = None

				pregap = track.get("pregap")
				if pregap is None and 0 in track._indexes:
					pregap = track._indexes[0]
				if pregap is not None and previous and previous.end is None:
					previous.end = pregap

				try:
					track.begin = min([v for k, v in track._indexes.items() if k != 0])
				except:
					continue

				if previous and previous.end is None:
					previous.end = track.begin if pregap is None else pregap

				postgap = track.get("postgap")
				if postgap is not None:
					track.end = postgap

				previous = track

def __read_file(filename, coding = None):
	f = open(filename, "rb")
	data = f.read()
	f.close()

	if coding:
		return data.decode(coding)

	encoded = None
	try:
		encoded = data.decode("utf-8-sig")
	except UnicodeDecodeError:
		if not encoding_detect:
			raise Exception("unknown encoding (autodetect is off)")
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
		except Exception as exc:
			raise Exception("decoding failed: %s" % exc)

	return encoded

def read(filename, coding=None, error_handler=None, ignore_errors=False):
	def report(fmt, *args):
		if error_handler:
			error_handler(lineno, fmt % args)

	def parse_line(line):
		data = line.split(None, 1)
		cmd = data[0]

		if len(data) is 1:
			report("invalid command '%s': arg missed", cmd)
		else:
			try:
				parser.parse(*data)
				return True
			except UnknownCommand:
				report("unknown command '%s'", cmd)
			except InvalidContext:
				report("invalid context for command '%s'", cmd)
			except InvalidCommand as err:
				report("invalid command '%s': %s", cmd, err)
			except CueParserError as err:
				report("%s", err)

		return False

	cuefile = __read_file(filename, coding)
	parser = CueParser()

	for line, lineno in zip(cuefile.split("\n"), itertools.count(1)):
		if line and not parse_line(line.strip()) and not ignore_errors:
			return None

	parser.calc_offsets()
	return parser.get_cue()
