from utils import is_python_v2, to_unicode
import os

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

ConfigParserClass = configparser.RawConfigParser

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
cfg.read(os.path.expanduser("~/.cutter.cfg"))

DIR			= cfg.get("encoding", "dir", ".")
TYPE			= cfg.get("encoding", "type")
USE_TEMPDIR		= cfg.getbool("encoding", "use_tempdir")
COMPRESSION		= cfg.getint("encoding", "compression")

SAMPLE_RATE		= cfg.getint("output", "sample_rate")
CHANNELS		= cfg.getint("output", "channels")
BITS_PER_SAMPLE		= cfg.getint("output", "bits_per_sample")

FILENAME_FORMAT		= cfg.get("filename", "format", DEFAULT_FILENAME_FORMAT)
CONVERT_CHARS		= cfg.getbool("filename", "convert_chars", False)

FLAC_COMPRESSION	= cfg.getint("flac", "compression")
OGG_COMPRESSION		= cfg.getint("ogg", "compression")
MP3_BITRATE		= cfg.getint("mp3", "bitrate")
