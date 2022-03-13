# avmosutils.py is a set of functions for automating operating system
# operations
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
import re
import shutil
import subprocess


def enable_docker(avium):
    config = avium.get_config()
    if 'managed' == config['vm']['node_type']:
        subprocess.call(['systemctl', 'enable', 'docker'])
        subprocess.call(['systemctl', 'enable', 'containerd'])


def start_docker(avium):
    config = avium.get_config()

    if 'managed' == config['vm']['node_type']:
        subprocess.call(['systemctl', 'start', 'docker'])
        subprocess.call(['systemctl', 'start', 'containerd'])


def format_docker_btrfs(avium):
    config = avium.get_config()
    if 'managed' == config['vm']['node_type']:
        subprocess.call(['umount', r'/var/lib/docker'])

        fs_out = subprocess.Popen(['/sbin/mkfs.btrfs', '-f',
                                  '/dev/mapper/datavg-var_lib_docker'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

        stdout, stderr = fs_out.communicate()
        __logger.debug(stdout.decode())


def mount_docker_btrfs(avium):
    config = avium.get_config()
    if 'managed' == config['vm']['node_type']:
        fs_out = subprocess.Popen(['mount', '-t', 'btrfs',
                                   '/dev/mapper/datavg-var_lib_docker',
                                   '/var/lib/docker'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

        stdout, stderr = fs_out.communicate()
        __logger.debug(stdout.decode())


def update_docker_fstab(avium):
    config = avium.get_config()

    fstab_path = r'/etc/fstab'

    with open(fstab_path, 'r') as fst:
        fst_content = fst.read()
        fst.close()

        fst_content = re.sub(config['vm']['docker_fs_key'],
                             config['vm']['docker_fs_value'],
                             fst_content)

    with open(fstab_path, 'w') as fst:
        fst.write(fst_content)
        fst.close()


def restart_sshd():
    subprocess.call(['systemctl', 'restart', 'sshd'])


def set_banner_message(avium):
    config = avium.get_config()
    banner_path = config['vm']['banner_path']

    if 'admin' == config['vm']['node_type']:
        banner_message = config['vm']['banner_admin']
    elif 'managed' == config['vm']['node_type']:
        banner_message = config['vm']['banner_managed']
    else:
        banner_message = ''

    with open(banner_path, 'w') as msg:
        msg.write(banner_message)
        msg.close()


def set_dual_nic_routing():
    # Set default route metric to place external nic (NAT)
    #   before internal nic (hostonly)
    subprocess.call(["nmcli", "con", "modify", "System enp0s3",
                     "ipv4.route-metric", "140"])
    subprocess.call(["nmcli", "con", "modify", "System enp0s3",
                     "ipv6.route-metric", "140"])
    subprocess.call(["nmcli", "con", "modify", "System enp0s8",
                     "ipv4.route-metric", "110"])
    subprocess.call(["nmcli", "con", "modify", "System enp0s8",
                     "ipv6.route-metric", "110"])


def set_etc_hosts(avium):
    # Append host info to /etc/hosts
    # Format: IP Address    hostname    fqdn
    __logger.info("Setting /etc/hosts entry...")
    hosts_path = r'/etc/hosts'

    # Set the host entry with the hostonly ipv4 address
    ipv4 = __get_ipv4_address("System enp0s3")

    fqdn = avium['vm']['hostname'] + avium['vm']['dns_domain']
    entry = ipv4 + "\t" + avium['vm']['hostname'] + "\t" + fqdn + "\n"

    with open(hosts_path, "a") as hosts:
        hosts.write("\n")
        hosts.write(entry)

    hosts.close()


def set_hostname(hostname):
    __logger.info("Setting hostname to... " + hostname)
    subprocess.call(["nmcli", "general", "hostname", hostname])


def set_ignore_auto_dns(avium):
    config = avium.get_config()
    nic = 'System enp0s8'

    if config['dnsmasq']['enabled']:
        # Remove DNS entries from external nic (NAT) to use
        # entries from internal nic (Hostonly)
        subprocess.call(["nmcli", "con", "modify", nic,
                        "ipv4.ignore-auto-dns"])


def set_sshd_config(avium):
    config = avium.get_config()

    sshd_config_file = config['sshd']['config_file_path']

    if os.path.exists(sshd_config_file):
        __logger.info("Updating SSH server configuration...")
        with open(sshd_config_file, 'r') as sshd_conf:
            sshd_conf_content = sshd_conf.read()

            sshd_conf.close()

        sshd_mod = re.sub(config['sshd']['pass_auth_key'],
                          config['sshd']['pass_auth_value'],
                          sshd_conf_content)

        sshd_mod = re.sub(config['sshd']['pubkey_auth_key'],
                          config['sshd']['pubkey_auth_value'],
                          sshd_mod)

        sshd_mod = re.sub(config['sshd']['client_ai_key'],
                          config['sshd']['client_ai_value'],
                          sshd_mod)

        sshd_mod = re.sub(config['sshd']['client_ai_count_key'],
                          config['sshd']['client_ai_count_value'],
                          sshd_mod)

        sshd_mod = re.sub(config['sshd']['tcp_keep_key'],
                          config['sshd']['tcp_keep_value'],
                          sshd_mod)

        sshd_mod = re.sub(config['sshd']['banner_key'],
                          config['sshd']['banner_value'],
                          sshd_mod)

        with open(sshd_config_file, 'w') as sshd_conf:
            sshd_conf.write(sshd_mod)
            sshd_conf.close()

        __logger.info("SSH server configuration updated.")


def set_kernel_userland_settings(avium):
    config = avium.get_config()
    __logger.info("Setting userland configuration...")

    sysctl_path = config['sysctl']['config_path']
    settings = config['sysctl']['settings']

    combined = "\n"

    for setting in settings:
        combined += setting + "\n"

    if not os.path.exists(sysctl_path):
        with open(sysctl_path, 'w') as conf:
            conf.write(combined)
            conf.close()
    else:
        with open(sysctl_path, 'a') as conf:
            conf.write(combined)
            conf.close()

    __logger.info("Userland configuration set.")


def set_selinux_permissive(avium):
    config = avium.get_config()

    enable_permissive = config['selinux']['set_to_permissive']

    if enable_permissive:

        selinux_path = config['selinux']['config_file_path']

        if os.path.exists(selinux_path):
            with open(selinux_path, 'r') as conf:
                conf_content = conf.read()

            conf.close()

            conf_content = re.sub(config['selinux']['se_perm_key'],
                                  config['selinux']['se_perm_value'],
                                  conf_content)

            with open(selinux_path, 'w') as conf:
                conf.write(conf_content)

            conf.close()


def set_limit_files(avium):
    config = avium.get_config()

    memlock_file_path = os.path.join(config['limits']['config_path'],
                                     config['limits']['memlock_file'])
    nofile_file_path = os.path.join(config['limits']['config_path'],
                                    config['limits']['nofile_file'])

    if not os.path.exists(memlock_file_path):
        settings = config['limits']['memlock']
        conf_content = ''
        for setting in settings:
            conf_content += setting + "\n"

        with open(memlock_file_path, 'w') as conf:
            conf.write(conf_content)

        conf.close()

    if not os.path.exists(nofile_file_path):
        settings = config['limits']['nofile']
        conf_content = ''
        for setting in settings:
            conf_content += setting + "\n"

        with open(nofile_file_path, 'w') as conf:
            conf.write(conf_content)

        conf.close()


def set_sudoer_priv_files(avium):
    config = avium.get_config()

    docker_file_path = os.path.join(config['sudoers']['config_path'],
                                    config['sudoers']['docker_file'])
    shutdown_file_path = os.path.join(config['sudoers']['config_path'],
                                      config['sudoers']['shutdown_file'])

    if not os.path.exists(docker_file_path):
        settings = config['sudoers']['docker_priv']
        conf_content = ''
        for setting in settings:
            conf_content += setting + "\n"

        with open(docker_file_path, 'w') as conf:
            conf.write(conf_content)

        conf.close()

    if not os.path.exists(shutdown_file_path):
        settings = config['sudoers']['shutdown_priv']
        conf_content = ''
        for setting in settings:
            conf_content += setting + "\n"

        with open(shutdown_file_path, 'w') as conf:
            conf.write(conf_content)

        conf.close()


def set_unified_cgroups():
    if shutil.which('grubby'):
        grubby_bin = shutil.which('grubby')

        gb_out = subprocess.Popen([grubby_bin, '--update-kernel=ALL',
                                   '--args="systemd.unified_cgroup_hierarchy=1'
                                   ],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

        stdout, stderr = gb_out.communicate()
        __logger.debug("Cgroup configured..." + stdout.decode())


def process_check(process_name):
    ps_out = subprocess.Popen(["pgrep", process_name],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = ps_out.communicate()

    ps_pid = stdout.decode().strip()

    return ps_pid


def restart_net():
    __logger.info("Stopping Network Manager service...")
    subprocess.call(["systemctl", "stop", "NetworkManager"])

    __logger.info("Starting Network Manager service...")
    subprocess.call(["systemclt", "start", "NetworkManager"])


# Restart mDNS on macOS


def restart_mdns():
    m_pid = process_check('mDNSResponder')

    if m_pid:
        __logger.info("Restarting mDNSResponder.")
        subprocess.call(["sudo", "/usr/bin/killall", "-HUP", "mDNSResponder"])
    else:
        print("mDNSResponder is not running.\n")


def start_xterm(config):
    # Start xterm s a bqckground process
    xterm_path = config['app']['xterm']['bin_path']

    if os.path.exists(xterm_path):
        if not process_check('xterm'):
            xt_out = subprocess.Popen([xterm_path],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)

            stdout, stderr = xt_out.communicate()
            # log result
    else:
        print("XTerm not found. Please install XQuartz or modify Avium's \
              configuration settings.\n")


##############################################################################
# Private functions
##############################################################################


__logger = logging.getLogger(__name__)


def __get_ipv4_address(nic):
    ip_out = subprocess.Popen(["nmcli", "-g", "ip4.address", "con",
                               "show", nic],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = ip_out.communicate()

    ip_nm = stdout.decode().strip()
    ip = ip_nm.split("/")

    return ip[0]
