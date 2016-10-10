/**
 * Copyright 2016, Mirantis, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

(function() {
  'use strict';

  /**
   * @ngdoc horizon.app.murano
   * @ng-module
   * @description
   * Provides all of the services and widgets required
   * to support and display the Murano Packages panel.
   */
  angular
    .module('horizon.app.murano', [])
    .config(config);

  config.$inject = [
    '$injector',
    '$provide'
  ];

  function config($injector, $provide) {
    if ($injector.has('horizon.app.core.metadata.service')) {
      $provide.decorator('horizon.app.core.metadata.service', patchMetadata);
    }

    patchMetadata.$inject = [
      '$delegate',
      'horizon.app.core.openstack-service-api.murano',
      'horizon.app.core.openstack-service-api.glance'
    ];
    function patchMetadata($delegate, murano, glance) {
      var origEditMetadata = $delegate.editMetadata;
      var origGetMetadata = $delegate.getMetadata;
      var origGetNamespaces = $delegate.getNamespaces;

      $delegate.editMetadata = editMetadata;
      $delegate.getMetadata = getMetadata;
      $delegate.getNamespaces = getNamespaces;

      return $delegate;

      function getMetadata(resource, id) {
        if (resource === 'muranoapp') {
          return murano.getComponentMeta(id);
        }
        if (resource === 'muranoenv') {
          return murano.getEnvironmentMeta(id);
        }
        return origGetMetadata(resource, id);
      }

      function editMetadata(resource, id, updated, removed) {
        if (resource === 'muranoapp') {
          return murano.editComponentMeta(id, updated, removed);
        }
        if (resource === 'muranoenv') {
          return murano.editEnvironmentMeta(id, updated, removed);
        }
        return origEditMetadata(resource, id, updated, removed);
      }

      function getNamespaces(resource, propertiesTarget) {
        var params;
        if (resource === 'muranoapp') {
          params = {resource_type: 'OS::Murano::Application'};
          if (propertiesTarget) {
            params.properties_target = propertiesTarget;
          }
          return glance.getNamespaces(params, false);
        }
        if (resource === 'muranoenv') {
          params = {resource_type: 'OS::Murano::Environment'};
          if (propertiesTarget) {
            params.properties_target = propertiesTarget;
          }
          return glance.getNamespaces(params, false);
        }

        return origGetNamespaces(resource, propertiesTarget);

      }
    }
  }

})();
