import functools
import logging
import os
import yaml
import zipfile

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

_ordered_counter = 0

MANIFEST = {'Format': 'MuranoPL/1.0',
            'Type': 'Application',
            'Description': 'MockApp for webUI tests',
            'Author': 'Mirantis, Inc',
            'UI': 'mock_ui.yaml'}


def ordered(func):
    global _ordered_counter
    func.counter = _ordered_counter
    _ordered_counter += 1
    return func


class OrderedMethodMetaclass(type):
    prefix = 'test_'

    def __new__(meta, name, bases, dct):
        test_methods, other = [], []
        for key, value in dct.items():
            if key.startswith(meta.prefix):
                test_methods.append((key, value))
            else:
                other.append((key, value))
        test_methods = sorted(test_methods, key=lambda pair: pair[1].counter)
        prefix_len = len(meta.prefix)
        dct = {}
        for index, (method_name, method) in enumerate(test_methods):
            method_name = '{0}{1:03d}_{2}'.format(
                meta.prefix, index, method_name[prefix_len:])
            delattr(method, 'counter')
            dct[method_name] = screenshot_on_error(method)

        dct.update(dict(other))
        return super(OrderedMethodMetaclass, meta).__new__(
            meta, name, bases, dct)


class ImageException(Exception):
    message = "Image doesn't exist"

    def __init__(self, im_type):
        self._error_string = (self.message + '\nDetails: {0} image is '
                                             'not found,'.format(im_type))

    def __str__(self):
        return self._error_string


def screenshot_on_error(test):
    """Taking screenshot on error

    This decorators will take a screenshot of the browser
    when the test failed or when exception raised on the test.
    Screenshot will be saved as PNG inside screenshots folder.

    """
    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        try:
            log.debug("\nExecuting test: '{0}'".format(test.func_name))
            test(*args, **kwargs)
        except Exception as e:
            log.exception('{0} failed'.format(test.func_name))
            test_object = args[0]
            screenshot_dir = './screenshots'
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            filename = os.path.join(screenshot_dir, test.func_name + '.png')
            test_object.driver.get_screenshot_as_file(filename)
            raise e
    return wrapper


def upload_app_package(client, app_name, data):
    def prepare_manifest(manifest):
        with open(manifest, 'w') as f:
            fqn = 'io.murano.apps.' + app_name
            MANIFEST['FullName'] = fqn
            MANIFEST['Name'] = app_name
            MANIFEST['Classes'] = {fqn: 'mock_muranopl.yaml'}
            f.write(yaml.dump(MANIFEST, default_flow_style=False))

    def compose_package(app_name, package_dir):
        name = app_name + '.zip'
        zip_file = zipfile.ZipFile(name, 'w')
        for root, dirs, files in os.walk(package_dir):
            for f in files:
                zip_file.write(
                    os.path.join(root, f),
                    arcname=os.path.join(os.path.relpath(root, package_dir),
                                         f))
        return name

    package_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'MockApp')
    manifest = os.path.join(package_dir, 'manifest.yaml')
    prepare_manifest(manifest)
    try:
        archive = compose_package(app_name, package_dir)
        package = client.packages.create(data, {app_name: open(archive, 'rb')})
        return package.id
    finally:
        os.remove(archive)
        os.remove(manifest)
