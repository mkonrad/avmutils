# avmvmutils.py is a set of functions for automating VitualBox virtual machine
# generation
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
import random
import re
import shutil
import subprocess
import sys
import time
import yaml


##############################################################################
# Create functions
##############################################################################


def create_hostonly_net(avium):
    config = avium.get_config()
    # Check if hostonly_net is already existing
    hi_out = subprocess.Popen(["vboxmanage", "list", "hostonlyifs"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = hi_out.communicate()

    result = stdout.decode()

    # If the hostonly network is not existing, create it
    if not result and not result.isspace():
        __logger.info("Adding VirtualBox host-only network...")
        # Create hostonly_net
        hi_out = subprocess.Popen(["vboxmanage", "hostonlyif", "create"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

        stdout, stderr = hi_out.communicate()
        __logger.info("Host only network added.\n" +
                      stdout.decode().strip())

    # Disable DHCP Server if Dnsmasq is enabled
    if config['app']['dnsmasq']:
        tmp = re.split('VBoxNetworkName: ', result.strip())
        if len(tmp) == 2:
            hostonly_name = tmp[1]

            dhcp_out = subprocess.Popen(["vboxmanage", "dhcpserver",
                                         "modify", "--netname",
                                         hostonly_name, "--disabled"],
                                        stdout.subprocess.PIPE,
                                        stderr.subprocess.STDOUT)

            stdout, stderr = dhcp_out.communicate()
            __logger.info("Disabled VirtualBox DHCP server on the " +
                          hostonly_name + " network, result..." +
                          stdout.decode().strip())


def create_vm(avium):
    # Create VM Shell verifies hostname
    vbox_home = create_vm_shell(avium)
    config = avium.get_config()

    __logger.info("Creating virtual machine...")
    # Generate VirtualBox machine
    subprocess.call(["vboxmanage", "modifyvm", config['vm']['hostname'],
                     "--memory", str(config['vm']['ram']), "--vram",
                     str(config['vm']['vram']), "--cpus",
                     str(config['vm']['cpu']),
                     "--defaultfrontend", config['vm']['frontend'],
                     "--graphicscontroller", "vmsvga", "--nic1",
                     config['vm']['nic1'], "--hostonlyadapter1",
                     config['vm']['hostonlynet'], "--nic2",
                     config['vm']['nic2'], "--boot1", "dvd", "--boot2", "disk",
                     "--boot3", "net"])

    # Create SATA controller
    subprocess.call(["vboxmanage", "storagectl", config['vm']['hostname'],
                    "--name", "SATA", "--add", "sata", "--bootable", "on"])

    # Add disk(s)
    disk_path = [None] * 2
    disk_path[0] = os.path.join(vbox_home, r'disk1.vdi')
    if 'managed' == config['vm']['node_type']:
        disk_path[1] = os.path.join(vbox_home, r'disk2.vdi')

    index = 0
    for dp in disk_path:
        subprocess.call(["vboxmanage", "createmedium", "disk", "--filename",
                         dp, "--size", str(config['vm']['hd_size']),
                         "--variant", "Standard"])
        subprocess.call(["vboxmanage", "storageattach",
                         config['vm']['hostname'],
                         "--storagectl", "SATA", "--port", str(index),
                         "--type", "hdd", "--medium", dp])
        index += 1

    if config['iso']['required']:
        # Add iso path
        if 'centos_7' == config['iso']['distro']:
            iso_path = os.path.join(config['app']['fs']['wd_path'], r'iso',
                                    config['centos_7']['custom_iso'])
        elif 'centos_8' == config['iso']['distro']:
            iso_path = os.path.join(config['app']['fs']['wd_path'], r'iso',
                                    config['centos_8']['custom_iso'])

        # Attach iso installer
        subprocess.call(["vboxmanage", "storageattach",
                         config['vm']['hostname'], "--storagectl", "SATA",
                         "--port", "2", "--type", "dvddrive",
                         "--medium", iso_path])

    __logger.info("Virtual machine created.")


def create_vm_shell(avium):
    config = avium.get_config()

    hostname = __check_hostname(config['vm']['hostname'])
    config['vm']['hostname'] = hostname
    ostype = config['vm']['ostype']
    __logger.info("Creating virtual machine shell...")

    vm_out = subprocess.Popen(["vboxmanage", "createvm", "--name", hostname,
                               "--ostype", ostype, "--register"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    try:
        vbox_settings = re.split(':', re.search('Settings file.*vbox?',
                                 stdout.decode()).group(0))

        tmp = vbox_settings[1].strip(" '")
        vbox_home = tmp.strip(hostname + '.vbox')

        # if only building a vm shell
        if not config['iso']['required']:
            # Attach empty optical drive to shell
            subprocess.call(["vboxmanage", "storageattach", hostname,
                             "--storagectl", "SATA", "--port", "1", "--type",
                             "dvddrive", "--medium", "emptydrive"])

        __logger.info("Virtual machine shell created.")
        return vbox_home

    except AttributeError:
        __logger.error("Exiting, unable to retrieve VirtualBox settings.")
        sys.exit(1)


def save_dhcp_record(avium):
    config = avium.get_config()

    if config['app']['dnsmasq']['enabled']:
        __logger.info("Saving DHCP record for " + config['vm']['hostname'])

        vm_rec_path = os.path.join(config['app']['fs']['wd_path'], r'db',
                                   config['vm']['hostname'] + ".yaml")

        with open(vm_rec_path) as rec:
            host_info = yaml.safe_load(rec)

        rec.close()

        # Filename format: <hostname>.yaml
        # Entry format: <hw:ma:ca:dd:re:ss>, <ipv.4ad.res.snn>, <hostname>
        sep_mac = ':'.join(host_info['vm']['hostonly_mac'][i:i + 2]
                           for i in range(0, len(
                               host_info['vm']['hostonly_mac']), 2))
        entry = sep_mac + ',' + host_info['vm']['hostonly_ipv4'] + ',' + \
            host_info['vm']['hostname']

        dhcp_path = os.path.join(config['app']['fs']['wd_path'], r'dhcp',
                                 host_info['vm']['hostname'])

        with open(dhcp_path, 'w') as dhcp:
            dhcp.write(entry)

        dhcp.close()
        __logger.info("Virtual machine DHCP record saved to " +
                      dhcp_path)


def save_vm_record(avium):
    # Saving a vm record is done on the host
    config = avium.get_config()
    # Get the hostonly inteface mac address
    hostonly_mac = __get_hostonly_mac_host(config['vm']['hostname'])

    __logger.info("Recording virtual machine record, " +
                  config['vm']['hostname'])

    template_path = os.path.join(avium.get_conf_home(), config['vm']['record'])

    with open(template_path) as rec:
        record = yaml.safe_load(rec)

    rec.close()

    record['vm']['hostname'] = config['vm']['hostname']
    record['vm']['dns_domain'] = config['vm']['dns_domain']
    record['vm']['hostonly_mac'] = hostonly_mac
    record['vm']['purpose'] = config['vm']['purpose']

    record_path = os.path.join(config['app']['fs']['wd_path'], r'db',
                               config['vm']['hostname'] + ".yaml")

    with open(record_path, 'w') as rec:
        yaml.dump(record, rec)

    rec.close()
    __logger.info("Vitual machine record recorded to " + record_path)


##############################################################################
# Read functions
##############################################################################


def get_vbox_version():
    if shutil.which('vboxmanage'):
        vbox_bin = shutil.which('vboxmanage')
    elif shutil.which('VBoxControl'):
        vbox_bin = shutil.which('VBoxControl')
    else:
        vbox_bin = ''

    vm_out = subprocess.Popen([vbox_bin, "--version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    tmp = re.split('r', stdout.decode())

    return tmp[0].strip()


def get_vm_state(hostname):
    vm_out = subprocess.Popen(["vboxmanage", "showvminfo", hostname,
                               "--details", "--machinereadable"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()
    state_tmp = re.split('=', re.search('VMState=.*',
                                        stdout.decode()).group(0))

    state = state_tmp[1].strip('""')

    return state


def list_vms():
    vm_out = subprocess.Popen(["vboxmanage", "list", "vms"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    tmp_list = stdout.decode().split("\n")
    idx = 0
    for vm in tmp_list:
        if not vm:
            tmp_list.pop(idx)
        idx += 1

    vm_list = []

    idx = 0
    for vm in tmp_list:
        name = tmp_list[idx].split(' ')[0].strip('""')
        name += ', ' + get_vm_state(name)
        vm_list.append(name)
        idx += 1

    print("VM Name,      State")
    print("===================")
    for vm in vm_list:
        print(vm)


def start_vm(vm_name):
    subprocess.call(["vboxmanage", "startvm", vm_name,
                     "--type", "headless"])

    # Check state
    result = get_vm_state(vm_name)
    while 'running' != result:
        time.sleep(0.500)
        result = get_vm_state(vm_name)
        if 'stuck' == result:
            __logger.error("Virtual machine, " + vm_name + " is in stuck \
                           state. Review virtual machine to troubleshoot.")
            sys.exit(3)

    __logger.info("Virtual machine, " + vm_name + " is now..." + result)


##############################################################################
# Update functions
##############################################################################


def post_deployment_cleanup():
    __logger.info("Setup complete, removing cron job and restoring issue file.\
                  ")
    # Remove the cron job
    if os.path.exists(r'/etc/cron.d/runner'):
        os.remove(r'/etc/cron.d/runner')

    # Replace issue message
    issue_orig = r'/etc/issue.orig'
    issue_path = r'/etc/issue'

    shutil.copy2(issue_orig, issue_path)


def update_vm_record_ipv4_guest(avium):
    """
    Updates the virtual machine record stored in the avium runtime directory
    on the host computer.
    The virual machine record is updated with the hostonly network ipv4
    address. This update is dependent upon virtual box guest integration.
    """
    config = avium.get_config()

    if config['virtualbox']['enabled']:
        __logger.info("Updating VM record with IPv4 address.")
        vm_rec_path = os.path.join(config['vm']['guest_share'],
                                   config['app']['fs']['wd_home'], r'db',
                                   config['vm']['hostname'] + r'.yaml')

        with open(vm_rec_path) as rec:
            vm_info = yaml.safe_load(rec)

        rec.close()

        # Add IPv4 Address to Inventory record
        vm_info['vm']['hostonly_ipv4'] = __get_hostonly_ipv4_guest()

        with open(vm_rec_path, 'w') as rec:
            yaml.dump_all(vm_info, rec)

        rec.close()
        __logger.info("VM record updated.")


def install_vbox_guest_additions(avium):
    """
    Install VirtualBox Guest Additions.
    """
    config = avium.get_config()

    if config['virtualbox']['enabled']:
        vbox_version = get_vbox_version()
        vbox_file_name = config['virtualbox']['ga_iso_file'] + vbox_version \
            + '.iso'
        vbox_file_path = os.join.path('/opt/local', vbox_file_name)
        vbox_run = config['virtualbox']['run_bin']

        if os.path.exists(vbox_file_path):
            vm_out = subprocess.Popen(['mount', vbox_file_path, '/mnt/media'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOU)

            stdout, stderr = vm_out.communicate()
            __logger.debug(stdout.decode())
        else:
            __logger.error("VirtualBox Guest Additions iso not found.")

        if os.path.exists(vbox_run):
            vm_out = subprocess.Popen([vbox_run],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)

            stdout, stderr = vm_out.communicate()
            __logger.debug(stdout.decode())

            if stderr is None:
                __update_etc_fstab(config)
                __mount_share(config)

        else:
            __logger.error("VirtualBox Guest Additions installer not found.")


##############################################################################
# Private functions
##############################################################################


def __check_hostname(hostname):
    if 'random' == hostname:
        ran_name = 'tmp'
        ran_num = random.randint(123456, 987654)

        hostname = ran_name + str(ran_num)

    # TODO: Validate hostname against RFC 1123
    # "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|
    # [A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"

    return hostname


def __get_hostonly_ipv4_guest():
    vm_out = subprocess.Popen(["VBoxControl", "guestproperty", "enumerate"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    hostonly_ip = re.split(':', re.search(r'Net\/0\/V4/IP, value: [0-9\.]+',
                                          stdout.decode()).group())

    return hostonly_ip[1].strip()


def __get_hostonly_mac_guest():
    vm_out = subprocess.Popen(["VBoxControl", "guestproperty", "enumerate"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    hostonly_mac = re.split(':', re.search(r'Net\/0\/MAC, value: [A-F0-9]+',
                            stdout.decode()).group())

    return hostonly_mac[1].strip()


def __get_hostonly_mac_host(hostname):

    vm_out = subprocess.Popen(["vboxmanage", "showvminfo", hostname,
                               "--machinereadable"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)

    stdout, stderr = vm_out.communicate()

    hi_raw = re.split('=', re.search('macaddress1=.*',
                                     stdout.decode()).group(0))

    hi_formatted = hi_raw[1].strip('""')

    return hi_formatted


def __mount_share(config):
    share = config['vm']['guest_share']
    subprocess.call(['mount', share])


def __update_etc_fstab(config):
    fstab_path = config['vm']['fstab_path']
    # Mount VirtualBox shared folder
    fstab_entry = config['vm']['fstab_entry_start'] + \
        config['vm']['guest_share'] + \
        config['vm']['fstab_entry_end']

    with open(fstab_path, 'a') as fst:
        fst.write("\n")
        fst.write(fstab_entry)

        fst.close()


__logger = logging.getLogger(__name__)
