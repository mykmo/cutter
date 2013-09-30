#!/usr/bin/env python

from distutils.core import setup

import shutil
import os

shutil.copyfile("cutter.py", "cutter/cutter")

setup(name="cutter",
	description="Cue split program",
	author="Mikhail Osipov",
	author_email="mike.osipov@gmail.com",
	url="https://github.com/mykmo/cutter",
	packages=["cutter", "cutter.formats"],
	scripts=["cutter/cutter"]
)

try:
	os.remove("cutter/cutter")
except:
	pass

try:
	if os.path.exists("build/"):
		shutil.rmtree("build")
except:
	pass
