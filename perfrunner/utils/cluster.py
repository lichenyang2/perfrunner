from optparse import OptionParser

from fabric.api import run

from perfrunner.helpers import Helper
from perfrunner.helpers.monitor import Monitor
from perfrunner.helpers.remote import RemoteHelper, all_hosts
from perfrunner.helpers.rest import RestHelper
from perfrunner.settings import ClusterSpec, TestConfig


class ClusterManager(Helper):

    def __init__(self, cluster_spec, test_config):
        super(ClusterManager, self).__init__(cluster_spec,
                                             test_config)

        self.rest = RestHelper(cluster_spec)
        self.monitor = Monitor(cluster_spec, test_config)

    @all_hosts
    def clean_data_path(self):
        for path in (self.data_path, self.index_path):
            run('rm -fr {0}/*'.format(path))

    def set_data_path(self):
        self.clean_data_path()
        for cluster in self.clusters:
            for host_port in cluster:
                self.rest.set_data_path(host_port)

    def set_auth(self):
        for cluster in self.clusters:
            for host_port in cluster:
                self.rest.set_auth(host_port)

    def set_mem_quota(self):
        for cluster in self.clusters:
            for host_port in cluster:
                self.rest.set_mem_quota(host_port, self.mem_quota)

    def add_nodes(self):
        for cluster in self.clusters:
            master = cluster[0]
            for host_port in cluster[1:self.initial_nodes]:
                host = host_port.split(':')[0]
                self.rest.add_node(master, host)

    def rebalance(self):
        for cluster in self.clusters:
            master = cluster[0]
            known_nodes = cluster[:self.initial_nodes]
            ejected_nodes = []
            self.rest.rebalance(master, known_nodes, ejected_nodes)
            self.monitor.monitor_rebalance(master)

    def create_buckets(self):
        ram_quota = self.mem_quota / self.num_buckets
        buckets = ['bucket-{0}'.format(i + 1) for i in xrange(self.num_buckets)]
        for cluster in self.clusters:
            master = cluster[0]
            for name in buckets:
                self.rest.create_bucket(master, name, ram_quota)

    def configure_auto_compaction(self):
        for cluster in self.clusters:
            master = cluster[0]
            self.rest.configure_auto_compaction(
                master, self.compaction_settings
            )


def get_options():
    usage = '%prog -c cluster -t test_config'

    parser = OptionParser(usage)

    parser.add_option('-c', dest='cluster_spec_fname',
                      help='path to cluster specification file',
                      metavar='cluster.spec')
    parser.add_option('-t', dest='test_config_fname',
                      help='path to test configuration file',
                      metavar='my_test.test')

    options, _ = parser.parse_args()
    if not options.cluster_spec_fname or not options.test_config_fname:
        parser.error('Missing mandatory parameter')

    return options


def main():
    options = get_options()

    cluster_spec = ClusterSpec()
    cluster_spec.parse(options.cluster_spec_fname)
    test_config = TestConfig()
    test_config.parse(options.test_config_fname)

    cm = ClusterManager(cluster_spec, test_config)
    cm.set_data_path()
    cm.set_auth()
    cm.set_mem_quota()
    if cm.initial_nodes > 1:
        cm.add_nodes()
        cm.rebalance()
    cm.create_buckets()
    cm.configure_auto_compaction()

    rh = RemoteHelper(cluster_spec)
    rh.reset_swap()
    rh.drop_caches()

if __name__ == '__main__':
    main()
