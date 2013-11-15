#!/usr/bin/env python

from cutter import formats, cue
from cutter.coding import to_unicode, to_bytes
from cutter.splitter import Splitter, StreamInfo
from cutter.tools import *

import argparse

import signal
import sys
import os
import re

re_range = re.compile("^(\d+)-(\d+)$")

try:
	from cutter import config
except Exception as err:
	fatal("import config failed: %s", err)

def print_cue(cue):
	for k, v in cue.attrs():
		printf("%s: %s\n", k.upper(), quote(v))

	for file in cue.files():
		name = cue.dir + file.name

		printf("FILE %s", quote(file.name))
		if not os.path.exists(name):
			printf(": not exists\n")
		else:
			info = StreamInfo.get(name)
			if not info:
				printf(": unknown type\n")
			else:
				printf(" [%s] (%d/%d, %d ch)\n",
					info.type,
					info.bits_per_sample,
					info.sample_rate,
					info.channels)

		for track in file.tracks():
			printf("\tTRACK %02d", track.number)
			title = track.get("title")
			if title != "":
				printf(" %s", quote(title))
			printf(": %s -", msf(track.begin))
			if track.end is not None:
				printf(" %s", msf(track.end))
			printf("\n")

			for k, v in track.attrs():
				if k not in ("pregap", "postgap", "title"):
					printf("\t\t%s: %s\n", k.upper(), quote(v))

def parse_dir(string):
	return to_unicode(os.path.normpath(string))

def parse_tracks(string):
	tracks = set()

	for item in string.split(","):
		try:
			value = int(item)
			tracks.add(value)
		except ValueError:
			m = re_range.match(item)
			if not m:
				raise argparse.ArgumentTypeError("invalid format")

			start, end = int(m.group(1)), int(m.group(2))
			if start <= 0 or end <= 0 or start == end:
				raise argparse.ArgumentTypeError("invalid value")

			if start > end:
				start, end = end, start

			tracks.update(range(start, end + 1))

	return None if len(tracks) == 0 else tracks

def parse_fmt(string):
	fmt = to_unicode(string)

	if not os.path.basename(string):
		raise argparse.ArgumentTypeError("invalid format")

	fmt = os.path.normpath(fmt)
	if fmt.startswith("/"):
		fmt = fmt[1:]

	return fmt

def parse_type(string):
	if string == "help":
		fatal("supported formats: " + " ".join(formats.supported()))

	if not formats.issupported(string):
		msg = "type %r is not supported" % string
		raise argparse.ArgumentTypeError(msg)

	return string

def read_titles(filename):
	if filename == "-":
		fp = sys.stdin
	else:
		try:
			fp = open(filename)
		except IOError as err:
			msg = "open %s: %s" % (err.filename, err.strerror)
			raise argparse.ArgumentTypeError(msg)

	return list(filter(None, [s.strip() for s in fp.readlines()]))

class HelpFormatter(argparse.HelpFormatter):
	def __init__(self, *args, **kwargs):
		kwargs["max_help_position"] = 40
		argparse.HelpFormatter.__init__(self, *args, **kwargs)

def parse_args():
	defaults = {
		"dir": config.DIR or ".",
		"fmt": config.FILENAME_FORMAT,
		"type": config.TYPE,

		"bitrate": config.MP3_BITRATE,

		"convert_chars": config.CONVERT_CHARS,
		"use_tempdir": config.USE_TEMPDIR,
		"show_progress": config.PROGRESS,

		"sample_rate": config.SAMPLE_RATE,
		"channels": config.CHANNELS,
		"bits_per_sample": config.BITS_PER_SAMPLE,
	}

	parser = argparse.ArgumentParser(
		usage="%(prog)s cuefile [options]",
		formatter_class=HelpFormatter,
		description="cue split tool")

	parser.add_argument("cuefile")

	parser.add_argument("--ignore", action="store_true",
		help="ignore cue parsing errors")

	parser.add_argument("--dump",
		choices=("cue", "tags", "tracks"),
		help="print cue data, file tags or track names")

	parser.add_argument("-n", "--dry-run", action="store_true", dest="dry_run")

	parser.add_argument("-v", "--verbose", action="store_true")

	general = parser.add_argument_group("General options")

	general.add_argument("--tag", action="store_true",
		help="tag existing files, do not split")

	general.add_argument("--coding", help="encoding of original text")

	general.add_argument("-d", "--dir", type=parse_dir, help="output directory")

	general.add_argument("--use-tempdir",
		dest="use_tempdir", action="store_true",
		help="use temporary directory for files")

	general.add_argument("--no-tempdir",
		dest="use_tempdir", action="store_false",
		help="do not use temporary directory")

	general.add_argument("--no-progress", dest="show_progress", action="store_false")

	general.add_argument("--tracks", type=parse_tracks, help="select tracks")

	enc = parser.add_argument_group("Encoding options")

	enc.add_argument("-t", "--type", type=parse_type, help="output file format")

	enc.add_argument("-C", "--compression", type=int, metavar="FACTOR",
		help="compression factor for output format (used for flac, ogg)")

	enc.add_argument("--bitrate", type=int, help="audio bitrate (used for mp3)")

	fname = parser.add_argument_group("Filename options")

	fname.add_argument("--format", type=parse_fmt, dest="fmt",
		help="the format string for new filenames")

	fname.add_argument("--convert-chars",
		dest="convert_chars", action="store_true",
		help="replace illegal characters in filename")

	fname.add_argument("--no-convert-chars",
		dest="convert_chars", action="store_false",
		help="do not replace characters in filename")

	format = parser.add_argument_group("Output format")

	format.add_argument("-r", "--sample-rate", type=int,
		dest="sample_rate", metavar="RATE")

	format.add_argument("-c", "--channels", type=int)

	format.add_argument("-b", "--bits-per-sample", type=int,
		dest="bits_per_sample", metavar="BITS")

	tag = parser.add_argument_group("Tag options")
	tag_options = ["album", "artist", ("date", "year"), "genre",
		"comment", "composer", "albumartist"]

	for opt in tag_options:
		if type(opt) in (list, tuple):
			tag.add_argument(*["--" + s for s in opt], default="")
		else:
			tag.add_argument("--" + opt, default="")

	tag.add_argument("--track-total", type=int, dest="tracktotal", metavar="TOTAL")
	tag.add_argument("--track-start", type=int, dest="trackstart", metavar="START")

	tag.add_argument("--export-titles-to", dest="export_titles", metavar="FILE")
	tag.add_argument("--import-titles-from", type=read_titles,
		dest="titles", metavar="FILE")

	parser.set_defaults(**defaults)

	return parser.parse_args()

def option_check_range(option, value, min, max):
	if value is not None and (value < min or value > max):
		printerr("invalid %s value %d, must be in range %d .. %d", option, value, min, max)
		return False

	return True

def process_options(opt):
	def choose(a, b):
		return a if a is not None else b

	if not opt.dump and opt.type is None:
		printerr("--type option is required")
		return False

	if opt.type == "flac":
		opt.compression = choose(opt.compression, config.FLAC_COMPRESSION)
		if not option_check_range("compression", opt.compression, 0, 8):
			return False
	elif opt.type == "ogg":
		opt.compression = choose(opt.compression, config.OGG_COMPRESSION)
		if not option_check_range("compression", opt.compression, -1, 10):
			return False
	elif opt.type == "mp3":
		if not option_check_range("bitrate", opt.bitrate, 32, 320):
			return False

	if not os.isatty(sys.stdout.fileno()):
		opt.show_progress = False

	if opt.dump and opt.export_titles != None:
		printerr("--dump and --export-titles-to cannot be used together")
		return False

	return True

def find_cuefile(path):
	for file in os.listdir(path):
		fullname = os.path.join(path, file)
		if os.path.isfile(fullname) and file.endswith(".cue"):
			return os.path.normpath(fullname)

	fatal("no cue file")

def switch(value, opts):
	opts.get(value, lambda: None)()

def sigint_handler(sig, frame):
	fatal("\n")

def fall_on_exception(func):
	def safe_method(self, *args):
		try:
			func(self, *args)
		except Exception as exc:
			if hasattr(exc, "strerror"):
				msg = exc.strerror
			else:
				msg = str(exc)

			name = func.__name__
			fatal(name + " %s: %s", quote(self.filename), msg)

	return safe_method

class File:
	def __init__(self, filename, mode):
		self.filename = filename
		self.mode = mode
		self.open()

	@fall_on_exception
	def open(self):
		self.fp = open(self.filename, self.mode)

	@fall_on_exception
	def write(self, data):
		self.fp.write(data)

	@fall_on_exception
	def close(self):
		self.fp.close()

def write_titles(splitter, filename):
	fp = File(filename, "w") if filename != "-" else sys.stdout

	for name in splitter.get_titles():
		fp.write(name + "\n")

	if fp != sys.stdout:
		fp.close()

def main():
	options = parse_args()
	if not process_options(options):
		sys.exit(1)

	cuepath = to_unicode(options.cuefile)
	if os.path.isdir(cuepath):
		cuepath = find_cuefile(cuepath)
		if options.dry_run:
			debug("use cue file %s", quote(cuepath))

	cuesheet = None
	cue_error = lambda line, msg: printerr("%d: %s\n", line, msg)

	try:
		cuesheet = cue.read(cuepath, options.coding, cue_error, options.ignore)
	except IOError as err:
		fatal("open %s: %s", err.filename, err.strerror)
	except Exception as err:
		msg = "%s (%s)" % (err, err.__class__.__name__)

		if hasattr(err, "filename"):
			fatal("%s: %s: %s\n", err.filename, msg)
		else:
			fatal("%s\n", msg)

	cuesheet.dir = os.path.dirname(cuepath)

	if options.dump == "cue":
		print_cue(cuesheet)
		return 0

	splitter = Splitter(cuesheet, options)

	if options.export_titles != None:
		write_titles(splitter, options.export_titles)
		return 0

	switch(options.dump, {
		"tags":		lambda: splitter.dump_tags(),
		"tracks":	lambda: splitter.dump_tracks(),
		None:		lambda: splitter.split()
	})

	return 0

if __name__ == '__main__':
	signal.signal(signal.SIGINT, sigint_handler)
	sys.exit(main())
