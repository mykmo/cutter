from . coding import to_unicode, to_bytes
from . tools import *

from . import formats

from tempfile import mkdtemp
from itertools import chain

import collections
import subprocess
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
	__mapping = {
		b"Channels:": "channels",
		b"Bits/sample:": "bits_per_sample",
		b"Samples/sec:": "sample_rate"
	}

	@staticmethod
	def get(name):
		info = StreamInfo()
		proc = subprocess.Popen(["shninfo", name], stdout = subprocess.PIPE)
		for line in proc.stdout.readlines():
			data = line.split()
			attr = StreamInfo.__mapping.get(data[0])
			if attr:
				setattr(info, attr, int(data[1]))
			elif line.startswith(b"Handled by:"):
				info.type = to_unicode(data[2])

		if proc.wait():
			return None

		return info

class Splitter:
	EXT = ["ape", "flac", "wv"]

	class File:
		def __init__(self, fileobj, name, info):
			self.fileobj = fileobj
			self.name = name
			self.info = info

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

		tracknumber = 0
		self.track_info = {}
		for track in self.all_tracks():
			tracknumber += 1
			self.track_info[track] = self.get_track_info(
				track, tracknumber, track_fmt
			)

	def __init__(self, cue, opt):
		self.cue = cue
		self.opt = opt
		self.tracktotal = len(list(self.all_tracks()))

		self.enctype = formats.handler(opt.type, logger=printf)
		self.tag_supported = self.enctype.is_tag_supported()

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

		return self.TrackInfo(name + "." + self.enctype.ext, tags)

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

			name = self.cue.dir + file.name
			if not os.path.exists(name):
				real = self.find_realfile(file.name)
				if not real:
					printerr("no such file %s", quote(file.name))
					sys.exit(1)
				name = self.cue.dir + real

			info = StreamInfo.get(name)
			if info is None:
				printerr("%s: unknown type", quote(file.name))
				sys.exit(1)

			lst.append(self.File(file, name, info))

		return lst

	def shntool_args(self, tool, info):
		encode = self.enctype.encode(self.opt, info)
		return [tool, "-w", "-d", self.dest, "-o", encode]

	def track_name(self, track):
		return self.track_info[track].name

	def track_tags(self, track):
		return self.track_info[track].tags

	def tag(self, track, path):
		if not self.tag_supported:
			return

		printf("Tag [%s] : ", path)
		if not self.enctype.tag(path, self.track_tags(track)):
			printf("FAILED\n")
			sys.exit(1)

		printf("OK\n")

	def copy_file(self, file):
		noteq = lambda a, b: a and a != b

		if file.info.type != self.enctype.name:
			return False
		if noteq(self.opt.sample_rate, file.info.sample_rate):
			return False
		if noteq(self.opt.bits_per_sample, file.info.bits_per_sample):
			return False
		if noteq(self.opt.channels, file.info.channels):
			return False

		track = list(file.tracks())[0]
		trackname = self.track_name(track)
		path = os.path.join(self.dest, trackname)

		if self.opt.dry_run:
			printf("Copy [%s] --> [%s]\n", file.name, path)
			return True

		printf("Copy [%s] --> [%s] : ", file.name, path)

		try:
			shutil.copyfile(file.name, path)
		except Exception as err:
			printf("FAILED: %s\n", err)
			sys.exit(1)
		else:
			printf("OK\n")

		self.tag(track, path)

		return True

	def convert_file(self, file):
		track = list(file.tracks())[0]
		trackname = self.track_name(track)

		args = self.shntool_args("shnconv", file.info)

		if self.opt.dry_run:
			name = "link to " + quote(file.name, "'")
			debug("run %s", " ".join(map(quote, args + [name])))
			return

		try:
			link = TempLink(os.path.abspath(file.name), trackname)
		except OSError as err:
			printerr("create symlink %s failed: %s", quote(trackname), err)
			sys.exit(1)

		ret = subprocess.call(args + [str(link)])
		link.remove()

		if ret:
			printerr("shnconv failed: exit code %d", ret);
			sys.exit(1)

		self.tag(track, os.path.join(self.dest, trackname))

	def split_file(self, file, points):
		args = self.shntool_args("shnsplit", file.info) + [file.name]

		if self.opt.dry_run:
			debug("run %s", " ".join(map(quote, args)))
			return

		proc = subprocess.Popen(args, stdin = subprocess.PIPE)
		proc.stdin.write(to_bytes("\n".join(map(str, points))))
		proc.stdin.close()

		if proc.wait():
			printerr("shnsplit failed: exit code %d", proc.returncode)
			sys.exit(1)

		splitted = filterdir(self.dest, "split-track")
		for track, filename in zip(file.tracks(), splitted):
			trackname = self.track_name(track)
			path = os.path.join(self.dest, trackname)

			printf("Rename [%s] --> [%s] : ", filename, trackname)
			try:
				os.rename(os.path.join(self.dest, filename), path)
			except OSError as err:
				printf("FAILED: %s\n", err)
				sys.exit(1)
			else:
				printf("OK\n")

			self.tag(track, path)

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

			printf("Copy [%s] into [%s] : ", file, dest)

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
			points = list(file.split_points(file.info))
			if not points:
				if not self.copy_file(file):
					self.convert_file(file)
			else:
				self.split_file(file, points)

		if self.realpath:
			self.transfer_files(self.dest, self.realpath)
			try:
				shutil.rmtree(self.dest)
			except Exception as err:
				printerr("rm %s failed: %s\n", self.dest, err)
				sys.exit(1)

	def all_tracks(self):
		return chain(*[f.tracks() for f in self.cue.files()])

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
