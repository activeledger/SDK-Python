#!/usr/bin/env python

# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

import os
import platform
import subprocess
import sys

import setuptools
from setuptools import find_packages, setup
from setuptools.command.install import install
from setuptools.command.test import test


# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
base_dir = os.path.dirname(__file__)
src_dir = os.path.join(base_dir, "src")
sys.path.insert(0, src_dir)

about = {}
with open(os.path.join(src_dir, "activeledgersdk", "__about__.py")) as f:
    exec(f.read(), about)

with open("README.md", "r") as fh:
    long_description = fh.read()
    
setup(
    name=about["__title__"],
    version=about["__version__"],

    description=about["__summary__"],
    long_description=long_description,
    license=about["__license__"],
    url=about["__uri__"],

    author=about["__author__"],
    author_email=about["__email__"],

    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True
)




