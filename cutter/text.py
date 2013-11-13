from . coding import is_python_v2, to_unicode

if is_python_v2():
	import ctypes.util
	import locale

	locale.setlocale(locale.LC_ALL, '')

	lib_path = ctypes.util.find_library('c')
	if lib_path:
		try:
			libc = ctypes.cdll.LoadLibrary(lib_path)
		except:
			libc = None

	if libc:
		__isprint = lambda char: libc.iswprint(ord(char)) != 0

		def isprint(string):
			return all(map(__isprint, to_unicode(string)))
	else:
		def isprint(string):
			raise Exception("Failed to load libc.so")
else:
	def isprint(string):
		return string.isprintable()
