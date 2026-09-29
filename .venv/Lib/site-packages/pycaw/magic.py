"""
Note
----
'import pycaw.magic' must be generally at the topmost.
To be more specific:
It needs to be imported before any other pycaw or comtypes import.


Reserved Atrributes
-------------------
Note that certain methods and attributes are reserved for the magic module.
    Please look into the source code for more information.
But to avoid conflicts now and in the future, i recommend using
a prefix for each of your custom methods and attributes.


COM Note for DEVS
-----------------
in order for AudioSessionNotification::OnSessionCreated to work
the entry point needs to CoInitialize
the main thread in Multi-threaded Apartment (MTA).

All the other Notification will work in the "default" comtypes mode:
    Single-threaded Apartment (STA)

Its generally true that when you work with COM components,
that to need to match the apartment to the component.
But since we are only accessing COM components,
it works using a MTA client to access both STA and MTA COM objects.

"""

import atexit
import logging
import sys
import warnings

# ____ COM WITH MULTITHREADED APARTMENT ____
sys.coinit_flags = 0

import psutil

from ctypes import pointer
from _ctypes import COMError
from comtypes import GUID, COMObject

from pycaw.api.audioclient import ISimpleAudioVolume
from pycaw.api.audiopolicy import (
    IAudioSessionControl2,
    IAudioSessionEvents,
    IAudioSessionNotification,
)
from pycaw.constants import AudioSessionState
from pycaw.utils import AudioUtilities

log = logging.getLogger(__name__)
# use logging.INFO to skip the logs from the comtypes module

__all__ = ("MagicManager", "MagicApp", "MagicSession")


class MagicManager(COMObject):
    """
    The 'MagicManager' handles the magic.

    Features
    --------
    -   handles adding and removing sessions from a dictionary.
    -   the main dict 'magic_root_sessions' contains all active sessions.

    -   If one or more MagicApps are hooked into the MagicManager,
            (by creating a new instance of a MagicApp)
        the MagicManager will hand over the requested sessions when available.
            (Those sessions which match the MagicApp(app_exec)
            like firefox.exe)
        Multiple sessions can be controlled by one MagicApp by passing
        multiple app_exec as a set to MagicApp:
            MagicApp({"firefox.exe", "vlc.exe"})
        When an app name has multiple audio sessions,
        they will be automatically 'merged'

        Note that when using MagicApp in multi session mode, that getting the
        volume will result in getting the volume of the loudest session.
        Mute and State will return the max(*states) state.

    -   handles giving each Windows audio session an iid. (0, 1, 2 ...)
        and manage it based on that.

    -   unregister all (still active) sessions from callback at shutdown

    -   OnSessionCreated is fired by Windows everytime a new session registers
    """

    _com_interfaces_ = (IAudioSessionNotification,)
    magic_activated = False

    @classmethod
    def str(cls):
        """Get infos about the current state."""
        # __str__ wont work since MagicManager is a class
        if not cls.magic_activated:
            log.warning("Nothing to show. MagicManager needs to be activated")
            return "unactive MagicManager"

        return (
            f"<MagicManager magic_apps='{len(cls.magic_apps)}' "
            f"magic_sessions='{len(cls.magic_sessions)}' "
            f"active_mrs='{len(cls.magic_root_sessions)}' "
            f"trash_mrs='{len(cls.expired_magic_root_sessions)}'"
            "/>"
        )

    @classmethod
    def activate_magic(cls):
        """
        Gets only called once or never. Not on import.
        Depending if MagicApp or MagicSession are used.
        see:
            self.add_magic_app()
            self.magic_session()
        """
        if cls.magic_activated:
            warn = "cannot activate MagicManager. MagicManager is already active!"
            log.warning(warn)
            warnings.warn(warn)
            return

        if cls.magic_activated is None:
            warn = (
                "<MagicManager/> was already activated an closed. "
                "Trying to activate again - untested"
            )
            log.warning(warn)
            warnings.warn(warn)

        cls.magic_activated = True
        log.info(":: activate magic")

        # dict with idd -> magic_root_session -> _MagicRootSession
        cls.magic_root_sessions = {}
        cls.expired_magic_root_sessions = set()
        # pycaw internal instance identifier
        cls.iid_count = 0

        # set of MagicApp instances
        cls.magic_apps = set()

        # if registered via MagicManager.magic_session()
        # will hold the MagicSession and additional args + kwargs
        cls.MagicSessionConfigured = None
        # dict like magic_root_sessions but for the
        # magic_sessions wrappers
        cls.magic_sessions = {}

        try:
            cls._mgr = AudioUtilities.GetAudioSessionManager()
            log.debug("<MagicManager/> got manager")
        except COMError:
            cls.magic_activated = False
            warn = "<MagicManager/> No speaker connected"
            log.warning(warn)
            raise ValueError(warn)

        # RegisterSessionNotification needs an instance not a class
        cls._callback_magic_manager = cls()
        cls._mgr.RegisterSessionNotification(cls._callback_magic_manager)
        # has to get called -
        # to make IAudioSessionNotification::OnSessionCreated working
        sessionEnumerator = cls._mgr.GetSessionEnumerator()

        log.debug("<MagicManager/> registered and activated session notification")

        # Scan for running session and add them to session_manager

        # get all active sessions
        count = sessionEnumerator.GetCount()
        log.info(f"{count} sessions already active")

        # add sessions to session_manager
        log.debug("adding sessions manually")

        for i in range(count):
            ctl = sessionEnumerator.GetSession(i)
            cls.OnSessionCreated(ctl)

        # register clean up mechanism, when script is closed.
        atexit.register(cls.clean_up)

        log.info(cls.str())

    @classmethod
    def OnSessionCreated(cls, ctl):
        """Is fired, when a new audio session is created/found."""
        log.debug(":: new session")

        # create a pycaw internal instance identifier
        iid = cls.iid_count
        cls.iid_count += 1

        # create a new magic_root_session
        magic_root_session = _MagicRootSession(ctl, iid, cls)

        cls.magic_root_sessions[iid] = magic_root_session

        if cls.magic_apps:
            # add exe to matching magic app
            cls._match_sess_to_mapp(magic_root_session, iid)

        if cls.MagicSessionConfigured:
            # if MagicSession is configured via cls.magic_session()
            MagicSessionClass, args, kwargs = cls.MagicSessionConfigured
            magic_session = MagicSessionClass.initialize(
                magic_root_session, *args, **kwargs
            )
            cls.magic_sessions[iid] = magic_session

        log.info(cls.str())

    @classmethod
    def magic_session(cls, MagicSessionClass, *args, **kwargs):
        """
        gets called explicit by the user with a custom MagicSession.
        this will tell the MagicManager to create for all current
        and new sessions a custom MagicSession.
        """
        if not cls.magic_activated:
            cls.activate_magic()

        if cls.MagicSessionConfigured:
            raise NotImplementedError("only one MagicSession wrapper is allowed")

        for iid, magic_root_session in cls.magic_root_sessions.items():
            magic_session = MagicSessionClass.initialize(
                magic_root_session, *args, **kwargs
            )
            cls.magic_sessions[iid] = magic_session
        cls.MagicSessionConfigured = (MagicSessionClass, args, kwargs)

    @classmethod
    def add_magic_app(cls, magic_app, app_execs):
        """
        gets called when a new magic_app is created.
        this will tell the MagicManager add all current and
        new matching sessions by app_execs to the magic_app.
        """
        if not cls.magic_activated:
            cls.activate_magic()
        log.info(f"searching matching active sessions for: {magic_app}")
        for app_exec in app_execs:
            for iid, magic_root_session in cls.magic_root_sessions.items():
                # and not magic_root_session.magic_app
                # will prohibit multiple magic_apps to use the same
                # magic_root_session
                if (
                    magic_root_session.app_exec == app_exec
                    and not magic_root_session.magic_app
                ):
                    log.info(f"{magic_root_session} matched {magic_app}.")
                    magic_app.add_magic_root_session(iid, magic_root_session)

        # keep reference to magic_app to check later
        # if new session should be added to this magic_app
        cls.magic_apps.add(magic_app)
        log.info(f"{magic_app} added to watchlist. {cls.str()}")

    @classmethod
    def _match_sess_to_mapp(cls, magic_root_session, iid):
        log.info(f"searching matching magic_app for: {magic_root_session}")
        new_app_exec = magic_root_session.app_exec
        for magic_app in cls.magic_apps:
            for app_exec in magic_app.app_execs:
                if app_exec == new_app_exec:
                    log.info(f"Match {magic_root_session} {magic_app}")
                    magic_app.add_magic_root_session(iid, magic_root_session)
                    # return will prohibit multiple magic_apps
                    # to use the same magic_root_session
                    return

    @classmethod
    def remove_session(cls, iid, magic_app=None):
        """magic_root_session will get removed because it is expired"""
        # pop(iid, None) must not be necessary
        magic_root_session = cls.magic_root_sessions.pop(iid)

        log.info(f":: removed {magic_root_session}")

        # deactivate "trash" solution by commenting:
        cls.expired_magic_root_sessions.add(magic_root_session)

        # unregister callback
        # (magic_root_session -> _MagicRootSession -> IAudioSessionEvents)
        magic_root_session.unregister_notification()

        # delete iid also from magic_app or magic_session
        if cls.MagicSessionConfigured:
            # pop session from magic sessions dict
            del_magic_sessions = cls.magic_sessions.pop(iid)

            # remove circular references
            magic_root_session.magic_session = None
            del_magic_sessions.magic_root_session = None

        # try to remove session from the magic_app dict which is in possession
        if magic_app:
            # pop(iid, None) must not be necessary
            magic_app.magic_root_sessions.pop(iid)

            # remove circular references
            magic_root_session.magic_app = None

            log.info(f":: :: removed {magic_root_session} from {magic_app}")

        log.info(cls.str())

    @classmethod
    def empty_trash(cls):
        while cls.expired_magic_root_sessions:
            to_remove = cls.expired_magic_root_sessions.pop()
            log.info(
                f":: :: :: release <POINTER(IAudioSessionControl2)/> from {to_remove}"
            )

            # at this point it is already unregistered ...
            # see cls.remove_session()
            # to_remove.unregister_notification()

    @classmethod
    def clean_up(cls):
        log.info(":: reverse spell")
        cls._mgr.UnregisterSessionNotification(cls._callback_magic_manager)
        log.info(f":: :: unregistered {cls.str()}")
        cls.unregister_all()

    @classmethod
    def unregister_all(cls):
        # since cls.magic_root_sessions can always change (multithreading)
        # instead of a for loop I present you the while loop:
        # while cls.magic_root_sessions contains any items,
        # they get popped and unregistered
        log.debug(f"unregister {len(cls.magic_root_sessions)} sessions.")
        while cls.magic_root_sessions:
            # ________ REMOVES 1 ITEM FROM LIST ________

            _, session = cls.magic_root_sessions.popitem()
            session.unregister_notification()
            log.info(f":: :: :: unregistered {session}")

        # XXX remove old session:
        # this is the only place where it works,
        # since it is user controlled and not
        # in a windows COM callback.
        cls.empty_trash()

        log.info(f"Bye {cls.str()}")

        del cls.magic_apps
        del cls.magic_sessions

        cls.magic_activated = None


def for_session_in_sessions(func):
    """Decorator for looping through sessions in MagicApp."""

    def wrapper(self, *args):
        if self.magic_root_sessions is None:
            # nothing to change
            return

        # RuntimeError: dictionary changed size during iteration
        temp_sessions = dict(self.magic_root_sessions)
        rv = [func(self, session, *args) for session in temp_sessions.values()]

        # max([None, None]) -> TypeError: '>' not supported ...
        rv_no_none = [r for r in rv if r is not None]

        # when rv = [None] -> rv_no_none = None
        if rv_no_none:
            # return if multiple sessions the one
            # with mute true or the highest volume
            # or the session with the highest AudioSessionState.value
            return max(rv_no_none)

    return wrapper


class _MagicAudioControl:
    """Simplifies the audio control by using the self.properties."""

    # TODO:
    # MagicApp, MagicSession and for_session_in_sessions to handle incorrect
    # input or raise exception.
    # also handle failing com calls
    # (failing in terms of the retrieved value is not 'S_OK')
    #   it will happen, when the speaker is gets disconnected!
    #   can be also fixed by implementing OnSessionDisconnected
    #   since OnSessionDisconnected will notify if the Speaker is unplugged.

    def toggle_mute(self):
        new_mute = not self.mute
        self.mute = new_mute
        return new_mute

    def step_volume(self, step=0.1):
        current = self.volume
        if current is None:
            return
        new = max(0, min(1, current + step))
        if new != current:
            self.volume = new
            return new


class MagicApp(_MagicAudioControl):
    """
    When instantiated with at least one app_execs name,
    will be able to get/ set volume etc, also if the
    session is created after initialize.
    """

    guid = pointer(GUID("{E0BD1A40-9624-44FC-A607-2ED4F00B1CC4}"))

    def __init__(
        self,
        app_execs,
        volume_callback=None,
        advanced_volume_callback=None,
        mute_callback=None,
        advanced_mute_callback=None,
        state_callback=None,
        session_callback=None,
    ):
        # normalize app_execs
        if isinstance(app_execs, str):
            # if string directly to set: {'a', 'b', 'c'}
            app_execs = (app_execs,)
        self.app_execs = set(app_execs)

        # latest dict of matching sessions
        self.magic_root_sessions = {}

        # callbacks
        self.volume_callback = volume_callback
        self.mute_callback = mute_callback
        self.state_callback = state_callback
        self.session_callback = session_callback

        self.advanced_volume_callback = advanced_volume_callback
        self.advanced_mute_callback = advanced_mute_callback

        log.info(str(self))
        MagicManager.add_magic_app(self, app_execs)

    def add_magic_root_session(self, iid, magic_root_session):
        """called by MagicManager, when a new matching session is found"""
        self.magic_root_sessions[iid] = magic_root_session
        # tells the magic_root_session to create a connection
        # for callbacks.
        magic_root_session.use_magic_app(self)

        log.info(f"Added {magic_root_session} to {self}.")

        # session callback is implemented here:
        if self.session_callback:
            self.session_callback(magic_root_session)

    def __str__(self):
        return (
            f"<{self.__class__.__name__} "
            f"registered-for='{self.app_execs}' "
            f"controls-sessions='{len(self.magic_root_sessions)}'/>"
        )

    # easy control:
    @property
    @for_session_in_sessions
    def state(self, magic_root_session):
        return magic_root_session.state

    @property
    @for_session_in_sessions
    def volume(self, magic_root_session):
        return magic_root_session.volume

    @volume.setter
    @for_session_in_sessions
    def volume(self, magic_root_session, volume):
        magic_root_session._sav.SetMasterVolume(volume, self.guid)

    @property
    @for_session_in_sessions
    def mute(self, magic_root_session):
        return magic_root_session.mute

    @mute.setter
    @for_session_in_sessions
    def mute(self, magic_root_session, mute):
        magic_root_session._sav.SetMute(mute, self.guid)


class MagicSession(_MagicAudioControl):
    """
    When activated and passed via
    MagicManager.magic_session(inherited_class_of_MagicSession)
    will be created for each new and current session.
    Dict of all iid -> MagicSession:
        MagicManager.magic_sessions
    """

    guid = pointer(GUID("{34482A3D-37DD-40E3-BB37-63A16036C87C}"))

    def __init__(
        self,
        volume_callback=None,
        advanced_volume_callback=None,
        mute_callback=None,
        advanced_mute_callback=None,
        state_callback=None,
    ):
        self.magic_root_session = self._passed_magic_root_session
        self._passed_magic_root_session = None

        # callbacks
        self.volume_callback = volume_callback
        self.mute_callback = mute_callback
        self.state_callback = state_callback

        self.advanced_volume_callback = advanced_volume_callback
        self.advanced_mute_callback = advanced_mute_callback

        # tells the magic_root_session to create a connection
        # for callbacks:
        self.magic_root_session.use_magic_session(self)

        log.info(str(self))

    @classmethod
    def initialize(cls, new_magic_root_session, *args, **kwargs):
        """
        is called by the MagicManager.

        Every new MagicSession needs to have a magic_root_session.

        instead of passing it visible as argument trough the inherited class
        back to the super().__init(new_magic_root_session) -

        the new_magic_root_session it is transferred by setting
        a class attribute and picking it up in the MagicSession.__init__()

        class PassingViaArg(MagicSession):
            def __init__(self, new_magic_root_session, *args, **kwargs):
                super().__init__(new_magic_root_session)

        class PassingViaClassAttr(MagicSession):
            def __init__(self, *args, **kwargs):
                super().__init__()
        """
        cls._passed_magic_root_session = new_magic_root_session

        magic_session = cls(*args, **kwargs)
        return magic_session

    def __str__(self):
        return (
            f"<{self.__class__.__name__} "
            f"app_exec='{self.magic_root_session.app_exec}'/>"
        )

    # easy control:
    @property
    def state(self):
        return self.magic_root_session.state

    @property
    def volume(self):
        return self.magic_root_session.volume

    @volume.setter
    def volume(self, volume):
        self.magic_root_session._sav.SetMasterVolume(volume, self.guid)

    @property
    def mute(self):
        return self.magic_root_session.mute

    @mute.setter
    def mute(self, mute):
        self.magic_root_session._sav.SetMute(mute, self.guid)


class _MagicGuidCompare:
    """
    Helper that is passed when 'advanced_xxx_callback=True'
    see _MagicRootSession._send_callback()
    """

    def __init__(self, master_guid, changer_guid):
        # the pointer(GUID("guid")) of the 'master'
        self.master = master_guid
        # the pointer(GUID("guid")) of the 'changer'
        self.changer = changer_guid

        compare = master_guid.contents != changer_guid.contents
        # True if changes are made external.
        self.compare = compare

    def __str__(self):
        return (
            f"<{self.__class__.__name__} "
            f"changed-external='{self.compare}' "
            f"master='{self.master.contents}' "
            f"changer='{self.changer.contents}'/>"
        )

    def __bool__(self):
        """Returns True if changes are made external."""
        return self.compare


class _MagicRootSession(COMObject):
    """Base session control with callback functionality"""

    _com_interfaces_ = (IAudioSessionEvents,)

    def __init__(self, ctl, iid, magic_manager):
        self._ctl2 = ctl.QueryInterface(IAudioSessionControl2)
        self.app_exec = self._get_app_exec()
        self._sav = None
        self.magic_manager = magic_manager
        self.iid = iid

        self.magic_app = None
        self.magic_session = None

        self.volume = None
        self.mute = None

        new_state_id = self._ctl2.GetState()
        self.state = AudioSessionState(new_state_id)

        self._activated = False

        self.register_notification()

        log.info(f":: created {self}")

    def __str__(self):
        return f"<{self.__class__.__name__} app='{self.app_exec}'/>"

    # only one magic_app at the time is able to
    # control and view this magic_root_session.
    # a second magic_app is blocked via the MagicManager ...
    # see:
    # MagicManager.add_magic_app() -> if not magic_root_session.magic_app
    # MagicManager._match_sess_to_mapp() -> return if match

    # TODO Feature:
    # allow multiple magic_app for one magic_root_session?
    # If multiple magic_app would be allowed:
    # Looping through multiple magic_app and checking for
    # callbacks in each would cost lots of time right?
    # any solution?
    #
    # or it could use this sessions without callbacks.
    #
    # also the session remove handle wouldnt work.

    def use_magic_app(self, magic_app):
        self.magic_app = magic_app
        self._activate()

    def use_magic_session(self, magic_session):
        self.magic_session = magic_session
        self._activate()

    def _activate(self):
        # activates this magic_root_session.
        # callbacks wont be "ignored", and volume and mute
        # will be saved to attributes.
        if not self._activated:
            self._sav = self._ctl2.QueryInterface(ISimpleAudioVolume)
            self.volume = self._sav.GetMasterVolume()
            self.mute = self._sav.GetMute()

            self._activated = True

    def OnSimpleVolumeChanged(self, new_volume, new_mute, event_context):
        """Is fired, when the audio session volume/mute changed."""
        log.debug(
            f"OnSimpleVolumeChanged: {self.app_exec} "
            f"Vol: ~{new_volume} Mute: {new_mute}"
        )
        # only make callbacks and update internal volume and mute
        # if someone is listening

        if not self._activated:
            return

        # check old volume vs new:
        if self.volume != new_volume:
            # self.volume will keep the none state
            # until self._activate()
            self.volume = new_volume

            # send callbacks, if callback exists
            self._send_callback(
                self.magic_app, "volume_callback", event_context, new_volume
            )

            self._send_callback(
                self.magic_session, "volume_callback", event_context, new_volume
            )

        # check old mute vs new:
        if self.mute != new_mute:
            # self.mute will keep the none state
            # until self._activate()
            self.mute = new_mute

            # send callbacks, if callback exists
            self._send_callback(
                self.magic_app, "mute_callback", event_context, new_mute
            )

            self._send_callback(
                self.magic_session, "mute_callback", event_context, new_mute
            )

    @staticmethod
    def _send_callback(master, callback, changer_guid, value):
        """
        Send callbacks, if callback exists.

        The default is, that callbacks which are made
        by MagicApp or MagicSession get filtered out

        The hooks 'advanced_volume_callback' or 'advanced_mute_callback'
        Dont filter the callback based on the changer.

        The 'compare' argument is an instance of _MagicGuidCompare

        compare == True
            not: 'compare is True'

        if the changer guid is external.
        """

        # get the callback method from the master.
        # will be None if the user didnt hook into it
        # or if master = None

        if master is None:
            return

        master_advanced_callback = getattr(master, "advanced_" + callback)
        master_callback = getattr(master, callback)

        # TODO: Does this safe resources, since _MagicGuidCompare is not
        # always instantiated?
        if master_callback is None and master_advanced_callback is None:
            return

        # create a new _MagicGuidCompare which will compare
        # changer_guid and master.guid
        compare = _MagicGuidCompare(master.guid, changer_guid)

        if master_advanced_callback:
            master_advanced_callback(value, compare)
            # TODO:
            # return or allow also simple callback?

        if master_callback and compare:
            # if the the callback is not caused by master.guid
            # then send simple callback
            master_callback(value)

    def OnStateChanged(self, new_state_id):
        """Is fired, when the audio session state changed."""
        self.state = AudioSessionState(new_state_id)

        # send callbacks, if defined
        if self.magic_app and self.magic_app.state_callback:
            self.magic_app.state_callback(self.state)

        if self.magic_session and self.magic_session.state_callback:
            self.magic_session.state_callback(self.state)

        if self.state == AudioSessionState.Expired:
            """
            calling the MagicManager to remove this magic_root_session.

            The MagicManager will unregister_notification()
            """

            # XXX remove old session:
            # self.magic_manager.empty_trash()
            # Empty trash should do the following:
            # Release <POINTER(IAudioSessionControl2)
            # ptr=xxxxxxxxx at xxxxxxxxx>
            # ... but that would only work if empty_trash()
            # is triggered by the user and not via a callback

            self.magic_manager.remove_session(self.iid, self.magic_app)

            # XXX remove old session:
            # would crash the app:
            # self._ctl2 = None
            # or:
            # self._ctl2.Release()

    def _get_app_exec(self):
        """Returns the executable name based on the process id."""
        self.pid = self._ctl2.GetProcessId()

        if self.pid != 0:
            try:
                return psutil.Process(self.pid).name()
            except psutil.NoSuchProcess:
                return None

        # System Sound:
        # self._ctl2.GetDisplayName() returns:
        # @%SystemRoot%\System32\AudioSrv.Dll,-202
        # and self._ctl2.IsSystemSoundsSession() returns S_OK
        # for system sounds

        returned_HRESULT = self._ctl2.IsSystemSoundsSession()

        # Possible returned_HRESULTs:
        S_OK = 0
        # S_FALSE = 1

        if returned_HRESULT == S_OK:
            return "SndVol.exe"
        else:
            warn = (
                "unidentified app! "
                f"pid: {self.pid}, is system sound: {returned_HRESULT}"
            )
            log.critical(warn)
            raise ValueError(warn)

    # TODO: Feature
    # implement:
    # def OnSessionDisconnected(self, disconnect_reason_id): pass

    def register_notification(self):
        self._ctl2.RegisterAudioSessionNotification(self)

    def unregister_notification(self):
        self._ctl2.UnregisterAudioSessionNotification(self)
