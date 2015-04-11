import os

PackageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          'MockApp')
Manifest = os.path.join(PackageDir, 'manifest.yaml')

CategorySelector = "//a[contains(text(), '{0}')][contains(@class, 'dropdown-toggle')]"  # noqa
App = "//div[contains(@class, 'app-list')]//h4[contains(text(), '{0}')]"
MockAppDescr = "//div[h4[contains(text(), 'MockApp')]]/p"
AppPackageDefinitions = "//tr[@data-display='{0}']"
TagInDetails = "//div[contains(@class, 'app-meta')]//ul//li[strong[contains(text(), 'Tags')]]"  # noqa
TestImage = "//tr[td[contains(text(), '{0}')]]"
DeleteImageMeta = TestImage + "//td//button[contains(text(), 'Delete Metadata')]"  # noqa
ImageMeta = "//dl[dt[contains(text(), 'murano_image_info')]]/dd"
More = "//tr[contains(@id, '{0}__row__{1}')]//a[contains(@class, dropdown-toggle) and @href='#']"  # noqa
Status = "//td[contains(text(), '{0}')]"
CellStatus = "//td[contains(@class, 'status_{0}')]"
ErrorMessage = '//span[contains(@class, "alert-danger") and contains(text(), "{0}")]'  # noqa
DatabaseCategory = "select[name='add_category-categories'] > option[value='Databases']"  # noqa
Action = '//a[contains(@class, "murano_action") and contains(text(), "testAction")]'  # noqa

# Buttons
ButtonSubmit = ".//*[@name='wizard_goto_step'][2]"
InputSubmit = "//input[@type='submit']"
ConfirmDeletion = "//div[@class='modal-footer']//a[contains(text(), 'Delete')]"  # noqa
UploadPackage = 'packages__action_upload_package'
CreateEnvironment = ".add_env .btn"
ConfirmCreateEnvironment = 'confirm_create_env'
AddComponent = "services__action_AddApplication"
AddCategory = "categories__action_add_category"
DeleteCategory = "//tr[td[contains(text(), '{0}')]]//button[contains(@id, 'action_delete')]"  # noqa

# Panel's

Murano = "//*[@id='main_content']/div[2]//dt[contains(text(), 'Murano')]"
Application_Catalog = Murano + "/following::h4[1]"
Manage = Murano + "/following::h4[2]"
