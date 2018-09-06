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


base_dir = os.path.dirname(__file__)
src_dir = os.path.join(base_dir, "src")

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
sys.path.insert(0, src_dir)

about = {}
with open(os.path.join(src_dir, "cryptography", "__about__.py")) as f:
    exec(f.read(), about)





class PyTest(test):
    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

        # This means there's a vectors/ folder with the package in here.
        # cd into it, install the vectors package and then refresh sys.path
        if VECTORS_DEPENDENCY not in test_requirements:
            subprocess.check_call(
                [sys.executable, "setup.py", "install"], cwd="vectors"
            )
            pkg_resources.get_distribution("cryptography_vectors").activate()

    def run_tests(self):
        # Import here because in module scope the eggs are not loaded.
        import pytest
        test_args = [os.path.join(base_dir, "tests")]
        errno = pytest.main(test_args)
        sys.exit(errno)








with open(os.path.join(base_dir, "README.rst")) as f:
    long_description = f.read()


