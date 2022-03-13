# avmnetutils.py is a set of functions for automating network operations
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

import hashlib
import logging
import os
import re
import requests
from urllib.parse import urlparse


def download_file(loc, url, overwrite=False):
    """
    Download a file from the specified url to the specified
    directory. Set overwrite to True to download and
    overwrite an existing file.

    If the file is existing and overwrite is false, the file
    will not be downloaded again.

    :param loc: the local directory to save the file to
    :param url: the complete URL including the file to be downloaded
    :param overwrite: set to True to overwrite a previously
                      downloaded file that exists locally
    """

    __logger.debug("Download location..." + loc)
    os.chdir(loc)

    furl = urlparse(url)

    if furl.scheme == '' and furl.netloc == '' and furl.path == '':
        raise Exception('The given URL will not work here.\n')
    else:
        url_path = furl.path
        path_parts = re.split('/', url_path)
        path_len = len(path_parts)
        file_name = path_parts[path_len - 1]

        wd = os.path.abspath(r'.')
        a_file = os.path.join(wd, file_name)

        if overwrite:
            dlf(file_name, url)
        else:
            if not os.path.exists(a_file):
                dlf(file_name, url)


def verify_hash(loc, file_name, checksum_file, hash_ver):
    """
    Verifies the hash of a downloaded file. Supports SHA1, SHA256, SHA512,
    and md5.

    :param loc: the local directory of the downloaded file
                and the checksum file
    :param file_name: the name of the file to verify
    :param checksum_file: the name of the file that contains
                          the hash to verify against
    :param hash_ver: Must be specified as: sha1, sha256, sha512, md5
    :return: returns True if the hash is verified, returns False
             if the hash is not verified
    """

    os.chdir(loc)

    hash_func = ''
    hash_len = 0
    # Set hash
    if 'sha1' == hash_ver:
        hash_len = 40
        hash_func = hashlib.sha1()
    elif 'sha256' == hash_ver:
        hash_len = 64
        hash_func = hashlib.sha256()
    elif 'sha512' == hash_ver:
        hash_len = 128
        hash_func = hashlib.sha512()
    elif 'md5' == hash_ver:
        hash_len = 16
        hash_func = hashlib.md5()
    else:
        return False

    ck_hash = ''
    # Open the checksum and get the relevant hash
    if os.path.exists(checksum_file) and os.path.exists(file_name):
        with open(checksum_file, 'r') as cf:
            cf_lines = cf.readlines()
            for line in cf_lines:
                tmp = line.strip().split(' ')
                if len(tmp) == 2:
                    if re.search(file_name, tmp[1]):
                        ck_hash = tmp[0]
                        __logger.debug("Retrieved checksum: %s", ck_hash)
                        __logger.debug("Length of checksum: %s", len(ck_hash))

    hf_hash = ''
    if os.path.exists(file_name):
        with open(file_name, 'rb') as hf:
            hf_content = hf.read()
            hash_func.update(hf_content)
            hf_hash = hash_func.hexdigest()
            __logger.debug("Calculated checksum:  %s", hf_hash)
            __logger.debug("Length of checksum: %s", len(hf_hash))

    if len(ck_hash) == hash_len and len(hf_hash) == hash_len:
        if ck_hash == hf_hash:
            __logger.info("Checksum... " + ck_hash + " verified.\n")
            return True
        else:
            return False
    else:
        return False


def dlf(file_name, furl):
    __logger.info("Downloading file... " + file_name)
    file_stream = requests.get(furl, stream=True)

    with open(file_name, 'wb') as local_file:
        for data in file_stream:
            local_file.write(data)

    local_file.close()
    __logger.info(file_name + " download completed.")


__logger = logging.getLogger(__name__)
