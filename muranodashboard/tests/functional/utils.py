import logging
import os
import yaml
import zipfile

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())


MANIFEST = {'Format': 'MuranoPL/1.0',
            'Type': 'Application',
            'Description': 'MockApp for webUI tests',
            'Author': 'Mirantis, Inc',
            'UI': 'mock_ui.yaml'}


class ImageException(Exception):
    message = "Image doesn't exist"

    def __init__(self, im_type):
        self._error_string = (self.message + '\nDetails: {0} image is '
                                             'not found,'.format(im_type))

    def __str__(self):
        return self._error_string


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
