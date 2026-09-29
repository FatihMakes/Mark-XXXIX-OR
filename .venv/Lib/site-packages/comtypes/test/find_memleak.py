import gc
from ctypes import POINTER, Structure, WinDLL, WinError, byref, c_size_t, sizeof
from ctypes.wintypes import BOOL, DWORD, HANDLE

################################################################


class PROCESS_MEMORY_COUNTERS(Structure):
    _fields_ = [
        ("cb", DWORD),
        ("PageFaultCount", DWORD),
        ("PeakWorkingSetSize", c_size_t),
        ("WorkingSetSize", c_size_t),
        ("QuotaPeakPagedPoolUsage", c_size_t),
        ("QuotaPagedPoolUsage", c_size_t),
        ("QuotaPeakNonPagedPoolUsage", c_size_t),
        ("QuotaNonPagedPoolUsage", c_size_t),
        ("PagefileUsage", c_size_t),
        ("PeakPagefileUsage", c_size_t),
    ]

    def __init__(self):
        self.cb = sizeof(self)

    def dump(self):
        for n, _ in self._fields_[2:]:
            print(n, getattr(self, n) / 1e6)


_psapi = WinDLL("psapi")

_GetProcessMemoryInfo = _psapi.GetProcessMemoryInfo
_GetProcessMemoryInfo.argtypes = [HANDLE, POINTER(PROCESS_MEMORY_COUNTERS), DWORD]
_GetProcessMemoryInfo.restype = BOOL


def wss():
    # Return the working set size (memory used by process)
    pmi = PROCESS_MEMORY_COUNTERS()
    if not _GetProcessMemoryInfo(-1, byref(pmi), sizeof(pmi)):
        raise WinError()
    return pmi.WorkingSetSize


LOOPS = 10, 1000


def find_memleak(func, loops=LOOPS):
    # call 'func' several times, so that memory consumption
    # stabilizes:
    for j in range(loops[0]):
        for k in range(loops[1]):
            func()
    gc.collect()
    gc.collect()
    gc.collect()
    bytes = wss()
    # call 'func' several times, recording the difference in
    # memory consumption before and after the call.  Repeat this a
    # few times, and return a list containing the memory
    # consumption differences.
    for j in range(loops[0]):
        for k in range(loops[1]):
            func()
    gc.collect()
    gc.collect()
    gc.collect()
    # return the increased in process size
    result = wss() - bytes
    # Sometimes the process size did decrease, we do not report leaks
    # in this case:
    return max(result, 0)
