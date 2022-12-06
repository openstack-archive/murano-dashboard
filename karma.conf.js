/*
 * Copyright 2015 IBM Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use strict';

var fs = require('fs');
var path = require('path');

module.exports = function (config) {
  // This tox venv is setup in the post-install npm step
  var toxPath = path.resolve('./.tox/npm');
  if (!toxPath) {
      console.error('xStatic libraries not found, please run `tox -e npm`');
      process.exit(1);
    }
    toxPath += '/lib/';
    toxPath += fs.readdirSync(toxPath).find(function(directory) {
      return directory.indexOf('python') === 0;
    });
    toxPath += '/site-packages/';
  var xstaticPath = toxPath + 'xstatic/pkg/';

  config.set({
    preprocessors: {
      // Used to collect templates for preprocessing.
      // NOTE: the templates must also be listed in the files section below.
      './static/**/*.html': ['ng-html2js']
    },

    // Sets up module to process templates.
    ngHtml2JsPreprocessor: {
      prependPrefix: '/',
      moduleName: 'templates'
    },

    basePath: './',

    // Contains both source and test files.
    files: [
      /*
       * shim, partly stolen from /i18n/js/horizon/
       * Contains expected items not provided elsewhere (dynamically by
       * Django or via jasmine template.
       */
      './test-shim.js',

      // from jasmine.html
      xstaticPath + 'jquery/data/jquery.js',
      xstaticPath + 'angular/data/angular.js',
      xstaticPath + 'angular/data/angular-route.js',
      xstaticPath + 'angular/data/angular-mocks.js',
      xstaticPath + 'angular/data/angular-cookies.js',
      xstaticPath + 'angular_bootstrap/data/angular-bootstrap.js',
      xstaticPath + 'angular_gettext/data/angular-gettext.js',
      xstaticPath + 'angular_fileupload/data/ng-file-upload-all.js',
      xstaticPath + 'angular/data/angular-sanitize.js',
      xstaticPath + 'd3/data/d3.js',
      xstaticPath + 'rickshaw/data/rickshaw.js',
      xstaticPath + 'angular_smart_table/data/smart-table.js',
      xstaticPath + 'angular_lrdragndrop/data/lrdragndrop.js',
      xstaticPath + 'spin/data/spin.js',
      xstaticPath + 'spin/data/spin.jquery.js',
      xstaticPath + 'tv4/data/tv4.js',
      xstaticPath + 'objectpath/data/ObjectPath.js',
      xstaticPath + 'angular_schema_form/data/schema-form.js',

      // TODO: These should be mocked.
      toxPath + '/horizon/static/horizon/js/horizon.js',

      /**
       * Include framework source code from horizon that we need.
       * Otherwise, karma will not be able to find them when testing.
       * These files should be mocked in the foreseeable future.
       */
      toxPath + 'horizon/static/framework/**/*.module.js',
      toxPath + 'horizon/static/framework/**/!(*.spec|*.mock).js',
      toxPath + 'openstack_dashboard/static/**/*.module.js',
      toxPath + 'openstack_dashboard/static/**/!(*.spec|*.mock).js',
      toxPath + 'openstack_dashboard/dashboards/**/static/**/*.module.js',
      toxPath + 'openstack_dashboard/dashboards/**/static/**/!(*.spec|*.mock).js',

      /**
       * First, list all the files that defines application's angular modules.
       * Those files have extension of `.module.js`. The order among them is
       * not significant.
       */
      './muranodashboard/static/**/*.module.js',

      /**
       * Followed by other JavaScript files that defines angular providers
       * on the modules defined in files listed above. And they are not mock
       * files or spec files defined below. The order among them is not
       * significant.
       */
      './muranodashboard/static/app/**/!(*.spec|*.mock).js',

      /**
       * Then, list files for mocks with `mock.js` extension. The order
       * among them should not be significant.
       */
      toxPath + 'openstack_dashboard/static/**/*.mock.js',

      /**
       * Finally, list files for spec with `spec.js` extension. The order
       * among them should not be significant.
       */
      './muranodashboard/static/app/**/*.spec.js',

      /**
       * Angular external templates
       */
      './muranodashboard/static/app/**/*.html'
    ],

    autoWatch: true,

    frameworks: ['jasmine'],

    browsers: ['Firefox'],

    phantomjsLauncher: {
      // Have phantomjs exit if a ResourceError is encountered
      // (useful if karma exits without killing phantom)
      exitOnResourceError: true
    },

    reporters: ['progress'],

    plugins: [
      'karma-firefox-launcher',
      'karma-jasmine',
      'karma-ng-html2js-preprocessor'
    ]

  });
};
