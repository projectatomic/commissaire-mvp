%if 0%{?rhel} != 0 && 0%{?rhel} <= 7
%bcond_with tests
%global py2_build %{__python} setup.py build '--executable=/usr/bin/python2 -s'
%global py2_install %{__python} setup.py install --root %{buildroot}
%else
%bcond_without tests
%endif

%global prerelease rc3

Name:           commissaire
Version:        0.0.1
Release:        0.1.%{prerelease}%{?dist}
Summary:        Simple cluster host management
License:        GPLv3+
URL:            http://github.com/projectatomic/commissaire
Source0:        https://github.com/projectatomic/%{name}/archive/%{version}%{prerelease}.tar.gz

BuildArch:      noarch

BuildRequires:  python-devel
BuildRequires:  systemd

# For docs
BuildRequires:  python-sphinx

# For tests
%if %{with tests}
BuildRequires:  python-coverage
BuildRequires:  python-mock
BuildRequires:  python-nose
BuildRequires:  python-flake8
%endif
BuildRequires:  pkgconfig(systemd)

Requires:  python-setuptools
Requires:  python-cherrypy
Requires:  python2-falcon
Requires:  python2-python-etcd
Requires:  python-jinja2
Requires:  python-requests
Requires:  py-bcrypt

# Ansible's Python API has no stability guarantees,
# so keep the acceptable versions on a short leash.
Requires:  ansible >= 2.1.0.0
Requires:  ansible < 2.1.1.0

%description
Commissaire allows administrators of a Kubernetes, Atomic Enterprise or
OpenShift installation to perform administrative tasks without the need
to write custom scripts or manually intervene on systems.

Example tasks include:
  * rolling reboot of cluster hosts
  * upgrade software on cluster hosts
  * check the status of cluster hosts
  * scan for known vulnerabilities
  * add a new host to a cluster for container orchestration


%prep
%autosetup -n %{name}-%{version}%{prerelease}


%build
%py2_build

# Build docs
%{__python2} setup.py build_sphinx -b text

%install
%py2_install
install -D contrib/systemd/commissaire %{buildroot}%{_sysconfdir}/sysconfig/commissaire
install -D contrib/systemd/commissaire.service %{buildroot}%{_unitdir}/commissaire.service

%check
# XXX: Issue with the coverage module.
#%{__python2} setup.py nosetests

%post
%systemd_post %{name}

%preun
%systemd_preun %{name}

%postun
%systemd_postun_with_restart %{name}



%files
%license LICENSE
%doc README.md
%doc CONTRIBUTORS
%doc MAINTAINERS
%doc build/sphinx/text/*.txt
%{_bindir}/commissaire
%{python2_sitelib}/*
%{_sysconfdir}/sysconfig/commissaire
%{_unitdir}/commissaire.service


%changelog
* Tue Jun 14 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc3-2
- Bumped up ansible version.

* Tue Apr 19 2016 Matthew Barnes <mbarnes@redhat.com> - 0.0.1rc3-1
- Update for RC3.

* Mon Apr  4 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-5
* commctl and commissaire-hash-pass are now their own package.

* Tue Mar 29 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-4
- Added author files
- Changed from pep8 to flake8

* Thu Mar 17 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-3
- Now using cherrypy rather than gevent.

* Tue Mar  8 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-2
- Adding in service items.

* Tue Mar  8 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-1
- Update for RC2.

* Mon Feb 22 2016 Matthew Barnes <mbarnes@redhat.com> - 0.0.1rc1-1
- Initial packaging.
