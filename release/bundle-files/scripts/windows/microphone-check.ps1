$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorClass {}
[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
 [PreserveSig] int EnumAudioEndpoints(int flow, uint mask, out IntPtr devices);
 [PreserveSig] int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice device);
 [PreserveSig] int GetDevice([MarshalAs(UnmanagedType.LPWStr)] string id, out IMMDevice device);
 [PreserveSig] int RegisterEndpointNotificationCallback(IntPtr callback);
 [PreserveSig] int UnregisterEndpointNotificationCallback(IntPtr callback);
}
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
 [PreserveSig] int Activate(ref Guid iid, uint context, IntPtr parameters, [MarshalAs(UnmanagedType.IUnknown)] out object obj);
 [PreserveSig] int OpenPropertyStore(uint access, out IntPtr store);
 [PreserveSig] int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
 [PreserveSig] int GetState(out uint state);
}
[ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
 [PreserveSig] int RegisterControlChangeNotify(IntPtr callback);
 [PreserveSig] int UnregisterControlChangeNotify(IntPtr callback);
 [PreserveSig] int GetChannelCount(out uint count);
 [PreserveSig] int SetMasterVolumeLevel(float db, ref Guid context);
 [PreserveSig] int SetMasterVolumeLevelScalar(float scalar, ref Guid context);
 [PreserveSig] int GetMasterVolumeLevel(out float db);
 [PreserveSig] int GetMasterVolumeLevelScalar(out float scalar);
 [PreserveSig] int SetChannelVolumeLevel(uint channel, float db, ref Guid context);
 [PreserveSig] int SetChannelVolumeLevelScalar(uint channel, float scalar, ref Guid context);
 [PreserveSig] int GetChannelVolumeLevel(uint channel, out float db);
 [PreserveSig] int GetChannelVolumeLevelScalar(uint channel, out float scalar);
 [PreserveSig] int SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, ref Guid context);
 [PreserveSig] int GetMute([MarshalAs(UnmanagedType.Bool)] out bool mute);
 [PreserveSig] int GetVolumeStepInfo(out uint step, out uint count);
 [PreserveSig] int VolumeStepUp(ref Guid context);
 [PreserveSig] int VolumeStepDown(ref Guid context);
 [PreserveSig] int QueryHardwareSupport(out uint mask);
 [PreserveSig] int GetVolumeRange(out float min, out float max, out float increment);
}
public class EndpointInfo {
 public int Role {get;set;}
 public string Id {get;set;}
 public uint State {get;set;}
 public uint Channels {get;set;}
 public bool Muted {get;set;}
 public float VolumePercent {get;set;}
 public float VolumeDb {get;set;}
 public uint HardwareSupport {get;set;}
 public int Error {get;set;}
}
public static class MicrophoneEndpoint {
 public static EndpointInfo[] Inspect() {
  var result = new List<EndpointInfo>();
  var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorClass());
  try {
   for(int role=0; role<3; ++role) {
    var info = new EndpointInfo { Role=role };
    IMMDevice device;
    int hr=enumerator.GetDefaultAudioEndpoint(1,role,out device);
    if(hr<0) { info.Error=hr; result.Add(info); continue; }
    try {
     string id; uint state;
     Marshal.ThrowExceptionForHR(device.GetId(out id));
     Marshal.ThrowExceptionForHR(device.GetState(out state));
     info.Id=id; info.State=state;
     var iid=typeof(IAudioEndpointVolume).GUID; object obj;
     Marshal.ThrowExceptionForHR(device.Activate(ref iid,23,IntPtr.Zero,out obj));
     try {
      var volume=(IAudioEndpointVolume)obj;
      bool muted; float scalar,db; uint channels,hw;
      Marshal.ThrowExceptionForHR(volume.GetMute(out muted));
      Marshal.ThrowExceptionForHR(volume.GetMasterVolumeLevelScalar(out scalar));
      Marshal.ThrowExceptionForHR(volume.GetMasterVolumeLevel(out db));
      Marshal.ThrowExceptionForHR(volume.GetChannelCount(out channels));
      Marshal.ThrowExceptionForHR(volume.QueryHardwareSupport(out hw));
      info.Muted=muted; info.VolumePercent=scalar*100; info.VolumeDb=db;
      info.Channels=channels; info.HardwareSupport=hw;
     } finally { Marshal.ReleaseComObject(obj); }
    } finally { Marshal.ReleaseComObject(device); }
    result.Add(info);
   }
  } finally { Marshal.ReleaseComObject(enumerator); }
  return result.ToArray();
 }
}
'@
$microphones = [MicrophoneEndpoint]::Inspect()
$microphones | ConvertTo-Json -Compress
if ($microphones | Where-Object Muted) {
    Write-Host 'Microphone is muted in Windows. Unmute it in Sound > Recording > Levels (or with the laptop microphone key).'
} else {
    Write-Host 'The default microphone is not muted. This check does not record audio or change settings.'
}
