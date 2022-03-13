import glob
import logging
import nox
import os
import shutil


@nox.session
def tests(session):
    session.install('pytest')
    session.install('-r', 'requirements.txt')

    dir_mode = 0o0750

    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=logging.DEBUG)

    tmpdir = session.create_tmp()

    base_path = os.path.abspath(tmpdir)
    app_name = 'avium'

    app_home = os.path.join(base_path, app_name)
    test_path = os.path.join(session.invoked_from, r'tests')
    conf_path = os.path.join(test_path, r'config.yaml')
    conf_path_tests = os.path.join(app_home, r'conf', r'config.yaml')

    session.chdir(tmpdir)
    conf = os.path.join(app_home, r'conf')
    os.makedirs(conf, dir_mode)
    shutil.copy2(conf_path, conf_path_tests)
    __logger.info("Conf path tests... " + conf_path_tests)

    test_path += os.sep
    if session.posargs:
        test_files = session.posargs
        if len(test_files) > 0:
            test_path += '{0}'
            test_files = [test_path.format(i) for i in test_files]

    else:
        test_files = glob.glob(test_path + 'test_*')

    session.run('pytest', '-o', 'log_cli_level=DEBUG',
                '-o', 'log_cli=True',
                # session.invoked_from + os.sep + 'tests',
                *test_files,
                env={'APP_NAME': app_name, 'BASE_PATH': base_path})


__logger = logging.getLogger(__name__)
