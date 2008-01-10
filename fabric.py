#!/usr/bin/env python

# Fabric - Pythonic remote deployment tool.
# Copyright (C) 2008  Christian Vest Hansen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import getpass
import os
import os.path
import re
import signal
import sys
import threading
import time
import types
import datetime

try:
    import paramiko as ssh
except ImportError:
    print("ERROR: paramiko is a required module. Please install it.")
    exit(1)

__version__ = '0.0.1'
__author__ = 'Christian Vest Hansen'
__author_email__ = 'karmazilla@gmail.com'
__url__ = 'https://savannah.nongnu.org/projects/fab/'
__license__ = 'GPL-2'
__greeter__ = '''\
   Fabric v. %(fab_version)s, Copyright (C) 2008 %(fab_author)s.
   Fabric comes with ABSOLUTELY NO WARRANTY; for details type `fab warranty'.
   This is free software, and you are welcome to redistribute it
   under certain conditions; type `fab license' for details.
'''

ENV = {
    'fab_version':__version__,
    'fab_author':__author__,
    'fab_mode':'fanout',
    'fab_port':22,
    'fab_user':None,
    'fab_password':None,
    'fab_pkey':None,
    'fab_key_filename':None,
    'fab_new_host_key':'accept',
    'fab_shell':'/bin/bash -l -c "%s"',
    # TODO: make fab_timestamp UTC
    'fab_timestamp':datetime.datetime.now().strftime('%F_%H-%M-%S'),
    'fab_debug':False,
}
COMMANDS = {} # populated by load() and _load_std_commands()
CONNECTIONS = []
OPERATIONS = {} # populated by _load_operations_helper_map()

#
# Standard fabfile operations:
#
def set(**variables):
    """Set a number of Fabric environment variables.
    
    Set takes a number of keyword arguments, and defines or updates the
    variables that corrosponds to each keyword with the respective value.
    
    The values can be of any type, but strings are used for most variables.
    If the value is a string and contain any eager variable references, such as
    %(fab_user)s, then these will be expanded to their corrosponding value.
    Lazy references, those beginning with a $ rather than a %, will not be
    expanded.
    
    Example:
        set(fab_user='joe.shmoe', fab_mode='rolling')
    
    """
    for k, v in variables.items():
        if isinstance(v, types.StringTypes):
            ENV[k] = (v % ENV)
        else:
            ENV[k] = v

def get(name):
    """Get the value of a given Fabric environment variable.
    
    If the variable isn't found, then this operation returns None.
    
    """
    return name in ENV and ENV[name] or None

def require(var, **kvargs):
    """Make sure that a certain environmet variable is available.
    
    The 'var' parameter is a string that names the variable to check for.
    Two other optional kvargs are supported:
     - 'used_for' is a string that gets injected into, and then printed, as
       something like this string: "This variable is used for %s".
     - 'provided_by' is a list of strings that name commands which the user
       can run in order to satisfy the requirement.
    
    If the required variable is not found in the current environment, then the
    operation is stopped and Fabric halts.
    
    Example:
        require('project_name',
            used_for='finding the target deployment dir.',
            provided_by=['staging', 'production'],
        )
    
    """
    if var in ENV:
        return
    print(
        ("The '%(fab_cur_command)s' command requires a '" + var
        + "' variable.") % ENV
    )
    if 'used_for' in kvargs:
        print("This variable is used for %s" % kvargs['used_for'])
    if 'provided_by' in kvargs:
        print("Get the variable by running one of these commands:")
        print('\t' + ('\n\t'.join(kvargs['provided_by'])))
    exit(1)

def put(localpath, remotepath, **kvargs):
    "Upload a file to the current hosts."
    if not CONNECTIONS: _connect()
    _on_hosts_do(_put, localpath, remotepath)

def run(cmd, **kvargs):
    "Run a shell command on the current hosts."
    if not CONNECTIONS: _connect()
    _on_hosts_do(_run, cmd)

def sudo(cmd, **kvargs):
    "Run a sudo (root privileged) command on the current hosts."
    if not CONNECTIONS: _connect()
    _on_hosts_do(_sudo, cmd)

def local(cmd, **kvargs):
    "Run a command locally."
    os.system(_lazy_format(cmd))

def local_per_host(cmd, **kvargs):
    "Run a command locally, for every defined host."
    _check_fab_hosts()
    for host in ENV['fab_hosts']:
        ENV['fab_host'] = host
        cur_cmd = _lazy_format(cmd)
        os.system(cur_cmd)

def load(filename):
    "Load up the given fabfile."
    execfile(filename)
    for name, obj in locals().items():
        if not name.startswith('_') and isinstance(obj, types.FunctionType):
            COMMANDS[name] = obj
        if not name.startswith('_'):
            __builtins__[name] = obj

def upload_project(**kvargs):
    "Uploads the current project directory to the connected hosts."
    tar_file = "/tmp/fab.%(fab_timestamp)s.tar" % ENV
    cwd_name = os.getcwd().split(os.sep)[-1]
    local("tar -czf %s ." % tar_file)
    put(tar_file, cwd_name + ".tar.gz")
    local("rm -f " + tar_file)
    run("tar -xzf " + cwd_name)
    run("rm -f " + cwd_name + ".tar.gz")

#
# Standard Fabric commands:
#
def _help(**kvargs):
    "Display usage help message to the console, or help for a given command."
    if kvargs:
        if not OPERATIONS:
            _load_operations_helper_map()
        for k, v in kvargs.items():
            if k in COMMANDS:
                _print_help_for_in(k, COMMANDS)
            elif k in OPERATIONS:
                _print_help_for_(k, OPERATIONS)
            elif k in ['ops', 'operations']:
                print("Available operations:")
                _list_objs(OPERATIONS)
            elif k in ['op', 'operation']:
                _print_help_for_in(kvargs[k], OPERATIONS)
            else:
                _print_help_for(k, None)

def _list_commands():
    "Display a list of commands with descriptions."
    print("Available commands are:")
    _list_objs(COMMANDS)

def _license():
    "Display the Fabric distribution license text."
    pass

def _warranty():
    "Display warranty information for the Fabric software."
    pass

def _set(**kvargs):
    """Set a Fabric variable.
    
    Example:
        $fab set:fab_user=billy,other_var=other_value
    """
    for k, v in kvargs.items():
        ENV[k] = (v % ENV)

def _shell(**kvargs):
    "Start an interactive shell connection to the specified hosts."
    def lines():
        try:
            while True:
                yield raw_input("fab> ")
        except EOFError:
            # user pressed ctrl-d
            print
    for line in lines():
        if line == 'exit':
            break
        elif line.startswith('sudo '):
            sudo(line[5:])
        else:
            run(line)

#
# Internal plumbing:
#
def _pick_fabfile():
    "Figure out what the fabfile is called."
    choise = 'fabfile'
    alternatives = ['Fabfile', 'fabfile.py', 'Fabfile.py']
    for alternative in alternatives:
        if os.path.exists(alternative):
            choise = alternative
            break
    return choise

def _load_std_commands():
    "Loads up the standard commands such as help, list, warranty and license."
    COMMANDS['help'] = _help
    COMMANDS['list'] = _list_commands
    COMMANDS['warranty'] = _warranty
    COMMANDS['license'] = _license
    COMMANDS['set'] = _set
    COMMANDS['shell'] = _shell

def _load_operations_helper_map():
    "Loads up the standard operations in OPERATIONS so 'help' can query them."
    OPERATIONS['set'] = set
    OPERATIONS['get'] = get
    OPERATIONS['put'] = put
    OPERATIONS['run'] = run
    OPERATIONS['sudo'] = sudo
    OPERATIONS['require'] = require
    OPERATIONS['local'] = local
    OPERATIONS['local_per_host'] = local_per_host
    OPERATIONS['load'] = load
    OPERATIONS['upload_project'] = upload_project

def _indent(text):
    "Indent all lines in text with four spaces."
    return '\n'.join(('    ' + line for line in text.splitlines()))

def _print_help_for(name, doc):
    "Output a pretty-printed help text for the given name & doc"
    default_help_msg = '* No help-text found.'
    print("Help for '%s':\n%s" % (name, _indent(doc or default_help_msg)))

def _print_help_for_in(name, dictionary):
    "Print a pretty help text for the named function in the dict."
    if name in dictionary:
        _print_help_for(name, dictionary[name].__doc__)
    else:
        _print_help_for(name, None)

def _list_objs(objs):
    max_name_len = reduce(lambda a,b: max(a, len(b)), objs.keys(), 0)
    cmds = objs.items()
    cmds.sort(lambda x,y: cmp(x[0], y[0]))
    for name, fn in cmds:
        print '  ', name.ljust(max_name_len),
        if fn.__doc__:
            print ':', fn.__doc__.splitlines()[0]
        else:
            print

def _check_fab_hosts():
    "Check that we have a fab_hosts variable, and complain if it's missing."
    if 'fab_hosts' not in ENV:
        print("Fabric requires a fab_hosts variable.")
        print("Please set it in your fabfile.")
        print("Example: set(fab_hosts=['node1.com', 'node2.com'])")
        exit(1)

def _connect():
    "Populate CONNECTIONS with (hostname, client) tuples as per fab_hosts."
    _check_fab_hosts()
    signal.signal(signal.SIGINT, _trap_sigint)
    ENV['fab_password'] = getpass.getpass()
    port = int(ENV['fab_port'])
    username = ENV['fab_user']
    password = ENV['fab_password']
    pkey = ENV['fab_pkey']
    key_filename = ENV['fab_key_filename']
    for host in ENV['fab_hosts']:
        client = ssh.SSHClient()
        client.load_system_host_keys()
        if 'fab_new_host_key' in ENV and ENV['fab_new_host_key'] == 'accept':
            client.set_missing_host_key_policy(ssh.AutoAddPolicy())
        client.connect(
            host, port, username, password, pkey, key_filename
        )
        CONNECTIONS.append((host, client))
    if not CONNECTIONS:
        print("The fab_hosts list was empty.")
        print("Please specify some hosts to connect to.")
        exit(1)

def _disconnect():
    "Disconnect all clients."
    for host, client in CONNECTIONS:
        client.close()

def _trap_sigint(signal, frame):
    "Trap ctrl-c and make sure we disconnect everything."
    _disconnect()
    exit(0)

def _lazy_format(string, env=ENV):
    "Do recursive string substitution of ENV vars - both lazy and earger."
    suber = re.compile(r'\$\((?P<var>\w+?)\)')
    def replacer_fn(match):
        var = match.group('var')
        if var in env:
            return _lazy_format(env[var] % env, env)
        else:
            return match.group(0)
    return re.sub(suber, replacer_fn, string % env)

def _on_hosts_do(fn, *args):
    """Invoke the given function with hostname and client parameters in
    accord with the current fac_mode strategy.
    
    fn should be of type:
        (str:hostname, paramiko.SSHClient:clinet) -> bool:success
    
    """
    strategy = ENV['fab_mode']
    if strategy == 'fanout':
        threads = []
        for host, client in CONNECTIONS:
            env = dict(ENV)
            env['fab_host'] = host
            thread = threading.Thread(None, lambda: fn(host, client, env, *args))
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
    elif strategy == 'rolling':
        for host, client in CONNECTIONS:
            env = dict(ENV)
            env['fab_host'] = host
            fn(host, client, env, *args)
    else:
        print("Unsupported fab_mode: %s" % strategy)
        print("Supported modes are: fanout, rolling")
        exit(1)

def _put(host, client, env, localpath, remotepath):
    ftp = client.open_sftp()
    localpath = _lazy_format(localpath, env)
    remotepath = _lazy_format(remotepath, env)
    print("[%s] put: %s -> %s" % (host, localpath, remotepath))
    ftp.put(localpath, remotepath)

def _run(host, client, env, cmd):
    cmd = _lazy_format(cmd, env)
    real_cmd = env['fab_shell'] % cmd.replace('"', '\\"')
    print("[%s] run: %s" % (host, (env['fab_debug'] and real_cmd or cmd)))
    stdin, stdout, stderr = client.exec_command(real_cmd)
    out_th = _start_outputter("[%s] out" % host, stdout)
    err_th = _start_outputter("[%s] err" % host, stderr)
    out_th.join()
    err_th.join()

def _sudo(host, client, env, cmd):
    cmd = _lazy_format(cmd, env)
    real_cmd = env['fab_shell'] % ("sudo -S " + cmd.replace('"', '\\"'))
    print("[%s] sudo: %s" % (host, (env['fab_debug'] and real_cmd or cmd)))
    stdin, stdout, stderr = client.exec_command(real_cmd)
    stdin.write(env['fab_password'])
    stdin.write('\n')
    stdin.flush()
    out_th = _start_outputter("[%s] out" % host, stdout)
    err_th = _start_outputter("[%s] err" % host, stderr)
    out_th.join()
    err_th.join()

def _start_outputter(prefix, channel):
    def outputter():
        line = channel.readline()
        while line:
            print("%s: %s" % (prefix, line)),
            line = channel.readline()
    thread = threading.Thread(None, outputter, prefix)
    thread.setDaemon(True)
    thread.start()
    return thread

def main(args):
    try:
        print(__greeter__ % ENV)
        _load_std_commands()
        fabfile = _pick_fabfile()
        load(fabfile)
        # validation:
        for cmd in args:
            if cmd.find(':') != -1:
                cmd = cmd.split(':', 1)[0]
            if not cmd in COMMANDS:
                print("No such command: %s" % cmd)
                _list_commands()
                exit(1)
        # execution:
        if not args:
            print("No commands given.")
            _list_commands()
        for cmd in args:
            cmd_name = cmd
            cmd_args = None
            if cmd.find(':') != -1:
                cmd_name, cmd_args = cmd.split(':', 1)
            ENV['fab_cur_command'] = cmd_name
            print("Running %s..." % cmd_name)
            if cmd_args is not None:
                cmd_arg_kvs = {}
                for cmd_arg_kv in cmd_args.split(','):
                    k, _, v = cmd_arg_kv.partition('=')
                    cmd_arg_kvs[k] = (v % ENV)
                COMMANDS[cmd_name](**cmd_arg_kvs)
            else:
                COMMANDS[cmd]()
    finally:
        _disconnect()
        print("Done.")
