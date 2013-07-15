from uuid import uuid4

from fabric.api import execute, get, run, parallel
from fabric import state
from logger import logger

from perfrunner.helpers import Helper


def all_hosts(task):
    def wrapper(self, *args, **kargs):
        return execute(parallel(task), self, *args, hosts=self.hosts, **kargs)
    return wrapper


class RemoteHelper(Helper):

    ARCH = {'i686': 'x86', 'i386': 'x86', 'x86_64': 'x86_64'}

    def __init__(self, *args, **kwargs):
        super(RemoteHelper, self).__init__(*args, **kwargs)
        state.env.user = self.ssh_username
        state.env.password = self.ssh_password
        state.env.host_string = self.hosts[0]
        state.output.running = False
        state.output.stdout = False

    def wget(self, url, outdir='/tmp'):
        logger.info('Fetching {0}'.format(url))
        run('wget -nc "{0}" -P {1}'.format(url, outdir))

    def detect_pkg(self):
        logger.info('Detecting package manager')
        dist = run('python -c "import platform; print platform.dist()[0]"')
        if dist in ('Ubuntu', 'Debian'):
            return 'deb'
        else:
            return 'rpm'

    def detect_arch(self):
        logger.info('Detecting platform architecture')
        arch = run('arch')
        return self.ARCH[arch]

    @all_hosts
    def reset_swap(self):
        logger.info('Resetting swap')
        run('swapoff --all && swapon --all')

    @all_hosts
    def drop_caches(self):
        logger.info('Dropping memory cache')
        run('sync && echo 3 > /proc/sys/vm/drop_caches')

    @all_hosts
    def clean_data_path(self):
        for path in (self.data_path, self.index_path):
            run('rm -fr {0}/*'.format(path))

    @all_hosts
    def collect_info(self):
        logger.info('Running cbcollect_info')
        fname = '/tmp/{0}.zip'.format(uuid4().hex)
        run('/opt/couchbase/bin/cbcollect_info {0}'.format(fname))
        get('{0}'.format(fname))
        run('rm -f {0}'.format(fname))
