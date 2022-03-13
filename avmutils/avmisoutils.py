# avmisoutils.py is a set of functions for customizing a Linux deployment iso
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

import logging
import os
import pycdlib
import re
import sys

from avmutils import avmnetutils as netutils
from avmutils import avmvmutils as vmutils


def build_custom_centos_iso(avium):
    __logger.info("Building custom CentOS iso...")
    config = avium.get_config()
    distro = config['iso']['distro']

    iso_path = download_distro(avium)
    download_vbox_guest_additions(avium)

    iso_tmp = pycdlib.PyCdlib()

    iso_tmp.open(iso_path)

    # Update boot configuration
    __mod_isolinux(config, iso_tmp)

    # Generate custom kickstart file
    __mod_kickstart(avium, iso_tmp)

    # Add local directory and configuration
    iso_tmp.add_directory('/LOCAL', rr_name='local')
    __add_avium_config(config, iso_tmp)

    # Add runner file
    __add_runner(avium, iso_tmp)

    # Add User' public ssh key
    __add_user_ssh_key(config, iso_tmp)

    # Add VirtualBox Guest Additions to ISO
    __add_vbox_guest_additions(config, iso_tmp)

    # Add avmutils library
    __add_avmutils(config, iso_tmp)

    # Save new iso image
    iso_wd = config['iso']['local_path']
    os.chdir(iso_wd)
    if 'centos_7' == distro:
        iso_tmp.write('centos7_ks.iso')
    elif 'centos_8' == distro:
        iso_tmp.write('centos8_ks.iso')
    else:
        __logger.error("Exiting, distribution not supported. Custom iso \
              not generated.")
        sys.exit(1)

    iso_tmp.close()
    __logger.info("Custom CentOS iso is ready.")


def download_vbox_guest_additions(avium):
    config = avium.get_config()

    if config['virtualbox']['enabled']:
        ga_checksum_file = config['virtualbox']['ga_checksum_file']
        ga_iso_file_base = config['virtualbox']['ga_iso_file']
        ga_iso_file = ga_iso_file_base + vmutils.get_vbox_version() + r'.iso'
        iso_url = config['virtualbox']['iso_url']
        vbox_path = config['virtualbox']['local_path']

        netutils.download_file(vbox_path, iso_url + r'/' + ga_iso_file)
        netutils.download_file(vbox_path, iso_url + r'/' + ga_checksum_file)
        netutils.verify_hash(vbox_path, ga_iso_file, ga_checksum_file, 'SHA26')


def download_distro(avium):
    config = avium.get_config()
    distro = config['iso']['distro']

    if 'centos_7' == distro:
        checksum_file = config['centos_7']['checksum_file']
        iso_file = config['centos_7']['iso_file']
        iso_url = config['centos_7']['iso_url']
        centos_path = config['centos_7']['local_path']
    elif 'centos_8' == distro:
        checksum_file = config['centos_8']['checksum_file']
        iso_file = config['centos_8']['iso_file']
        iso_url = config['centos_8']['iso_url']
        centos_path = config['centos_8']['local_path']
    else:
        __logger.error("Exiting, distro " + distro + " is not supported.\n")
        sys.exit(1)

    __logger.debug("CentOS path..." + centos_path)
    netutils.download_file(centos_path, iso_url + r'/' + iso_file)
    netutils.download_file(centos_path, iso_url + r'/' + checksum_file)
    netutils.verify_hash(centos_path, iso_file, checksum_file, 'SHA26')

    return os.path.join(centos_path, iso_file)


def __add_avium_config(config, iso_tmp):
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    config_bytes = bytes(str(config), 'utf-8')
    config_bio = BytesIO(config_bytes)

    iso_tmp.add_fp(config_bio, len(config_bytes),
                   iso_path='/LOCAL/AVIUM.YAML;1', rr_name='avium.yaml')


def __add_runner(avium, iso_tmp):
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    runner_file_name = r'runner.py'
    runner_path = os.path.join(avium.get_conf_home(), r'local',
                               runner_file_name)

    if os.path.isfile(runner_path):
        with open(runner_path, 'r') as run:
            runner_content = run.read()

            runner_bytes = bytes(str(runner_content), 'utf-8')
            runner_bio = BytesIO(runner_bytes)

            iso_tmp.add_fp(runner_bio, len(runner_bytes),
                           iso_path='/LOCAL/RUNNER.PY;1',
                           rr_name=runner_file_name)


def __add_user_ssh_key(config, iso_tmp):
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    __logger.info("Adding SSH public key file to iso image...")
    ssh_pub_key_path = config['user']['public_key']
    path, pub_key_file_name = os.path.split(ssh_pub_key_path)

    if os.path.isfile(ssh_pub_key_path):
        with open(ssh_pub_key_path, 'r') as pubkey:
            pubkey_content = pubkey.read()

            pubkey_bytes = bytes(str(pubkey_content), 'utf-8')
            pubkey_bio = BytesIO(pubkey_bytes)

            iso_tmp.add_fp(pubkey_bio, len(pubkey_bytes),
                           iso_path='/LOCAL/PUBKEY.PUB;1',
                           rr_name=pub_key_file_name)

        pubkey.close()
        __logger.info("Public key added to the iso image.")

    else:
        __logger.error("SSH public key file, " + ssh_pub_key_path +
                       " not found.")


def __add_vbox_guest_additions(config, iso_tmp):
    if config['virtualbox']['enabled']:

        try:
            from cStringIO import StringIO as BytesIO
        except ImportError:
            from io import BytesIO

        __logger.info("Adding Virtual Box Guest Additions installer to "
                      "iso image.")

        ga_filename = config['virtualbox']['ga_iso_file'] + \
            vmutils.get_vbox_version() + r'.iso'

        vbox_guest_path = os.path.join(config['virtualbox']['local_path'],
                                       ga_filename)

        if os.path.isfile(vbox_guest_path):
            with open(vbox_guest_path, 'rb') as ga:
                ga_content = ga.read()

                ga_bytes = bytes(str(ga_content), 'utf-8')
                ga_bio = BytesIO(ga_bytes)

                iso_tmp.add_fp(ga_bio, len(ga_bytes),
                               iso_path='/LOCAL/VBGUEST.ISO;1',
                               rr_name=ga_filename)

            __logger.info("Vitual Box Guest Additions installer added to \
                          the iso image.")
            ga.close()
        else:
            __logger.error("Virtual Box Guest Additions iso, " +
                           vbox_guest_path + " not found.")


def __add_avmutils(config, iso_tmp):
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    __logger.info("Adding Avium Utilities to the iso image.")

    avmutils_filename = config['app']['avmutils']['wheel_name']
    avmutils_path = os.path.join(config['app']['fs']['wd_path'], r'avmutils',
                                 avmutils_filename)

    if os.path.isfile(avmutils_path):
        with open(avmutils_path, 'rb') as au:
            au_content = au.read()

            au_bytes = bytes(str(au_content), 'utf-8')
            au_bio = BytesIO(au_bytes)

            iso_tmp.add_fp(au_bio, len(au_bytes),
                           iso_path='/LOCAL/AVMUTILS.WHL;1',
                           rr_name=avmutils_filename)

        __logger.info("Avium utilities added to the iso image.")
        au.close()
    else:
        __logger.error("Avium utilities, " + avmutils_path + " not found.")


def __mod_isolinux(config, iso_tmp):
    distro = config['iso']['distro']
    __logger.debug("Distro..." + distro)

    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    __logger.info("Updating isolinux.cfg...")
    # Update boot menu
    ext_isolinux_cfg = BytesIO()

    iso_tmp.get_file_from_iso_fp(ext_isolinux_cfg,
                                 iso_path='/ISOLINUX/ISOLINUX.CFG;1')
    isolinux_cfg = ext_isolinux_cfg.getvalue().decode('utf-8')

    isolinux_mod = re.sub(config['isolinux']['timeout_key'],
                          config['isolinux']['timeout_value'], isolinux_cfg)

    isolinux_mod = re.sub(config['isolinux']['menu_key'],
                          config['isolinux']['menu_value'], isolinux_mod)

    if 'centos_7' == distro:
        isolinux_mod = re.sub(config['isolinux']['label_key'],
                              config['isolinux']['label_7_value'],
                              isolinux_mod)
    elif 'centos_8' == distro:
        isolinux_mod = re.sub(config['isolinux']['label_key'],
                              config['isolinux']['label_8_value'],
                              isolinux_mod)
    else:
        __logger.error("Exiting, distro " + distro + " not supported.")
        sys.exit(1)

    # Remove existing file
    iso_tmp.rm_file(iso_path='/ISOLINUX/ISOLINUX.CFG;1')
    # __logger.debug("Updated isolinux.cfg...\n" + isolinux_mod)
    isolinux_bytes = bytes(isolinux_mod, 'utf-8')
    isolinux_bio = BytesIO(isolinux_bytes)

    iso_tmp.add_fp(isolinux_bio, len(isolinux_bytes),
                   iso_path='/ISOLINUX/ISOLINUX.CFG;1', rr_name='isolinux.cfg')

    __logger.info("Isolinux.cfg updated on iso image.")


def __mod_kickstart(avium, iso_tmp):
    __logger.info("Generating kickstart file...")
    config = avium.get_config()

    distro = config['iso']['distro']

    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from io import BytesIO

    # Add custom kickstart file to ISO
    if 'centos_7' == distro:
        ks_fh = os.path.join(avium.get_conf_home(), r'local',
                             config['centos_7']['kickstart'])
        __logger.debug("CentOS 7 kickstart file..." + ks_fh)
    elif 'centos_8' == distro:
        ks_fh = os.path.join(avium.get_conf_home(), r'local',
                             config['centos_8']['kickstart'])
        __logger.debug("CentOS 8 kickstart file..." + ks_fh)
    else:
        __logger.error("Exiting, Linux distribution not supported.")
        sys.exit(1)

    # Type of node to build
    node_type = config['vm']['node_type']

    if os.path.isfile(ks_fh):
        with open(ks_fh, 'r') as ks:
            ks_content = ks.read()
            ks.seek(0)

            ks_content = re.sub(config['kickstart']['username_key'],
                                config['user']['username'], ks_content)

            ks_content = re.sub(config['kickstart']['fullname_key'],
                                config['user']['fullname'], ks_content)

            ks_content = re.sub(config['kickstart']['disk_use_key'],
                                config['kickstart']['disk_use_value'],
                                ks_content)

            ks_content = re.sub(config['kickstart']['disk_part_key'],
                                config['kickstart']['disk_part_value'],
                                ks_content)

            ks_content = re.sub(config['kickstart']['disk_add_key'],
                                config['kickstart']['disk_add_value'],
                                ks_content)

            if 'managed' == node_type:
                ks_content = re.sub(config['kickstart']['package_key'],
                                    config['kickstart']
                                    ['package_managed'], ks_content)
            elif 'admin' == node_type:
                ks_content = re.sub(config['kickstart']['package_key'],
                                    config['kickstart']
                                    ['package_admin'], ks_content)
            else:
                ks_content = re.sub(config['kickstart']['package_key'],
                                    config['kickstart']
                                    ['package_none'], ks_content)

            ks.close()
            kickstart_bytes = bytes(ks_content, 'utf-8')
            kickstart_bio = BytesIO(kickstart_bytes)

            iso_tmp.add_fp(kickstart_bio, len(kickstart_bytes),
                           '/KS.CFG;1', rr_name='ks.cfg')

            __logger.info("Kickstart file generated and added to iso image.")
    else:
        __logger.error("Kickstart file, " + ks_fh + " not found.")


__logger = logging.getLogger(__name__)
