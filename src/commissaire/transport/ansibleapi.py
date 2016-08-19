# Copyright (C) 2016  Red Hat, Inc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Ansible API transport.
"""

import logging

from collections import namedtuple
from pkg_resources import resource_filename
from time import sleep

from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory, Host, Group
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import default
from ansible.utils.display import Display

from commissaire import constants as C
from commissaire.handlers.models import Cluster, Network
from commissaire.store.etcdstorehandler import EtcdStoreHandler
from commissaire.store.kubestorehandler import KubernetesStoreHandler


class LogForward(default.CallbackModule):
    """
    Forwards Ansible's output into a logger.
    """
    #: Version required for this callback
    CALLBACK_VERSION = 2.0
    #: Kind of callback
    CALLBACK_TYPE = 'log'
    #: Name of the callback
    CALLBACK_NAME = 'logforward'
    #: Does it require a callback
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self):
        """
        Creates the instance and sets the logger.
        """
        display = Display()
        self.log = logging.getLogger('transport')
        # TODO: Make verbosity more configurable
        display.verbosity = 1
        if logging.getLevelName(self.log.level) == 'DEBUG':
            display.verbosity = 5
        # replace Displays display method with our own
        display.display = lambda msg, *a, **k: self.log.info(msg)
        super(LogForward, self).__init__(display)

    def v2_runner_on_failed(self, result, *args, **kwargs):
        """
        Called when the runner failed.

        :param result: Ansible's result.
        :type result: ansible.executor.task_result.TaskResult
        :param args: All other ignored non-keyword arguments.
        :type args: tuple
        :param kwargs: All other ignored keyword arguments.
        :type kwargs: dict
        """
        if 'exception' in result._result.keys():
            self.log.warn(
                'An exception occurred for {0}: {1}'.format(
                    result._host.get_name(), result._result['exception']))
            self.log.debug('{0}'.format(result.__dict__))

    def v2_runner_on_skipped(self, result):
        """
        Called when ansible skips a host.

        :param result: Ansible's result.
        :type result: ansible.executor.task_result.TaskResult
        """
        self.log.warn('SKIPPED {0}: {1}'.format(
            result._host.get_name(), result._task.get_name().strip()))
        self.log.debug('{0}'.format(result.__dict__))

    def v2_runner_on_unreachable(self, result):
        """
        Called when a host can not be reached.

        :param result: Ansible's result.
        :type result: ansible.executor.task_result.TaskResult
        """
        self.log.warn('UNREACHABLE {0}: {1}'.format(
            result._host.get_name(), result._task.get_name().strip()))
        self.log.debug('{0}'.format(result.__dict__))


class Transport:
    """
    Transport using Ansible.
    """

    def __init__(self, remote_user='root'):
        """
        Creates an instance of the Transport.
        """
        self.logger = logging.getLogger('transport')
        self.Options = namedtuple(
            'Options', ['connection', 'module_path', 'forks', 'remote_user',
                        'private_key_file', 'ssh_common_args',
                        'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args',
                        'become', 'become_method', 'become_user', 'verbosity',
                        'check'])
        # initialize needed objects
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.passwords = {}
        self.remote_user = remote_user

    def _run(self, ips, key_file, play_file,
             expected_results=[0], play_vars={}, disable_reconnect=False):
        """
        Common code used for each run.

        :param ips: IP address(es) to check.
        :type ips: str or list
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: string
        :param play_file: Path to the ansible play file.
        :type play_file: str
        :param expected_results: List of expected return codes. Default: [0]
        :type expected_results: list
        :param disable_reconnect: Disables connection loop.
        :type disable_reconnect:  bool
        :returns: Ansible exit code
        :type: int
        """
        if type(ips) != list:
            ips = [ips]

        ssh_args = ('-o StrictHostKeyChecking=no -o '
                    'ControlMaster=auto -o ControlPersist=60s')
        become = {
            'become': None,
            'become_user': None,
        }
        if self.remote_user != 'root':
            self.logger.debug('Using user {0} for ssh communication.'.format(
                self.remote_user))
            become['become'] = True
            become['become_user'] = 'root'

        options = self.Options(
            connection='ssh', module_path=None, forks=1,
            remote_user=self.remote_user, private_key_file=key_file,
            ssh_common_args=ssh_args, ssh_extra_args=ssh_args,
            sftp_extra_args=None, scp_extra_args=None,
            become=become['become'], become_method='sudo',
            become_user=become['become_user'],
            verbosity=None, check=False)
        # create inventory and pass to var manager
        inventory = Inventory(
            loader=self.loader,
            variable_manager=self.variable_manager,
            host_list=ips)
        self.logger.debug('Options: {0}'.format(options))

        group = Group('commissaire_targets')
        for ip in ips:
            host = Host(ip, 22)
            group.add_host(host)

        inventory.groups.update({'commissaire_targets': group})
        self.logger.debug('Inventory: {0}'.format(inventory))

        self.variable_manager.set_inventory(inventory)

        play_source = self.loader.load_from_file(play_file)[0]
        play = Play().load(
            play_source,
            variable_manager=self.variable_manager,
            loader=self.loader)

        # Add any variables provided into the play
        play.vars.update(play_vars)

        self.logger.debug(
            'Running play for hosts {0}: play={1}, vars={2}'.format(
                ips, play_source, play.vars))

        # actually run it
        for cnt in range(0, 3):
            tqm = None
            try:
                tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=options,
                    passwords=self.passwords,
                    stdout_callback=LogForward(),
                )
                result = tqm.run(play)

                # Deal with unreachable hosts (result == 3) by retrying
                # up to 3 times, sleeping 5 seconds after each attempt.
                if disable_reconnect:
                    self.logger.warn(
                        'Not attempting to reconnect to {0}'.format(ips))
                    break
                elif result == 3 and cnt < 2:
                    self.logger.warn(
                        'One or more hosts in {0} is unreachable, '
                        'retrying in 5 seconds...'.format(ips))
                    sleep(5)
                else:
                    break
            finally:
                if tqm is not None:
                    self.logger.debug(
                        'Cleaning up after the TaskQueueManager.')
                    tqm.cleanup()

        if result in expected_results:
            self.logger.debug('{0}: Good result {1}'.format(ip, result))
            fact_cache = self.variable_manager._fact_cache.get(ip, {})
            return (result, fact_cache)

        self.logger.debug('{0}: Bad result {1}'.format(ip, result))
        raise Exception('Can not run for {0}'.format(ip))

    def deploy(self, ips, key_file, oscmd, kwargs):
        """
        Deploys a tree image on a host via ansible.

        :param ips: IP address(es) to upgrade.
        :type ips: str or list
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: str
        :param oscmd: OSCmd class to use
        :type oscmd: commissaire.oscmd.OSCmdBase
        :param kwargs: keyword arguments for the remote command
        :type kwargs: dict
        :returns: tuple -- (exitcode(int), facts(dict)).
        """
        play_file = resource_filename(
            'commissaire', 'data/ansible/playbooks/deploy.yaml')
        deploy_command = " ".join(oscmd.deploy(kwargs['version']))
        return self._run(
            ips, key_file, play_file, [0],
            {'commissaire_deploy_command': deploy_command})

    def upgrade(self, ips, key_file, oscmd, kwargs):
        """
        Upgrades a host via ansible.

        :param ips: IP address(es) to upgrade.
        :type ips: str or list
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: str
        :param oscmd: OSCmd class to use
        :type oscmd: commissaire.oscmd.OSCmdBase
        :param kwargs: keyword arguments for the remote command
        :type kwargs: dict
        :returns: tuple -- (exitcode(int), facts(dict)).
        """
        play_file = resource_filename(
            'commissaire', 'data/ansible/playbooks/upgrade.yaml')
        upgrade_command = " ".join(oscmd.upgrade())
        return self._run(
            ips, key_file, play_file, [0],
            {'commissaire_upgrade_command': upgrade_command})

    def restart(self, ips, key_file, oscmd, kwargs):
        """
        Restarts a host via ansible.

        :param ips: IP address(es) to restart.
        :type ips: str or list
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: str
        :param oscmd: OSCmd class to use
        :type oscmd: commissaire.oscmd.OSCmdBase
        :param kwargs: keyword arguments for the remote command
        :type kwargs: dict
        :returns: tuple -- (exitcode(int), facts(dict)).
        """
        play_file = resource_filename(
            'commissaire', 'data/ansible/playbooks/restart.yaml')
        restart_command = " ".join(oscmd.restart())
        return self._run(
            ips, key_file, play_file, [0, 2],
            {'commissaire_restart_command': restart_command},
            disable_reconnect=True)

    def get_info(self, ip, key_file):
        """
        Get's information from the host via ansible.

        :param ip: IP address to check.
        :type ip: str
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: str
        :returns: tuple -- (exitcode(int), facts(dict)).
        """
        play_file = resource_filename(
            'commissaire', 'data/ansible/playbooks/get_info.yaml')
        result, fact_cache = self._run(ip, key_file, play_file)
        facts = {}
        facts['os'] = fact_cache['ansible_distribution'].lower()
        facts['cpus'] = fact_cache['ansible_processor_cores']
        facts['memory'] = fact_cache['ansible_memory_mb']['real']['total']
        space = 0
        for x in fact_cache['ansible_mounts']:
            space += x['size_total']
        facts['space'] = space

        # Special case for atomic: Since Atomic doesn't advertise itself
        # and instead calls itself 'redhat' or 'centos' or 'fedora', we
        # need to check for 'atomicos' in other ansible_cmdline facts.
        atomic_os_types = {
            'redhat': '/ostree/rhel-atomic-host',
            'centos': '/ostree/centos-atomic-host',
            'fedora': '/ostree/fedora-atomic'
        }
        os_type = facts['os']
        if os_type in atomic_os_types:
            self.logger.debug(
                'Found os of {0}. Checking for special '
                'atomic case...'.format(os_type))
            boot_image = fact_cache.get(
                'ansible_cmdline', {}).get('BOOT_IMAGE', '')
            root_mapper = fact_cache.get('ansible_cmdline', {}).get('root', '')
            if (boot_image.startswith(atomic_os_types[os_type]) or
                    'atomicos' in root_mapper):
                facts['os'] = 'atomic'
            self.logger.debug('Facts: {0}'.format(facts))

        return (result, facts)

    def check_host_availability(self, host, key_file):
        """
        Checks if a host node is available.

        :param host: The host model to check.
        :type host: commissaire.handlers.models.Host
        :param key_file: The path to the ssh_priv_key.
        :type key_file: str
        :returns: Ansible results for the run
        :rtype: dict
        """
        play_file = resource_filename(
            'commissaire',
            'data/ansible/playbooks/check_host_availability.yaml')
        results = self._run(
            host.address, key_file, play_file, [0, 3], disable_reconnect=True)
        return results

    def _get_etcd_config(self, store_manager):
        """
        Extracts etcd configuration from a registered handler.
        If no matching handler is found, return defaults for required values.

        :returns: A dictionary of configuration values
        :rtype: dict
        """
        # Need defaults for all required keys.
        etcd_config = {
            'server_url': EtcdStoreHandler.DEFAULT_SERVER_URL
        }

        entries = store_manager.list_store_handlers()
        for handler_type, config, model_types in entries:
            if handler_type is EtcdStoreHandler:
                etcd_config.update(config)
                break

        return etcd_config

    def _get_kube_config(self, store_manager):
        """
        Extracts Kubernetes configuration from a registered handler.
        If no matching handler is found, return defaults for required values.

        :returns: A dictionary of configuration values
        :rtype: dict
        """
        # Need defaults for all required keys.
        kube_config = {
            'server_url': KubernetesStoreHandler.DEFAULT_SERVER_URL,
            'token': ''
        }

        entries = store_manager.list_store_handlers()
        for handler_type, config, model_types in entries:
            if handler_type is KubernetesStoreHandler:
                kube_config.update(config)
                break

        return kube_config

    def bootstrap(self, ip, cluster_data, key_file, store_manager, oscmd):
        """
        Bootstraps a host via ansible.

        :param ip: IP address to bootstrap.
        :type ip: str
        :param cluster_data: The data required to create a Cluster instance.
        :type cluster_data: dict or None
        :param key_file: Full path to the file holding the private SSH key.
        :type key_file: str
        :param store_manager: Remote object for remote stores
        :type store_manager: commissaire.store.storehandlermanager.
                             StoreHandlerManager
        :param oscmd: OSCmd class to use
        :type oscmd: commissaire.oscmd.OSCmdBase
        :returns: tuple -- (exitcode(int), facts(dict)).
        """
        self.logger.debug('Using {0} as the oscmd class for {1}'.format(
            oscmd.os_type, ip))

        cluster_type = C.CLUSTER_TYPE_HOST
        network = Network.new(**C.DEFAULT_CLUSTER_NETWORK_JSON)
        try:
            cluster = Cluster.new(**cluster_data)
            cluster_type = cluster.type
            network = store_manager.get(Network.new(name=cluster.network))
        except KeyError:
            # Not part of a cluster
            pass

        etcd_config = self._get_etcd_config(store_manager)
        kube_config = self._get_kube_config(store_manager)

        play_vars = {
            'commissaire_cluster_type': cluster_type,
            'commissaire_bootstrap_ip': ip,
            'commissaire_kubernetes_api_server_url': kube_config['server_url'],
            'commissaire_kubernetes_bearer_token': kube_config['token'],
            # TODO: Where do we get this?
            'commissaire_docker_registry_host': '127.0.0.1',
            # TODO: Where do we get this?
            'commissaire_docker_registry_port': 8080,
            # TODO: Where do we get this?
            'commissaire_flannel_key': '/atomic01/network',
            'commissaire_docker_config_local': resource_filename(
                'commissaire', 'data/templates/docker'),
            'commissaire_flanneld_config_local': resource_filename(
                'commissaire', 'data/templates/flanneld'),
            'commissaire_kubelet_config_local': resource_filename(
                'commissaire', 'data/templates/kubelet'),
            'commissaire_kubernetes_config_local': resource_filename(
                'commissaire', 'data/templates/kube_config'),
            'commissaire_kubeconfig_config_local': resource_filename(
                'commissaire', 'data/templates/kubeconfig'),
            'commissaire_install_libselinux_python': " ".join(
                oscmd.install_libselinux_python()),
            'commissaire_docker_config': oscmd.docker_config,
            'commissaire_flanneld_config': oscmd.flanneld_config,
            'commissaire_kubelet_config': oscmd.kubelet_config,
            'commissaire_kubernetes_config': oscmd.kubernetes_config,
            'commissaire_kubeconfig_config': oscmd.kubernetes_kubeconfig,
            'commissaire_install_flannel': " ".join(oscmd.install_flannel()),
            'commissaire_install_docker': " ".join(oscmd.install_docker()),
            'commissaire_install_kube': " ".join(oscmd.install_kube()),
            'commissaire_flannel_service': oscmd.flannel_service,
            'commissaire_docker_service': oscmd.flannel_service,
            'commissaire_kubelet_service': oscmd.kubelet_service,
            'commissaire_kubeproxy_service': oscmd.kubelet_proxy_service,
        }

        # TODO: get the data!!
        # If we are a flannel_server network then set the var
        if network.type == 'flannel_server':
            play_vars['commissaire_flanneld_server'] = network.options.get(
                'address')
        elif network.type == 'flannel_etcd':
            play_vars['commissaire_etcd_server_url'] = etcd_config[
                'server_url']

        # Provide the CA if etcd is being used over https
        if (
                etcd_config['server_url'].startswith('https:') and
                'certificate_ca_path' in etcd_config):
            play_vars['commissaire_etcd_ca_path'] = oscmd.etcd_ca
            play_vars['commissaire_etcd_ca_path_local'] = (
                etcd_config['certificate_ca_path'])

        # Client Certificate additions
        if 'certificate_path' in etcd_config:
            self.logger.info('Using etcd client certs')
            play_vars['commissaire_etcd_client_cert_path'] = (
                oscmd.etcd_client_cert)
            play_vars['commissaire_etcd_client_cert_path_local'] = (
                etcd_config['certificate_path'])
            play_vars['commissaire_etcd_client_key_path'] = (
                oscmd.etcd_client_key)
            play_vars['commissaire_etcd_client_key_path_local'] = (
                etcd_config['certificate_key_path'])

        if 'certificate_path' in kube_config:
            self.logger.info('Using kubernetes client certs')
            play_vars['commissaire_kubernetes_client_cert_path'] = (
                oscmd.kube_client_cert)
            play_vars['commissaire_kubernetes_client_cert_path_local'] = (
                kube_config['certificate_path'])
            play_vars['commissaire_kubernetes_client_key_path'] = (
                oscmd.kube_client_key)
            play_vars['commissaire_kubernetes_client_key_path_local'] = (
                kube_config['certificate_key_path'])

        # XXX: Need to enable some package repositories for OS 'rhel'
        #      (or 'redhat').  This is a hack for a single corner case.
        #      We discussed how to generalize future cases where we need
        #      extra commands for a specific OS but decided to defer until
        #      more crop up.
        #
        #      See https://github.com/projectatomic/commissaire/pull/56
        #
        if oscmd.os_type in ('rhel', 'redhat'):
            play_vars['commissaire_enable_pkg_repos'] = (
                'subscription-manager repos '
                '--enable=rhel-7-server-extras-rpms '
                '--enable=rhel-7-server-optional-rpms')
        else:
            play_vars['commissaire_enable_pkg_repos'] = 'true'

        self.logger.debug('Variables for bootstrap: {0}'.format(play_vars))

        play_file = resource_filename(
            'commissaire', 'data/ansible/playbooks/bootstrap.yaml')
        results = self._run(ip, key_file, play_file, [0], play_vars)

        return results
