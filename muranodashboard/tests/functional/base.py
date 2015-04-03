#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import logging
import os
import sys
import testtools
import time
import urlparse

from glanceclient import client as gclient
from keystoneclient.v2_0 import client as ksclient
from muranoclient import client as mclient
from selenium.common import exceptions as exc
from selenium import webdriver
import selenium.webdriver.common.by as by
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support import ui

import config.config as cfg
from muranodashboard.tests.functional import consts
from muranodashboard.tests.functional import utils

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

if sys.version_info >= (2, 7):
    class BaseDeps(testtools.TestCase):
        pass
else:
    # Define asserts for python26
    import unittest2

    class BaseDeps(testtools.TestCase,
                   unittest2.TestCase):
        pass


class UITestCase(BaseDeps):
    @classmethod
    def setUpClass(cls):
        cls.keystone_client = ksclient.Client(username=cfg.common.user,
                                              password=cfg.common.password,
                                              tenant_name=cfg.common.tenant,
                                              auth_url=cfg.common.keystone_url)
        cls.murano_client = mclient.Client(
            '1', endpoint=cfg.common.murano_url,
            token=cls.keystone_client.auth_token)
        cls.url_prefix = urlparse.urlparse(cfg.common.horizon_url).path or ''
        if cls.url_prefix.endswith('/'):
            cls.url_prefix = cls.url_prefix[:-1]

    def setUp(self):
        super(UITestCase, self).setUp()

        self.driver = webdriver.Firefox()
        self.driver.maximize_window()
        self.driver.get(cfg.common.horizon_url + '/')
        self.driver.implicitly_wait(30)
        self.addOnException(self.take_screenshot)
        self.log_in()

    def tearDown(self):
        super(UITestCase, self).tearDown()
        self.driver.quit()

        for env in self.murano_client.environments.list():
            self.remove_environment(env.id)

    def remove_environment(self, environment_id, timeout=180):
        self.murano_client.environments.delete(environment_id)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.murano_client.environments.get(environment_id)
                time.sleep(1)
            except Exception:
                # TODO(smurashov): bug/1378764 replace Exception to NotFound
                return
        raise Exception(
            'Environment {0} was not deleted in {1} seconds'.format(
                environment_id, timeout))

    def take_screenshot(self, exception):
        """Taking screenshot on error

        This decorators will take a screenshot of the browser
        when the test failed or when exception raised on the test.
        Screenshot will be saved as PNG inside screenshots folder.

        """
        name = self._testMethodName
        log.exception('{0} failed'.format(name))
        screenshot_dir = './screenshots'
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        filename = os.path.join(screenshot_dir, name + '.png')
        self.driver.get_screenshot_as_file(filename)

    def log_in(self):
        self.fill_field(by.By.ID, 'id_username', cfg.common.user)
        self.fill_field(by.By.ID, 'id_password', cfg.common.password)
        self.driver.find_element_by_xpath("//button[@type='submit']").click()
        self.driver.find_element_by_xpath(consts.Murano).click()

    def fill_field(self, by_find, field, value):
        self.driver.find_element(by=by_find, value=field).clear()
        self.driver.find_element(by=by_find, value=field).send_keys(value)

    def get_element_id(self, el_name):
        el = ui.WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (by.By.XPATH, consts.AppPackageDefinitions.format(el_name))))
        path = el.get_attribute("id")
        return path.split('__')[-1]

    def select_and_click_action_for_app(self, action, app):
        self.driver.find_element_by_xpath(
            "//*[@href='{0}/murano/catalog/{1}/{2}']".format(self.url_prefix,
                                                             action,
                                                             app)).click()

    def go_to_submenu(self, link):
        element = self.wait_element_is_clickable(by.By.PARTIAL_LINK_TEXT, link)
        element.click()
        self.wait_for_sidebar_is_loaded()

    def check_panel_is_present(self, panel_name):
        self.assertIn(panel_name,
                      self.driver.find_element_by_xpath(
                          ".//*[@class='page-header']").text)

    def navigate_to(self, menu):
        el = ui.WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (by.By.XPATH, getattr(consts, menu))))
        el.click()
        self.wait_for_sidebar_is_loaded()

    def select_from_list(self, list_name, value):
        locator = (by.By.XPATH,
                   "//select[contains(@name, '{0}')]"
                   "/option[@value='{1}']".format(list_name, value))
        el = ui.WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(locator))
        el.click()

    def check_element_on_page(self, method, value, sec=10):
        try:
            ui.WebDriverWait(self.driver, sec).until(
                EC.presence_of_element_located((method, value)))
        except exc.TimeoutException:
            self.fail("Element {0} is not preset on the page".format(value))

    def check_element_not_on_page(self, method, value):
        self.driver.implicitly_wait(3)
        present = True
        try:
            self.driver.find_element(method, value)
        except (exc.NoSuchElementException, exc.ElementNotVisibleException):
            present = False
        self.assertFalse(present, "Element {0} is preset on the page"
                                  " while it should't".format(value))
        self.driver.implicitly_wait(30)

    def create_environment(self, env_name):
        self.driver.find_element_by_id(consts.CreateEnvironment).click()
        self.fill_field(by.By.ID, 'id_name', env_name)
        self.driver.find_element_by_id(consts.ConfirmCreateEnvironment).click()
        self.wait_for_alert_message()

    def delete_environment(self, env_name):
        self.select_action_for_environment(env_name, 'delete')
        self.driver.find_element_by_xpath(consts.ConfirmDeletion).click()
        self.wait_for_alert_message()

    def edit_environment(self, old_name, new_name):
        self.select_action_for_environment(old_name, 'edit')
        self.fill_field(by.By.ID, 'id_name', new_name)
        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        self.wait_for_alert_message()

    def select_action_for_environment(self, env_name, action):
        element_id = self.get_element_id(env_name)
        more_button = consts.More.format('murano', element_id)
        self.driver.find_element_by_xpath(more_button).click()
        btn_id = "murano__row_{0}__action_{1}".format(element_id, action)
        self.driver.find_element_by_id(btn_id).click()

    def wait_for_alert_message(self):
        locator = (by.By.CSS_SELECTOR, 'div.alert-success')
        log.debug("Waiting for a success message")
        ui.WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located(locator))
        is_open = self.driver.find_elements(by.By.CSS_SELECTOR,
                                            'a.close')
        if is_open:
            log.debug("Hide success message")
            is_open[0].click()

    def wait_element_is_clickable(self, method, element):
        return ui.WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((method, element)))

    def wait_for_sidebar_is_loaded(self):
        ui.WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (by.By.CSS_SELECTOR, "div.sidebar dt.active")))
        time.sleep(0.5)


class PackageBase(UITestCase):
    @classmethod
    def setUpClass(cls):
        super(PackageBase, cls).setUpClass()
        cls.mockapp_id = utils.upload_app_package(
            cls.murano_client,
            "MockApp",
            {"categories": ["Web"], "tags": ["tag"]})
        cls.postgre_id = utils.upload_app_package(
            cls.murano_client,
            "PostgreSQL",
            {"categories": ["Databases"], "tags": ["tag"]})

    @classmethod
    def tearDownClass(cls):
        super(PackageBase, cls).tearDownClass()
        cls.murano_client.packages.delete(cls.mockapp_id)
        cls.murano_client.packages.delete(cls.postgre_id)


class ImageTestCase(PackageBase):
    @classmethod
    def setUpClass(cls):
        super(ImageTestCase, cls).setUpClass()
        glance_endpoint = cls.keystone_client.service_catalog.url_for(
            service_type='image', endpoint_type='publicURL')
        cls.glance = gclient.Client('1', endpoint=glance_endpoint,
                                    token=cls.keystone_client.auth_token)
        cls.image_title = 'New Image ' + str(time.time())
        cls.image = cls.upload_image(cls.image_title)

    @classmethod
    def tearDownClass(cls):
        super(ImageTestCase, cls).tearDownClass()
        cls.glance.images.delete(cls.image.id)

    @classmethod
    def upload_image(cls, title):
        try:
            property = {'murano_image_info': json.dumps({'title': title,
                                                         'type': 'linux'})}

            image = cls.glance.images.create(name='TestImage',
                                             disk_format='qcow2',
                                             size=0,
                                             is_public=True,
                                             properties=property)
        except Exception as e:
            log.exception("Unable to create or update image in Glance")
            raise e
        return image

    def select_and_click_element(self, element):
        self.driver.find_element_by_xpath(
            ".//*[@value = '{0}']".format(element)).click()

    def repair_image(self):
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()
        self.select_from_list('image', self.image.id)
        self.fill_field(by.By.ID, 'id_title', self.image_title)
        self.select_from_list('type', 'linux')
        self.select_and_click_element('Mark')
        self.check_element_on_page(by.By.XPATH,
                                   consts.TestImage.format(self.image_title))


class FieldsTestCase(PackageBase):
    def check_error_message_is_present(self, error_message):
        self.driver.find_element_by_xpath(consts.ButtonSubmit).click()
        self.driver.find_element_by_xpath(
            consts.ErrorMessage.format(error_message))

    def check_error_message_is_absent(self, error_message):
        self.driver.find_element_by_xpath(consts.ButtonSubmit).click()

        self.driver.implicitly_wait(2)
        try:
            self.driver.find_element_by_xpath(
                consts.ErrorMessage.format(error_message))
        except (exc.NoSuchElementException, exc.ElementNotVisibleException):
            log.info("Message {0} is not"
                     " present on the page".format(error_message))

        self.driver.implicitly_wait(30)


class ApplicationTestCase(ImageTestCase):
    def delete_component(self, component_name):
        component_id = self.get_element_id(component_name)
        self.driver.find_element_by_id(
            'services__row_{0}__action_delete'.format(component_id)).click()
        el = self.wait_element_is_clickable(by.By.LINK_TEXT,
                                            'Delete Component')
        el.click()
        self.wait_for_alert_message()

    def select_action_for_package(self, package, action):
        package_id = self.get_element_id(package)
        if action == 'more':
            el = self.wait_element_is_clickable(
                by.By.XPATH, "//tr[@data-object-id='{0}']"
                             "//a[@data-toggle='dropdown']".format(package_id))
            el.click()
            ui.WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
                by.By.XPATH,
                ".//*[@id='packages__row_{0}__action_download_package']".
                format(package_id)).is_displayed())
        else:
            self.driver.find_element_by_xpath(
                ".//*[@id='packages__row_{0}__action_{1}']".
                format(package_id, action)).click()

    def check_package_parameter(self, package, column, value):
        columns = {'Active': 3, 'Public': 4}

        package_id = self.get_element_id(package)
        column_num = str(columns[column])

        column_element = self.driver.find_element_by_xpath(
            "//tr[@data-object-id='{0}']/td[{1}]".format(package_id,
                                                         column_num))
        self.assertTrue(column_element.text == value,
                        "'{0}' column doesn't contain '{1}'".format(column,
                                                                    value))

    def modify_package(self, param, value):
        self.fill_field(by.By.ID, 'id_{0}'.format(param), value)
        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        self.wait_for_alert_message()

    def add_app_to_env(self, app_id, app_name='TestApp'):
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('quick-add', app_id)
        field_id = "{0}_0-name".format(app_id)
        self.fill_field(by.By.ID, field_id, value=app_name)
        self.driver.find_element_by_xpath(consts.ButtonSubmit).click()
        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        self.select_from_list('osImage', self.image.id)

        self.driver.find_element_by_xpath(consts.InputSubmit).click()
        self.wait_for_alert_message()


class PackageTestCase(ApplicationTestCase):
    @classmethod
    def setUpClass(cls):
        super(ApplicationTestCase, cls).setUpClass()
        cls.archive_name = "ToUpload"
        cls.alt_archive_name = "ModifiedAfterUpload"
        cls.archive = utils.compose_package(cls.archive_name,
                                            consts.Manifest,
                                            consts.PackageDir)

    def tearDown(self):
        super(PackageTestCase, self).tearDown()

        for package in self.murano_client.packages.list(include_disabled=True):
            if package.name in [self.archive_name, self.alt_archive_name]:
                self.murano_client.packages.delete(package.id)

    @classmethod
    def tearDownClass(cls):
        super(ApplicationTestCase, cls).tearDownClass()
        if os.path.exists(consts.Manifest):
            os.remove(consts.Manifest)
        if os.path.exists(cls.archive):
            os.remove(cls.archive)
