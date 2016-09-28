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
(function () {
  'use strict';

  describe('Murano API', function () {
    var testCall, service;
    var apiService = {};
    var toastService = {};

    beforeEach(
      module('horizon.mock.openstack-service-api',
        function($provide, initServices) {
          testCall = initServices($provide, apiService, toastService);
        })
    );

    beforeEach(module('horizon.app.core.openstack-service-api'));

    beforeEach(inject([
      'horizon.app.core.openstack-service-api.murano',
      function(muranoAPI) {
        service = muranoAPI;
      }]));

    it('defines the service', function () {
      expect(service).toBeDefined();
    });

    var tests = [
      {
        func: 'getPackages',
        method: 'get',
        path: '/api/app-catalog/packages/',
        data: {params: 'config'},
        error: 'Unable to retrieve the packages.',
        testInput: [ 'config' ]
      }, {
        func: 'getComponentMeta',
        method: 'get',
        path: '/api/app-catalog/environments/1/components/2/metadata/',
        data: {params: {session: 'sessionId'}},
        error: 'Unable to retrieve component metadata.',
        testInput: [{session: 'sessionId', environment: '1', component: '2'}]
      }, {
        func: 'editComponentMeta',
        method: 'post',
        path: '/api/app-catalog/environments/1/components/2/metadata/',
        call_args: [
          '/api/app-catalog/environments/1/components/2/metadata/',
          {updated: {'key1': 10}, removed: ['key2']},
          {params: {session: 'sessionId'}}
        ],
        error: 'Unable to edit component metadata.',
        testInput: [
          {session: 'sessionId', environment: '1', component: '2'},
          {'key1': 10},
          ['key2']
        ]
      }, {
        func: 'getEnvironmentMeta',
        method: 'get',
        path: '/api/app-catalog/environments/1/metadata/',
        data: {params: {session: 'sessionId'}},
        error: 'Unable to retrieve environment metadata.',
        testInput: [{session: 'sessionId', environment: '1'}]
      }, {
        func: 'editEnvironmentMeta',
        method: 'post',
        path: '/api/app-catalog/environments/1/metadata/',
        call_args: [
          '/api/app-catalog/environments/1/metadata/',
          {updated: {'key1': 10}, removed: ['key2']},
          {params: {session: 'sessionId'}}
        ],
        error: 'Unable to edit environment metadata.',
        testInput: [
          {session: 'sessionId', environment: '1'},
          {'key1': 10},
          ['key2']
        ]
      }
    ];

    // Iterate through the defined tests and apply as Jasmine specs.
    angular.forEach(tests, function(params) {
      it('defines the ' + params.func + ' call properly', function () {
        var callParams = [apiService, service, toastService, params];
        testCall.apply(this, callParams);
      });
    });

  });

})();
