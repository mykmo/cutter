from . coding import to_unicode, to_bytes
from . tools import *

from . import formats

from tempfile import mkdtemp

import collections
import subprocess
import itertools
import shutil
import sys
import os

ILLEGAL_CHARACTERS_MAP = {
	u"\\": u"-",
	u":": u"-",
	u"*": u"+",
	u"?": u"_",
	u'"': u"'",
	u"<": u"(",
	u">": u")",
	u"|": u"-"
}

def filterdir(dir, prefix):
	return sorted(filter(lambda f: f.startswith(prefix), os.listdir(dir)))

def mkdir(path):
	if not os.path.exists(path):
		try:
			os.makedirs(path)
		except OSError as err:
			printerr("make dir %s failed: %s", quote(path), err)
			sys.exit(1)

def convert_characters(path):
	return "".join([ILLEGAL_CHARACTERS_MAP.get(ch, ch) for ch in path])

class TempLink:
	def __init__(self, path, name):
		self.tmpdir = mkdtemp(prefix = "temp-")
		self.linkpath = "%s/%s" % (self.tmpdir, name)

		try:
			os.symlink(path, self.tmpdir + "/" + name)
		except Exception as err:
			os.rmdir(self.tmpdir)
			raise err

	def remove(self):
		os.unlink(self.linkpath)
		os.rmdir(self.tmpdir)

	def __repr__(self):
		return "TempLink('%s')" % self.linkpath

	def __str__(self):
		return self.linkpath

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.remove()

class StreamInfo:
	@staticmethod
	def get(name):
		stream = formats.decoder_open(name)

		if not stream or not stream.ready():
			return None

		return stream.info()

class Splitter:
	EXT = ["ape", "flac", "wv"]

	class File:
		def __init__(self, fileobj, path):
			self.fileobj = fileobj
			self.path = path

		def __getattr__(self, attr):
			return getattr(self.fileobj, attr)

	class TrackInfo:
		def __init__(self, name, tags):
			self.name = name
			self.tags = tags

	@staticmethod
	def format_by_tags(fmt, tags, replace=False):
		if replace:
			def conv(var):
				if isinstance(var, str):
					return var.replace("/", "-")
				return var

			tags = {k: conv(v) for k, v in tags.items()}

		try:
			return fmt.format(year=tags["date"], **tags)
		except KeyError as err:
			printerr("invalid format key: %s", err)
			sys.exit(1)
		except ValueError as err:
			printerr("invalid format option: %s", err)
			sys.exit(1)

	def init_tags(self):
		self.tracktotal = self.opt.tracktotal or len(list(self.all_tracks()))

		self.tags = {
			"album": self.opt.album or self.cue.get("title"),
			"date": self.opt.date or self.cue.get("date"),
			"genre": self.opt.genre or self.cue.get("genre"),
			"comment": self.opt.comment or self.cue.get("comment"),
			"composer": self.opt.composer
				or self.cue.get("songwriter"),
			"artist": self.opt.albumartist or self.opt.artist
				or self.cue.get("performer"),
			"albumartist": self.opt.albumartist
		}

		tmp = self.format_by_tags(os.path.dirname(self.opt.fmt), self.tags, True)

		if self.opt.convert_chars:
			tmp = convert_characters(tmp)

		self.dest = os.path.join(self.opt.dir, tmp)
		track_fmt = os.path.basename(self.opt.fmt)

		tracknumber = self.opt.trackstart or 1
		self.track_info = {}
		for track in self.all_tracks():
			self.track_info[track] = self.get_track_info(
				track, tracknumber, track_fmt
			)
			tracknumber += 1

	def __init__(self, cue, opt):
		self.cue = cue
		self.opt = opt
		self.tracks = None

		self.encoder = formats.encoder(opt.type)
		self.tag_supported = self.encoder.is_tag_supported()

		self.init_tags()

	def get_track_info(self, track, tracknumber, fmt):
		tags = dict(self.tags)
		tags.update({
			"tracknumber": tracknumber,
			"tracktotal": self.tracktotal,

			"title": track.get("title") or "track",
			"artist": self.opt.artist or track.get("performer")
				or self.cue.get("performer"),
			"composer": self.opt.composer or track.get("songwriter")
				or self.cue.get("songwriter")
		})

		name = self.format_by_tags(fmt, tags).replace("/", "-")

		if self.opt.convert_chars:
			name = convert_characters(name)

		return self.TrackInfo(name + "." + self.encoder.ext, tags)

	def find_realfile(self, name):
		if not name.endswith(".wav"):
			return None

		orig = name.rpartition(".")[0]
		for file in filterdir(self.cue.dir or ".", orig):
			head, _, ext = file.rpartition(".")
			if head == orig and ext in self.EXT:
				return file

		return None

	def open_files(self):
		lst = []

		for file in self.cue.files():
			if not file.has_audio_tracks():
				debug("skip file %s: no tracks", quote(file.name))
				continue

			path = self.cue.dir + file.name
			if not os.path.exists(path):
				real = self.find_realfile(file.name)
				if not real:
					printerr("no such file %s", quote(file.name))
					sys.exit(1)
				path = self.cue.dir + real

			lst.append(self.File(file, path))

		return lst

	def track_name(self, track):
		return self.track_info[track].name

	def track_tags(self, track):
		return self.track_info[track].tags

	def tag(self, track, path):
		if not self.tag_supported:
			return

		printf("tag %s: ", quote(self.track_name(track)))
		if not self.encoder.tag(path, self.track_tags(track)):
			printf("FAILED\n")
			sys.exit(1)

		printf("OK\n")

	def is_need_convert(self, info):
		noteq = lambda a, b: a and a != b

		if info.type != self.encoder.name:
			return True
		if noteq(self.opt.sample_rate, info.sample_rate):
			return True
		if noteq(self.opt.bits_per_sample, info.bits_per_sample):
			return True
		if noteq(self.opt.channels, info.channels):
			return True

		return False

	def copy_file(self, file):
		track = list(file.tracks())[0]
		trackname = self.track_name(track)
		path = os.path.join(self.dest, trackname)

		printf("copy %s -> %s", quote(file.path), quote(path))
		printf("\n" if self.opt.dry_run else ": ")

		if self.opt.dry_run:
			return

		try:
			shutil.copyfile(file.path, path)
		except Exception as err:
			printf("FAILED: %s\n", err)
			sys.exit(1)
		else:
			printf("OK\n")

		self.tag(track, path)

	@staticmethod
	def print_command_error(name, stream):
		status, msg = stream.get_status()

		cmd = stream.get_command()
		printerr("%s failed (%s), command: %s", name, status, cmd)
		for line in msg.split("\n"):
			if len(line):
				printf("> %s\n", line)

	def open_decode(self, path):
		stream = formats.decoder_open(path, self.opt)

		if stream is None:
			printerr("%s: unsupported type", quote(path))
		elif not stream.ready():
			self.print_command_error("decode", stream)
			stream = None
		else:
			if self.opt.verbose and self.opt.dry_run:
				self.print_decode_info(path, stream)

		return stream

	def open_encode(self, reader, path):
		stream = self.encoder.open(reader, path, self.opt)

		if self.opt.dry_run:
			if self.opt.verbose:
				debug("encode: %s", stream.get_command())
			return stream

		if not stream.ready():
			self.print_command_error("encode", stream)
			stream = None

		return stream

	def print_decode_info(self, path, stream):
		info = stream.info()
		debug("decode: %s", stream.get_command())
		debug("input: %s [%s] (%d/%d, %d ch)", quote(path),
			info.type, info.bits_per_sample, info.sample_rate,
			info.channels)

	@staticmethod
	def track_timerange(track):
		ts = "%8s -" % msf(track.begin)

		if track.end is not None:
			ts += " %8s" % msf(track.end)

		return ts

	@staticmethod
	def track_length(track):
		if track.end is None:
			return None

		return track.end - track.begin

	def split_file(self, file):
		stream = self.open_decode(file.path)
		if not stream:
			sys.exit(1)

		if file.ntracks() == 1:
			if not self.is_need_convert(stream.info()):
				stream.close()
				self.copy_file(file)
				return

		for track in file.tracks():
			ts = self.track_timerange(track)

			if track not in self.tracks:
				if self.opt.verbose:
					printf("split %s (%s): SKIP\n", quote(file.path), ts)
				continue

			trackname = self.track_name(track)
			path = os.path.join(self.dest, trackname)

			stream.seek(track.begin)
			reader = stream.get_reader(self.track_length(track))

			out = self.open_encode(reader, path)

			printf("split %s (%s) -> %s", quote(file.path), ts, quote(trackname))
			printf("\n" if self.opt.dry_run else ": ")

			if self.opt.dry_run:
				continue

			if out is None:
				printf("FAILED\n")
				sys.exit(1)

			out.process()
			out.close()

			printf("OK\n")

			self.tag(track, path)

		stream.close()

	def check_duplicates(self):
		names = [x.name for x in self.track_info.values()]
		dup = [k for k, v in collections.Counter(names).items() if v > 1]
		if dup:
			printerr("track names are duplicated: %s", " ".join(dup))
			sys.exit(1)

	def transfer_files(self, source, dest):
		for file in sorted(os.listdir(source)):
			path = os.path.join(source, file)
			if not os.path.isfile(path):
				debug("skip non file %s", quote(file))
				continue

			printf("copy %s -> %s: ", quote(file), quote(dest))

			try:
				shutil.copy(path, dest)
			except Exception as err:
				printf("FAILED: %s\n", err)
				sys.exit(1)
			else:
				printf("OK\n")

	def split(self):
		self.check_duplicates()

		files = self.open_files()

		self.realpath = None
		if not self.opt.dry_run:
			mkdir(self.dest)
			if self.opt.use_tempdir:
				self.realpath = self.dest
				tempdir = mkdtemp(prefix="cutter-")
				self.dest = to_unicode(tempdir)

		for file in files:
			self.split_file(file)

		if self.realpath:
			self.transfer_files(self.dest, self.realpath)
			try:
				shutil.rmtree(self.dest)
			except Exception as err:
				printerr("rm %s failed: %s\n", self.dest, err)
				sys.exit(1)

	def all_tracks(self):
		if self.tracks:
			return self.tracks

		tracks = itertools.chain(*[f.tracks() for f in self.cue.files()])

		if self.opt.tracks is None:
			self.tracks = list(tracks)
		else:
			mapped = zip(tracks, itertools.count(1))
			self.tracks = [t for t, n in mapped if n in self.opt.tracks]

		return self.tracks

	def dump_tags(self):
		add_line = False
		for track in self.all_tracks():
			if add_line:
				printf("\n")
			add_line = True

			tags = self.track_tags(track)
			for k, v in sorted(tags.items()):
				if v is not "":
					printf("%s=%s\n", k.upper(), v)

	def dump_tracks(self):
		for track in self.all_tracks():
			trackname = self.track_name(track)
			printf("%s\n", os.path.join(self.dest, trackname))
