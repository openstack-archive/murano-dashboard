
/*    Copyright (c) 2014 Mirantis, Inc.

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

    if ( window.murano === undefined )
        window.murano = {};

    if ( !murano.bind_add_item_handlers ) {
        murano.bind_add_item_handlers = true;
        horizon.modals.addModalInitFunction(function (el) {
        var $selects = $(el).find('select[data-add-item-url]');
        $selects.each(function () {
            var $this = $(this), urls, link, $choices;
            try {
              urls = $.parseJSON($this.attr("data-add-item-url"));
            } catch(err) {}
            if ( urls && urls[0].length ) {
                if ( urls.length == 1 ) {
                  $this.next().find('a').attr('href', urls[0][1]);
                } else {
                  link = $this.next().find('a').toggleClass('dropdown-toggle');
                  link.attr('href', '#');
                  link.attr('data-toggle', 'dropdown');
                  link.removeClass('ajax-add ajax-modal')
                  $choices = $("<ul class='dropdown-menu murano-dropdown-menu' role='menu'></ul>");
                    $(urls).each(function(i, url) {
                        $choices.append($("<li><a href='" + url[1] + "' data-add-to-field='" +
                            $this.attr("id") + "' class='ajax-add ajax-modal'>" + url[0] +
                      "</a></li>"));
                    });
                  $this.next('span').append($choices);
                }
            }
        });
    });
    }
});
