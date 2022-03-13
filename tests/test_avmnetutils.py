# Name: test_avmnetutils.py
# Author: Michael Konrad,
# Purpose: A set of methods to test the utility methods
# Date: 02-10-2021

import os

from avmutils import avmnetutils as lentils


def test_download_file():
    # Download VirtualBox Guest Additions to the tmp directory
    # Download VirtualBox Guest SHA Checksum to the tmp directory
    # Assert the files do not exist before the download
    # Assert the files do exist after the download
    vbox_url = r'https://download.virtualbox.org/virtualbox/6.1.26/'
    vbox_guest_iso = r'VBoxGuestAdditions_6.1.26.iso'
    vbox_guest_sha = r'SHA256SUMS'
    loc = r'.'

    assert not os.path.exists(vbox_guest_iso)
    assert not os.path.exists(vbox_guest_sha)

    lentils.download_file(loc, vbox_url + vbox_guest_iso)
    lentils.download_file(loc, vbox_url + vbox_guest_sha)

    assert os.path.exists(vbox_guest_iso)
    assert os.path.exists(vbox_guest_sha)


def test_verify_hash():
    loc = r'.'
    vbox_guest_iso = r'VBoxGuestAdditions_6.1.26.iso'
    vbox_guest_sha = r'SHA256SUMS'
    hash_ver = 'sha256'

    assert lentils.verify_hash(loc, vbox_guest_iso, vbox_guest_sha,
                               hash_ver)
