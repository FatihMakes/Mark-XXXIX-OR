from ctypes import POINTER, Structure, c_float
from ctypes.wintypes import BOOL, UINT

from comtypes import GUID


class AUDIO_VOLUME_NOTIFICATION_DATA(Structure):
    _fields_ = [
        ("guidEventContext", GUID),
        ("bMuted", BOOL),
        ("fMasterVolume", c_float),
        ("nChannels", UINT),
        ("afChannelVolumes", c_float * 1),
    ]


PAUDIO_VOLUME_NOTIFICATION_DATA = POINTER(AUDIO_VOLUME_NOTIFICATION_DATA)
