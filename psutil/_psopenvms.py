# Copyright (c) 2019, Remi Chateauneu
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OpenVMS platform implementation."""

import errno
import glob
import os
import re
import subprocess
import sys
from collections import namedtuple

from ._compat import PY3


__extra__all__ = []


# =====================================================================
# --- globals
# =====================================================================

import psutil

class cext:
    version = 550 # See psutil.version_info
    __file__ = ""

HAS_THREADS = False

PAGE_SIZE = 0
AF_LINK = None

PROC_STATUSES = {
}

TCP_STATUSES = {
}

proc_info_map = dict()

# These objects get set on "import psutil" from the __init__.py
# file, see: https://github.com/giampaolo/psutil/issues/1402
NoSuchProcess = None
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None


# =====================================================================
# --- named tuples
# =====================================================================


# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
# psutil.Process.memory_full_info()
pfullmem = pmem
# psutil.Process.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'system', 'idle', 'iowait'])
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple('pmmap_grouped', ['path', 'rss', 'anon', 'locked'])
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple('pmmap_ext', [])


# =====================================================================
# --- utils
# =====================================================================


def get_procfs_path():
    """Return updated psutil.PROCFS_PATH constant."""
    raise Exception("Not implemented yet")


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    raise Exception("Not implemented yet")


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    raise Exception("Not implemented yet")


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system-wide CPU times as a named tuple"""
    raise Exception("Not implemented yet")


def per_cpu_times():
    """Return system per-CPU times as a list of named tuples"""
    raise Exception("Not implemented yet")


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    raise Exception("Not implemented yet")


def cpu_count_physical():
    raise Exception("Not implemented yet")


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    raise Exception("Not implemented yet")


# =====================================================================
# --- disks
# =====================================================================


disk_io_counters = None
disk_usage = None


def disk_partitions(all=False):
    """Return system disk partitions."""
    raise Exception("Not implemented yet")

# =====================================================================
# --- network
# =====================================================================


net_if_addrs = None
net_io_counters = None


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    raise Exception("Not implemented yet")


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    raise Exception("Not implemented yet")


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    raise Exception("Not implemented yet")


def users():
    """Return currently connected users as a list of namedtuples."""
    raise Exception("Not implemented yet")


# =====================================================================
# --- processes
# =====================================================================


def pids():
    """Returns a list of PIDs currently running on the system."""
    raise Exception("Not implemented yet")


def pid_exists(pid):
    """Check for the existence of a unix pid."""
    raise Exception("Not implemented yet")


def wrap_exceptions(fun):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """

    def wrapper(self, *args, **kwargs):
        return fun(self, *args, **kwargs)

    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    def oneshot_enter(self):
        pass

    def oneshot_exit(self):
        pass

    @wrap_exceptions
    def name(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def exe(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def cmdline(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def create_time(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def num_threads(self):
        raise Exception("Not implemented yet")

    if HAS_THREADS:
        @wrap_exceptions
        def threads(self):
		    raise Exception("Not implemented yet")

    @wrap_exceptions
    def connections(self, kind='inet'):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def nice_get(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def nice_set(self, value):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def ppid(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def uids(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def gids(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def cpu_times(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def terminal(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def cwd(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def memory_info(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def status(self):
        raise Exception("Not implemented yet")

    def open_files(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def num_fds(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def num_ctx_switches(self):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def wait(self, timeout=None):
        raise Exception("Not implemented yet")

    @wrap_exceptions
    def io_counters(self):
        raise Exception("Not implemented yet")
