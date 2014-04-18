from . handler import DecoderHandler, EncoderHandler

import os

handlers = ["flac", "ape", "ogg", "mp3", "wav", "wavpack"]

path = os.path.dirname(__file__) or "."

__encoders = {}
__decoders = {}

def __can_decode(obj):
	return hasattr(obj, "decode")

def __can_encode(obj):
	return hasattr(obj, "encode")

for entry in handlers:
	mod = __import__(entry, globals(), locals(), ["init"], 1)
	fmt = mod.init()

	if __can_encode(fmt):
		__encoders[fmt.name] = fmt
	if __can_decode(fmt):
		__decoders[fmt.ext] = fmt

def supported():
	return sorted(__encoders.keys())

def issupported(name):
	return name in __encoders

def encoder(name):
	return EncoderHandler(__encoders.get(name)())

def decoder(name):
	handler_type = __decoders.get(name)

	if not handler_type:
		return None

	return DecoderHandler(handler_type())

def decoder_open(filename, *args, **kwargs):
	ext = filename.rpartition(".")[-1].lower()
	handler = decoder(ext)
	if handler is None:
		return None

	return handler.open(filename, *args, **kwargs)
