#!/usr/bin/env python

import os
import re

from setuptools import find_packages, setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    with open(os.path.join(package, "__init__.py")) as f:
        return re.search("__version__ = ['\"]([^'\"]+)['\"]", f.read()).group(1)


setup(
    name='StarMallow',
    version=get_version("starmallow"),
    description='TechLock Query Service',
    author='Michiel Vanderlee',
    author_email='jmt.vanderlee@gmail.com',
    license="MIT",
    packages=find_packages(exclude=('tests', 'docs')),
    include_package_data=True,
    install_requires=[
        'apispec[marshmallow]>=5.1,<6',
        'dpath>=2.0.6,<3',
        "marshmallow>=3.11.0,<4",
        "marshmallow-dataclass>=8.3.1,<9",
        "python-multipart >=0.0.5,<0.0.6",
        "pyyaml>=5,<6",
        "starlette>=0.19,<1",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Typing :: Typed",
        "Framework :: AnyIO",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
