# Name: test_app.py
# Author: Michael Konrad,
# Definition: A set of methods to test the App Class
# Date: 09-10-2021

import logging
import os

from avmutils import app


def test_app():
    # Test configuration reading
    app_name = os.environ['APP_NAME']
    base_path = os.environ['BASE_PATH']
    name = 'avium'
    version = '0.0.1'
    sub_wd = ['vbox_guest', 'centos', 'dhcp', 'db', 'iso']
    an_app = app.App(app_name, base_path)

    config = an_app.get_config()
    c_name = config['app']['name']
    c_version = config['app']['version']
    c_sub_wd = config['app']['fs']['sub_wd']
    vim_plug_url = config['user']['vim_plug_url']
    __logger.info("Vim plug url... " + vim_plug_url)

    assert name == c_name
    assert version == c_version
    assert sub_wd == c_sub_wd


__logger = logging.getLogger(__name__)
