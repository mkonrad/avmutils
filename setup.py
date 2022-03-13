# setup.py
# Copyright (C) 2021, 2022 Michael Konrad

# This file is part of Avium Utilities.

# Avium Utilities is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Avium Utilities is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Avium Utilities. If not, see <https://www.gnu.org/licenses/>.

from setuptools import find_packages, setup

setup(
    name='avmutils',
    packages=find_packages(include=['avmutils']),
    version='0.1.1',
    description='Avium Utility Library',
    author='Michael Konrad',
    license='GNU Affero General Public License',
    install_requires=[
        'certifi == 2021.10.8',
        'charset-normalizer == 2.0.6',
        'idna == 3.2',
        'pycdlib == 1.12.0',
        'PyYAML == 5.4.1',
        'requests == 2.26.0',
        'urllib3 == 1.26.7',
    ],
)
