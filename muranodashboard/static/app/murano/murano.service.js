/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(function () {
  'use strict';

  angular
    .module('horizon.app.core.openstack-service-api')
    .factory('horizon.app.core.openstack-service-api.murano', muranoAPI);

  muranoAPI.$inject = [
    'horizon.framework.util.http.service',
    'horizon.framework.widgets.toast.service'
  ];

  /**
   * @ngdoc service
   * @name horizon.app.core.openstack-service-api.murano
   * @description Provides direct pass through to Murano with NO abstraction.
   */

  function muranoAPI(apiService, toastService) {
    var service = {
      getPackages: getPackages,
      getComponentMeta: getComponentMeta,
      editComponentMeta: editComponentMeta,
      getEnvironmentMeta: getEnvironmentMeta,
      editEnvironmentMeta: editEnvironmentMeta
    };

    return service;

    /**
     * @name horizon.app.core.openstack-service-api.murano.getPackages
     * @description
     * Get a list of packages.
     *
     * The listing result is an object with property "packages". Each item is
     * an packages.
     *
     * @param {Object} params
     * Query parameters. Optional.
     *
     * @param {boolean} params.paginate
     * True to paginate automatically.
     *
     * @param {string} params.marker
     * Specifies the image of the last-seen image.
     *
     * The typical pattern of limit and marker is to make an
     * initial limited request and then to use the last
     * image from the response as the marker parameter
     * in a subsequent limited request. With paginate, limit
     * is automatically set.
     *
     * @param {string} params.sort_dir
     * The sort direction ('asc' or 'desc').
     */

    function getPackages(params) {
      var config = params ? { "params" : params} : {};
      return apiService.get('/api/app-catalog/packages/', config)
        .catch(function onError() {
          toastService.add('error', gettext('Unable to retrieve the packages.'));
        });
    }

    /**
    * @name horizon.app.core.openstack-service-api.murano.getComponentMeta
    * @description
    * Get metadata attributes associated with a given component
    *
    * @param {Object} target
    * The object identifying the target component
    *
    * @param {string} target.environment
    * The identifier of the environment the component belongs to
    *
    * @param {string} target.component
    * The identifier of the component within the environment
    *
    * @param {string} target.session
    * The identifier of the configuration session for which the data should be
    * fetched
    *
    * @returns {Object} The metadata object
    */
    function getComponentMeta(target) {
      var params = { params: { session: target.session} };
      var url = '/api/app-catalog/environments/' + target.environment +
          '/components/' + target.component + '/metadata/';
      return apiService.get(url, params)
          .catch(function onError() {
            toastService.add('error', gettext('Unable to retrieve component metadata.'));
          });
    }

    /**
    * @name horizon.app.core.openstack-service-api.murano.editComponentMetadata
    * @description
    * Update metadata attributes associated with a given component
    *
    * @param {Object} target
    * The object identifying the target component
    *
    * @param {string} target.environment
    * The identifier of the environment the component belongs to
    *
    * @param {string} target.component
    * The identifier of the component within the environment
    *
    * @param {string} target.session
    * The identifier of the configuration session for which the data should be
    * updated
    *
    * @param {object} updated New metadata definitions.
    *
    * @param {[]} removed Names of removed metadata definitions.
    *
    * @returns {Object} The result of the API call
    */
    function editComponentMeta(target, updated, removed) {
      var params = { params: { session: target.session} };
      var url = '/api/app-catalog/environments/' + target.environment +
          '/components/' + target.component + '/metadata/';
      return apiService.post(
          url, { updated: updated, removed: removed}, params)
          .catch(function onError() {
            toastService.add('error', gettext('Unable to edit component metadata.'));
          });
    }

    /**
    * @name horizon.app.core.openstack-service-api.murano.getEnvironmentMeta
    * @description
    * Get metadata attributes associated with a given environment
    *
    * @param {Object} target
    * The object identifying the target environment
    *
    * @param {string} target.environment
    * The identifier of the target environment
    *
    * @param {string} target.session
    * The identifier of the configuration session for which the data should be
    * fetched
    *
    * @returns {Object} The metadata object
    */
    function getEnvironmentMeta(target) {
      var params = { params: { session: target.session} };
      var url = '/api/app-catalog/environments/' + target.environment +
          '/metadata/';
      return apiService.get(url, params)
          .catch(function onError() {
            toastService.add('error', gettext('Unable to retrieve environment metadata.'));
          });
    }

    /**
    * @name horizon.app.core.openstack-service-api.murano.editEnvironmentMeta
    * @description
    * Update metadata attributes associated with a given environment
    *
    * @param {Object} target
    * The object identifying the target environment
    *
    * @param {string} target.environment
    * The identifier of the environment the component belongs to
    *
    * @param {string} target.session
    * The identifier of the configuration session for which the data should be
    * updated
    *
    * @param {object} updated New metadata definitions.
    *
    * @param {[]} removed Names of removed metadata definitions.
    *
    * @returns {Object} The result of the API call
    */
    function editEnvironmentMeta(target, updated, removed) {
      var params = { params: { session: target.session} };
      var url = '/api/app-catalog/environments/' + target.environment +
          '/metadata/';
      return apiService.post(
          url, { updated: updated, removed: removed}, params)
          .catch(function onError() {
            toastService.add('error', gettext('Unable to edit environment metadata.'));
          });
    }

  }
})();
