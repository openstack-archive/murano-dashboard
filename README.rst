Murano
======

Murano Project introduces an application catalog, which allows application
developers and cloud administrators to publish various cloud-ready
applications in a browsable categorised catalog. Cloud users,
including inexperienced ones, can then use the catalog to
compose reliable application environments with the push of a button.

Murano Dashboard
----------------
Murano Dashboard is an extension for OpenStack Dashboard that provides a UI for
Murano. With murano-dashboard, a user is able to easily manage and control
an application catalog, running applications and created environments alongside
with all other OpenStack resources.

For developer purposes, please symlink the following OpenStack Dashboard plugin
files:
* muranodashboard/local/enabled/_50_murano.py into
  horizon/openstack_dashboard/local/enabled/_50_murano.py
* muranodashboard/local/local_settings.d/_50_murano.py into
  horizon/openstack_dashboard/local/local_settings.d/_50_murano.py

re-compress static assets and restart Horizon web-server as usual.

Project Resources
-----------------

* `Murano at Launchpad <http://launchpad.net/murano>`_
* `Wiki <https://wiki.openstack.org/wiki/Murano>`_
* `Code Review <https://review.openstack.org/>`_
* `Sources <https://wiki.openstack.org/wiki/Murano/SourceCode>`_
* `Documentation <http://docs.openstack.org/developer/murano/>`_
