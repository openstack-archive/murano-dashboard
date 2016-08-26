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

import os

PackageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          'MockApp')
HotPackageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'HotApp')
DeployingPackageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'DeployingApp')

CategorySelector = "//a[contains(text(), '{0}')][contains(@class, 'dropdown-toggle')]"  # noqa
EnvAppsCategorySelector = "//*[contains(@id, 'envAppsCategoryBtn')]"
App = "//div[contains(@class, 'app-list')]//h4[contains(text(), '{0}')]"
MockAppDescr = "//div[h4[contains(text(), 'MockApp')]]/p"
AppPackages = u"//tr[@data-display='{0}']"
AppDetail = "//dl[dt[contains(text(), 'Name')]]/dd"
TagInDetails = "//div[contains(@class, 'app-meta')]//ul//li[strong[contains(text(), 'Tags')]]"  # noqa
TestImage = "//tr[td[contains(text(), '{0}')]]"
DeleteImageMeta = TestImage + "//td//button[contains(text(), 'Delete Metadata')]"  # noqa
ImageMeta = "//dl//div[dt[contains(text(), 'murano_image_info')]]/dd"
More = "//tr[contains(@id, '{0}__row__{1}')]//a[contains(@class, dropdown-toggle) and @href='#']"  # noqa
Status = "//td[contains(text(), '{0}')]"
EnvStatus = "//tr[contains(@data-display, '{0}')]/td[contains(text(), '{1}')]"
CellStatus = "//td[contains(@class, 'status_{0}')]"
Row = "//tr[contains(@id, 'services__row__{0}')]"
ErrorMessage = '//span[contains(@class, "help-block") and contains(text(), "{0}")]'  # noqa
EnvAppsCategory = "//div[contains(@class, 'draggable_app')]//div[contains(text(), '{0}')]"  # noqa
PackageCategory = "//select[@name='add_category-categories']/option[text()='{0}']"  # noqa
DatabaseCategory = "select[name='add_category-categories'] > option[value='Databases']"  # noqa
CategoryPackageCount = "//tr[contains(@data-display, '{0}')]/td[contains(text(), '{1}')]"  # noqa
Action = '//a[contains(@class, "murano_action") and contains(text(), "testAction")]'  # noqa
HotFlavorField = '//div[contains(@class, "has-error")]//input'
EnvCheckbox = "//tr[contains(@data-display, '{0}')]/td[contains(@class, 'multi_select_column')]//div//label"  # noqa
NewEnvRow = "table#environments thead tr.new_env"
TableSorterByName = "table#environments thead th.tablesorter-header[data-column='1']"  # noqa

# Buttons
ButtonSubmit = ".//*[@name='wizard_goto_step'][2]"
InputSubmit = "//input[@type='submit']"
ConfirmDeletion = "//div[@class='modal-footer']//a[contains(text(), 'Delete')]"  # noqa
ConfirmAbandon = "//div[@class='modal-footer']//a[contains(text(), 'Abandon')]"  # noqa
UploadPackage = 'packages__action_upload_package'
ImportBundle = 'packages__action_import_bundle'
CreateEnvironment = ".add_env .btn"
DeployEnvironment = "services__action_deploy_env"
DeleteEnvironment = "//button[contains(@id, 'action_delete')]"
DeployEnvironments = ".btn#environments__action_deploy"
DeployEnvironmentsDisabled = ".btn#environments__action_deploy[disabled]"
DeleteEnvironments = ".btn#environments__action_delete"
DeleteEnvironmentsDisabled = ".btn#environments__action_delete[disabled]"
AbandonEnvironments = ".btn#environments__action_abandon"
AbandonEnvironmentsDisabled = ".btn#environments__action_abandon[disabled]"
ConfirmCreateEnvironment = 'confirm_create_env'
AddComponent = "services__action_AddApplication"
AddCategory = "categories__action_add_category"
DeleteCategory = "//tr[td[contains(text(), '{0}')]]//button[contains(@id, 'action_delete')]"  # noqa
NextBtn = "//tfoot//tr//td//a[contains(@href,'?marker')]"
PrevBtn = "//tfoot//tr//td//a[contains(@href,'prev_marker')]"

# Panel's

Applications = "//*[@id='main_content']/div[2]//a[contains(text(), 'Applications')]"  # noqa
Catalog = Applications + "/following::a[span[contains(text(), 'Catalog')]]"
Manage = Applications + "/following::a[span[contains(text(), 'Manage')]]"
