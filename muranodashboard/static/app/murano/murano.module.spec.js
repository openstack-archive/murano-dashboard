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

  describe('horizon.app.murano', function () {
    it('should be defined', function () {
      expect(angular.module('horizon.app.murano')).toBeDefined();
    });
  });

  describe('murano metadata patcher', function () {
    var metadataService, glance, murano;

    var lastFakeCallArgs = [];
    var fakeResult = 'fakeMeta';

    beforeEach(function () {
      murano = {
        getComponentMeta: fakeMeta,
        editComponentMeta: fakeMeta,
        getEnvironmentMeta: fakeMeta,
        editEnvironmentMeta: fakeMeta
      };
      module('horizon.framework');
      module('horizon.app.core');
      module('horizon.app.murano');
      module(function($provide) {
        $provide.value('horizon.app.core.openstack-service-api.murano', murano);
      });

      function fakeMeta() {
        var i;
        for (i = 0, lastFakeCallArgs = []; i < arguments.length; i++) {
          lastFakeCallArgs.push(arguments[i]);
        }
        return fakeResult;
      }
    });

    beforeEach(inject(function ($injector) {
      metadataService = $injector.get('horizon.app.core.metadata.service');
      glance = $injector.get('horizon.app.core.openstack-service-api.glance');
    }));

    it('should get component metadata', function () {
      var actual = metadataService.getMetadata('muranoapp', 'compId');
      expect(actual).toBe(fakeResult);
      expect(lastFakeCallArgs).toEqual(['compId']);
    });

    it('should get environment metadata', function () {
      var actual = metadataService.getMetadata('muranoenv', 'envId');
      expect(actual).toBe(fakeResult);
      expect(lastFakeCallArgs).toEqual(['envId']);
    });

    it('should edit component metadata', function () {
      metadataService.editMetadata('muranoapp', 'compId',
        {'key1': 10}, ['key2']);
      expect(lastFakeCallArgs).toEqual(['compId', {'key1': 10}, ['key2']]);
    });

    it('should edit environment metadata', function () {
      metadataService.editMetadata('muranoenv', 'envId',
        {'key1': 10}, ['key2']);
      expect(lastFakeCallArgs).toEqual(['envId', {'key1': 10}, ['key2']]);
    });

    it('should get component namespace', function () {
      var params, flag;
      spyOn(glance, 'getNamespaces').and.callFake(function(_params, _flag) {
        params = _params;
        flag = _flag;
      });
      metadataService.getNamespaces('muranoapp', 'something');
      expect(params).toEqual({
        resource_type: 'OS::Murano::Application',
        properties_target: 'something'
      });
      expect(flag).toBe(false);
    });

    it('should get environment namespace', function () {
      var params, flag;
      spyOn(glance, 'getNamespaces').and.callFake(function(_params, _flag) {
        params = _params;
        flag = _flag;
      });
      metadataService.getNamespaces('muranoenv', 'something');
      expect(params).toEqual({
        resource_type: 'OS::Murano::Environment',
        properties_target: 'something'
      });
      expect(flag).toBe(false);
    });

  });

})();
