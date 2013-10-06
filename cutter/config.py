from . coding import is_python_v2, to_unicode
import os

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

CONFIG_FILE_PATH = os.path.expanduser("~/.cutter.cfg")

ConfigParserClass = configparser.RawConfigParser

def __create_default(name):
	fp = open(name, "w")

	fp.write(
"""[encoding]
# type = <default format type>

# where to place new files
dir = .

# use temporary directory for converted files
use_tempdir = false

[output]
# sample_rate =
# channels =
# bits_per_sample =

[filename]
format = %s

# convert illegal for fat32 filesystem characters
convert_chars = false

[flac]
# from the least compression (but fastest) to the best compression (but slowest)
# compression = <0 .. 8>

[ogg]
# from the highest compression (lowest quality) to the lowest compression (highest quality)
# compression = <-1 .. 10>

[mp3]
# bitrate = <32 .. 320>
""" % DEFAULT_FILENAME_FORMAT)

	fp.close()

def with_default(func, msg = None):
	def method(cls, section, option, default = None):
		try:
			return func(cls.parser, section, option)
		except configparser.NoSectionError:
			return default
		except configparser.NoOptionError:
			return default
		except ValueError as err:
			raise Exception("%s::%s: %s" % (section, option, msg or err))
	return method

class CfgParser:
	def __init__(self):
		self.parser = ConfigParserClass()

	__get = with_default(ConfigParserClass.get)

	if not is_python_v2():
		get = __get
	else:
		def get(self, *args):
			return to_unicode(self.__get(*args))

	getint = with_default(ConfigParserClass.getint, "invalid number")
	getbool = with_default(ConfigParserClass.getboolean, "invalid bool")

	def __getattr__(self, attr):
		return getattr(self.parser, attr)

DEFAULT_FILENAME_FORMAT = "{tracknumber:02d}.{title}"

cfg = CfgParser()
if not cfg.read(os.path.expanduser(CONFIG_FILE_PATH)):
	__create_default(CONFIG_FILE_PATH)

DIR			= cfg.get("encoding", "dir", ".")
TYPE			= cfg.get("encoding", "type")
USE_TEMPDIR		= cfg.getbool("encoding", "use_tempdir")

SAMPLE_RATE		= cfg.getint("output", "sample_rate")
CHANNELS		= cfg.getint("output", "channels")
BITS_PER_SAMPLE		= cfg.getint("output", "bits_per_sample")

FILENAME_FORMAT		= cfg.get("filename", "format", DEFAULT_FILENAME_FORMAT)
CONVERT_CHARS		= cfg.getbool("filename", "convert_chars", False)

FLAC_COMPRESSION	= cfg.getint("flac", "compression")
OGG_COMPRESSION		= cfg.getint("ogg", "compression")
MP3_BITRATE		= cfg.getint("mp3", "bitrate")
