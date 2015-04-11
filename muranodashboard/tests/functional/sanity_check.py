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

import time

from selenium.webdriver.common import by

from muranodashboard.tests.functional import base
from muranodashboard.tests.functional import consts as c


class TestSuiteSmoke(base.UITestCase):
    """This class keeps smoke tests which check operability of all main panels
    """
    def test_smoke_environments_panel(self):
        self.go_to_submenu('Environments')
        self.check_panel_is_present('Environments')

    def test_smoke_applications_panel(self):
        self.go_to_submenu('Applications')
        self.check_panel_is_present('Applications')

    def test_smoke_images_panel(self):
        self.navigate_to('Manage')
        self.go_to_submenu('Images')
        self.check_panel_is_present('Marked Images')

    def test_smoke_package_definitions_panel(self):
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.check_panel_is_present('Package Definitions')


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
        self.driver.find_element_by_link_text('test_edit_env')

        self.edit_environment(old_name='test_edit_env', new_name='edited_env')
        self.check_element_on_page(by.By.LINK_TEXT, 'edited_env')
        self.check_element_not_on_page(by.By.LINK_TEXT, 'test_edit_env')

    def test_create_env_from_the_catalog_page(self):
        """Test create environment from the catalog page

        Scenario:
           1. Go the the Applications page
           2. Press 'Create Env'
           3. Make sure that it's possible to chose just created environment
        """
        self.go_to_submenu('Applications')
        self.driver.find_elements_by_xpath(
            "//a[contains(text(), 'Create Env')]")[0].click()
        self.fill_field(by.By.ID, 'id_name', 'TestEnv')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH,
            "//div[@id='environment_switcher']/a[contains(text(), 'TestEnv')]")


class TestSuiteImage(base.ImageTestCase):
    def test_rename_image(self):
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
        self.select_and_click_element('Mark')
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
        """Test checks that validation of domain name field work
        and appropriate error message is appeared after entering
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
        self.go_to_submenu('Applications')

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
        """Test checks validation of field that usually define
        application name

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create Mock App
            3. Check a set of names, if current name isn't valid
            appropriate error message should appears
        """
        self.go_to_submenu('Applications')

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
        """Test checks that fields with parameter 'required=True' in yaml form
        are truly required and can't be omitted

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create MockApp
            3. Don't type app name in the 'Application Name'
            field that is required and click 'Next',check that there is
            error message
            4. Set app name and click 'Next',
            check that there is no error message
        """
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.check_error_message_is_present('This field is required.')

        self.fill_field(by.By.NAME, "0-name", "name")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.wait_element_is_clickable(by.By.XPATH, c.ButtonSubmit)

    def test_password_validation(self):
        """Test checks password validation

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create MockApp
            3. Set weak password consisting of numbers,
            check that error message appears
            4. Set different passwords to Password field and Confirm password
            field, check that validation failed
            5. Set correct password. Validation has to pass
        """
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "name")
        self.fill_field(by.By.NAME, '0-adminPassword', value='123456')
        self.check_error_message_is_present(
            'The password must contain at least one letter')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.fill_field(by.By.NAME, "0-adminPassword-clone", value='P@ssw0rd')
        self.check_error_message_is_absent('Passwords do not match')
        self.fill_field(by.By.NAME, '0-adminPassword', value='P@ssw0rd')
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()
        self.wait_element_is_clickable(by.By.XPATH, c.ButtonSubmit)


class TestSuiteApplications(base.ApplicationTestCase):
    def test_check_transitions_from_one_wizard_to_another(self):
        """Test checks that transitions "Next" and "Back" are not broken

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create MockApp
            3. Set app name and click on "Next", check that second wizard step
            will appear
            4. Click 'Back' and check that first wizard step is shown
        """
        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "name")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.driver.find_element_by_id(
            'wizard_{0}_btn'.format(self.mockapp_id)).click()

        self.check_element_on_page(by.By.NAME, "0-name")

    def test_check_ability_create_two_dependent_apps(self):
        """Test checks that using one creation form it is possible to
        add to related apps in the one environment

        Scenario:
            1. Navigate to Application Catalog > Applications
            2. Start to create MockApp
            3. Set app name and click on "Next"
            4. Click '+' and verify that creation of second app is possible
        """

        self.go_to_submenu('Applications')

        self.select_and_click_action_for_app('quick-add', self.mockapp_id)

        self.fill_field(by.By.NAME, "0-name", "app1")
        self.driver.find_element_by_xpath(c.ButtonSubmit).click()

        self.driver.find_element_by_css_selector(
            'form i.fa-plus-circle').click()
        self.fill_field(by.By.NAME, "0-name", "app2")

    def test_creation_deletion_app(self):
        """Test check ability to create and delete test app

        Scenario:
            1. Navigate to 'Application Catalog'
            2. Click on 'Quick Deploy' for MockApp application
            3. Create TestApp app by filling the creation form
            4. Delete TestApp app from environment
        """

        self.go_to_submenu('Applications')

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
            1. Navigate to 'Application Catalog > Applications' panel
            2. Set search criterion in the search field(e.g 'PostgreSQL')
            3. Click on 'Filter' and check result
        """
        self.go_to_submenu('Applications')
        self.fill_field(by.By.CSS_SELECTOR, 'input.form-control', 'PostgreSQL')
        self.driver.find_element_by_id('apps__action_filter').click()

        self.check_element_on_page(by.By.XPATH,
                                   c.App.format('PostgreSQL'))
        self.check_element_not_on_page(by.By.XPATH,
                                       c.App.format('MockApp'))

    def test_filter_by_category(self):
        """Test checks ability to filter applications by category
        in Application Catalog page

        Scenario:
            1. Navigate to 'Application Catalog' panel
            2. Select 'Databases' category in 'App Category' dropdown menu
            3. Verify that PostgreSQL is shown
            4. Select 'Web' category in
            'App Category' dropdown menu
            5. Verify that MockApp is shown
        """
        self.go_to_submenu('Applications')
        self.driver.find_element_by_xpath(
            c.CategorySelector.format('All')).click()
        self.driver.find_element_by_link_text('Databases').click()

        self.check_element_on_page(by.By.XPATH, c.App.format('PostgreSQL'))

        self.driver.find_element_by_xpath(
            c.CategorySelector.format('Databases')).click()
        self.driver.find_element_by_link_text('Web').click()

        self.check_element_on_page(by.By.XPATH, c.App.format('MockApp'))

    def test_check_option_switch_env(self):
        """Test checks ability to switch environment and add app in other env

        Scenario:
            1. Navigate to 'Application Catalog>Environments' panel
            2. Create environment 'env1'
            3. Create environment 'env2'
            4. Navigate to 'Application Catalog>Application Catalog'
            5. Click on 'Environment' panel
            6. Switch to env2
            7. Add application in env2
            8. Navigate to 'Application Catalog>Environments'
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

        self.go_to_submenu('Applications')
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
            1. Navigate Applications and click MockApp 'Quick Deploy'
            2. Check that for "Ready to deploy" state progress bar is not seen
            3. Click deploy
            4. Check that for "Deploying" status progress bar is seen
        """
        self.go_to_submenu('Applications')
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
            1. Navigate Applications and click MockApp 'Quick Deploy'
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
            1. Navigate Applications and click MockApp 'Quick Deploy'
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
        """Test checks that information about app is available and tr
        Scenario:
            1. Navigate to 'Application Catalog > Applications' panel
            2. Choose some application and click on 'More info'
            3. Verify info about application
        """
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('details', self.mockapp_id)

        self.assertEqual('MockApp for webUI tests',
                         self.driver.find_element_by_xpath(
                             "//div[@class='app-description']").text)
        self.driver.find_element_by_link_text('Requirements').click()
        self.driver.find_element_by_class_name('app_requirements')
        self.driver.find_element_by_link_text('License').click()
        self.driver.find_element_by_class_name('app_license')

    def test_check_topology_page(self):
        """Test checks that topology tab is available
        and topology page displays correctly

        Scenario:
            1. Navigate Applications and click MockApp 'Quick Deploy'
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
        """Test checks that deployment history tab is available
        and deployment logs are present and correctly

        Scenario:
            1. Navigate Applications and click MockApp 'Quick Deploy'
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


class TestSuitePackages(base.PackageTestCase):
    def test_modify_package_name(self):
        """Test check ability to change name of the package

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select package and click on 'Modify Package'
            3. Rename package
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('PostgreSQL',
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL-modified')
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.wait_for_alert_message()

        self.check_element_on_page(by.By.XPATH,
                                   c.AppPackageDefinitions.format(
                                       'PostgreSQL-modified'))

        self.select_action_for_package('PostgreSQL-modified',
                                       'modify_package')
        self.fill_field(by.By.ID, 'id_name', 'PostgreSQL')
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.check_element_on_page(by.By.XPATH,
                                   c.AppPackageDefinitions.format(
                                       'PostgreSQL'))

    def test_modify_package_add_tag(self):
        """Test that new tag is shown in description

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Click on "Modify Package" and add new tag
            3. Got to the Application Catalog page
            4. Check, that new tag is browsed in application description
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('PostgreSQL',
                                       'modify_package')

        self.fill_field(by.By.ID, 'id_tags', 'TEST_TAG')
        self.modify_package('tags', 'TEST_TAG')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.select_and_click_action_for_app('details', self.postgre_id)
        self.assertIn('TEST_TAG',
                      self.driver.find_element_by_xpath(
                          c.TagInDetails).text)

    def test_download_package(self):
        """Test check ability to download package from repository

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select PostgreSQL package and click on "More>Download Package"
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'download_package')

    def test_check_toggle_enabled_package(self):
        """Test check ability to make package active or inactive

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select some package and make it inactive ("More>Toggle Active")
            3. Check that package is inactive
            4. Select some package and make it active ("More>Toggle Active ")
            5. Check that package is active
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_enabled')

        self.check_package_parameter('PostgreSQL', 'Active', 'False')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_enabled')

        self.check_package_parameter('PostgreSQL', 'Active', 'True')

    def test_check_toggle_public_package(self):
        """Test check ability to make package active or inactive

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select some package and make it inactive ("More>Toggle Public")
            3. Check that package is unpublic
            4. Select some package and make it active ("More>Toggle Public ")
            5. Check that package is public
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_public_enabled')

        self.check_package_parameter('PostgreSQL', 'Public', 'True')

        self.select_action_for_package('PostgreSQL', 'more')
        self.select_action_for_package('PostgreSQL', 'toggle_public_enabled')

        self.check_package_parameter('PostgreSQL', 'Public', 'False')

    def test_modify_description(self):
        """Test check ability to change description of the package

        Scenario:
            1. Navigate to 'Package Definitions' page
            2. Select package and click on 'Modify Package'
            3. Change description
        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')
        self.select_action_for_package('MockApp',
                                       'modify_package')

        self.modify_package('description', 'New Description')

        self.navigate_to('Application_Catalog')
        self.go_to_submenu('Applications')
        self.assertEqual('New Description',
                         self.driver.find_element_by_xpath(
                             c.MockAppDescr).text)

    def test_upload_package(self):
        """Test package uploading via Package Definitions view.
           Skip category selection step.

        """
        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        # No application data modification is needed
        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.AppPackageDefinitions.format(self.archive_name))

        # public
        el = self.driver.find_element_by_xpath(
            c.AppPackageDefinitions.format(self.archive_name) + '/td[3]')
        self.assertEqual(el.text.strip().lower(), 'true')
        # enabled
        el = self.driver.find_element_by_xpath(
            c.AppPackageDefinitions.format(self.archive_name) + '/td[4]')
        self.assertEqual(el.text.strip().lower(), 'false')

    def test_upload_package_modify(self):
        """Test package modifying a package after uploading it."""

        self.navigate_to('Manage')
        self.go_to_submenu('Package Definitions')

        self.driver.find_element_by_id(c.UploadPackage).click()
        el = self.driver.find_element_by_css_selector(
            "input[name='upload-package']")
        el.send_keys(self.archive)
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        pkg_name = self.alt_archive_name
        self.fill_field(by.By.CSS_SELECTOR,
                        "input[name='modify-name']", pkg_name)
        self.driver.find_element_by_css_selector(
            "input[name=modify-is_public]"
        ).click()
        self.driver.find_element_by_css_selector(
            "input[name=modify-enabled]"
        ).click()

        self.driver.find_element_by_xpath(c.InputSubmit).click()
        self.driver.find_element_by_xpath(c.InputSubmit).click()

        self.wait_for_alert_message()
        self.check_element_on_page(
            by.By.XPATH, c.AppPackageDefinitions.format(pkg_name))
        # public
        el = self.driver.find_element_by_xpath(
            c.AppPackageDefinitions.format(pkg_name) + '/td[3]')
        self.assertEqual(el.text.strip().lower(), 'false')
        # enabled
        el = self.driver.find_element_by_xpath(
            c.AppPackageDefinitions.format(pkg_name) + '/td[4]')
        self.assertEqual(el.text.strip().lower(), 'true')

    def test_category_management(self):
        """Test application category adds and deletes succesfully

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
