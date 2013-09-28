import importlib
import os

path = os.path.dirname(__file__) or "."

__formats = {}

for entry in sorted(os.listdir(path)):
	if not entry.endswith(".py") or entry.startswith("_"):
		continue

	modname = entry.replace(".py", "")
	mod = __import__(modname, globals(), locals(), ["init"], 1)
	fmt = mod.init()
	__formats[fmt.name] = fmt

def supported():
	return sorted(__formats.keys())

def issupported(name):
	return name in __formats

def handler(name, logger = None):
	return __formats.get(name)(logger)
