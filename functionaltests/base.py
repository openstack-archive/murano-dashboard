import datetime
import os
import random
import sys

import ConfigParser
import json
import logging
import requests
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
import selenium.webdriver.common.by as by
from selenium.webdriver.support.ui import WebDriverWait
import testtools
import time

import config.config as cfg
from glanceclient import client as gclient
from keystoneclient.v2_0 import client as ksclient
from muranoclient import client as mclient

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


class ImageException(Exception):
    message = "Image doesn't exist"

    def __init__(self, im_type):
        self._error_string = (self.message + '\nDetails: {0} image is '
                                             'not found,'.format(im_type))

    def __str__(self):
        return self._error_string


class UITestCase(BaseDeps):

    @classmethod
    def setUpClass(cls):
        super(UITestCase, cls).setUpClass()
        keystone_client = ksclient.Client(username=cfg.common.user,
                                          password=cfg.common.password,
                                          tenant_name=cfg.common.tenant,
                                          auth_url=cfg.common.keystone_url)

        cls.murano_client = mclient.Client('1', endpoint=cfg.common.murano_url,
                                           token=keystone_client.auth_token)
        glance_endpoint = keystone_client.service_catalog.url_for(
            service_type='image', endpoint_type='publicURL')
        glance = gclient.Client('1', endpoint=glance_endpoint,
                                token=keystone_client.auth_token)
        cls.headers = {'X-Auth-Token': keystone_client.auth_token}

        image_list = []
        for i in glance.images.list():
            image_list.append(i)

        cls.demo_image = cls.get_image_name('demo', image_list)
        cls.linux_image = cls.get_image_name('linux', image_list)
        cls.windows_image = cls.get_image_name('windows', image_list)
        cls.keypair = cfg.common.keypair_name
        cls.tomcat_repository = cfg.common.tomcat_repository

        cls.elements = ConfigParser.RawConfigParser()
        cls.elements.read('common.ini')
        cls.logger = logging.getLogger(__name__)

        cls.url_prefix = cfg.common.horizon_url.split('/')[-1]
        cls.location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

        def upload_package(package_name, body, app):
            files = {'%s' % package_name: open(
                os.path.join(cls.location, app), 'rb')}

            post_body = {'JsonString': json.dumps(body)}
            request_url = '{endpoint}{url}'.format(
                endpoint=cfg.common.murano_url,
                url='/v1/catalog/packages')

            return requests.post(request_url,
                                 files=files,
                                 data=post_body,
                                 headers=cls.headers).json()['id']

        cls.postgre_id = upload_package(
            'PostgreSQL',
            {"categories": ["Databases"], "tags": ["tag"]},
            'murano-app-incubator/io.murano.apps.PostgreSql.zip')
        cls.apache_id = upload_package(
            'Apache',
            {"categories": ["Application Servers"], "tags": ["tag"]},
            'murano-app-incubator/io.murano.apps.apache.Apache.zip')
        cls.tomcat_id = upload_package(
            'Tomcat',
            {"categories": ["Application Servers"], "tags": ["tag"]},
            'murano-app-incubator/io.murano.apps.apache.Tomcat.zip')
        cls.telnet_id = upload_package(
            'Telnet',
            {"categories": ["Web"], "tags": ["tag"]},
            'murano-app-incubator/io.murano.apps.linux.Telnet.zip')
        cls.ad_id = upload_package(
            'Active Directory',
            {"categories": ["Microsoft Services"], "tags": ["tag"]},
            'murano-app-incubator/io.murano.windows.ActiveDirectory.zip')

    def setUp(self):
        super(UITestCase, self).setUp()

        self.driver = webdriver.Firefox()

        self.driver.get(cfg.common.horizon_url + '/')
        self.driver.implicitly_wait(30)
        self.log_in()

    def tearDown(self):
        super(UITestCase, self).tearDown()
        self.addOnException(self.take_screenshot(self._testMethodName))
        self.driver.quit()

        for env in self.murano_client.environments.list():
            self.murano_client.environments.delete(env.id)

    @classmethod
    def tearDownClass(cls):
        super(UITestCase, cls).tearDownClass()

        def delete_package(package_id):
            request_url = '{endpoint}{url}'.format(
                endpoint=cfg.common.murano_url,
                url='/v1/catalog/packages/{0}'.format(package_id))
            requests.delete(request_url, headers=cls.headers)

        delete_package(cls.postgre_id)
        delete_package(cls.apache_id)
        delete_package(cls.tomcat_id)
        delete_package(cls.telnet_id)
        delete_package(cls.ad_id)

    def take_screenshot(self, test_name):
        screenshot_dir = './screenshots'
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        date = datetime.datetime.now().strftime('%H%M%S')
        filename = '{0}/{1}-{2}.png'.format(screenshot_dir, test_name, date)
        self.driver.get_screenshot_as_file(filename)
        log.debug("\nScreenshot {0} was saved".format(filename))

    @classmethod
    def get_image_name(cls, type_of_image, list_of_images):
        for i in list_of_images:
            if 'murano_image_info' in i.properties.keys():
                if type_of_image in json.loads(
                        i.properties['murano_image_info'])['type']:
                    return json.loads(i.properties[
                        'murano_image_info'])['title']
        raise ImageException(type_of_image)

    def log_in(self):
        self.fill_field(by.By.ID, 'id_username', cfg.common.user)
        self.fill_field(by.By.ID, 'id_password', cfg.common.password)
        sign_in = self.elements.get('button', 'ButtonSubmit')
        self.driver.find_element_by_xpath(sign_in).click()
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'Murano')).click()

    def fill_field(self, by_find, field, value):
        self.driver.find_element(by=by_find, value=field).clear()
        self.driver.find_element(by=by_find, value=field).send_keys(value)

    def confirm_deletion(self):
        confirm_deletion = self.elements.get('button', 'ConfirmDeletion')
        self.driver.find_element_by_xpath(confirm_deletion).click()

    def create_environment(self, env_name):
        self.driver.find_element_by_id(
            'murano__action_CreateEnvironment').click()
        self.fill_field(by.By.ID, 'id_name', env_name)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

    def delete_environment(self, env_name):
        self.driver.find_element_by_link_text('Environments').click()
        self.click_on_more(env_name)
        self.select_action_for_environment(env_name, 'delete')
        self.confirm_deletion()

    def edit_environment(self, old_name, new_name):
        self.click_on_more(old_name)
        self.select_action_for_environment(old_name, 'edit')
        self.fill_field(by.By.ID, 'id_name', new_name)
        save = self.elements.get('button', 'InputSubmit')
        self.driver.find_element_by_xpath(save).click()

    def click_on_more(self, env_name):
        element_id = self.get_element_id(env_name)
        self.driver.find_element_by_xpath(
            ".//*[@id='murano__row__{0}']/td[4]/div/a[2]".
            format(element_id)).click()

    def select_action_for_environment(self, env_name, action):
        element_id = self.get_element_id(env_name)
        self.driver.find_element_by_id(
            "murano__row_{0}__action_{1}".format(element_id, action)).click()

    def go_to_submenu(self, link):
        self.driver.find_element_by_link_text('{0}'.format(link)).click()

    def navigate_to(self, menu):
        self.driver.find_element_by_xpath(
            self.elements.get('button', '{0}'.format(menu))).click()

    def select_from_list(self, list_name, value):
        self.driver.find_element_by_xpath(
            "//select[@name='{0}']/option[text()='{1}']".
            format(list_name, value)).click()

    def check_element_on_page(self, method, value):
        try:
            self.driver.find_element(method, value)
        except NoSuchElementException:
            return False
        return True

    def env_to_components_list(self, env_name):
        element_id = self.get_element_id(env_name)
        self.driver.find_element_by_id(
            "murano__row_{0}__action_show".format(element_id)).click()

    def create_linux_telnet(self, app_name, app_id):
        self.select_and_click_action_for_app('quick-add', app_id)

        self.fill_field(by.By.ID, 'id_0-name', app_name)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        self.select_from_list('1-osImage', self.linux_image)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

    def create_linux_apache(self, app_name, app_id):
        self.select_and_click_action_for_app('quick-add', app_id)

        self.fill_field(by.By.ID, 'id_0-name', app_name)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()
        self.select_from_list('1-osImage', self.linux_image)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

    def create_ad_service(self, app_name):
        self.fill_field(by.By.ID, 'id_0-name', app_name)
        self.fill_field(by.By.ID, 'id_0-adminPassword', 'P@ssw0rd')
        self.fill_field(by.By.ID, 'id_0-adminPassword-clone', 'P@ssw0rd')
        self.fill_field(by.By.ID, 'id_0-recoveryPassword', 'P@ssw0rd')
        self.fill_field(by.By.ID, 'id_0-recoveryPassword-clone', 'P@ssw0rd')
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        self.select_from_list('1-osImage', self.windows_image)
        next_button = self.elements.get('button', 'InputSubmit')
        self.driver.find_element_by_xpath(next_button).click()

    def create_tomcat_service(self, app_name, database):
        self.fill_field(by.By.ID, 'id_0-name', app_name)
        self.select_from_list('0-database', database)
        self.fill_field(by.By.ID, 'id_0-repository', self.tomcat_repository)

        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        self.select_from_list('1-osImage', self.linux_image)

        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

    def create_postgreSQL_service(self, app_name):
        self.fill_field(by.By.ID, 'id_0-name', app_name)
        self.fill_field(by.By.ID, 'id_0-database', 'psql-base')
        self.fill_field(by.By.ID, 'id_0-username', 'admin')
        self.fill_field(by.By.ID, 'id_0-password', 'P@ssw0rd')
        self.fill_field(by.By.ID, 'id_0-password-clone', 'P@ssw0rd')

        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        self.select_from_list('1-osImage', self.linux_image)

        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()

    def get_element_id(self, el_name):
        path = self.driver.find_element_by_xpath(
            ".//*[@data-display='{0}']".format(el_name)).get_attribute("id")
        return path.split('__')[-1]

    def delete_component(self, component_name):
        component_id = self.get_element_id(component_name)
        self.driver.find_element_by_id(
            'services__row_{0}__action_delete'.format(component_id)).click()
        self.driver.find_element_by_link_text('Delete Component').click()

    def get_env_subnet(self):
        help_text = self.driver.find_element_by_xpath(
            "(.//span[@class = 'help-inline'])[1]").text
        subnet = help_text.split('.')[-2]
        num = random.randint(0, 255)
        return '10.0.{0}.{1}'.format(subnet, num)

    def check_that_error_message_is_correct(self, error_message, num):
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()
        time.sleep(3)
        appeared_text = self.driver.find_element_by_xpath(
            ".//div[@class = 'control-group form-field clearfix error'][%d]"
            % num).text
        index = appeared_text.find(error_message)

        if index != -1:
            return True
        else:
            return False

    def check_that_alert_message_is_appeared(self, error_message):
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'ButtonSubmit')).click()

        xpath = ".//*[@id='create_service_form']/div[2]/input[2]"
        WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
            by.By.XPATH, xpath).is_displayed())

        appeared_text = self.driver.find_element_by_xpath(
            "(.//div[@class = 'alert alert-message alert-error'])").text
        index = appeared_text.find(error_message)

        if index != -1:
            return True
        else:
            return False

    def click_on_package_action(self, action):
        self.driver.find_element_by_xpath(
            ".//*[@id='packages__action_{0}']".format(action)).click()

    def select_action_for_package(self, package, action):
        time.sleep(2)
        package_id = self.get_element_id(package)
        if action == 'more':
            self.driver.find_element_by_xpath(
                ".//*[@id='packages__row__{0}']/td[6]/div/a[2]".
                format(package_id)).click()
            WebDriverWait(self.driver, 10).until(lambda s: s.find_element(
                by.By.XPATH,
                ".//*[@id='packages__row_{0}__action_download_package']".
                format(package_id)).is_displayed())
        else:
            self.driver.find_element_by_xpath(
                ".//*[@id='packages__row_{0}__action_{1}']".
                format(package_id, action)).click()

    def check_package_parameter(self, package, column, value):
        package_id = self.get_element_id(package)

        result = self.driver.find_element_by_xpath(
            ".//*[@id='packages__row__{0}']/td[{1}]".
            format(package_id, column)).text
        if result == value:
            return True
        else:
            return False

    def select_and_click_element(self, element):
        self.driver.find_element_by_xpath(
            ".//*[@value = '{0}']".format(element)).click()

    def choose_and_upload_files(self, name):
        __location = os.path.realpath(os.path.join(os.getcwd(),
                                                   os.path.dirname(__file__)))
        self.driver.find_element_by_xpath(".//*[@id='id_file']").click()
        self.driver.find_element_by_id('id_file').send_keys(
            os.path.join(__location, name))

    def check_the_status_of_env(self, env_name, status):
        env_id = self.get_element_id(env_name)

        env_status = self.driver.find_element_by_xpath(
            ".//*[@id='murano__row__{0}']/td[3]".format(env_id))
        k = 0
        while env_status.text != status:
            time.sleep(15)
            k += 1
            self.driver.refresh()
            env_status = self.driver.find_element_by_xpath(
                ".//*[@id='murano__row__{0}']/td[3]".format(env_id))
            if k > 160:
                log.error('\nTimeout has expired')
                break

    def check_that_deploy_finished(self, env_name):
        self.navigate_to('Environments')
        self.click_on_more(env_name)
        self.select_action_for_environment(env_name, 'show_deployments')
        status = self.driver.find_element_by_xpath(
            "/html/body/div/div[2]/div[3]/form/table/tbody/tr/td[3]").text

        self.driver.find_element_by_link_text("Show Details").click()
        self.driver.find_element_by_link_text("Logs").click()
        self.take_screenshot(self._testMethodName)

        self.navigate_to('Environments')
        self.click_on_more(env_name)
        self.select_action_for_environment(env_name, 'show_deployments')

        self.assertEqual('Successful', status, 'Deploy finished with errors')

    def select_and_click_action_for_app(self, action, app):
        self.driver.find_element_by_xpath(
            "//*[@href='/{0}/murano/catalog/{1}/{2}']"
            .format(self.url_prefix, action, app)).click()

    def modify_package(self, param, value):
        self.fill_field(by.By.ID, 'id_{0}'.format(param), value)
        self.driver.find_element_by_xpath(
            self.elements.get('button', 'InputSubmit')).click()
        self.driver.refresh()
