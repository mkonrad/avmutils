# avmusrmgmt.py is a set of functions for automating user management
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

import grp
import logging
import os
import pwd
import shutil
import stat
import subprocess

from avmutils import avmnetutils as netutils


def create_svc_account(username):
    try:
        grp_ent = grp.getgrnam('docker')
        __logger.debug("Docker group found, id..." + grp_ent.gr_gid)
        subprocess.call(["/usr/sbin/useradd", "-r", "-m", username,
                        "-G", "users,docker", "-s", "/sbin/nologin"])

    except KeyError:
        subprocess.call(["/usr/sbin/useradd", "-r", "-m", username,
                         "-G", "users", "-s", "/sbin/nologin"])


def create_vim_profile(avium, username):
    dir_mode = 0o0750
    config = avium.get_config()

    try:
        usr_ent = pwd.getpwnam(username)
        home = usr_ent.pw_dir

        if os.path.exists(home):
            vim_dir = os.path.join(home, r'.vim')
            vim_colors = os.path.join(vim_dir, r'colors')
            vim_autoload = os.path.join(vim_dir, r'autoload')
            vim_plugged = os.path.join(vim_dir, r'plugged')

            if not os.path.exists(vim_dir):
                os.mkdir(vim_dir, dir_mode)
            elif not os.path.exists(vim_colors):
                os.mkdir(vim_colors, dir_mode)
            elif not os.path.exists(vim_autoload):
                os.mkdir(vim_autoload, dir_mode)
            elif not os.path.exists(vim_plugged):
                os.mkdir(vim_plugged, dir_mode)
            else:
                __logger.info("Vim paths available...")

            __write_vimrc(home, config['user']['vimrc'])
            __load_vim_plug(vim_autoload, config['user']['vim_plug_url'])
            __load_vim_pymode(vim_plugged, config['user']['bash_support_url'],
                              config['app']['git']['bin_path'])

            subprocess.call(["chown", "-R", username, ":", username, vim_dir])

            subprocess.call(["su", "-", username, "vim", "+", "PlugInstall",
                             "--sync", "+", "qa"])

    except KeyError:
        __logger.error("User " + username + " not found.")


def update_bashrc(avium, username):
    config = avium.get_config()

    try:
        usr_ent = pwd.getpwnam(username)
        home = usr_ent.pw_dir

        bashrc_path = os.path.join(home, r'.bashrc')

        if os.path.isfile(bashrc_path):
            with open(bashrc_path, 'a') as rc:
                rc.write(config['user']['bash_aliases'])

            rc.close()

    except KeyError:
        __logger.error("User " + username + " not found.")


def initialize_user_ssh(avium):
    dir_mode = 0o0700
    config = avium.get_config()
    username = config['user']['username']
    ssh_pub_key = config['user']['public_key']

    try:
        usr_ent = pwd.getpwnam(username)
        home = usr_ent.pw_dir
        ssh_dir = os.path.join(home, r'.ssh')
        pub_key_src_path = os.path.join(config['app']['fs']['int_path'],
                                        ssh_pub_key)
        authz_keys_path = os.path.join(ssh_dir, r'authorized_keys')

        if not os.path.exists(ssh_dir):
            os.mkdir(ssh_dir, dir_mode)
            os.chdir(ssh_dir)
        if not os.path.isfile(authz_keys_path):
            shutil.copy2(pub_key_src_path, authz_keys_path)
        else:
            subprocess.call(['cat', pub_key_src_path, '>>', authz_keys_path])

        known_hosts_path = os.path.join(ssh_dir, r'known_hosts')

        if not os.path.isfile(known_hosts_path):
            with open(known_hosts_path, 'w') as knw:
                knw.write()
                knw.close()

        subprocess.call(['ssh-keyscan', 'github.com', '>>', known_hosts_path])
        subprocess.call(['ssh-keyscan', 'gitlab.com', '>>', known_hosts_path])

        shutil.chown(ssh_dir, username, username)
        shutil.chown(authz_keys_path, username, username)
        os.chmod(authz_keys_path, stat.IRUSR | stat.IWUSR)
        shutil.chown(known_hosts_path, username, username)
        os.chmod(known_hosts_path, stat.IRUSR | stat.IWUSR)

    except KeyError:
        __logger.error("User " + username + " not found.")


def set_password(username, password, length=20):
    if 'generate' == password:
        new_pass = __generate_pwd(length)
    else:
        new_pass = password

    __change_password(username, new_pass)


def __write_vimrc(home, vimrc_content):
    vim_rc = os.path.join(home, r'.vimrc')
    with open(vim_rc, 'w') as vrc:
        vrc.write(vimrc_content)

    vrc.close()


def __load_vim_plug(vim_autoload, vim_plug_url):
    plug_vim = os.path.join(vim_autoload, r'plug.vim')
    if not os.path.exists(plug_vim):
        netutils.download_file(vim_autoload, vim_plug_url)


def __load_vim_pymode(vim_plugged, vim_pymode_url, git_path):
    pymode_vim = os.path.join(vim_plugged, r'python-mode')
    if not os.path.exists(pymode_vim):
        if os.path.exists(git_path):
            subprocess.call([git_path, "clone",
                            "--recurse-submodules", vim_pymode_url])


def __generate_pwd(length):
    if shutil.which('pwgen'):
        pwd_out = subprocess.Popen(['pwgen', '-1', length],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

        stdout, stderr = pwd_out.communicate()

        return stdout.decode().strip()
    else:
        return "Ug1yP*$$Phr@s3DoN4tUs9_"


def __change_password(username, password):
    chp_bin = shutil.which('chpasswd')

    chp_out = subprocess.Popen(['echo', username + ':' + password, '|',
                                chp_bin],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    stdout, stderr = chp_out.communicate()
    __logger.debug(stdout.decode())


__logger = logging.getLogger(__name__)
