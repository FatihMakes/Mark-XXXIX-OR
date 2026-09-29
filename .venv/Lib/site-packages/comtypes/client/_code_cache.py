"""comtypes.client._code_cache helper module.

The main function is _find_gen_dir(), which on-demand creates the
comtypes.gen package and returns a directory where generated code can
be written to.
"""

import ctypes
import logging
import os
import sys
import tempfile
import types
from ctypes.wintypes import BOOL, HWND, LPWSTR, MAX_PATH

from comtypes import typeinfo

logger = logging.getLogger(__name__)


def _ensure_list(path):
    """
    On Python 3.4 and later, when a package is imported from
    an empty directory, its `__path__` will be a _NamespacePath
    object and not a list, and _NamespacePath objects cannot
    be indexed, leading to the error reported in #102.
    This wrapper ensures that the path is a list for that reason.
    """
    return list(path)


def _find_gen_dir():
    """Create, if needed, and return a directory where automatically
    generated modules will be created.

    Usually, this is the directory 'Lib/site-packages/comtypes/gen'.

    If the above directory cannot be created, or if it is not a
    directory in the file system (when comtypes is imported from a
    zip-archive or a zipped egg), or if the current user cannot create
    files in this directory, an additional directory is created and
    appended to comtypes.gen.__path__ .

    For a Python script using comtypes, the additional directory is
    '%APPDATA%\\<username>\\Python\\Python25\\comtypes_cache'.

    For an executable frozen with py2exe, the additional directory is
    '%TEMP%\\comtypes_cache\\<imagebasename>-25'.
    """
    _create_comtypes_gen_package()
    from comtypes import gen

    gen_path = _ensure_list(gen.__path__)
    if not _is_writeable(gen_path):
        # check type of executable image to determine a subdirectory
        # where generated modules are placed.
        ftype = getattr(sys, "frozen", None)
        pymaj, pymin = sys.version_info[:2]
        if ftype is None:
            # Python script
            subdir = rf"Python\Python{pymaj:d}{pymin:d}\comtypes_cache"
            basedir = _get_appdata_dir()

        elif ftype == "dll":
            # dll created with py2exe
            path = typeinfo.GetModuleFileName(sys.frozendllhandle, MAX_PATH)
            base = os.path.splitext(os.path.basename(path))[0]
            subdir = rf"comtypes_cache\{base}-{pymaj:d}{pymin:d}"
            basedir = tempfile.gettempdir()

        else:  # ftype in ('windows_exe', 'console_exe')
            # exe created by py2exe
            base = os.path.splitext(os.path.basename(sys.executable))[0]
            subdir = rf"comtypes_cache\{base}-{pymaj:d}{pymin:d}"
            basedir = tempfile.gettempdir()

        gen_dir = os.path.join(basedir, subdir)
        if not os.path.exists(gen_dir):
            logger.info("Creating writeable comtypes cache directory: '%s'", gen_dir)
            os.makedirs(gen_dir)
        gen_path.append(gen_dir)
    result = os.path.abspath(gen_path[-1])
    logger.info("Using writeable comtypes cache directory: '%s'", result)
    return result


################################################################

_shell32 = ctypes.OleDLL("shell32.dll")
SHGetSpecialFolderPath = _shell32.SHGetSpecialFolderPathW
SHGetSpecialFolderPath.argtypes = [HWND, LPWSTR, ctypes.c_int, BOOL]
SHGetSpecialFolderPath.restype = BOOL

CSIDL_APPDATA = 26


def _create_comtypes_gen_package():
    """Import (creating it if needed) the comtypes.gen package."""
    try:
        import comtypes.gen

        logger.info("Imported existing %s", comtypes.gen)
    except ImportError:
        import comtypes

        logger.info("Could not import comtypes.gen, trying to create it.")
        try:
            comtypes_path = os.path.abspath(os.path.join(comtypes.__path__[0], "gen"))
            if not os.path.isdir(comtypes_path):
                os.mkdir(comtypes_path)
                logger.info("Created comtypes.gen directory: '%s'", comtypes_path)
            comtypes_init = os.path.join(comtypes_path, "__init__.py")
            if not os.path.exists(comtypes_init):
                logger.info("Writing __init__.py file: '%s'", comtypes_init)
                ofi = open(comtypes_init, "w")
                ofi.write("# comtypes.gen package, directory for generated files.\n")
                ofi.close()
        except OSError as details:
            logger.info("Creating comtypes.gen package failed: %s", details)
            module = sys.modules["comtypes.gen"] = types.ModuleType("comtypes.gen")
            comtypes.gen = module
            comtypes.gen.__path__ = []
            logger.info("Created a memory-only package.")


def _is_writeable(path):
    """Check if the first part, if any, on path is a directory in
    which we can create files."""
    if not path:
        return False
    # TODO: should we add os.X_OK flag as well? It seems unnecessary on Windows.
    return os.access(path[0], os.W_OK)


def _get_appdata_dir():
    """Return the 'file system directory that serves as a common
    repository for application-specific data' - CSIDL_APPDATA"""
    path = ctypes.create_unicode_buffer(MAX_PATH)
    # get u'C:\\Documents and Settings\\<username>\\Application Data'
    SHGetSpecialFolderPath(0, path, CSIDL_APPDATA, True)
    return path.value
