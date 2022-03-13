# avmdmasqutils.py is a set of functions for automating dnsmasq configuration
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
import shutil
import stat
import subprocess

from avmutils import avmosutils as lentils


def start_dnsmasq(avium):
    config = avium.get_config()

    if config['app']['dnsmasq']['enabled']:
        __logger.info("Starting Dnsmasq...")

        if os.path.isfile(config['app']['dnsmasq']['bin_path']):
            if config['app']['dnsmasq']['configured']:
                if is_sudopriv_existing(config):
                    dhcp_wd = os.path.join(config['app']['fs']['wd_path'],
                                           r'dhcp')
                    log_file = os.path.join(
                        config['app']['dnsmasq']['log_path'], r'dnsmasq.log')
                    config_file = os.path.join(
                        config['app']['dnsmasq']['etc_path'],
                        config['app']['dnsmasq']['avium_dns'])

                    d_pid = lentils.process_check('dnsmasq')

                    if not d_pid:
                        subprocess.call(["sudo",
                                         config['app']['dnsmasq']['bin_path'],
                                         "--dhcp-hostsfile", dhcp_wd,
                                         "--log-facility", log_file,
                                         "--local-service",
                                         "--localise-queries",
                                         "-u",
                                         config['app']['dnsmasq']['user'],
                                         "-g",
                                         config['app']['dnsmasq']['group'],
                                         "-C", config_file
                                         ])
                    elif d_pid:
                        __logger.info("Dnsmasq is running.")
                else:
                    __logger.error("Dnsmasq sudoer privilege not found.\
                                   \nRun Avium setup_dnsmasq.py.")

            else:
                print("Please run Avium setup_dnsmasq.py.\
                      \nName resolution will not work until dnsmasq is \
                      configured.\n")
        else:
            __logger.error("Dnsmasq not found. Please install dnsmasq\
                           or modify Avium's configurations settings.")


def stop_dnsmasq(avium):
    config = avium.get_config()
    if is_sudopriv_existing(config):
        d_pid = lentils.process_check('dnsmasq')
        if d_pid:
            __logger.info("Stopping Dnsmasq...")
            subprocess.call(["sudo", "/bin/kill", "-TERM", d_pid])

        d_pid = lentils.process_check('dnsmasq')

        if not d_pid:
            __logger.info("Dnsmasq stopped.")
    else:
        __logger.info("Please run Avium dnsmasq_setup.py first.")


def setup_dnsmasq(avium):
    dir_mode = 0o0750
    config = avium.get_config()
    conf_home = avium.get_conf_home()

    if not config['app']['dnsmasq']['configured']:
        __logger.info("Configuring Dnsmasq...")

        avium_dns_path = os.path.join(conf_home,
                                      config['app']['dnsmasq']['avium_dns'])
        avium_resolv_path = os.path.join(conf_home,
                                         config['app']['dnsmasq']
                                         ['avium_resolv'])
        etc_path = config['app']['dnsmasq']['etc_path']
        log_path = config['app']['dnsmasq']['log_path']
        mdns_resolver_path = os.path.join(conf_home,
                                          config['app']
                                          ['dnsmasq']['mdns_resolver'])
        etc_sudoer_path = config['app']['dnsmaq']['sudoer_path']
        sudo_priv_path = os.path.join(conf_home,
                                      config['app']['dnsmasq']['sudo_priv'])
        sudoer_path = os.path.join(etc_sudoer_path,
                                   config['app']['dnsmasq']['sudo_priv'])

        resolver_path = config['app']['dnsmasq']['resolver_path']

        if not os.path.exists(log_path):
            os.makedirs(config['app']['dnsmasq']['log_path'], dir_mode)

        if os.path.exists(etc_path):
            etc_avium_dns = os.path.join(etc_path,
                                         config['app']['dnsmasq']['avium_dns'])
            etc_avium_resolv = os.path.join(etc_path,
                                            config['app']['dnsmasq']
                                            ['avium_resolv'])
            if not os.path.exists(etc_avium_dns):
                shutil.copy2(avium_dns_path, etc_path)

            if not os.path.exists(etc_avium_resolv):
                shutil.copy2(avium_resolv_path, etc_path)

        if not os.path.exists(resolver_path):
            os.makedirs(resolver_path, dir_mode)
            shutil.copy2(mdns_resolver_path, resolver_path)

        if not os.path.exists(sudoer_path):
            shutil.copy2(sudo_priv_path,
                         config['app']['dnsmasq']['sudoer_path'])
            shutil.chown(sudoer_path, 'root', 'wheel')
            os.chmod(sudoer_path, stat.IRUSR | stat.IWUSR)

        config['app']['dnsmasq']['configured'] = True

        __logger.info("Dnsmasq configured.")

        avium.save_config()


def is_sudopriv_existing(config):
    etc_sudoer_path = config['app']['dnsmasq']['sudoer_path']
    sudoer_file_path = os.path.join(etc_sudoer_path,
                                    config['app']['dnsmasq']['sudo_priv'])
    if os.path.exists(sudoer_file_path):
        return True
    else:
        return False


__logger = logging.getLogger(__name__)
