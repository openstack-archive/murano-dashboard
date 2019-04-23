========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/murano-dashboard.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

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

* ``muranodashboard/local/enabled/*.py`` into
  ``horizon/openstack_dashboard/local/enabled/``
* ``muranodashboard/local/local_settings.d/_50_murano.py`` into
  ``horizon/openstack_dashboard/local/local_settings.d/_50_murano.py``
* ``muranodashboard/conf/murano_policy.json`` into
  ``horizon/openstack_dashboard/conf/``

re-compress static assets and restart Horizon web-server as usual.

Project Resources
-----------------

* `Murano at Launchpad <https://launchpad.net/murano>`_
* `Wiki <https://wiki.openstack.org/wiki/Murano>`_
* `Code Review <https://review.opendev.org/>`_
* `Sources <https://wiki.openstack.org/wiki/Murano/SourceCode>`_
* `Documentation <https://docs.openstack.org/developer/murano/>`_
