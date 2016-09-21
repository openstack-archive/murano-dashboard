/*    Copyright (c) 2013 Mirantis, Inc.

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

  horizon.tabs.addTabLoadFunction(initServicesTab);
  initServicesTab($('.tab-content .tab-pane.active'));

  function initServicesTab($tab) {
    var $dropArea = $tab.find('.drop_component');
    var draggedAppUrl = null;
    var firstDropTarget = null;

    function bindAppTileHandlers() {
      $('.draggable_app').each(function () {
        $(this).on('dragstart', function (ev) {
          ev.originalEvent.dataTransfer.effectAllowed = 'copy';
          // we have to use an external variable for this since
          // storing data in dataTransfer object works only for FF
          draggedAppUrl = $(this).find('input[type="hidden"]').val();
          // set it so the DND works in FF
          ev.originalEvent.dataTransfer.setData('text/uri-list', draggedAppUrl);
        }).on('dragend', function () {
          $dropArea.removeClass('over');
        });
      });
    }

    $dropArea.on('dragover', function (ev) {
      ev.preventDefault();
      ev.originalEvent.dataTransfer.dropEffect = 'copy';
      return false;
    }).on('dragenter', function (ev) {
      $dropArea.addClass('over');
      firstDropTarget = ev.target;
    }).on('dragleave', function (ev) {
      if (firstDropTarget === ev.target) {
        $dropArea.removeClass('over');
      }
    }).on('drop', function (ev) {
      ev.preventDefault();
      horizon.modals.loadModal(draggedAppUrl);
      return false;
    });
    var packages = $.parseJSON($('#apps_carousel_contents').val());
    function subdivide(array, numOfItems) {
      var chunks = [];
      var seq = array;
      var head = seq.slice(0, numOfItems);
      var tail = seq.slice(numOfItems);
      while (tail.length) {
        chunks.push(head);
        head = tail.slice(0, numOfItems);
        tail = tail.slice(numOfItems);
      }
      chunks.push(head);
      return chunks;
    }

    var $carouselInner = $tab.find('.carousel-inner');
    var $carousel = $('#apps_carousel');
    var $filter = $('#envAppsFilter').find('input');
    var $noAppMsg = $('#no_apps_found_message');
    var category = 'All';
    var ALL_CATEGORY = 'All';
    var filterValue = '';
    var ENTER_KEYCODE = 13;
    var tileTemplate,
      environmentId;

    var $appTitleSmall = $('#app_tile_small');
    if ($appTitleSmall.length > 0) {
      tileTemplate = Hogan.compile($appTitleSmall.html());
    }
    if ($('#environmentId').length > 0) {
      environmentId = $('#environmentId').val();
    }

    function fillCarousel(apps) {
      var i = apps.length;
      while (i--) {
        if (TENANT_ID !== apps[i].owner_id && apps[i].is_public === false) {
          apps.splice(i, 1);
        }
      }
      if (apps.length) {
        $dropArea.show();
        $noAppMsg.hide();
        if ($carousel.css('display') === 'none') {
          $carousel.show();
        }
        subdivide(apps, 6).forEach(function (chunk, index) {
          var $item = $('<div class="item"></div>');
          var $row = $('<div class="row"></div>');
          if (index === 0) {
            $item.addClass('active');
          }
          $item.appendTo($row);
          chunk.forEach(function (pkg) {
            var html = tileTemplate.render({
              app_name: pkg.name,
              environment_id: environmentId,
              app_id: pkg.id
            });
            // tenant_id is obtained from corresponding Django template
            if (TENANT_ID === pkg.owner_id) {
              html = $(html).find('img.ribbon').remove().end();
            }
            $(html).appendTo($item);
          });
          $item.appendTo($carouselInner);
        });
        $('div.carousel-control').removeClass('item');
        bindAppTileHandlers();
      } else {
        if ($('#no_apps_in_catalog_message').length === 0) {
          $noAppMsg.show();
        }
        $carousel.hide();
        $dropArea.hide();

      }
    }

    if (packages) {
      fillCarousel(packages);
    }
    $carousel.carousel({interval: false});
    function refillCarousel() {
      $carouselInner.empty();
      if (category === ALL_CATEGORY && filterValue === '') {
        fillCarousel(packages);
      } else {
        var filterRegexp = new RegExp(filterValue, 'i');
        var filterRegexpExact = new RegExp('\\b' + filterValue + '\\b', 'i');
        fillCarousel(packages.filter(function (pkg) {
          var categorySatisfied = true;
          var filterSatisfied = true;
          if (category !== ALL_CATEGORY) {
            categorySatisfied = pkg.categories.indexOf(category) > -1;
          }
          if (filterValue !== '') {
            filterSatisfied = pkg.name.match(filterRegexp);
            filterSatisfied = filterSatisfied || pkg.description.match(filterRegexp);
            filterSatisfied = filterSatisfied || pkg.tags.some(function (tag) {
              return tag.match(filterRegexpExact);
            });
          }
          return categorySatisfied && filterSatisfied;
        }));
      }
    }

    // dynamic carousel refilling on category change
    $('#envAppsCategory').on('click', 'a', function (env) {
      var $category = $(this);
      category = $category.attr('data-category-name');
      $('#envAppsCategoryName').text($category.text());
      refillCarousel();
      env.preventDefault();
    });
    // dynamic carousel refilling on search box non-empty submission
    $filter.keypress(function (ev) {
      if (ev.which === ENTER_KEYCODE) {
        filterValue = $filter.val();
        refillCarousel();
        ev.preventDefault();
      }
    });
    // show full name on text overflow
    $('.may_overflow').each(function() {
      $(this).bind('mouseenter', function () {
        var $this = $(this);

        if (this.offsetWidth < this.scrollWidth && !$this.attr('title')) {
          $this.attr('title', $this.text());
        }
      });
    });

    // actions
    function hideSpinner() {
      horizon.modals.spinner.modal('hide');
    }

    function handleError() {
      hideSpinner();
      horizon.alert('error', gettext('Unable to run action.'));
    }

    bindActionHandlers($tab);
    var $table = $('table.datatable');
    $table.on('update', function () {
      bindActionHandlers($table);
    });

    function bindActionHandlers($parent) {
      $parent.find('.murano_action').off('click').on('click', function(event) {
        var $this = $(this);
        var $form = $this.closest('.table_wrapper > form');
        var startUrl = $this.attr('href');
        var resultUrl = null;
        var ERRDATA = 'error';
        var data = null;
        function doRequest(url) {
          var requestData;
          $.ajax({
            type: 'GET',
            url: url,
            async: false,
            error: function () {
              handleError();
              requestData = ERRDATA;
            },
            success: function (newData) {
              requestData = newData;
            }
          });
          return requestData;
        }

        horizon.modals.modal_spinner(gettext("Waiting for a result"));
        var button = '<div class="modal-close"' +
          '><button class="btn btn-sm btn-danger" data-placement="right"' +
          ' data-original-title="Action result won\'t be available">Stop Waiting</button></div>';
        var modalContent = horizon.modals.spinner.find(".modal-content");
        var intervalId;

        modalContent.append(button);
        $('.modal-close button').tooltip();
        $('.modal-close button').on("click", function () {
          window.clearInterval(intervalId);
          document.location = $form.attr('action');
        });
        if (startUrl) {
          $.ajax({
            type: 'POST',
            url: startUrl,
            data: $form.serialize(),
            async: false,
            success: function (successData) {
              resultUrl = successData && successData.url;
            },
            error: handleError
          });
          if (resultUrl) {

            intervalId = window.setInterval(function () {
              // it's better to avoid placing the whole downloadable content
              // into JS memory in case of downloading very large files
              data = doRequest(resultUrl + 'poll');
              if (!$.isEmptyObject(data)) {
                window.clearInterval(intervalId);
                if (data !== ERRDATA) {
                  if (data.isException) {
                    handleError();
                    document.location = resultUrl;
                  } else if (typeof data.result !== "undefined" && data.result === null) {
                    hideSpinner();
                    document.location = $form.attr('action');
                  } else {
                    hideSpinner();
                    document.location = resultUrl;
                  }
                }
              }
            }, 1000);
          }
        }
        event.preventDefault();
      });
    }
  }
});
