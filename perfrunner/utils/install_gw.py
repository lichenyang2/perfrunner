import json
from optparse import OptionParser

import requests
from logger import logger

from perfrunner.helpers.misc import pretty_dict
from perfrunner.helpers.remote import RemoteHelper
from perfrunner.settings import ClusterSpec
from perfrunner.settings import TestConfig


class GatewayInstaller(object):

    CBFS = 'http://cbfs-ext.hq.couchbase.com/builds/'

    def __init__(self, cluster_spec, test_config, options):
        self.remote_helper = RemoteHelper(cluster_spec)
        self.cluster_spec = cluster_spec
        self.test_config = test_config
        self.pkg = self.remote_helper.detect_pkg()
        self.version = options.version

    def find_package(self):
        filename = 'couchbase-sync-gateway_{}_x86_64.rpm'.format(self.version)
        url = '{}{}'.format(self.CBFS, filename)
        try:
            status_code = requests.head(url).status_code
        except requests.exceptions.ConnectionError:
            pass
        else:
            if status_code == 200:
                logger.info('Found "{}"'.format(url))
                return filename, url
        logger.interrupt('Target build not found - {}'.format(url))

    def kill_processes_gw(self):
        self.remote_helper.kill_processes_gw()

    def kill_processes_gl(self):
        self.remote_helper.kill_processes_gl()

    def uninstall_package_gw(self):
        filename, url = self.find_package()
        self.remote_helper.uninstall_package_gw(self.pkg, filename)

    def uninstall_package_gl(self):
        self.remote_helper.uninstall_package_gl()

    def install_package_gw(self):
        filename, url = self.find_package()
        self.remote_helper.install_package_gw(self.pkg, url, filename,
                                              self.version)

    def install_package_gl(self):
        self.remote_helper.install_package_gl()

    def start_sync_gateways(self):
        with open('templates/gateway_config_template.json') as fh:
            template = json.load(fh)

        db_master = self.cluster_spec.yield_masters().next()
        template['databases']['db']['server'] = "http://bucket-1:password@{}/".format(db_master)
        template['maxIncomingConnections'] = self.test_config.gateway_settings.conn_in
        template['maxCouchbaseConnections'] = self.test_config.gateway_settings.conn_db
        template['CompressResponses'] = self.test_config.gateway_settings.compression

        with open('templates/gateway_config.json', 'w') as fh:
            fh.write(pretty_dict(template))
        self.remote_helper.start_sync_gateway()

    def install(self):
        num_gateways = len(self.cluster_spec.gateways)
        num_gateloads = len(self.cluster_spec.gateloads)
        if num_gateways != num_gateloads:
            logger.interrupt(
                'The cluster config file has different number of gateways({}) and gateloads({})'
                .format(num_gateways, num_gateloads)
            )
        self.kill_processes_gw()
        self.uninstall_package_gw()
        self.install_package_gw()
        self.start_sync_gateways()
        self.kill_processes_gl()
        self.uninstall_package_gl()
        self.install_package_gl()


def main():
    usage = '%prog -c cluster -t test_config -v version'

    parser = OptionParser(usage)

    parser.add_option('-c', dest='cluster_spec_fname',
                      help='path to cluster specification file',
                      metavar='ClusterSpecFilePath')
    parser.add_option('-t', dest='test_config_fname',
                      help='path to test config file',
                      metavar='TestConfigFilePath')
    parser.add_option('-v', dest='version',
                      help='build version', metavar='Version')

    options, _ = parser.parse_args()
    if not options.cluster_spec_fname or not options.test_config_fname \
            or not options.version:
        parser.error('Missing mandatory parameter')

    cluster_spec = ClusterSpec()
    cluster_spec.parse(options.cluster_spec_fname)

    test_config = TestConfig()
    test_config.parse(options.test_config_fname)

    installer = GatewayInstaller(cluster_spec, test_config, options)
    installer.install()

if __name__ == '__main__':
    main()
