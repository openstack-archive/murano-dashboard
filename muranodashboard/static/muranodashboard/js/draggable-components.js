$(function() {
  horizon.tabs.addTabLoadFunction(initServicesTab);
  initServicesTab($('.tab-content .tab-pane.active'));
  function initServicesTab($tab) {
    var $dropArea = $tab.find('.drop_component'),
      draggedAppUrl = null,
      firstDropTarget = null;

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
        })
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
    function subdivide(numOfItems) {
      var chunks = [],
        seq = this,
        head = seq.slice(0, numOfItems),
        tail = seq.slice(numOfItems);
      while (tail.length) {
        chunks.push(head);
        head = tail.slice(0, numOfItems);
        tail = tail.slice(numOfItems);
      }
      chunks.push(head);
      return chunks;
    }

    Array.prototype.subdivide = subdivide;
    var $carouselInner = $tab.find('.carousel-inner'),
      $carousel = $('#apps_carousel'),
      $filter = $('#envAppsFilter').find('input'),
      category = ALL_CATEGORY = 'All',
      filterValue = '',
      ENTER_KEYCODE = 13;
    var tileTemplate = Hogan.compile($('#app_tile_small').html()),
      environmentId = $('#environmentId').val();

    function fillCarousel(apps) {
      if (apps.length) {
        apps.subdivide(6).forEach(function (chunk, index) {
          var $item = $('<div class="item"></div>'),
            $row = $('<div class="row"></div>');
          if (index == 0) {
            $item.addClass('active');
          }
          $item.appendTo($row);
          chunk.forEach(function (pkg) {
            var html = tileTemplate.render({
              app_name: pkg.name,
              environment_id: environmentId,
              app_id: pkg.id
            });
            $(html).appendTo($item);
          });
          $item.appendTo($carouselInner);
        });
        $('div.carousel-control').removeClass('item')
        $carousel.show();
        bindAppTileHandlers();
      } else {
        $carousel.hide();
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
        var filterRegexp = new RegExp(filterValue, 'i'),
          filterRegexpExact = new RegExp('\\b' + filterValue + '\\b', 'i');
        fillCarousel(packages.filter(function (pkg) {
          var categorySatisfied = true, filterSatisfied = true;
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
        }))
      }
    }

    // dynamic carousel refilling on category change
    $('#envAppsCategory').on('click', 'a', function (env) {
      category = $(this).text();
      $('#envAppsCategoryName').text(category);
      refillCarousel();
      env.preventDefault();
    });
    // dynamic carousel refilling on search box non-empty submission
    $filter.keypress(function (ev) {
      if (ev.which == ENTER_KEYCODE) {
        filterValue = $filter.val();
        refillCarousel();
        ev.preventDefault();
      }
    });

    function hideSpinner() {
      horizon.modals.spinner.modal('hide');
    }

    function handleError() {
      hideSpinner();
      horizon.alert('error', 'Unable to run action.');
    }

    bindActionHandlers($tab);
    var $table = $('table.datatable');
    $table.on('update', function () {
      bindActionHandlers($table);
    });

    function bindActionHandlers($parent) {
      $parent.find('.murano_action').off('click').on('click', function(event) {
        var $this = $(this),
          $form = $this.closest('.table_wrapper > form'),
          startUrl = $this.attr('href'),
          resultUrl = null,
          ERRDATA = 'error',
          data = null;

          horizon.modals.modal_spinner(gettext("Waiting for a result"));
          button = '<div class="modal-close"' +
            '><button class="btn btn-sm btn-danger" data-placement="right"' +
            ' data-original-title="Action result won\'t be available">Stop Waiting</button></div>'
          var modal_content = horizon.modals.spinner.find(".modal-content");
          modal_content.append(button)
            $('.modal-close button').tooltip();
          $('.modal-close button').on("click", function () {
            window.clearInterval(intervalId);
            document.location = $form.attr('action');
          });
        if (startUrl) {
          $.ajax({
            method: 'POST',
            url: startUrl,
            data: $form.serialize(),
            async: false,
            success: function (data) {
              resultUrl = data && data.url;
            },
            error: handleError
          });
          if ( resultUrl ) {
            function doRequest(url) {
              var _data;
              $.ajax({
                method: 'GET',
                url: url,
                async: false,
                error: function () {
                  handleError();
                  _data = ERRDATA;
                },
                success: function (newData) {
                  _data = newData;
                }
              });
              return _data;
            }

            var intervalId = window.setInterval(function () {
              // it's better to avoid placing the whole downloadable content
              // into JS memory in case of downloading very large files
              data = doRequest(resultUrl + 'poll');
              if (!$.isEmptyObject(data)) {
                window.clearInterval(intervalId);
                if (data !== ERRDATA) {
                  if (data.isException) {
                    handleError();
                    document.location = resultUrl;
                  }
                  else if (data.result !== undefined && data.result === null) {
                    hideSpinner();
                    document.location = $form.attr('action');
                  }
                  else {
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