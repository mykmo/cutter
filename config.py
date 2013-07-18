from utils import is_python_v2, to_unicode
import os

if is_python_v2():
	import ConfigParser as configparser
else:
	import configparser

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

cfg = CfgParser()
cfg.read(os.path.expanduser("~/.cutter.cfg"))

DIR = to_unicode(cfg.get("encoding", "dir", "."))
COMPRESSION = cfg.getint("encoding", "compression")

SAMPLE_RATE = cfg.getint("output", "sample_rate")
CHANNELS = cfg.getint("output", "channels")
BITS_PER_SAMPLE = cfg.getint("output", "bits_per_sample")
