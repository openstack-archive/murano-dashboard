import os

PackageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          'MockApp')
Manifest = os.path.join(PackageDir, 'manifest.yaml')

More = "/html/body/div/div[2]/div[3]/form/table/tbody/tr/td[4]/div/a[2]"
CategorySelector = "//a[contains(text(), '{0}')][contains(@class, 'dropdown-toggle')]"  # noqa
App = "//div[contains(@class, 'app-list')]//h4[contains(text(), '{0}')]"
MockAppDescr = "//div[h4[contains(text(), 'MockApp')]]/p"
AppPackageDefinitions = "//tr[@data-display='{0}']"
TagInDetails = "//div[contains(@class, 'app-meta')]//ul//li[strong[contains(text(), 'Tags')]]"  # noqa
TestImage = "//tr[td[contains(text(), '{0}')]]"
DeleteImageMeta = TestImage + "//td//button[contains(text(), 'Delete Metadata')]"  # noqa
ImageMeta = "//dl[dt[contains(text(), 'murano_image_info')]]/dd"
More = "//tr[@id='murano__row__{0}']//a[@data-toggle='dropdown']"
Status = "//td[contains(text(), '{0}')]"
CellStatus = "//td[contains(@class, 'status_{0}')]"
ErrorMessage = '//span[contains(@class, "alert-danger") and contains(text(), "{0}")]'  # noqa
DatabaseCategory = "select[name='add_category-categories'] > option[value='Databases']"  # noqa

# Buttons
ButtonSubmit = ".//*[@name='wizard_goto_step'][2]"
InputSubmit = "//input[@type='submit']"
ConfirmDeletion = "//div[@class='modal-footer']//a[contains(text(), 'Delete')]"  # noqa
UploadPackage = 'packages__action_upload_package'
CreateEnvironment = 'murano__action_CreateEnvironment'
AddComponent = "services__action_AddApplication"

# Panel's

Murano = "//*[@id='main_content']/div[2]//dt[contains(text(), 'Murano')]"
Application_Catalog = Murano + "/following::h4[1]"
Manage = Murano + "/following::h4[2]"
