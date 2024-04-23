"""
Setup file for the ecommerce-payfort Open edX ecommerce payment processor backend plugin.
"""
import os
import re
from pathlib import Path

from setuptools import find_packages, setup

README = open(Path(__file__).parent / 'README.rst').read()
CHANGELOG = open(Path(__file__).parent / 'CHANGELOG.rst').read()


def get_version(*file_paths):
    """
    Extract the version string from the file.

    @param file_paths: The path to the file containing the version string.
    @type file_paths: multiple str
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename, encoding="utf8").read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


def package_data(pkg, root_list):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for root in root_list:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


VERSION = get_version('ecommerce_payfort', '__init__.py')

setup(
    name='ecommerce-payfort',
    description='PayFort ecommerce payment processor backend plugin',
    version=VERSION,
    author='ZeitLabs',
    author_email='info@zeitlabs.com',
    long_description=f'{README}\n\n{CHANGELOG}',
    long_description_content_type='text/x-rst',
    url='https://github.com/Zeit-Labs/ecommerce-payfort',
    include_package_data=True,
    zip_safe=False,
    keywords='Django openedx openedx-plugin ecommerce payfort',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    install_requires=[
        'Django~=3.2',
    ],
    package_data=package_data('ecommerce_payfort', ['locale']),
    packages=find_packages(
        include=[
            'ecommerce_payfort', 'ecommerce_payfort.*',
        ],
        exclude=["*tests"],
    ),
    entry_points={
        'ecommerce': [
            'ecommerce_payfort = ecommerce_payfort.apps:PayFortConfig',
        ],
    },
)
