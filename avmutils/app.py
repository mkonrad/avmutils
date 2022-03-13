# app.py is a python class for managing the Avium application configuration
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
import yaml


class App:
    config = {}
    conf_file = ''
    conf_home = ''
    wd_home = ''
    name = ''
    runtime = ''

    __logger = logging.getLogger(__name__)

    def __init__(self, conf_home, name='avium'):
        self.name = name
        self.conf_home = conf_home
        self.__init_config()

    def get_config(self):
        return self.config

    def get_conf_home(self):
        return self.conf_home

    def save_config(self):
        if 'initialize' == self.runtime:
            self.conf_file = os.path.join(self.conf_home,
                                          self.config['app']['name'] +
                                          r'.yaml')
        with open(self.conf_file, 'w') as conf:
            yaml.dump(self.config, conf)

    def __init_config(self):
        self.__determine_conf_file()

        with open(self.conf_file) as conf:
            self.config = yaml.safe_load(conf)

            conf.close()

            if not self.config['app']['configured']:
                p_wd = self.config['vm']['host_share']
                if not os.path.exists(p_wd):
                    raise RuntimeError('Application shared directory does not \
                                    exist.')
                else:
                    p_wd = os.path.join(p_wd,
                                        self.config['app']['fs']['wd_home'])
                    self.wd_home = os.path.abspath(p_wd)
                    self.config['app']['fs']['wd_path'] = self.wd_home
                    self.__init_app_directory()
                    self.config['app']['configured'] = True
                    self.save_config()

    def __init_app_directory(self):
        dir_mode = 0o0750
        # Create the application hidden working directory <.app_name>
        if not os.path.exists(self.wd_home):
            os.mkdir(self.wd_home, dir_mode)
            os.chdir(self.wd_home)
            sub_wds = self.config['app']['fs']['wd_sub']
            for a_wd in sub_wds:
                if not os.path.exists(a_wd):
                    os.mkdir(a_wd, dir_mode)

        # Create avium specific directories
        if 'avium' == self.config['app']['name']:
            self.__init_avium_directory()

    def __init_avium_directory(self):
        dir_mode = 0o0750
        if not self.config['app']['configured']:
            centos_wd = os.path.join(self.wd_home, r'centos')
            iso_wd = os.path.join(self.wd_home, r'iso')
            virtualbox_wd = os.path.join(self.wd_home, r'vbox_guest')

            os.chdir(centos_wd)
            centos_sub = self.config['app']['fs']['centos_sub']
            for a_wd in centos_sub:
                if not os.path.exists(a_wd):
                    os.mkdir(a_wd, dir_mode)

            centos7_wd = os.path.join(centos_wd, r'centos_7')
            centos8_wd = os.path.join(centos_wd, r'centos_8')
            self.config['centos_7']['local_path'] = os.path.abspath(centos7_wd)
            self.config['centos_8']['local_path'] = os.path.abspath(centos8_wd)
            self.config['iso']['local_path'] = os.path.abspath(iso_wd)
            self.config['virtualbox']['local_path'] = \
                os.path.abspath(virtualbox_wd)

    def __determine_conf_file(self):
        # Default configuration file
        default_file = os.path.join(self.conf_home, r'config.yaml')
        # Runtime configuration file
        runtime_file = os.path.join(self.conf_home, self.name + '.yaml')

        self.__logger.debug("Default configuration file..." + default_file)
        self.__logger.debug("Runtime configuration file..." + runtime_file)

        if not os.path.exists(runtime_file):
            self.runtime = 'initialize'
            self.conf_file = default_file
        elif os.path.exists(runtime_file):
            self.runtime = 'active'
            self.conf_file = runtime_file
        else:
            raise RuntimeError('Application configuration file not found.\n')
