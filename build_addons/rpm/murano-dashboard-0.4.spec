Name:           murano-dashboard
Version:        0.4
Release:        5%{?dist}
Summary:       OpenStack Murano Dashboard
Group:         Applications/Communications
License:        Apache License, Version 2.0
URL:            https://launchpad.net/murano
Source0:        murano-dashboard-0.4.tar.gz
BuildArch:     noarch
Requires:      openstack-dashboard
Requires:      python-eventlet
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-pbr
BuildRequires: python-d2to1
Requires: python-pbr >= 0.5.21, python-pbr < 1.0
Requires: python-anyjson >= 0.3.3
Requires: python-bunch >= 1.0.1
Requires: python-iso8601 >= 0.1.8
Requires: python-six >= 1.4.1
Requires: PyYAML >= 3.10
Requires: python-django-floppyforms >= 1.1
Requires: python-ordereddict >= 1.1
Requires: python-yaql >= 0.2
Requires: python-muranoclient >= 0.4
Requires: murano-metadataclient >= 0.4


%description
Murano Dashboard
Sytem package - murano-dashboard
Python package - murano-dashboard

%prep
%setup -q muranodashboard-%{version}

%build
%{__python} setup.py build

%install

%{__python} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p  %{buildroot}/usr/bin
cp %{_builddir}/murano-dashboard-%{version}/build_addons/rpm/modify-horizon-config.sh %{buildroot}/usr/bin/

%post
/usr/bin/modify-horizon-config.sh install
if [ ! -d "/var/log/murano" ]; then
    mkdir -p /var/log/murano
fi
touch /var/log/murano/murano-dashboard.log
mkdir -p /usr/share/openstack-dashboard/static/floppyforms
mkdir -p /usr/share/openstack-dashboard/static/muranodashboard
chown -R apache:root /usr/share/openstack-dashboard/static/muranodashboard
chown -R apache:root /usr/share/openstack-dashboard/static/floppyforms
chown apache:root /var/log/murano/murano-dashboard.log
su -c "python /usr/share/openstack-dashboard/manage.py collectstatic --noinput | /usr/bin/logger -t murano-dashboard-install " -s /bin/bash apache
service httpd restart

%files
%{python_sitelib}/*
/usr/bin/*

%changelog
* Thu Dec 12 2013 built by Igor Yozhikov <iyozhikov@mirantis.com>
- build number - 5

