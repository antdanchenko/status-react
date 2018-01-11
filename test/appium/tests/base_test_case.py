import pytest
import sys
import hmac
import re
import subprocess
import time
from tests import *
from os import environ
from appium import webdriver
from abc import ABCMeta, abstractmethod
from hashlib import md5
from selenium.common.exceptions import WebDriverException
from api_bindings.bitbar import BitBar
from tests.conftest import get_latest_apk
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt


class AbstractTestCase:

    __metaclass__ = ABCMeta

    @property
    def sauce_access_key(self):
        return environ.get('SAUCE_ACCESS_KEY')

    @property
    def sauce_username(self):
        return environ.get('SAUCE_USERNAME')

    @property
    def executor_sauce_lab(self):
        return 'http://%s:%s@ondemand.saucelabs.com:80/wd/hub' % (self.sauce_username, self.sauce_access_key)

    @property
    def executor_local(self):
        return 'http://localhost:4723/wd/hub'

    def get_public_url(self, driver):
        token = hmac.new(bytes(self.sauce_username + ":" + self.sauce_access_key, 'latin-1'),
                         bytes(driver.session_id, 'latin-1'), md5).hexdigest()
        return "https://saucelabs.com/jobs/%s?auth=%s" % (driver.session_id, token)

    def print_sauce_lab_info(self, driver):
        sys.stdout = sys.stderr
        print("SauceOnDemandSessionID=%s job-name=%s" % (driver.session_id,
                                                         pytest.config.getoption('build')))
        print(self.get_public_url(driver))

    def add_local_devices_to_capabilities(self):
        updated_capabilities = list()
        raw_out = re.split(r'[\r\\n]+', str(subprocess.check_output(['adb', 'devices'])).rstrip())
        for line in raw_out[1:]:
            serial = re.findall(r"([\d.\d:]*\d+)", line)
            if serial:
                capabilities = self.capabilities_local
                capabilities['udid'] = serial[0]
                updated_capabilities.append(capabilities)
        return updated_capabilities

    @property
    def capabilities_sauce_lab(self):
        desired_caps = dict()
        desired_caps['app'] = 'sauce-storage:' + test_data.apk_name

        desired_caps['build'] = pytest.config.getoption('build')
        desired_caps['name'] = test_data.test_name
        desired_caps['platformName'] = 'Android'
        desired_caps['appiumVersion'] = '1.7.1'
        desired_caps['platformVersion'] = '6.0'
        desired_caps['deviceName'] = 'Android GoogleAPI Emulator'
        desired_caps['deviceOrientation'] = "portrait"
        desired_caps['commandTimeout'] = 600
        desired_caps['idleTimeout'] = 1000
        return desired_caps

    @property
    def capabilities_local(self):
        desired_caps = dict()
        desired_caps['app'] = pytest.config.getoption('apk')
        desired_caps['deviceName'] = 'nexus_5'
        desired_caps['platformName'] = 'Android'
        desired_caps['appiumVersion'] = '1.7.1'
        desired_caps['platformVersion'] = '6.0'
        desired_caps['newCommandTimeout'] = 600
        desired_caps['fullReset'] = True
        return desired_caps

    @abstractmethod
    def setup_method(self, method):
        raise NotImplementedError('Should be overridden from a child class')

    @abstractmethod
    def teardown_method(self, method):
        raise NotImplementedError('Should be overridden from a child class')

    @property
    def environment(self):
        return pytest.config.getoption('env')

    @property
    def implicitly_wait(self):
        return 10


class LocalMultipleDeviceTestCase(AbstractTestCase):

    def setup_method(self, method):
        capabilities = self.add_local_devices_to_capabilities()
        self.driver_1 = webdriver.Remote(self.executor_local, capabilities[0])
        self.driver_2 = webdriver.Remote(self.executor_local, capabilities[1])
        for driver in self.driver_1, self.driver_2:
            driver.implicitly_wait(self.implicitly_wait)

    def teardown_method(self, method):
        for driver in self.driver_1, self.driver_2:
            try:
                driver.quit()
            except WebDriverException:
                pass


class SauceMultipleDeviceTestCase(AbstractTestCase):

    @classmethod
    def setup_class(cls):
        cls.loop = asyncio.get_event_loop()

    def setup_method(self, method):
        self.driver_1, \
        self.driver_2 = self.loop.run_until_complete(start_threads(2,
                                                              webdriver.Remote,
                                                              self.executor_sauce_lab,
                                                              self.capabilities_sauce_lab))
        for driver in self.driver_1, self.driver_2:
            driver.implicitly_wait(self.implicitly_wait)

    def teardown_method(self, method):
        for driver in self.driver_1, self.driver_2:
            self.print_sauce_lab_info(driver)
            try:
                driver.quit()
            except WebDriverException:
                pass

    @classmethod
    def teardown_class(cls):
        cls.loop.close()


class SingleDeviceTestCase(AbstractTestCase):

    def setup_method(self, method):

        capabilities = {'local': {'executor': self.executor_local,
                                  'capabilities': self.capabilities_local},
                        'sauce': {'executor': self.executor_sauce_lab,
                                  'capabilities': self.capabilities_sauce_lab}}

        self.driver = webdriver.Remote(capabilities[self.environment]['executor'],
                                       capabilities[self.environment]['capabilities'])
        self.driver.implicitly_wait(self.implicitly_wait)

    def teardown_method(self, method):
        if self.environment == 'sauce':
            self.print_sauce_lab_info(self.driver)
        try:
            self.driver.quit()
        except WebDriverException:
            pass


class BitBarTestCase(AbstractTestCase):

    @property
    def bit_bar_api_key(self):
        return environ.get('BIT_BAR_API_KEY')

    def get_performance_diff(self, previous_build=None):
        mpl.use('Agg')
        bit_bar = BitBar(self.bit_bar_api_key)
        data = dict()
        for name in test_data.apk_name, previous_build:
            data[name] = dict()
            data[name]['seconds'] = list()
            data[name]['CPU'] = list()
            data[name]['RAM'] = list()
            build_data = bit_bar.get_performance_by(name, test_data.test_name)
            for second, nothing in enumerate(build_data):
                data[name]['seconds'].append(second)
                data[name]['CPU'].append(nothing['cpuUsage'] * 100)
                data[name]['RAM'].append(float(nothing['memUsage']) / 1000000)
        plt.style.use('dark_background')
        for i in 'CPU', 'RAM':
            fig, ax = plt.subplots(nrows=1, ncols=1)
            ax.plot(data[test_data.apk_name]['seconds'], data[test_data.apk_name][i], 'o-', color='#40e0d0',
                    label=test_data.apk_name)
            ax.plot(data[previous_build]['seconds'], data[previous_build][i], 'o-', color='#ffa500',
                    label=previous_build)
            plt.title('diff(%s): ' % i + test_data.test_name)
            plt.legend()
            fig.savefig('%s_' % i
                        + test_data.test_name + '.png')

    @property
    def capabilities_bitbar(self):
        capabilities = dict()
        capabilities['testdroid_apiKey'] = self.bit_bar_api_key
        capabilities['testdroid_target'] = 'android'
        capabilities['testdroid_device'] = 'LG Google Nexus 5X 6.0.1'
        capabilities['testdroid_app'] = pytest.config.getoption('apk')
        capabilities['testdroid_project'] = test_data.apk_name
        capabilities['testdroid_testrun'] = test_data.test_name
        capabilities['testdroid_findDevice'] = True
        capabilities['testdroid_testTimeout'] = 600

        capabilities['platformName'] = 'Android'
        capabilities['deviceName'] = 'Android Phone'
        capabilities['automationName'] = 'Appium'
        capabilities['newCommandTimeout'] = 600
        return capabilities

    @property
    def executor_bitbar(self):
        return 'http://appium.testdroid.com/wd/hub'

    def setup_method(self, method):
        self.driver = webdriver.Remote(self.executor_bitbar,
                                       self.capabilities_bitbar)
        self.driver.implicitly_wait(10)

    def teardown_method(self, method):
        try:
            self.driver.quit()
        except WebDriverException:
            pass
        finally:
            for i in range(10):
                try:
                    self.get_performance_diff(BitBar(self.bit_bar_api_key).get_previous_project_name())
                    return
                except BitBar.ResponseError:
                    time.sleep(30)


environments = {'bitbar': BitBarTestCase,
                'local': LocalMultipleDeviceTestCase,
                'sauce': SauceMultipleDeviceTestCase}


class MultipleDeviceTestCase(environments[pytest.config.getoption('env')]):

    pass
