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

import multiprocessing
import os
import shutil
import SimpleHTTPServer
import SocketServer
import tempfile
import time
import uuid
import zipfile

from selenium.webdriver.common import by
from selenium.webdriver.support import ui

from muranodashboard.tests.functional import base
from muranodashboard.tests.functional.config import config as cfg
from muranodashboard.tests.functional import consts as c
from muranodashboard.tests.functional import utils


class TestSuiteSmoke(base.UITestCase):
    """This class keeps smoke tests which check operability of main panels"""
    def test_smoke_environments_panel(self):
        self.go_to_submenu('Environments')
        self.check_panel_is_present('Environments')

    def test_smoke_applications_panel(self):
        self.go_to_submenu('Browse')
        self.check_panel_is_present('Applications')

    def test_smoke_images_panel(self):
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.check_panel_is_present('Marked Images')

    def test_smoke_package_definitions_panel(self):
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.check_panel_is_present('Packages')


class TestSuiteEnvironment(base.ApplicationTestCase):
    def test_create_delete_environment(self):
        """Test check ability to create and delete environment

        Scenario:
            1. Create environment
            2. Navigate to this environment
            3. Go back to environment list and delete created environment
        """
        self.go_to_submenu('Environments')
        self.create_environment('test_create_del_env')
        self.go_to_submenu('Environments')
        self.delete_environment('test_create_del_env')
        self.check_element_not_on_page(by.By.LINK_TEXT, 'test_create_del_env')

    def test_edit_environment(self):
        """Test check ability to change environment name

        Scenario:
            1. Create environment
            2. Change environment's name
            3. Check that renamed environment is in environment list
        """
        self.go_to_submenu('Environments')
        self.create_environment('test_edit_env')
        self.go_to_submenu('Environments')

        self.edit_environment(old_name='test_edit_env', new_name='edited_env')

        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, 'edited_env')
        self.check_element_not_on_page(by.By.LINK_TEXT, 'test_edit_env')

    def test_create_env_from_the_catalog_page(self):
        """Test create environment from the catalog page

        Scenario:
           1. Go to the Browse page
           2. Press 'Create Env'
           3. Make sure that it's possible to choose just created environment
        """
        self.go_to_submenu('Browse')
        self.driver.find_elements_by_xpath(
            "//a[contains(text(), 'Create Env')]")[0].click()
        self.fill_field(by.By.ID, 'id_name', 'TestEnv')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH,
            "//div[@id='environment_switcher']/a[contains(text(), 'TestEnv')]")

    def test_create_and_delete_environment_with_unicode_name(self):
        """Test check ability to create and delete environment with unicode name

        Scenario:
            1. Create environment with unicode name
            2. Navigate to this environment
            3. Go back to environment list and delete created environment
        """
        unicode_name = u'$yaql \u2665 unicode'
        self.go_to_submenu('Environments')
        self.create_environment(unicode_name)
        self.go_to_submenu('Environments')
        self.delete_environment(unicode_name)
        self.check_element_not_on_page(by.By.LINK_TEXT, unicode_name)

    def test_check_env_name_validation(self):
        """Test checks validation of field that usually defines environment name

        Scenario:
            1. Navigate to Catalog > Environments
            2. Press 'Create environment'
            3. Check a set of names, if current name isn't valid
            appropriate error message should appear
        """
        self.go_to_submenu('Environments')
        self.driver.find_element_by_css_selector(c.CreateEnvironment).click()

        self.driver.find_element_by_id(c.ConfirmCreateEnvironment).click()
        error_message = 'This field is required.'
        self.driver.find_element_by_xpath(
            c.ErrorMessage.format(error_message))

        self.fill_field(by.By.ID, 'id_name', '  ')
        self.driver.find_element_by_id(c.ConfirmCreateEnvironment).click()
        error_message = ('Environment name must contain at least one '
                         'non-white space symbol.')
        self.driver.find_element_by_xpath(
            c.ErrorMessage.format(error_message))

    def test_environment_detail_page_with_button(self):
        """Test check availability of delete button in environment detail

        Scenario:
            1. Create environment
            2. Go to the environment detail page
            3. Check that 'Delete Environment' button is in environment detail
        """
        # uuid.uuid4() generates random uuid
        env_name = str(uuid.uuid4())
        self.go_to_submenu('Environments')
        self.create_environment(env_name)

        delete_environment_btn = c.DeleteEnvironment
        self.check_element_on_page(by.By.XPATH, delete_environment_btn)


class TestSuiteImage(base.ImageTestCase):
    def test_mark_image(self):
        """Test check ability to mark murano image

        Scenario:
            1. Navigate to Images page
            2. Click on button "Mark Image"
            3. Fill the form and submit it
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_id(
            'marked_images__action_mark_image').click()

        self.select_from_list('image', self.image.id)
        new_title = 'RenamedImage ' + str(time.time())
        self.fill_field(by.By.ID, 'id_title', new_title)
        self.select_from_list('type', 'linux')
        self.select_and_click_element('Mark Image')
        self.check_element_on_page(by.By.XPATH, c.TestImage.format(new_title))

        self.repair_image()

    def test_check_image_info(self):
        """Test check ability to view image details

        Scenario:
            1. Navigate to Images page
            2. Click on the name of selected image, check image info
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_xpath(
            c.TestImage.format(self.image_title) + '//a').click()
        self.assertIn(self.image_title,
                      self.driver.find_element(by.By.XPATH, c.ImageMeta).text)

    def test_delete_image(self):
        """Test check ability to delete image

        Scenario:
            1. Navigate to Images page
            2. Select created image and click on "Delete Metadata"
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.driver.find_element_by_xpath(
            c.DeleteImageMeta.format(self.image_title)).click()
        self.driver.find_element_by_xpath(c.ConfirmDeletion).click()
        self.check_element_not_on_page(by.By,
                                       c.TestImage.format(self.image_title))

        self.repair_image()


class TestSuiteFields(base.FieldsTestCase):
    def test_check_domain_name_field_validation(self):
        """Check domain name validation

        Test checks that validation of domain name field works
        and appropriate error message appears after entering
        incorrect domain name

        Scenario:
            1. Navigate to Environments page
            2. Create environment and start to create MockApp service
            3. Set "a" as a domain name and verify error message
            4. Set "aa" as a domain name and check that error message
            didn't appear
            5. Set "@ct!v3" as a domain name and verify error message
            6. Set "active.com" as a domain name and check that error message
            didn't appear
            7. Set "domain" as a domain name and verify error message
            8. Set "domain.com" as a domain name and check that error message
            didn't appear
            9. Set "morethan15symbols.beforedot" as a domain name and
            verify error message
            10. Set "lessthan15.beforedot" as a domain name and check that
            error message didn't appear
            11. Set ".domain.local" as a domain name and
            verify error message
            12. Set "domain.local" as a domain name and check that
            error message didn't appear
        """
        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)
        field_id = self.mockapp_id + "_0-domain"

        self.fill_field(by.By.ID, field_id, value='a')
        self.check_error_message_is_present(
            'Ensure this value has at least 2 characters (it has 1).')
        self.fill_field(by.By.ID, field_id, value='aa')
        self.check_error_message_is_absent(
            'Ensure this value has at least 2 characters (it has 1).')

        self.fill_field(by.By.ID, field_id, value='@ct!v3')
        self.check_error_message_is_present(
            'Only letters, numbers and dashes in the middle are allowed.')

        self.fill_field(by.By.ID, field_id, value='active.com')
        self.check_error_message_is_absent(
            'Only letters, numbers and dashes in the middle are allowed.')

        self.fill_field(by.By.ID, field_id, value='domain')
        self.check_error_message_is_present(
            'Single-level domain is not appropriate.')

        self.fill_field(by.By.ID, field_id, value='domain.com')
        self.check_error_message_is_absent(
            'Single-level domain is not appropriate.')

        self.fill_field(by.By.ID, field_id,
                        value='morethan15symbols.beforedot')
        self.check_error_message_is_present(
            'NetBIOS name cannot be shorter than'
            ' 1 symbol and longer than 15 symbols.')
        self.fill_field(by.By.ID, field_id, value='lessthan15.beforedot')
        self.check_error_message_is_absent(
            'NetBIOS name cannot be shorter than'
            ' 1 symbol and longer than 15 symbols.')

        self.fill_field(by.By.ID, field_id, value='.domain.local')
        self.check_error_message_is_present(
            'Period characters are allowed only when '
            'they are used to delimit the components of domain style names')

        self.fill_field(by.By.ID, field_id, value='domain.local')
        self.check_error_message_is_absent(
            'Period characters are allowed only when '
            'they are used to delimit the components of domain style names')

    def test_check_app_name_validation(self):
        """Test checks validation of field that usually defines application name

        Scenario:
            1. Navigate to Catalog > Browse
            2. Start to create Mock App
            3. Check a set of names, if current name isn't valid
            appropriate error message should appears
        """
        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, '0-name', value='a')
        self.check_error_message_is_present(
            'Ensure this value has at least 2 characters (it has 1).')

        self.fill_field(by.By.NAME, '0-name', value='@pp')
        self.check_error_message_is_present(
            'Just letters, numbers, underscores and hyphens are allowed.')

        self.fill_field(by.By.NAME, '0-name', value='AppL1')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.wait_element_is_clickable(by.By.XPATH, c.ButtonSubmit)

    def test_check_required_field(self):
        """Test required fields

        Test checks that fields with parameter 'required=True' in yaml form
        are truly required and can't be omitted

        Scenario:
            1. Navigate to Catalog > Browse
            2. Start to create MockApp
            3. Don't type app name in the 'Application Name'
            field that is required and click 'Next', check that there is
            error message
            4. Set app name and click 'Next',
            check that there is no error message
        """
        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.check_error_message_is_present('This field is required.')

        self.fill_field(by.By.NAME, "0-name", "name")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.wait_element_is_clickable(by.By.XPATH, c.ButtonSubmit)

    def test_password_validation(self):
        """Test checks password validation

        Scenario:
            1. Navigate to Catalog > Browse
            2. Start to create MockApp
            3. Set weak password consisting of numbers,
            check that error message appears
            4. Set different passwords to Password field and Confirm password
            field, check that validation failed
            5. Set correct password. Validation has to pass
        """
        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "name")
        self.fill_field(by.By.NAME, '0-adminPassword-password', value='123456')
        self.check_error_message_is_present(
            'The password must contain at least one letter')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.fill_field(by.By.NAME, "0-adminPassword-password-clone",
                        value='P@ssw0rd')
        self.check_error_message_is_absent('Passwords do not match')
        self.fill_field(by.By.NAME, '0-adminPassword-password',
                        value='P@ssw0rd')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.wait_element_is_clickable(by.By.XPATH, c.ButtonSubmit)


class TestSuiteApplications(base.ApplicationTestCase):
    def test_check_transitions_from_one_wizard_to_another(self):
        """Test checks that transitions "Next" and "Back" are not broken

        Scenario:
            1. Navigate to Catalog > Browse
            2. Start to create MockApp
            3. Set app name and click on "Next", check that second wizard step
            will appear
            4. Click 'Back' and check that first wizard step is shown
        """
        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "name")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.driver.find_element_by_id(
            'wizard_{0}_btn'.format(self.mockapp_id)).click()

        self.check_element_on_page(by.By.NAME, "0-name")

    def test_check_ability_create_two_dependent_apps(self):
        """Test using two dependent apps

        Test checks that with using one creation form it is possible to
        add two related apps in one environment

        Scenario:
            1. Navigate to Catalog > Browse
            2. Start to create MockApp
            3. Set app name and click on "Next"
            4. Click '+' and verify that creation of second app is possible
        """

        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "app1")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.driver.find_element_by_css_selector(
            'form i.fa-plus-circle').click()
        self.fill_field(by.By.NAME, "0-name", "app2")

    def test_creation_deletion_app(self):
        """Test check ability to create and delete test app

        Scenario:
            1. Navigate to 'Catalog' > Browse
            2. Click on 'Quick Deploy' for MockApp application
            3. Create TestApp app by filling the creation form
            4. Delete TestApp app from environment
        """

        self.go_to_submenu('Browse')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, '0-name'.format(self.mockapp_id), 'TestA')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.select_from_list('osImage', self.image.id)
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_element_is_clickable(by.By.ID, c.AddComponent)
        self.check_element_on_page(by.By.LINK_TEXT, 'TestA')
        self.delete_component('TestA')
        self.check_element_not_on_page(by.By.LINK_TEXT, 'TestA')

    def test_check_search_option(self):
        """Test checks that 'Search' option is operable.

        Scenario:
            1. Navigate to 'Catalog > Browse' panel
            2. Set search criterion in the search field(e.g 'PostgreSQL')
            3. Click on 'Filter' and check result
        """
        self.go_to_submenu('Browse')
        self.fill_field(by.By.CSS_SELECTOR, 'input.form-control', 'PostgreSQL')
        self.driver.find_element_by_id('apps__action_filter').click()

        self.check_element_on_page(by.By.XPATH,
                                   c.App.format('PostgreSQL'))
        self.check_element_not_on_page(by.By.XPATH,
                                       c.App.format('MockApp'))

    def test_filter_by_category(self):
        """Test filtering by category

        Test checks ability to filter applications by category
        in Catalog page

        Scenario:
            1. Navigate to 'Catalog'>'Browse' panel
            2. Select 'Databases' category in 'App Category' dropdown menu
            3. Verify that PostgreSQL is shown
            4. Select 'Web' category in 'App Category' dropdown menu
            5. Verify that MockApp is shown
        """
        self.go_to_submenu('Browse')
        self.driver.find_element_by_xpath(
            c.CategorySelector.format('All')).click()
        self.driver.find_element_by_partial_link_text('Databases').click()

        self.check_element_on_page(by.By.XPATH, c.App.format('PostgreSQL'))

        self.driver.find_element_by_xpath(
            c.CategorySelector.format('Databases')).click()
        self.driver.find_element_by_partial_link_text('Web').click()

        self.check_element_on_page(by.By.XPATH, c.App.format('MockApp'))

    def test_check_option_switch_env(self):
        """Test checks ability to switch environment and add app in other env

        Scenario:
            1. Navigate to 'Catalog>Environments' panel
            2. Create environment 'env1'
            3. Create environment 'env2'
            4. Navigate to 'Catalog>Browse'
            5. Click on 'Environment' panel
            6. Switch to env2
            7. Add application in env2
            8. Navigate to 'Catalog>Environments'
            and go to the env2
            9. Check that added application is here
        """
        self.go_to_submenu('Environments')
        self.create_environment('env1')
        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, 'env1')
        self.create_environment('env2', by_id=True)
        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, 'env2')

        env_id = self.get_element_id('env2')

        self.go_to_submenu('Browse')
        self.driver.find_element_by_xpath(
            ".//*[@id='environment_switcher']/a").click()

        self.driver.find_element_by_link_text("env2").click()

        self.select_and_click_action_for_app(
            'add', '{0}/{1}'.format(self.mockapp_id, env_id))

        self.fill_field(by.By.NAME, '0-name', 'TestA')
        self.driver.find_element_by_xpath(
            c.ButtonSubmit).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.select_from_list('osImage', self.image.id)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.check_element_on_page(by.By.LINK_TEXT, 'TestA')

    def test_check_progress_bar(self):
        """Test that progress bar appears only for 'Deploying' status

        Scenario:
            1. Navigate to Catalog>Browse and click MockApp 'Quick Deploy'
            2. Check that for "Ready to deploy" state progress bar is not seen
            3. Click deploy
            4. Check that for "Deploying" status progress bar is seen
        """
        self.go_to_submenu('Browse')
        self.select_and_click_action_for_app('quick-add', self.mockapp_id)
        field_id = "{0}_0-name".format(self.mockapp_id)
        self.fill_field(by.By.ID, field_id, value='TestApp')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.select_from_list('osImage', self.image.id)

        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.check_element_on_page(by.By.XPATH,
                                   c.Status.format('Ready to deploy'))
        self.check_element_on_page(by.By.XPATH, c.CellStatus.format('up'))

        self.driver.find_element_by_id('services__action_deploy_env').click()
        self.check_element_on_page(by.By.XPATH,
                                   c.Status.format('Deploying'))
        self.check_element_on_page(by.By.XPATH, c.CellStatus.format('unknown'))
        self.check_element_on_page(by.By.XPATH,
                                   c.Status.format('Ready'),
                                   sec=90)
        self.check_element_on_page(by.By.XPATH, c.CellStatus.format('up'))

    def test_check_overview_tab(self):
        """Test check that created application overview tab browsed correctly

        Scenario:
            1. Navigate to Catalog>Browse and click MockApp 'Quick Deploy'
            2. Click on application name to go to the detail page
        """
        app_name = 'NewTestApp'
        self.add_app_to_env(self.mockapp_id, app_name)
        self.driver.find_element_by_link_text(app_name).click()
        self.check_element_on_page(
            by.By.XPATH, "//dd[contains(text(), {0})]".format(app_name))

    def test_ensure_actions(self):
        """Checks that action is available for deployed application

        Scenario:
            1. Navigate to Catalog>Browse and click MockApp 'Quick Deploy'
            2. Click deploy
            3. Wait 'Ready' status
            4. Click on application
            5. Check that defined action name is in the list of app 'actions'

        """
        self.add_app_to_env(self.mockapp_id)
        self.driver.find_element_by_id('services__action_deploy_env').click()

        self.check_element_on_page(by.By.XPATH,
                                   c.Status.format('Ready'),
                                   sec=90)
        el = self.wait_element_is_clickable(by.By.XPATH,
                                            c.More.format('services', ''))
        el.click()
        self.driver.find_element_by_xpath(c.Action).click()
        self.driver.find_element_by_css_selector('.modal-close button').click()
        self.check_element_on_page(by.By.XPATH,
                                   "//*[contains(text(), 'Completed')]")

    def test_check_info_about_app(self):
        """Test checks that information about app is available

        Scenario:
            1. Navigate to 'Catalog>Browse' panel
            2. Choose some application and click on 'More info'
            3. Verify info about application
        """
        self.go_to_submenu('Browse')
        self.select_and_click_action_for_app('details', self.mockapp_id)

        self.assertEqual('MockApp for webUI tests',
                         self.driver.find_element_by_xpath(
                             "//div[@class='app-description']").text)
        self.driver.find_element_by_link_text('Requirements').click()
        self.driver.find_element_by_class_name('app_requirements')
        self.driver.find_element_by_link_text('License').click()
        self.driver.find_element_by_class_name('app_license')

    def test_check_topology_page(self):
        """Test checks that topology tab is available, displays correctly

        Scenario:
            1. Navigate to Catalog>Browse and click MockApp 'Quick Deploy'
            2. Click deploy
            3. Wait 'Ready' status
            4. Click on 'Topology' tab
            5. Check that status is 'Waiting for deployment' is displayed
            6. Check that app logo is present on page
        """
        self.add_app_to_env(self.mockapp_id)
        self.driver.find_element_by_link_text('Topology').click()

        self.assertEqual(
            'Status: Waiting for deployment',
            self.driver.find_element_by_css_selector('#stack_box > p').text)

        self.check_element_on_page(by.By.TAG_NAME, 'image')

    def test_check_deployment_history(self):
        """Test checks that deployment history tab is available, logs are ok

        Scenario:
            1. Navigate to Catalog>Browse and click MockApp 'Quick Deploy'
            2. Click deploy
            3. Wait 'Ready' status
            4. Click on 'Deployment History' tab
            5. Click 'Show Details' button
            6. Click 'Logs' button
            7. Check that app deployment message is present in logs
        """
        self.add_app_to_env(self.mockapp_id)
        self.driver.find_element_by_id('services__action_deploy_env').click()

        self.check_element_on_page(by.By.XPATH,
                                   c.Status.format('Ready'),
                                   sec=90)

        self.driver.find_element_by_link_text('Deployment History').click()
        self.driver.find_element_by_link_text('Show Details').click()
        self.driver.find_element_by_link_text('Logs').click()

        self.assertIn('Follow the white rabbit',
                      self.driver.find_element_by_class_name('logs').text)

    def test_hot_application(self):
        """Checks that UI got hot app is rendered correctly

        Scenario:
            1. Navigate to Catalog>Browse and click Hot app 'Quick Deploy'
            2. Check for YAQL validator
            3. Check that app is added to the environment
        """
        self.go_to_submenu('Browse')
        self.select_and_click_action_for_app('quick-add', self.hot_app_id)
        field_id = "{0}_0-name".format(self.hot_app_id)
        self.fill_field(by.By.ID, field_id, value='TestHotApp')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.fill_field(by.By.CSS_SELECTOR,
                        'input[id$="flavor"]',
                        value='testFlavor')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.check_element_on_page(by.By.XPATH, c.HotFlavorField)
        self.fill_field(by.By.CSS_SELECTOR,
                        'input[id$="flavor"]',
                        value='m1.small')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.check_element_on_page(by.By.LINK_TEXT, 'TestHotApp')

    def test_deploy_mockapp_remove_it_and_deploy_another_mockapp(self):
        """Checks that app is not available after remove and new app deployment

        Scenario:
            1. Navigate to Environments
            2. Create new environment
            3. Navigate to Catalog>Browse and click MockApp 'Add to Env'
            4. Fill the form use environment from step 2 and click submit
            5. Click deploy environment
            6. Wait 'Ready' status
            7. Click Delete Application in row actions.
            8. Navigate to Catalog>Browse and click MockApp 'Add to Env'
            9. Fill the form use environment from step 2 and new app name
               and click submit
            10. Click deploy environment
            11. Check that the first application created in step 5
                is not in the list
            12. Click Delete Application in row actions.
        """
        # uuid.uuid4() generates random uuid
        env_name = str(uuid.uuid4())
        # range specifies total amount of applications used in the test
        app_names = []
        for x in range(4):
            # In case of application some short name is needed to fit on page
            app_names.append(str(uuid.uuid4())[::4])

        self.go_to_submenu('Environments')
        self.create_environment(env_name)
        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, env_name)
        env_id = self.get_element_id(env_name)

        for idx, app_name in enumerate(app_names):
            # Add application to the environment
            self.go_to_submenu('Browse')
            self.select_and_click_action_for_app(
                'add', '{0}/{1}'.format(self.mockapp_id, env_id))
            self.fill_field(by.By.NAME,
                            '0-name'.format(self.mockapp_id), app_name)
            self.driver.find_element_by_xpath(c.ButtonSubmit).click()
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.select_from_list('osImage', self.image.id)
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.wait_element_is_clickable(by.By.ID, c.AddComponent)
            self.check_element_on_page(by.By.LINK_TEXT, app_name)

            # Deploy the environment with all current applications
            self.driver.find_element_by_id(c.DeployEnvironment).click()
            # Wait until the end of deploy
            self.check_element_on_page(by.By.XPATH,
                                       c.Status.format('Ready'),
                                       sec=90)
            # Starting form the second application will check
            # that previous application is not in the list on the page
            if idx:
                self.check_element_not_on_page(by.By.LINK_TEXT,
                                               app_names[idx - 1])
            self.delete_component(app_name)

        # To ensure that the very last application is deleted as well
        for app_name in app_names[-1::]:
            self.check_element_not_on_page(by.By.LINK_TEXT, app_name)

    def test_deploy_several_mock_apps_in_a_row(self):
        """Checks that app works after another app is deployed

        Scenario:
            1. Navigate to Environments
            2. Create new environment
            3. Navigate to Catalog>Browse and click MockApp 'Add to Env'
            4. Fill the form and use environment from step 2 and click submit
            5. Click deploy environment
            6. Wait 'Ready' status
            7. Click testAction in row actions.
            8. Wait 'Completed' status
            9. Repeat steps 3-6 to add one more application.
            10 Execute steps 7-8 for each application in the environment
        """
        # uuid.uuid4() generates random uuid
        env_name = str(uuid.uuid4())
        # range specifies total amount of applications used in the test
        app_names = []
        for x in range(4):
            # In case of application some short name is needed to fit on page
            app_names.append(str(uuid.uuid4())[::4])

        self.go_to_submenu('Environments')
        self.create_environment(env_name)
        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, env_name)
        env_id = self.get_element_id(env_name)

        for idx, app_name in enumerate(app_names, 1):
            # Add application to the environment
            self.go_to_submenu('Browse')
            self.select_and_click_action_for_app(
                'add', '{0}/{1}'.format(self.mockapp_id, env_id))
            self.fill_field(by.By.NAME,
                            '0-name'.format(self.mockapp_id), app_name)
            self.driver.find_element_by_xpath(c.ButtonSubmit).click()
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.select_from_list('osImage', self.image.id)
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.driver.find_element_by_xpath(c.InputSubmit).click()
            self.wait_element_is_clickable(by.By.ID, c.AddComponent)
            self.check_element_on_page(by.By.LINK_TEXT, app_name)

            # Deploy the environment with all current applications
            self.driver.find_element_by_id(c.DeployEnvironment).click()
            # Wait until the end of deploy
            self.wait_element_is_clickable(by.By.ID, c.AddComponent)

            # For each current application in the deployed environment
            for app_name in app_names[:idx]:
                # Check that application with exact name is in the list
                # and has status Ready
                row_id = self.get_element_id(app_name)
                row_xpath = c.Row.format(row_id)
                status_xpath = '{0}{1}'.format(row_xpath,
                                               c.Status.format('Ready'))
                self.check_element_on_page(by.By.XPATH, status_xpath, sec=90)

                # Click on the testAction button for the application
                buttons_xpath = c.More.format('services', row_id)
                el = self.wait_element_is_clickable(by.By.XPATH, buttons_xpath)
                el.click()
                action_xpath = '{0}{1}'.format(row_xpath, c.Action)
                menu_item = self.wait_element_is_clickable(by.By.XPATH,
                                                           action_xpath)
                menu_item.click()

                # And check that status of the application is 'Completed'
                status_xpath = '{0}{1}'.format(row_xpath,
                                               c.Status.format('Completed'))
                self.check_element_on_page(by.By.XPATH, status_xpath, sec=90)
        # Delete applications one by one
        for app_name in app_names:
            self.delete_component(app_name)
            self.check_element_not_on_page(by.By.LINK_TEXT, app_name)


class TestSuiteAppsPagination(base.UITestCase):
    def setUp(self):
        super(TestSuiteAppsPagination, self).setUp()
        self.apps = []
        # Create 30 additional packages with applications
        for i in range(100, 130):
            app_name = self.gen_random_resource_name('app', 4)
            tag = self.gen_random_resource_name('tag', 8)
            metadata = {"categories": ["Web"], "tags": [tag]}
            app_id = utils.upload_app_package(self.murano_client, app_name,
                                              metadata)
            self.apps.append(app_id)

    def tearDown(self):
        super(TestSuiteAppsPagination, self).tearDown()
        for app_id in self.apps:
            self.murano_client.packages.delete(app_id)

    def test_apps_pagination(self):
        """Test check pagination in case of many applications installed."""
        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        packages_list = [elem.name for elem in
                         self.murano_client.packages.list()]
        # No list of apps available in the client only packages are.
        # Need to remove 'Core library' from it since it is not visible in
        # application's list.
        packages_list.remove('Core library')

        apps_per_page = 6
        pages_itself = [packages_list[i:i + apps_per_page] for i in
                        range(0, len(packages_list), apps_per_page)]
        for i, names in enumerate(pages_itself, 1):
            for name in names:
                self.check_element_on_page(by.By.XPATH, c.App.format(name))
            if i != len(pages_itself):
                self.driver.find_element_by_link_text('Next Page').click()

        # Wait till the Next button disappear
        # Otherwise 'Prev' buttion from previous page might be used
        self.check_element_not_on_page(by.By.LINK_TEXT, 'Next Page')

        # Now go back to the first page
        pages_itself.reverse()
        for i, names in enumerate(pages_itself, 1):
            for name in names:
                self.check_element_on_page(by.By.XPATH, c.App.format(name))
            if i != len(pages_itself):
                self.driver.find_element_by_link_text('Previous Page').click()


class TestSuitePackages(base.PackageTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestSuitePackages, cls).setUpClass()
        suffix = str(uuid.uuid4())[:6]
        cls.testuser_name = 'test_{}'.format(suffix)
        cls.testuser_password = 'test'
        email = '{}@example.com'.format(cls.testuser_name)
        cls.create_user(name=cls.testuser_name,
                        password=cls.testuser_password,
                        email=email)

    @classmethod
    def tearDownClass(cls):
        cls.delete_user(cls.testuser_name)
        super(TestSuitePackages, cls).tearDownClass()

    def test_modify_package_name(self):
        """Test check ability to change name of the package

        Scenario:
            1. Navigate to 'Packages' page
            2. Select package and click on 'Modify Package'
            3. Rename package
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.select_action_for_package(self.postgre_id,
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL-modified')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()

        self.check_element_on_page(by.By.XPATH,
                                   c.AppPackages.format(
                                       'PostgreSQL-modified'))

        self.select_action_for_package(self.postgre_id,
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL')
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.check_element_on_page(by.By.XPATH,
                                   c.AppPackages.format(
                                       'PostgreSQL'))

    def test_modify_package_add_tag(self):
        """Test that new tag is shown in description

        Scenario:
            1. Navigate to 'Packages' page
            2. Click on "Modify Package" and add new tag
            3. Got to the Catalog page
            4. Check, that new tag is browsed in application description
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.select_action_for_package(self.postgre_id,
                                       'modify_package')

        self.fill_field(by.By.ID, 'id_tags', 'TEST_TAG')
        self.modify_package('tags', 'TEST_TAG')

        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        self.select_and_click_action_for_app('details', self.postgre_id)
        self.assertIn('TEST_TAG',
                      self.driver.find_element_by_xpath(
                          c.TagInDetails).text)

    def test_download_package(self):
        """Test check ability to download package from repository

        Scenario:
            1. Navigate to 'Packages' page
            2. Select PostgreSQL package and click on "More>Download Package"
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'more')
        self.select_action_for_package(self.postgre_id, 'download_package')

    def test_check_toggle_enabled_package(self):
        """Test check ability to make package active or inactive

        Scenario:
            1. Navigate to 'Packages' page
            2. Select some package and make it inactive "More>Toggle Active"
            3. Check that package is inactive
            4. Switch to 'Browse' page
            5. Check that application is not available on the page
            6. Navigate to 'Packages' page
            7. Select the same package and make it active "More>Toggle Active"
            8. Check that package is active
            9. Switch to 'Browse' page
            10. Check that application now is available on the page
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'more')
        self.select_action_for_package(self.postgre_id, 'toggle_enabled')

        self.wait_for_alert_message()
        self.check_package_parameter_by_id(self.postgre_id, 'Active', 'False')

        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        # 'Quick Deploy' button contains id of the application.
        # So it is possible to definitely determinate is it in catalog or not.
        btn_xpath = ("//*[@href='{0}/murano/catalog/quick-add/{1}']"
                     "".format(self.url_prefix, self.postgre_id))
        self.check_element_not_on_page(by.By.XPATH, btn_xpath)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'more')
        self.select_action_for_package(self.postgre_id, 'toggle_enabled')

        self.wait_for_alert_message()

        self.check_package_parameter_by_id(self.postgre_id, 'Active', 'True')

        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        self.check_element_on_page(by.By.XPATH, btn_xpath)

    def test_check_toggle_public_package(self):
        """Test check ability to make package active or inactive

        Scenario:
            1. Create new project but keep default project active
            2. Navigate to 'Packages' page
            3. Select some package and make it active "More>Toggle Public"
            4. Check that package is public
            5. Switch to the new project and check that the application is
               available in the catalog
            6. Switch back to default project
            7. Select the same package and inactivate it "More>Toggle Public"
            8. Check that package is unpublic
            9. Switch to the new project and check that the application
               is not available in the catalog
        """
        default_project = self.keystone_client.project_name
        new_project = str(uuid.uuid4())[::4]
        project_id = self.create_project(new_project)
        self.add_user_to_project(project_id, self.keystone_client.user_id)
        # Generally the new project will appear in the dropdown menu only after
        # page refresh. But in this case refresh is not necessary.

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'more')
        self.select_action_for_package(self.postgre_id,
                                       'toggle_public_enabled')

        self.wait_for_alert_message()
        self.check_package_parameter_by_id(self.postgre_id, 'Public', 'True')

        # Check that application is available in other project.
        self.switch_to_project(new_project)
        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        # 'Quick Deploy' button contains id of the application.
        # So it is possible to definitely determine is it in catalog or not.
        btn_xpath = ("//*[@href='{0}/murano/catalog/quick-add/{1}']"
                     "".format(self.url_prefix, self.postgre_id))

        self.check_element_on_page(by.By.XPATH, btn_xpath)

        self.switch_to_project(default_project)
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'more')
        self.select_action_for_package(self.postgre_id,
                                       'toggle_public_enabled')

        self.wait_for_alert_message()
        self.check_package_parameter_by_id(self.postgre_id, 'Public', 'False')

        # Check that application now is not available in other porject.
        self.switch_to_project(new_project)
        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        self.check_element_not_on_page(by.By.XPATH, btn_xpath)

    def test_modify_description(self):
        """Test check ability to change description of the package

        Scenario:
            1. Navigate to 'Packages' page
            2. Select package and click on 'Modify Package'
            3. Change description
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.select_action_for_package(self.mockapp_id,
                                       'modify_package')

        self.modify_package('description', 'New Description')

        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        self.assertEqual('New Description',
                         self.driver.find_element_by_xpath(
                             c.MockAppDescr).text)

    def test_upload_package(self):
        """Test package uploading via Packages view.

           Skips category selection step.
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        # No application data modification is needed
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        self.check_package_parameter_by_name(self.archive_name,
                                             'Active',
                                             'True')
        self.check_package_parameter_by_name(self.archive_name,
                                             'Public',
                                             'False')
        self.check_package_parameter_by_name(self.archive_name,
                                             'Tenant Name',
                                             cfg.common.tenant)

    def test_upload_package_modify(self):
        """Test package modifying a package after uploading it."""

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        pkg_name = self.alt_archive_name
        self.fill_field(by.By.CSS_SELECTOR,
                        "input[name='modify-name']", pkg_name)

        label = self.driver.find_element_by_css_selector(
            "label[for=id_modify-is_public]")
        label.click()
        label = self.driver.find_element_by_css_selector(
            "label[for=id_modify-enabled]")
        label.click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

        self.check_package_parameter_by_name(pkg_name, 'Public', 'True')
        self.check_package_parameter_by_name(pkg_name, 'Active', 'False')

    def test_package_share(self):
        """Test that admin is able to share Murano Apps

        Scenario:
            1. Hit 'Modify Package' on any package
            2. Mark 'Public' checkbox
            3. Hit 'Update' button
            4. Verify, that package is available for other users
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.mockapp_id, 'modify_package')

        self.driver.find_element_by_css_selector(
            "label[for=id_is_public]"
        ).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.log_out()
        self.log_in(self.testuser_name, self.testuser_password)
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.check_element_on_page(
            by.By.XPATH, c.AppPackages.format('MockApp'))

    def test_upload_package_detail(self):
        """Test check ability to view package details after uploading it."""

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        # No application data modification is needed
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        pkg_name = self.archive_name
        self.driver.find_element_by_xpath(
            "//a[contains(text(), '{0}')]".format(pkg_name)).click()
        self.assertIn(pkg_name,
                      self.driver.find_element(by.By.XPATH, c.AppDetail).text)

    def test_add_pkg_to_category_non_admin(self):
        """Test package addition to category as non admin user

        Scenario:
            1. Log into OpenStack Horizon dashboard as non-admin user
            2. Navigate to 'Packages' page
            3. Modify any package by changing its category from
                'category 1' to 'category 2'
            4. Log out
            5. Log into OpenStack Horizon dashboard as admin user
            6. Navigate to 'Categories' page
            7. Check that 'category 2' has one more package
        """
        # save initial package count
        self.navigate_to('Manage')
        self.go_to_submenu('Categories')

        web_pkg_count = int(self.driver.find_element_by_xpath(
            "//tr[contains(@data-display, 'Web')]/td[2]").text)

        database_pkg_count = int(self.driver.find_element_by_xpath(
            "//tr[contains(@data-display, 'Database')]/td[2]").text)

        # relogin as test user
        self.log_out()
        self.log_in(self.testuser_name, self.testuser_password)
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        self.select_action_for_package(self.postgre_id, 'modify_package')
        sel = self.driver.find_element_by_xpath(
            "//select[contains(@name, 'categories')]")
        sel = ui.Select(sel)
        sel.deselect_all()
        sel.select_by_value('Web')
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        self.log_out()

        # log in as admin user
        self.log_in(cfg.common.user, cfg.common.password)

        # check packages count for categories
        self.navigate_to('Manage')
        self.go_to_submenu('Categories')
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(
                'Web', web_pkg_count + 1))
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(
                'Databases', database_pkg_count - 1))

    def test_category_management(self):
        """Test application category adds and deletes successfully

        Scenario:
            1. Navigate to 'Categories' page
            2. Click on 'Add Category' button
            3. Create new category and check it's browsed in the table
            4. Delete new category and check it's not browsed anymore
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Categories')
        self.driver.find_element_by_id(c.AddCategory).click()
        self.fill_field(by.By.XPATH, "//input[@id='id_name']", 'TEST_CATEGORY')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()
        delete_new_category_btn = c.DeleteCategory.format('TEST_CATEGORY')
        self.driver.find_element_by_xpath(delete_new_category_btn).click()
        self.driver.find_element_by_xpath(c.ConfirmDeletion).click()
        self.wait_for_alert_message()
        self.check_element_not_on_page(by.By.XPATH, delete_new_category_btn)

    def test_sharing_app_without_permission(self):
        """Tests sharing Murano App without permission

        Scenario:
            1) Login as admin;
            2) Identity -> Users: Create User:
                User Name: Test_service_user
                Primary Project: service
                Enabled: Yes
            3) Login to Horizon as an 'Test_service_user';
            4) Catalog -> Manage -> Packages: Import Package
                Set public Off, Active On
            5) Try to modify created package and set Public = On.
                Error: You are not allowed to perform this operation
            6) Delete new package
        """
        service_prj_name = 'service'
        new_user = {'name': 'Test_service_user',
                    'password': 'somepassword',
                    'email': 'test_serv_user@email.com'}
        try:
            self.delete_user(new_user['name'])
        except Exception:
            pass
        # Create new user in 'service' prj
        service_prj_id = self.get_tenantid_by_name(service_prj_name)
        self.create_user(tenant_id=service_prj_id, **new_user)

        # login as 'Test_service_user'
        self.log_out()
        self.log_in(new_user['name'], new_user['password'])

        # Import package
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        # Public = OFF; Active = ON.
        public_checkbox = self.driver.find_element_by_id('id_modify-is_public')
        active_checkbox = self.driver.find_element_by_id('id_modify-enabled')
        if public_checkbox.is_selected():
            public_checkbox.click()
        if not active_checkbox.is_selected():
            active_checkbox.click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.AppPackages.format(self.archive_name))

        # Modify Package to set Public = ON
        package = self.driver.find_element_by_xpath(
            c.AppPackages.format(self.archive_name))
        pkg_id = package.get_attribute("data-object-id")
        self.select_action_for_package(pkg_id, 'modify_package')

        label = self.driver.find_element_by_css_selector(
            "label[for=id_is_public]")
        label.click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        # Expecting Error
        self.wait_for_error_message()

        # Clean up
        self.select_action_for_package(pkg_id, 'more')
        self.select_action_for_package(pkg_id, 'delete_package')
        self.driver.find_element_by_xpath(c.ConfirmDeletion).click()
        self.log_out()
        self.log_in()
        self.delete_user(new_user['name'])


class TestSuiteRepository(base.PackageTestCase):
    _apps_to_delete = set()

    def _compose_app(self, name, require=None):
        package_dir = os.path.join(self.serve_dir, 'apps/', name)
        shutil.copytree(c.PackageDir, package_dir)

        app_name = utils.compose_package(
            name,
            os.path.join(package_dir, 'manifest.yaml'),
            package_dir,
            require=require,
            archive_dir=os.path.join(self.serve_dir, 'apps/'),
        )
        self._apps_to_delete.add(name)
        return app_name

    def _compose_bundle(self, name, app_names):
        bundles_dir = os.path.join(self.serve_dir, 'bundles/')
        shutil.os.mkdir(bundles_dir)
        utils.compose_bundle(os.path.join(bundles_dir, name + '.bundle'),
                             app_names)

    def _make_pkg_zip_regular_file(self, name):
        file_name = os.path.join(self.serve_dir, 'apps', name + '.zip')
        with open(file_name, 'w') as f:
            f.write("I'm not an application. I'm not a zip file at all")

    def _make_non_murano_zip_in_pkg(self, name):
        file_name = os.path.join(self.serve_dir, 'apps', 'manifest.yaml')
        with open(file_name, 'w') as f:
            f.write("Description: I'm not a murano package at all")
        zip_name = os.path.join(self.serve_dir, 'apps', name + '.zip')
        with zipfile.ZipFile(zip_name, 'w') as archive:
            archive.write(file_name)

    def _make_big_zip_pkg(self, name, size):
        file_name = os.path.join(self.serve_dir, 'apps', 'images.lst')
        self._compose_app(name)

        # create file with size 10 mb
        with open(file_name, 'wb') as f:
            f.seek(size - 1)
            f.write('\0')

        # add created file to archive
        zip_name = os.path.join(self.serve_dir, 'apps', name + '.zip')
        with zipfile.ZipFile(zip_name, 'a') as archive:
            archive.write(file_name)

    def setUp(self):
        super(TestSuiteRepository, self).setUp()
        self.serve_dir = tempfile.mkdtemp(suffix="repo")

        def serve_function():
            class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
                pass
            os.chdir(self.serve_dir)
            httpd = SocketServer.TCPServer(
                ("0.0.0.0", 8099),
                Handler, bind_and_activate=False)
            httpd.allow_reuse_address = True
            httpd.server_bind()
            httpd.server_activate()
            httpd.serve_forever()

        self.p = multiprocessing.Process(target=serve_function)
        self.p.start()

    def tearDown(self):
        super(TestSuiteRepository, self).tearDown()
        self.p.terminate()
        for package in self.murano_client.packages.list(include_disabled=True):
            if package.name in self._apps_to_delete:
                self.murano_client.packages.delete(package.id)
                self._apps_to_delete.remove(package.name)
        shutil.rmtree(self.serve_dir)

    def test_import_package_by_url(self):
        """Test package importing via url."""

        pkg_name = "dummy_package"
        self._compose_app(pkg_name)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_url")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-url']")
        el.send_keys("http://127.0.0.1:8099/apps/{0}.zip".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        # No application data modification is needed
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_package_from_repo(self):
        """Test package importing via fqn from repo with dependent apps."""

        pkg_name_parent = "PackageParent"
        pkg_name_child = "PackageChild"
        pkg_name_grand_child = "PackageGrandChild"

        self._compose_app(pkg_name_parent, require={pkg_name_child: ''})
        self._compose_app(pkg_name_child,
                          require={pkg_name_grand_child: '0.1'})
        pkg_name_grand_child += '.0.1'
        self._compose_app(pkg_name_grand_child)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-repo_name']")
        el.send_keys("{0}".format(pkg_name_parent))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        pkg_names = [pkg_name_parent, pkg_name_child, pkg_name_grand_child]
        for pkg_name in pkg_names:
            self.check_element_on_page(
                by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_bundle_by_url(self):
        """Test bundle importing via url."""
        pkg_name_one = "PackageOne"
        pkg_name_two = "PackageTwo"
        pkg_name_parent = "PackageParent"
        pkg_name_child = "PackageChild"

        self._compose_app(pkg_name_one)
        self._compose_app(pkg_name_two)
        self._compose_app(pkg_name_parent, require={pkg_name_child: ''})
        self._compose_app(pkg_name_child)

        bundle_name = 'PackageWithPackages'
        self._compose_bundle(bundle_name, [pkg_name_parent,
                                           pkg_name_one,
                                           pkg_name_two])

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.ImportBundle).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_url")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-url']")
        el.send_keys(
            "http://127.0.0.1:8099/bundles/{0}.bundle".format(bundle_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        pkg_names = [pkg_name_parent, pkg_name_child,
                     pkg_name_one, pkg_name_two]
        for pkg_name in pkg_names:
            self.check_element_on_page(
                by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_bundle_from_repo(self):
        """Test bundle importing via fqn from repo."""
        pkg_name_parent = "PackageParent"
        pkg_name_child = "PackageChild"
        pkg_name_grand_child = "PackageGrandChild"
        pkg_name_single = "PackageSingle"

        self._compose_app(pkg_name_single)
        self._compose_app(pkg_name_parent, require={pkg_name_child: ''})
        self._compose_app(pkg_name_child,
                          require={pkg_name_grand_child: '0.1'})
        pkg_name_grand_child += '.0.1'
        self._compose_app(pkg_name_grand_child)

        bundle_name = 'PackageWithPackages'
        self._compose_bundle(bundle_name, [pkg_name_parent, pkg_name_single])

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.ImportBundle).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-name']")
        el.send_keys("{0}".format(bundle_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        pkg_names = [pkg_name_parent, pkg_name_child,
                     pkg_name_grand_child, pkg_name_single]
        for pkg_name in pkg_names:
            self.check_element_on_page(
                by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_package_by_invalid_url(self):
        """Negative test when package is imported by invalid url."""
        pkg_name = self.gen_random_resource_name('pkg')
        self._compose_app(pkg_name)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')

        # Invalid folder
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_url")
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-url']")
        el.send_keys("http://127.0.0.1:8099/None/{0}.zip".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_error_message()

        # HTTP connect error
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_url")
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-url']")
        el.send_keys("http://127.0.0.2:12345/apps/{0}.zip".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_error_message(sec=90)

        # Invalid app name
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_url")
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-url']")
        el.send_keys(
            "http://127.0.0.1:8099/apps/invalid_{0}.zip".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_error_message()

        self.check_element_not_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_package_by_invalid_name(self):
        """Negative test when package is imported by invalid name from repo."""
        pkg_name = self.gen_random_resource_name('pkg')
        self._compose_app(pkg_name)
        pkg_to_import = "invalid_" + pkg_name

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-repo_name']")
        el.send_keys("{0}".format(pkg_to_import))
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_error_message()

        self.check_element_not_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_to_import))

    def test_import_non_zip_file(self):
        """"Negative test import regualr file instead of zip package."""
        # Create dummy package with zip file replaced by text one
        pkg_name = self.gen_random_resource_name('pkg')
        self._compose_app(pkg_name)
        self._make_pkg_zip_regular_file(pkg_name)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-repo_name']")
        el.send_keys("{0}".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        err_msg = self.wait_for_error_message()
        self.assertIn('File is not a zip file', err_msg)

        self.check_element_not_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_invalid_zip_file(self):
        """"Negative test import zip file which is not a murano package."""
        # At first create dummy package with zip file replaced by text one
        pkg_name = self.gen_random_resource_name('pkg')
        self._compose_app(pkg_name)
        self._make_non_murano_zip_in_pkg(pkg_name)

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-repo_name']")
        el.send_keys("{0}".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        err_msg = self.wait_for_error_message()
        self.assertIn("There is no item named 'manifest.yaml'", err_msg)

        self.check_element_not_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_big_zip_file(self):
        """Import very big zip archive.

        Scenario:
            1. Log in Horizon with admin credentials
            2. Navigate to 'Packages' page
            3. Click 'Import Package' and select 'File' as a package source
            4. Choose very big zip file
            5. Click on 'Next' button
            6. Check that error message that user can't upload file more than
                5 MB is displayed
        """
        pkg_name = self.gen_random_resource_name('pkg')
        self._make_big_zip_pkg(name=pkg_name,
                               size=10 * 1024 * 1024)

        # import package and choose big zip file for it
        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-repo_name']")
        el.send_keys("{0}".format(pkg_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        # check that error message appeared
        error_message = ("Error: 400 Bad Request Uploading file is too "
                         "large. The limit is 5 Mb")
        self.check_alert_message(error_message)

        self.check_element_not_on_page(
            by.By.XPATH, c.AppPackages.format(pkg_name))

    def test_import_bundle_when_dependencies_installed(self):
        """Test bundle import if some dependencies are installed.

        Check that bundle can be imported if some of its dependencies
        are already installed from repository.
        """
        pkg_name_parent_one = self.gen_random_resource_name('pkg')
        pkg_name_child_one = self.gen_random_resource_name('pkg')
        pkg_name_grand_child = self.gen_random_resource_name('pkg')
        pkg_name_parent_two = self.gen_random_resource_name('pkg')
        pkg_name_child_two = self.gen_random_resource_name('pkg')

        self._compose_app(pkg_name_parent_one,
                          require={pkg_name_child_one: ''})
        self._compose_app(pkg_name_child_one,
                          require={pkg_name_grand_child: '0.1'})
        pkg_name_grand_child += '.0.1'
        self._compose_app(pkg_name_grand_child)
        self._compose_app(pkg_name_parent_two,
                          require={pkg_name_child_two: ''})
        self._compose_app(pkg_name_child_two)

        bundle_name = self.gen_random_resource_name('bundle')
        self._compose_bundle(bundle_name,
                             [pkg_name_parent_one, pkg_name_parent_two])

        utils.upload_app_package(self.murano_client, pkg_name_grand_child,
                                 {"categories": ["Web"], "tags": ["tag"]})
        utils.upload_app_package(self.murano_client, pkg_name_child_two,
                                 {"categories": ["Web"], "tags": ["tag"]})

        self.navigate_to('Manage')
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.ImportBundle).click()
        sel = self.driver.find_element_by_css_selector(
            "select[name='upload-import_type']")
        sel = ui.Select(sel)
        sel.select_by_value("by_name")

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-name']")
        el.send_keys("{0}".format(bundle_name))
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        pkg_names = [pkg_name_parent_one, pkg_name_child_one,
                     pkg_name_grand_child, pkg_name_parent_two,
                     pkg_name_child_two]
        for pkg_name in pkg_names:
            self.check_element_on_page(
                by.By.XPATH, c.AppPackages.format(pkg_name))


class TestSuitePackageCategory(base.PackageTestCase):
    def _import_package_with_category(self, package_archive, category):
        self.go_to_submenu('Packages')
        self.driver.find_element_by_id(c.UploadPackage).click()

        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(package_archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()
        # choose the required category
        self.driver.find_element_by_xpath(
            c.PackageCategory.format(category)).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        # To wait till the focus is swithced
        # from modal dialog back to the window.
        self.wait_for_sidebar_is_loaded()

    def setUp(self):
        super(TestSuitePackageCategory, self).setUp()

        # add new category
        self.category = str(uuid.uuid4())

        self.navigate_to('Manage')
        self.go_to_submenu('Categories')
        self.driver.find_element_by_id(c.AddCategory).click()
        self.fill_field(
            by.By.XPATH, "//input[@id='id_name']", self.category)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(self.category, 0))

        # save category id
        self.category_id = self.get_element_id(self.category)

    def tearDown(self):
        super(TestSuitePackageCategory, self).tearDown()

        # delete created category
        self.murano_client.categories.delete(self.category_id)

    def test_add_delete_category_for_package(self):
        """Test package importing with new category and changing the category.

        Scenario:
            1. Log into OpenStack Horizon dashboard as admin user
            2. Navigate to 'Categories' page
            3. Click on 'Add Category' button
            4. Create new category and check it's browsed in the table
            5. Navigate to 'Packages' page
            6. Click on 'Import Package' button
            7. Import package and select created 'test' category for it
            8. Navigate to "Categories" page
            9. Check that package count = 1 for created category
            10. Navigate to 'Packages' page
            11. Modify imported earlier package, by changing its category
            12. Navigate to 'Categories' page
            13. Check that package count = 0 for created category
        """
        # add new package to the created category
        self._import_package_with_category(self.archive, self.category)

        # Check that package count = 1 for created category
        self.go_to_submenu('Categories')
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(self.category, 1))

        # Modify imported earlier package by changing its category
        self.go_to_submenu('Packages')

        package = self.driver.find_element_by_xpath(
            c.AppPackages.format(self.archive_name))
        pkg_id = package.get_attribute("data-object-id")

        self.select_action_for_package(pkg_id, 'modify_package')
        sel = self.driver.find_element_by_xpath(
            "//select[contains(@name, 'categories')]")
        sel = ui.Select(sel)
        sel.deselect_all()
        sel.select_by_value('Web')
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()

        # Check that package count = 0 for created category
        self.go_to_submenu('Categories')
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(self.category, 0))

    def test_filter_by_new_category(self):
        """Filter by new category from Catalog>Browse page

        Scenario:
            1. Log into OpenStack Horizon dashboard as admin user
            2. Navigate to 'Categories' page
            3. Click on 'Add Category' button
            4. Create new category and check it's browsed in the table
            5. Navigate to 'Packages' page
            6. Click on 'Import Package' button
            7. Import package and select created 'test' category for it
            8. Navigate to "Catalog>Browse" page
            9. Select new category in "App category" dropdown list
        """
        self._import_package_with_category(self.archive, self.category)
        self.navigate_to('Catalog')
        self.go_to_submenu('Browse')
        self.driver.find_element_by_xpath(
            c.CategorySelector.format('All')).click()
        self.driver.find_element_by_partial_link_text(self.category).click()

        self.check_element_on_page(
            by.By.XPATH, c.App.format(self.archive_name))

    def test_filter_by_category_from_env_components(self):
        """Filter by new category from Environment Components page

        Scenario:
            1. Log into OpenStack Horizon dashboard as admin user
            2. Navigate to 'Categories' page
            3. Click on 'Add Category' button
            4. Create new category and check it's browsed in the table
            5. Navigate to 'Packages' page
            6. Click on 'Import Package' button
            7. Import package and select created 'test' category for it
            8. Navigate to 'Environments' page
            9. Create environment
            10. Select new category in 'App category' dropdown list
            11. Check that imported package is displayed
            12. Select 'Web' category in 'App category' dropdown list
            13. Check that imported package is not displayed
        """
        self._import_package_with_category(self.archive, self.category)

        # create environment
        env_name = str(uuid.uuid4())

        self.navigate_to('Catalog')
        self.go_to_submenu('Environments')
        self.create_environment(env_name)
        self.go_to_submenu('Environments')
        self.check_element_on_page(by.By.LINK_TEXT, env_name)

        # filter by new category
        self.select_action_for_environment(env_name, 'show')
        self.driver.find_element_by_xpath(c.EnvAppsCategorySelector).click()
        self.driver.find_element_by_partial_link_text(self.category).click()

        # check that imported package is displayed
        self.check_element_on_page(
            by.By.XPATH, c.EnvAppsCategory.format(self.archive_name))

        # filter by 'Web' category
        self.driver.find_element_by_xpath(c.EnvAppsCategorySelector).click()
        self.driver.find_element_by_partial_link_text('Web').click()

        # check that imported package is not displayed
        self.check_element_not_on_page(
            by.By.XPATH, c.EnvAppsCategory.format(self.archive_name))

    def test_add_existing_category(self):
        """Add category with name of already existing category

        Scenario:
            1. Log into OpenStack Horizon dashboard as admin user
            2. Navigate to 'Categories' page
            3. Add new category
            4. Check that new category has appeared in category list
            5. Try to add category with the same name
            6. Check that appropriate user friendly error message has
                appeared.
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Categories')

        self.driver.find_element_by_id(c.AddCategory).click()
        self.fill_field(
            by.By.XPATH, "//input[@id='id_name']", self.category)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        error_message = ("Error: Requested operation conflicts "
                         "with an existing object.")
        self.check_alert_message(error_message)

    def test_delete_category_with_package(self):
        """Deletion of category with package in it

        Scenario:
            1. Log into OpenStack Horizon dashboard as admin user
            2. Navigate to 'Categories' page
            3. Add new category
            4. Navigate to 'Packages' page
            5. Import package and select created category for it
            6. Navigate to "Categories" page
            7. Check that package count = 1 for created category
            8. Check that there is no 'Delete Category' button for the category
        """
        # add new package to the created category
        self._import_package_with_category(self.archive, self.category)

        # Check that package count = 1 for created category
        self.go_to_submenu('Categories')
        self.check_element_on_page(
            by.By.XPATH, c.CategoryPackageCount.format(self.category, 1))

        self.check_element_not_on_page(
            by.By.XPATH, c.DeleteCategory.format(self.category))

    def test_list_of_existing_categories(self):
        """Checks that list of categories is available

        Scenario:
            1. Navigate to 'Categories' page
            2. Check that list of categories available and basic categories
                ("Web", "Databases") are present in the list
        """
        self.go_to_submenu("Categories")
        categories_table_locator = (by.By.CSS_SELECTOR, "table#categories")
        self.check_element_on_page(*categories_table_locator)
        for category in ("Databases", "Web"):
            category_locator = (by.By.XPATH,
                                "//tr[@data-display='{}']".format(category))
            self.check_element_on_page(*category_locator)


class TestSuiteCategoriesPagination(base.PackageTestCase):
    def setUp(self):
        super(TestSuiteCategoriesPagination, self).setUp()
        self.categories_to_delete = []
        # Create at least 5 more pages with categories
        for x in range(cfg.common.items_per_page * 5):
            name = self.gen_random_resource_name('category')
            category = self.murano_client.categories.add({'name': name})
            self.categories_to_delete.append(category.id)

    def tearDown(self):
        super(TestSuiteCategoriesPagination, self).tearDown()
        for category_id in self.categories_to_delete:
            self.murano_client.categories.delete(id=category_id)

    def test_category_pagination(self):
        """Test categories pagination in case of many categories created """
        self.navigate_to('Manage')
        self.go_to_submenu('Categories')

        categories_list = [elem.name for elem in
                           self.murano_client.categories.list()]
        # Murano client lists the categories in order of creation
        # starting from the last created. So need to reverse it to align with
        # the table in UI form. Where categories are listed starting from the
        # first created to the last one.
        categories_list.reverse()

        categories_per_page = cfg.common.items_per_page
        pages_itself = [categories_list[i:i + categories_per_page] for i in
                        range(0, len(categories_list), categories_per_page)]
        for i, names in enumerate(pages_itself, 1):
            for name in names:
                self.check_element_on_page(by.By.XPATH, c.Status.format(name))
            if i != len(pages_itself):
                self.driver.find_element_by_xpath(c.NextBtn).click()
        # Wait till the Next button disappear
        # Otherwise 'Prev' button from the previous page might be used
        self.check_element_not_on_page(by.By.XPATH, c.NextBtn)
        pages_itself.reverse()
        for i, names in enumerate(pages_itself, 1):
            for name in names:
                self.check_element_on_page(by.By.XPATH, c.Status.format(name))
            if i != len(pages_itself):
                self.driver.find_element_by_xpath(c.PrevBtn).click()


class TestSuiteMultipleEnvironments(base.ApplicationTestCase):
    def test_create_two_environments_and_delete_them_at_once(self):
        """Test check ability to create and delete multiple environments

        Scenario:
            1. Create two environments
            2. Navigate to environment list
            3. Check created environments
            4. Delete created environments at once
        """
        self.go_to_submenu('Environments')
        self.create_environment('test_create_del_env_1')
        self.go_to_submenu('Environments')
        self.create_environment('test_create_del_env_2', by_id=True)
        self.go_to_submenu('Environments')
        self.driver.find_element_by_css_selector(
            "label[for=ui-id-1]").click()
        self.driver.find_element_by_css_selector(
            c.DeleteEnvironments).click()
        self.driver.find_element_by_xpath(c.ConfirmDeletion).click()
        self.wait_for_alert_message()
        self.check_element_not_on_page(by.By.LINK_TEXT,
                                       'test_create_del_env_1')
        self.check_element_not_on_page(by.By.LINK_TEXT,
                                       'test_create_del_env_2')

    def test_deploy_two_environments_at_once(self):
        """Test check ability to deploy multiple environments

        Scenario:
            1. Add two apps to different environments
            2. Navigate to environment list
            3. Check created environments
            4. Deploy created environments at once
        """
        self.add_app_to_env(self.mockapp_id)
        self.add_app_to_env(self.mockapp_id)
        self.go_to_submenu('Environments')
        self.driver.find_element_by_css_selector(
            "label[for=ui-id-1]").click()
        self.driver.find_element_by_css_selector(
            c.DeployEnvironments).click()
        # check statuses of two environments
        self.check_element_on_page(by.By.XPATH,
                                   c.EnvStatus.format('quick-env-1', 'Ready'),
                                   sec=90)
        self.check_element_on_page(by.By.XPATH,
                                   c.EnvStatus.format('quick-env-2', 'Ready'),
                                   sec=90)

    def test_abandon_two_environments_at_once(self):
        """Test check ability to abandon multiple environments

        Scenario:
            1. Add two apps to different environments
            2. Navigate to environment list
            3. Check created environments
            4. Deploy created environments at once
            5. Abandon environments before they are deployed
        """
        self.add_app_to_env(self.mockapp_id)
        self.add_app_to_env(self.mockapp_id)
        self.go_to_submenu('Environments')
        self.driver.find_element_by_css_selector(
            "label[for=ui-id-1]").click()
        self.driver.find_element_by_css_selector(
            c.DeployEnvironments).click()
        self.go_to_submenu('Environments')
        self.driver.find_element_by_css_selector(
            "label[for=ui-id-1]").click()
        self.driver.find_element_by_css_selector(
            c.AbandonEnvironments).click()
        self.driver.find_element_by_xpath(c.ConfirmAbandon).click()
        self.wait_for_alert_message()
        self.check_element_not_on_page(by.By.LINK_TEXT, 'quick-env-1')
        self.check_element_not_on_page(by.By.LINK_TEXT, 'quick-env-2')
