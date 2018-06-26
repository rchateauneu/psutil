# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX platform implementation."""

import contextlib
import errno
import collections
import functools
import os
from socket import AF_INET
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_osx as cext
from . import _psutil_posix as cext_posix
from ._common import AF_INET6
from ._common import conn_tmap
from ._common import isfile_strict
from ._common import memoize_when_activated
from ._common import parse_environ_block
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._exceptions import AccessDenied
from ._exceptions import NoSuchProcess
from ._exceptions import ZombieProcess


__extra__all__ = []


# =====================================================================
# --- globals
# =====================================================================


PAGESIZE = os.sysconf("SC_PAGE_SIZE")
AF_LINK = cext_posix.AF_LINK

TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RECEIVED: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

PROC_STATUSES = {
    cext.SIDL: _common.STATUS_IDLE,
    cext.SRUN: _common.STATUS_RUNNING,
    cext.SSLEEP: _common.STATUS_SLEEPING,
    cext.SSTOP: _common.STATUS_STOPPED,
    cext.SZOMB: _common.STATUS_ZOMBIE,
}

temperatures = (
    # group, key, label

    # --- CPU
    ("CPU", "TCXC", "PECI CPU"),
    ("CPU", "TCXc", "PECI CPU"),
    ("CPU", "TC0P", "CPU 1 Proximity"),
    ("CPU", "TC0H", "CPU 1 Heatsink"),
    ("CPU", "TC0D", "CPU 1 Package"),
    ("CPU", "TC0E", "CPU 1"),
    ("CPU", "TC1C", "CPU Core 1"),
    ("CPU", "TC2C", "CPU Core 2"),
    ("CPU", "TC3C", "CPU Core 3"),
    ("CPU", "TC4C", "CPU Core 4"),
    ("CPU", "TC5C", "CPU Core 5"),
    ("CPU", "TC6C", "CPU Core 6"),
    ("CPU", "TC7C", "CPU Core 7"),
    ("CPU", "TC8C", "CPU Core 8"),
    ("CPU", "TCAH", "CPU 1 Heatsink Alt."),
    ("CPU", "TCAD", "CPU 1 Package Alt."),
    ("CPU", "TC1P", "CPU 2 Proximity"),
    ("CPU", "TC1H", "CPU 2 Heatsink"),
    ("CPU", "TC1D", "CPU 2 Package"),
    ("CPU", "TC1E", "CPU 2"),
    ("CPU", "TCBH", "CPU 2 Heatsink Alt."),
    ("CPU", "TCBD", "CPU 2 Package Alt."),

    ("CPU", "TCSC", "PECI SA"),
    ("CPU", "TCSc", "PECI SA"),
    ("CPU", "TCSA", "PECI SA"),

    # --- GPU
    ("GPU", "TCGC", "PECI GPU"),
    ("GPU", "TCGc", "PECI GPU"),
    ("GPU", "TG0P", "GPU Proximity"),
    ("GPU", "TG0D", "GPU Die"),
    ("GPU", "TG1D", "GPU Die"),
    ("GPU", "TG0H", "GPU Heatsink"),
    ("GPU", "TG1H", "GPU Heatsink"),

    # --- Memory
    ("Memory", "Ts0S", "Memory Proximity"),
    ("Memory", "TM0P", "Mem Bank A1"),
    ("Memory", "TM1P", "Mem Bank A2"),
    ("Memory", "TM8P", "Mem Bank B1"),
    ("Memory", "TM9P", "Mem Bank B2"),
    ("Memory", "TM0S", "Mem Module A1"),
    ("Memory", "TM1S", "Mem Module A2"),
    ("Memory", "TM8S", "Mem Module B1"),
    ("Memory", "TM9S", "Mem Module B2"),

    # --- HDD
    ("HDD", "TH0P", "HDD Bay 1"),
    ("HDD", "TH1P", "HDD Bay 2"),
    ("HDD", "TH2P", "HDD Bay 3"),
    ("HDD", "TH3P", "HDD Bay 4"),

    # --- Battery
    ("Battery", "TB0T", "Battery TS_MAX"),
    ("Battery", "TB1T", "Battery 1"),
    ("Battery", "TB2T", "Battery 2"),
    ("Battery", "TB3T", "Battery"),

    # --- Others
    ("Others", "TN0D", "Northbridge Die"),
    ("Others", "TN0P", "Northbridge Proximity 1"),
    ("Others", "TN1P", "Northbridge Proximity 2"),
    ("Others", "TN0C", "MCH Die"),
    ("Others", "TN0H", "MCH Heatsink"),
    ("Others", "TP0D", "PCH Die"),
    ("Others", "TPCD", "PCH Die"),
    ("Others", "TP0P", "PCH Proximity"),

    ("Others", "TA0P", "Airflow 1"),
    ("Others", "TA1P", "Airflow 2"),
    ("Others", "Th0H", "Heatpipe 1"),
    ("Others", "Th1H", "Heatpipe 2"),
    ("Others", "Th2H", "Heatpipe 3"),

    ("Others", "Tm0P", "Mainboard Proximity"),
    ("Others", "Tp0P", "Powerboard Proximity"),
    ("Others", "Ts0P", "Palm Rest"),
    ("Others", "Tb0P", "BLC Proximity"),

    ("Others", "TL0P", "LCD Proximity"),
    ("Others", "TW0P", "Airport Proximity"),
    ("Others", "TO0P", "Optical Drive"),

    ("Others", "Tp0P", "Power Supply 1"),
    ("Others", "Tp0C", "Power Supply 1 Alt."),
    ("Others", "Tp1P", "Power Supply 2"),
    ("Others", "Tp1C", "Power Supply 2 Alt."),
    ("Others", "Tp2P", "Power Supply 3"),
    ("Others", "Tp3P", "Power Supply 4"),
    ("Others", "Tp4P", "Power Supply 5"),
    ("Others", "Tp5P", "Power Supply 6"),

    ("Others", "TS0C", "Expansion Slots"),
    ("Others", "TA0S", "PCI Slot 1 Pos 1"),
    ("Others", "TA1S", "PCI Slot 1 Pos 2"),
    ("Others", "TA2S", "PCI Slot 2 Pos 1"),
    ("Others", "TA3S", "PCI Slot 2 Pos 2"),
)

kinfo_proc_map = dict(
    ppid=0,
    ruid=1,
    euid=2,
    suid=3,
    rgid=4,
    egid=5,
    sgid=6,
    ttynr=7,
    ctime=8,
    status=9,
    name=10,
)

pidtaskinfo_map = dict(
    cpuutime=0,
    cpustime=1,
    rss=2,
    vms=3,
    pfaults=4,
    pageins=5,
    numthreads=6,
    volctxsw=7,
)


# =====================================================================
# --- named tuples
# =====================================================================


# psutil.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'nice', 'system', 'idle'])
# psutil.virtual_memory()
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'wired'])
# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms', 'pfaults', 'pageins'])
# psutil.Process.memory_full_info()
pfullmem = namedtuple('pfullmem', pmem._fields + ('uss', ))
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple(
    'pmmap_grouped',
    'path rss private swapped dirtied ref_count shadow_depth')
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    """System virtual memory as a namedtuple."""
    total, active, inactive, wired, free = cext.virtual_mem()
    avail = inactive + free
    used = active + inactive + wired
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, avail, percent, used, free,
                 active, inactive, wired)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, used, free, sin, sout = cext.swap_mem()
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = cext.cpu_times()
    return scputimes(user, nice, system, idle)


def per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in cext.per_cpu_times():
        user, nice, system, idle = cpu_t
        item = scputimes(user, nice, system, idle)
        ret.append(item)
    return ret


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


def cpu_count_physical():
    """Return the number of physical CPUs in the system."""
    return cext.cpu_count_phys()


def cpu_stats():
    ctx_switches, interrupts, soft_interrupts, syscalls, traps = \
        cext.cpu_stats()
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls)


def cpu_freq():
    """Return CPU frequency.
    On OSX per-cpu frequency is not supported.
    Also, the returned frequency never changes, see:
    https://arstechnica.com/civis/viewtopic.php?f=19&t=465002
    """
    curr, min_, max_ = cext.cpu_freq()
    return [_common.scpufreq(curr, min_, max_)]


# =====================================================================
# --- disks
# =====================================================================


disk_usage = _psposix.disk_usage
disk_io_counters = cext.disk_io_counters


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples."""
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) or not os.path.exists(device):
                continue
        ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


# =====================================================================
# --- sensors
# =====================================================================


def sensors_temperatures():
    """Returns a dictionary of regions of temperature sensors:
        CPU/GPU/Memory/Others
    Each entry contains a list of results of all the successfully polled
    SMC keys from the system.

    References for SMC keys and meaning:

    https://stackoverflow.com/questions/28568775/
        description-for-apples-smc-keys/31033665#31033665

    https://github.com/Chris911/iStats/blob/
        09b159f85a9481b59f347a37259f6d272f65cc05/lib/iStats/smc.rb

    http://web.archive.org/web/20140714090133/http://www.parhelia.ch:80/
        blog/statics/k3_keys.html
    """
    ret = collections.defaultdict(list)

    for group, key, label in temperatures:
        result = cext.smc_get_temperature(key)
        result = round(result, 1)
        if result <= 0:
            continue
        ret[group].append((label, result, None, None))

    return dict(ret)


def sensors_battery():
    """Return battery information.
    """
    try:
        percent, minsleft, power_plugged = cext.sensors_battery()
    except NotImplementedError:
        # no power source - return None according to interface
        return None
    power_plugged = power_plugged == 1
    if power_plugged:
        secsleft = _common.POWER_TIME_UNLIMITED
    elif minsleft == -1:
        secsleft = _common.POWER_TIME_UNKNOWN
    else:
        secsleft = minsleft * 60
    return _common.sbattery(percent, secsleft, power_plugged)


def sensors_fans():
    """Return fans speed information.
    """
    ret = collections.defaultdict(list)
    rawlist = cext.sensors_fans()
    if rawlist is not None:
        for fan in rawlist:
            ret["Fans"].append(_common.sfan(fan[0], fan[1]))

    return dict(ret)


# =====================================================================
# --- network
# =====================================================================


net_io_counters = cext.net_io_counters
net_if_addrs = cext_posix.net_if_addrs


def net_connections(kind='inet'):
    """System-wide network connections."""
    # Note: on OSX this will fail with AccessDenied unless
    # the process is owned by root.
    ret = []
    for pid in pids():
        try:
            cons = Process(pid).connections(kind)
        except NoSuchProcess:
            continue
        else:
            if cons:
                for c in cons:
                    c = list(c) + [pid]
                    ret.append(_common.sconn(*c))
    return ret


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        mtu = cext_posix.net_if_mtu(name)
        isup = cext_posix.net_if_flags(name)
        duplex, speed = cext_posix.net_if_duplex_speed(name)
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    return ret


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp, pid = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = _common.suser(user, tty or None, hostname or None, tstamp, pid)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    ls = cext.pids()
    if 0 not in ls:
        # On certain OSX versions pids() C doesn't return PID 0 but
        # "ps" does and the process is querable via sysctl():
        # https://travis-ci.org/giampaolo/psutil/jobs/309619941
        try:
            Process(0).create_time()
            ls.insert(0, 0)
        except NoSuchProcess:
            pass
        except AccessDenied:
            ls.insert(0, 0)
    return ls


pid_exists = _psposix.pid_exists


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError as err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
        except cext.ZombieProcessError:
            raise ZombieProcess(self.pid, self._name, self._ppid)
    return wrapper


@contextlib.contextmanager
def catch_zombie(proc):
    """There are some poor C APIs which incorrectly raise ESRCH when
    the process is still alive or it's a zombie, or even RuntimeError
    (those who don't set errno). This is here in order to solve:
    https://github.com/giampaolo/psutil/issues/1044
    """
    try:
        yield
    except (OSError, RuntimeError) as err:
        if isinstance(err, RuntimeError) or err.errno == errno.ESRCH:
            try:
                # status() is not supposed to lie and correctly detect
                # zombies so if it raises ESRCH it's true.
                status = proc.status()
            except NoSuchProcess:
                raise err
            else:
                if status == _common.STATUS_ZOMBIE:
                    raise ZombieProcess(proc.pid, proc._name, proc._ppid)
                else:
                    raise AccessDenied(proc.pid, proc._name)
        else:
            raise


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    @memoize_when_activated
    def _get_kinfo_proc(self):
        # Note: should work with all PIDs without permission issues.
        ret = cext.proc_kinfo_oneshot(self.pid)
        assert len(ret) == len(kinfo_proc_map)
        return ret

    @memoize_when_activated
    def _get_pidtaskinfo(self):
        # Note: should work for PIDs owned by user only.
        with catch_zombie(self):
            ret = cext.proc_pidtaskinfo_oneshot(self.pid)
        assert len(ret) == len(pidtaskinfo_map)
        return ret

    def oneshot_enter(self):
        self._get_kinfo_proc.cache_activate()
        self._get_pidtaskinfo.cache_activate()

    def oneshot_exit(self):
        self._get_kinfo_proc.cache_deactivate()
        self._get_pidtaskinfo.cache_deactivate()

    @wrap_exceptions
    def name(self):
        name = self._get_kinfo_proc()[kinfo_proc_map['name']]
        return name if name is not None else cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        with catch_zombie(self):
            return cext.proc_exe(self.pid)

    @wrap_exceptions
    def cmdline(self):
        with catch_zombie(self):
            return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def environ(self):
        with catch_zombie(self):
            return parse_environ_block(cext.proc_environ(self.pid))

    @wrap_exceptions
    def ppid(self):
        self._ppid = self._get_kinfo_proc()[kinfo_proc_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def cwd(self):
        with catch_zombie(self):
            return cext.proc_cwd(self.pid)

    @wrap_exceptions
    def uids(self):
        rawtuple = self._get_kinfo_proc()
        return _common.puids(
            rawtuple[kinfo_proc_map['ruid']],
            rawtuple[kinfo_proc_map['euid']],
            rawtuple[kinfo_proc_map['suid']])

    @wrap_exceptions
    def gids(self):
        rawtuple = self._get_kinfo_proc()
        return _common.puids(
            rawtuple[kinfo_proc_map['rgid']],
            rawtuple[kinfo_proc_map['egid']],
            rawtuple[kinfo_proc_map['sgid']])

    @wrap_exceptions
    def terminal(self):
        tty_nr = self._get_kinfo_proc()[kinfo_proc_map['ttynr']]
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def memory_info(self):
        rawtuple = self._get_pidtaskinfo()
        return pmem(
            rawtuple[pidtaskinfo_map['rss']],
            rawtuple[pidtaskinfo_map['vms']],
            rawtuple[pidtaskinfo_map['pfaults']],
            rawtuple[pidtaskinfo_map['pageins']],
        )

    @wrap_exceptions
    def memory_full_info(self):
        basic_mem = self.memory_info()
        uss = cext.proc_memory_uss(self.pid)
        return pfullmem(*basic_mem + (uss, ))

    @wrap_exceptions
    def cpu_times(self):
        rawtuple = self._get_pidtaskinfo()
        return _common.pcputimes(
            rawtuple[pidtaskinfo_map['cpuutime']],
            rawtuple[pidtaskinfo_map['cpustime']],
            # children user / system times are not retrievable (set to 0)
            0.0, 0.0)

    @wrap_exceptions
    def create_time(self):
        return self._get_kinfo_proc()[kinfo_proc_map['ctime']]

    @wrap_exceptions
    def num_ctx_switches(self):
        # Unvoluntary value seems not to be available;
        # getrusage() numbers seems to confirm this theory.
        # We set it to 0.
        vol = self._get_pidtaskinfo()[pidtaskinfo_map['volctxsw']]
        return _common.pctxsw(vol, 0)

    @wrap_exceptions
    def num_threads(self):
        return self._get_pidtaskinfo()[pidtaskinfo_map['numthreads']]

    @wrap_exceptions
    def open_files(self):
        if self.pid == 0:
            return []
        files = []
        with catch_zombie(self):
            rawlist = cext.proc_open_files(self.pid)
        for path, fd in rawlist:
            if isfile_strict(path):
                ntuple = _common.popenfile(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        with catch_zombie(self):
            rawlist = cext.proc_connections(self.pid, families, types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            fam = sockfam_to_enum(fam)
            type = socktype_to_enum(type)
            if fam in (AF_INET, AF_INET6):
                if laddr:
                    laddr = _common.addr(*laddr)
                if raddr:
                    raddr = _common.addr(*raddr)
            nt = _common.pconn(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

    @wrap_exceptions
    def num_fds(self):
        if self.pid == 0:
            return 0
        with catch_zombie(self):
            return cext.proc_num_fds(self.pid)

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def nice_get(self):
        with catch_zombie(self):
            return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        with catch_zombie(self):
            return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def status(self):
        code = self._get_kinfo_proc()[kinfo_proc_map['status']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def memory_maps(self):
        return cext.proc_memory_maps(self.pid)
