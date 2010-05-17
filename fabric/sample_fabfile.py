# Just getting started? Check out http://docs.fabfile.org for more info.

# Required to use the "with" statement under Python 2.5.
from __future__ import with_statement

# Fabric's primary API objects, such as env, run, and sudo.
from fabric.api import *

# Uncomment the below to set a global host list. If a given task has no host
# list of its own, it will run once on each host in this list. Host strings may
# contain user, hostname and/or port information.
# env.hosts = ['server1', 'user@server2', 'otheruser@server3:2222']

# You may also set a global default username and/or password.
# env.user = 'notmylocalusername'
# env.password = 'secret'

# A sample task using various parts of Fabric's API. Again, please see the
# documentation for tutorials and detailed information.
# @host('remote-hostname') # bypasses env.hosts
# def example():
#     local('echo "run something locally"')
#     contents = run("ls /some/remote/directory")
#     if "foldername" in contents:
#         sudo("rm /some/remote/directory/foldername")
