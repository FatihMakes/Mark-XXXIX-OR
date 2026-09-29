from ctypes import addressof, c_float, pointer

from comtypes import COMObject

from pycaw.api.audiopolicy import (
    IAudioSessionControl2,
    IAudioSessionEvents,
    IAudioSessionNotification,
)
from pycaw.api.endpointvolume import IAudioEndpointVolumeCallback
from pycaw.api.endpointvolume.depend import AUDIO_VOLUME_NOTIFICATION_DATA
from pycaw.api.mmdeviceapi import IMMNotificationClient
from pycaw.utils import AudioSession


class AudioSessionNotification(COMObject):
    """
    Callback handler for audio session creation events.

    To use this class, subclass it and override the `on_session_created` method.

    Notes
    -----
    AudioSessionNotification requires Multi-Threaded Apartment (MTA) COM
    initialization. Follow these steps:

    1. Set COM to MTA mode before importing pycaw or comtypes::

        import sys
        sys.coinit_flags = 0

    2. Get the AudioSessionManager::

        from pycaw.utils import AudioUtilities
        mgr = AudioUtilities.GetAudioSessionManager()

    3. Create and register your callback subclass::

        class MyCallback(AudioSessionNotification):
            def on_session_created(self, new_session):
                print(f"New session created: {new_session}")

        callback = MyCallback()
        mgr.RegisterSessionNotification(callback)

    4. Activate notifications by calling GetSessionEnumerator::

        mgr.GetSessionEnumerator()

    5. Unregister when finished::

        mgr.UnregisterSessionNotification(callback)

    See Also
    --------
    AudioUtilities.GetAudioSessionManager : Get the session manager instance
    """

    _com_interfaces_ = (IAudioSessionNotification,)

    def OnSessionCreated(self, new_session):
        ctl2 = new_session.QueryInterface(IAudioSessionControl2)
        new_session = AudioSession(ctl2)
        self.on_session_created(new_session)

    def on_session_created(self, new_session):
        """
        Called when a new audio session is created.

        Override this method in your subclass to handle session creation events.

        Parameters
        ----------
        new_session : AudioSession
            The newly created audio session object

        Raises
        ------
        NotImplementedError
            This base implementation must be overridden in subclasses
        """
        raise NotImplementedError


class AudioSessionEvents(COMObject):
    """
    Callback handler for audio session state and property changes.

    Subclass this class and override any of the callback methods to handle
    specific events related to an audio session's state, volume, or properties.

    Examples
    --------
    Create a custom callback to monitor session volume changes::

        class VolumeMonitor(AudioSessionEvents):
            def on_simple_volume_changed(self, new_volume, new_mute, event_context):
                mute_str = "muted" if new_mute else "unmuted"
                print(f"Volume changed: {new_volume:.2f}, {mute_str}")

    See Also
    --------
    AudioSession : Represents an audio session that can be monitored
    """

    _com_interfaces_ = (IAudioSessionEvents,)

    # ======= DECODE RETURNED INT VALUE =======
    # see audiosessiontypes.h and audiopolicy.h
    AudioSessionState = ("Inactive", "Active", "Expired")

    AudioSessionDisconnectReason = (
        "DeviceRemoval",
        "ServerShutdown",
        "FormatChanged",
        "SessionLogoff",
        "SessionDisconnected",
        "ExclusiveModeOverride",
    )

    def OnDisplayNameChanged(self, new_display_name, event_context):
        self.on_display_name_changed(new_display_name, event_context)

    def OnIconPathChanged(self, new_icon_path, event_context):
        self.on_icon_path_changed(new_icon_path, event_context)

    def OnSimpleVolumeChanged(self, new_volume, new_mute, event_context):
        self.on_simple_volume_changed(new_volume, new_mute, event_context)

    def OnChannelVolumeChanged(
        self, channel_count, new_channel_volume_array, changed_channel, event_context
    ):
        channel_volumes = list(new_channel_volume_array[:channel_count])
        self.on_channel_volume_changed(
            channel_count, channel_volumes, changed_channel, event_context
        )

    def OnGroupingParamChanged(self, new_grouping_param, event_context):
        self.on_grouping_param_changed(new_grouping_param, event_context)

    def OnStateChanged(self, new_state_id):
        new_state = self.AudioSessionState[new_state_id]
        self.on_state_changed(new_state, new_state_id)

    def OnSessionDisconnected(self, disconnect_reason_id):
        disconnect_reason = self.AudioSessionDisconnectReason[disconnect_reason_id]
        self.on_session_disconnected(disconnect_reason, disconnect_reason_id)

    def on_display_name_changed(self, new_display_name, event_context):
        """
        Called when the audio session display name changes.

        Parameters
        ----------
        new_display_name : str
            The new display name for the audio session
        event_context : comtypes.GUID
            GUID identifying who made the change. Access string representation
            via event_context.contents
        """
        pass

    def on_icon_path_changed(self, new_icon_path, event_context):
        """pycaw user interface"""
        pass

    def on_simple_volume_changed(self, new_volume, new_mute, event_context):
        """
        Called when the audio session volume or mute state changes.

        Parameters
        ----------
        new_volume : float
            New master volume level in range [0.0, 1.0]
        new_mute : int
            Mute state: 0 (unmuted) or 1 (muted)
        event_context : comtypes.GUID
            GUID identifying who made the change. Access string representation
            via event_context.contents
        """
        pass

    def on_channel_volume_changed(
        self, channel_count, new_channel_volume_array, changed_channel, event_context
    ):
        """
        Called when an audio session channel volume changes.

        Parameters
        ----------
        channel_count : int
            Number of audio channels
        new_channel_volume_array : list of float
            Per-channel volume levels in range [0.0, 1.0]. Length equals
            channel_count
        changed_channel : int
            Index of the channel whose volume changed
        event_context : comtypes.GUID
            GUID identifying who made the change. Access string representation
            via event_context.contents
        """
        pass

    def on_grouping_param_changed(self, new_grouping_param, event_context):
        """pycaw user interface"""
        pass

    def on_state_changed(self, new_state, new_state_id):
        """
        Called when the audio session state changes.

        Parameters
        ----------
        new_state : str
            New state as string: "Inactive", "Active", or "Expired"
        new_state_id : int
            Numeric state code: 0 (Inactive), 1 (Active), or 2 (Expired)
        """
        pass

    def on_session_disconnected(self, disconnect_reason, disconnect_reason_id):
        """
        Called when the audio session is disconnected.

        Note: In most cases, you should use on_state_changed with state "Expired"
        instead, as it provides more reliable notification.

        Parameters
        ----------
        disconnect_reason : str
            Reason for disconnection as string (see AudioSessionDisconnectReason)
        disconnect_reason_id : int
            Numeric disconnect reason code
        """
        pass


class AudioEndpointVolumeCallback(COMObject):
    """
    Callback handler for audio endpoint (device) volume changes.

    Subclass this class and override the `on_notify` method to handle
    notifications when an audio device's volume or mute state changes.

    Examples
    --------
    Monitor the default audio device for volume changes::

        class DeviceVolumeMonitor(AudioEndpointVolumeCallback):
            def on_notify(self, new_volume, new_mute, event_context,
                          channels, channel_volumes):
                print(f"Device volume: {new_volume:.2f}, muted: {new_mute}")

        device = AudioUtilities.GetSpeakers()
        callback = DeviceVolumeMonitor()
        device.EndpointVolume.RegisterControlChangeNotify(callback)

    See Also
    --------
    AudioDevice.EndpointVolume : Access endpoint volume control interface
    """

    _com_interfaces_ = (IAudioEndpointVolumeCallback,)

    def OnNotify(self, pNotify):
        """Fired by Windows, when the audio device volume/mute changed"""

        # get the data of the PAUDIO_VOLUME_NOTIFICATION_DATA Structure
        notify_data = pNotify.contents

        channels = notify_data.nChannels
        channel_array = (c_float * channels).from_address(
            addressof(notify_data)
            + AUDIO_VOLUME_NOTIFICATION_DATA.afChannelVolumes.offset
        )
        channel_volumes = list(channel_array)

        event_context = pointer(notify_data.guidEventContext)

        self.on_notify(
            notify_data.fMasterVolume,
            notify_data.bMuted,
            event_context,
            channels,
            channel_volumes,
        )

    def on_notify(self, new_volume, new_mute, event_context, channels, channel_volumes):
        """
        Called when the audio endpoint volume or mute state changes.

        Override this method in your subclass to handle volume change notifications.

        Parameters
        ----------
        new_volume : float
            Master volume level in range [0.0, 1.0]
        new_mute : int
            Mute state: 0 (unmuted) or 1 (muted)
        event_context : comtypes.GUID
            GUID identifying who made the change. Access string representation
            via event_context.contents
        channels : int
            Number of audio channels
        channel_volumes : list of float
            Per-channel volume levels in range [0.0, 1.0].
            Length equals the channels parameter

        Raises
        ------
        NotImplementedError
            This base implementation must be overridden in subclasses
        """
        raise NotImplementedError


class MMNotificationClient(COMObject):
    """
    Callback handler for audio endpoint device events.

    Subclass this class and override any callback methods to handle events
    such as device addition, removal, state changes, or default device changes.

    Examples
    --------
    Monitor for device additions and removals::

        class DeviceMonitor(MMNotificationClient):
            def on_device_added(self, added_device_id):
                print(f"Device added: {added_device_id}")

            def on_device_removed(self, removed_device_id):
                print(f"Device removed: {removed_device_id}")

        enumerator = AudioUtilities.GetDeviceEnumerator()
        monitor = DeviceMonitor()
        enumerator.RegisterEndpointNotificationCallback(monitor)

    See Also
    --------
    AudioUtilities.GetDeviceEnumerator : Get the device enumerator
    """

    _com_interfaces_ = (IMMNotificationClient,)

    DeviceStates = {1: "Active", 2: "Disabled", 4: "NotPresent", 8: "Unplugged"}
    Roles = ["eConsole", "eMultimedia", "eCommunications", "ERole_enum_count"]
    DataFlow = ["eRender", "eCapture", "eAll", "EDataFlow_enum_count"]

    def OnDefaultDeviceChanged(self, flow_id, role_id, default_device_id):
        flow = self.DataFlow[flow_id]
        role = self.Roles[role_id]
        self.on_default_device_changed(flow, flow_id, role, role_id, default_device_id)

    def OnDeviceAdded(self, added_device_id):
        self.on_device_added(added_device_id)

    def OnDeviceRemoved(self, removed_device_id):
        self.on_device_removed(removed_device_id)

    def OnDeviceStateChanged(self, device_id, new_state_id):
        new_state = self.DeviceStates[new_state_id]
        self.on_device_state_changed(device_id, new_state, new_state_id)

    def OnPropertyValueChanged(self, device_id, property_struct):
        fmtid = property_struct.fmtid
        pid = property_struct.pid
        self.on_property_value_changed(device_id, property_struct, fmtid, pid)

    def on_default_device_changed(
        self, flow, flow_id, role, role_id, default_device_id
    ):
        """
        Called when the default audio device for a role changes.

        Parameters
        ----------
        flow : str
            Data flow direction as string (e.g., "eRender", "eCapture")
        flow_id : int
            Numeric data flow direction code
        role : str
            Device role as string (e.g., "eConsole", "eMultimedia")
        role_id : int
            Numeric role code
        default_device_id : str
            Device ID of the new default device
        """
        pass

    def on_device_added(self, added_device_id):
        """
        Called when a new audio endpoint device is added.

        Parameters
        ----------
        added_device_id : str
            Device ID of the newly added device
        """
        pass

    def on_device_removed(self, removed_device_id):
        """
        Called when an audio endpoint device is removed.

        Parameters
        ----------
        removed_device_id : str
            Device ID of the removed device
        """
        pass

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        """
        Called when an audio endpoint device state changes.

        Parameters
        ----------
        device_id : str
            Device ID of the device that changed state
        new_state : str
            New state as string (e.g., "Active", "Disabled", "NotPresent")
        new_state_id : int
            Numeric state code (see DeviceStates class attribute)
        """
        pass

    def on_property_value_changed(self, device_id, property_struct, fmtid, pid):
        """
        Called when a device property value changes.

        Parameters
        ----------
        device_id : str
            Device ID of the device with changed property
        property_struct : pycaw.api.mmdeviceapi.depend.structures.PROPERTYKEY
            Structure containing the property GUID and PID
        fmtid : comtypes.GUID
            GUID of the changed property
        pid : int
            Property identifier (PID) of the changed property
        """
        pass
