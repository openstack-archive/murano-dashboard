/*    Copyright (c) 2015 Mirantis, Inc.

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
*/

$(function() {
  "use strict";

  horizon.modals.addModalInitFunction(muranoUploadBundle);

  function muranoUploadBundle(modal) {
    var uploadForm = $(modal).find('#import_bundle');
    var importType = uploadForm.find('[name=upload-import_type]');

    uploadForm.find('input[name=upload-url]').closest('.form-group').addClass('required');
    uploadForm.find('input[name=upload-name]').closest('.form-group').addClass('required');

    importType.change(function() {
      var uploadType = $(this).val();
      if (uploadType === 'by_name') {
        uploadForm.find('.description-by_name').show();
        uploadForm.find('.description-by_url').hide();
      } else if (uploadType === 'by_url') {
        uploadForm.find('.description-by_name').hide();
        uploadForm.find('.description-by_url').show();
      }
    });
    importType.change();
  }

  muranoUploadBundle($('#import_bundle').parent());
});
