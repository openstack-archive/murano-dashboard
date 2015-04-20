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
    var upload_form = $('#import_bundle');
    var import_type = upload_form.find('[name=upload-import_type]');

    upload_form.find('input[name=upload-url]').closest('.form-group').addClass('required');
    upload_form.find('input[name=upload-name]').closest('.form-group').addClass('required');

    import_type.change(function(){
        var upload_type = $(this).val();
        if (upload_type === 'by_name') {
            upload_form.find('input[name=upload-url]').closest('.form-group').hide();
            upload_form.find('input[name=upload-name]').closest('.form-group').show();
            upload_form.find('.description-by_name').show();
            upload_form.find('.description-by_url').hide();
        } else if (upload_type === 'by_url') {
            upload_form.find('input[name=upload-url]').closest('.form-group').show();
            upload_form.find('input[name=upload-name]').closest('.form-group').hide();
            upload_form.find('.description-by_name').hide();
            upload_form.find('.description-by_url').show();
        }
    });
    import_type.change();
});
