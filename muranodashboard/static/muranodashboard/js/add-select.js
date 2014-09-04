
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
    var CUSTOM_CTRL_CLS = 'murano-add-select';
    function bind_add_item_handlers(el) {
        var $selects = $(el).find('select[data-add-item-url]');
        $selects.each(function () {
            var $this = $(this),
                urls = $.parseJSON($this.attr("data-add-item-url"));
            if ( urls[0].length ) {
                // if instead of single url there is an Application name + url
                // then it was created by custom FQN reference and not by vanilla horizon
                $('div.dynamic-select a[class*=btn]').filter(function() {
                    return !$(this).hasClass(CUSTOM_CTRL_CLS);
                }).remove();
                if ( urls.length == 1 ) {
                    $button = $("<a href='" + urls[0][1] + "' " +
                        "data-add-to-field='" + $this.attr("id") + "' " +
                        "class='btn ajax-add ajax-modal btn-default " +
                        CUSTOM_CTRL_CLS + "'>+</a>");
                } else {
                    $button = $("<div class='dynamic-select' id='" +
                        $this.attr("id") + "-button' ><button type='button' class='btn " +
                        "btn-default dropdown-toggle " + CUSTOM_CTRL_CLS + "' " +
                        "data-toggle='dropdown'>+</button>" +
                        "<ul class='dropdown-menu' role='menu'></ul></div>");

                    var $choices = $button.find('ul');
                    $selects.css('margin-bottom', 22);
                    $button.css('display', 'inline-block');
                    $(urls).each(function(i, url) {
                        $choices.append($("<li><a href='" + url[1] + "' data-add-to-field='" +
                            $this.attr("id") + "' class='ajax-add ajax-modal'>" + url[0] +
                      "</a></li>"));
                    });
                }
                $this.after($button);
            }
        });
    }
    if ( window.murano === undefined )
        window.murano = {};

    if ( !murano.bind_add_item_handlers ) {
        murano.bind_add_item_handlers = true;
        horizon.modals.addModalInitFunction(bind_add_item_handlers);
    }
});
