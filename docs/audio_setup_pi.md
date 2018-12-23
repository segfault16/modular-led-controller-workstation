# Audio Setup on RaspberryPi

## Using USB audio device

Any class-compliant USB interface should work.
Tested and recommended: https://www.esi-audio.com/products/ugm96/

In order to configure the USB audio device as default device:

Create/edit `/etc/asound.conf`
```
sudo nano /etc/asound.conf
```
Set the file to the following text
```
pcm.!default {
    type hw
    card 1
}
ctl.!default {
    type hw
    card 1
}
```

Next, set the USB device to as the default device by editing `/usr/share/alsa/alsa.conf`
```
sudo nano /usr/share/alsa/alsa.conf:
```
Change
```
defaults.ctl.card 0
defaults.pcm.card 0
```
To
```
defaults.ctl.card 1
defaults.pcm.card 1
```

## Using virtual loopback device

RaspberryPi has no audio input devices. See e.g. following output:

```bash
python3 server.py -A -1
```

Lists the following devices:

```bash
...
bcm2835 ALSA: - (hw:0,0)
	Device index: 0
	Sample rate: 44100.0
	Max input channels: 0
	Max output channels: 2
bcm2835 ALSA: IEC958/HDMI (hw:0,1)
	Device index: 1
	Sample rate: 44100.0
	Max input channels: 0
	Max output channels: 2
sysdefault
	Device index: 2
	Sample rate: 44100.0
	Max input channels: 0
	Max output channels: 128
default
	Device index: 3
	Sample rate: 44100.0
	Max input channels: 0
	Max output channels: 128
dmix
	Device index: 4
	Sample rate: 48000.0
	Max input channels: 0
	Max output channels: 2
...
```

If you want to play audio from your RaspberryPi and feed it into the server, we need to configure a loopback audio device. For that we need to know what the audio card is called.

```bash
aplay -L
```

Lists the available devices:
```
null
    Discard all samples (playback) or generate zero samples (capture)
default:CARD=ALSA
    bcm2835 ALSA, bcm2835 ALSA
    Default Audio Device
sysdefault:CARD=ALSA
    bcm2835 ALSA, bcm2835 ALSA
    Default Audio Device
dmix:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct sample mixing device
dmix:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct sample mixing device
dsnoop:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct sample snooping device
dsnoop:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct sample snooping device
hw:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct hardware device without any conversions
hw:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct hardware device without any conversions
plughw:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Hardware device with all software conversions
plughw:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Hardware device with all software conversions
```

Note the `CARD=ALSA` entry.

You can verify that your audio is working by playing a .wav file:
```bash
aplay SomeWav.wav
```



Install the snd_loopback module:
```bash
sudo modprobe snd-aloop pcm_substreams=1
```

Running `aplay -L` again:
```bash
null
    Discard all samples (playback) or generate zero samples (capture)
default:CARD=ALSA
    bcm2835 ALSA, bcm2835 ALSA
    Default Audio Device
sysdefault:CARD=ALSA
    bcm2835 ALSA, bcm2835 ALSA
    Default Audio Device
dmix:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct sample mixing device
dmix:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct sample mixing device
dsnoop:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct sample snooping device
dsnoop:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct sample snooping device
hw:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Direct hardware device without any conversions
hw:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Direct hardware device without any conversions
plughw:CARD=ALSA,DEV=0
    bcm2835 ALSA, bcm2835 ALSA
    Hardware device with all software conversions
plughw:CARD=ALSA,DEV=1
    bcm2835 ALSA, bcm2835 IEC958/HDMI
    Hardware device with all software conversions
default:CARD=Loopback
    Loopback, Loopback PCM
    Default Audio Device
sysdefault:CARD=Loopback
    Loopback, Loopback PCM
    Default Audio Device
front:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    Front speakers
surround21:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    2.1 Surround output to Front and Subwoofer speakers
surround40:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    4.0 Surround output to Front and Rear speakers
surround41:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    4.1 Surround output to Front, Rear and Subwoofer speakers
surround50:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    5.0 Surround output to Front, Center and Rear speakers
surround51:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    5.1 Surround output to Front, Center, Rear and Subwoofer speakers
surround71:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    7.1 Surround output to Front, Center, Side, Rear and Woofer speakers
dmix:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    Direct sample mixing device
dmix:CARD=Loopback,DEV=1
    Loopback, Loopback PCM
    Direct sample mixing device
dsnoop:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    Direct sample snooping device
dsnoop:CARD=Loopback,DEV=1
    Loopback, Loopback PCM
    Direct sample snooping device
hw:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    Direct hardware device without any conversions
hw:CARD=Loopback,DEV=1
    Loopback, Loopback PCM
    Direct hardware device without any conversions
plughw:CARD=Loopback,DEV=0
    Loopback, Loopback PCM
    Hardware device with all software conversions
plughw:CARD=Loopback,DEV=1
    Loopback, Loopback PCM
    Hardware device with all software conversions
```

There are new devices with `CARD=Loopback`.

```bash
sudo nano /etc/asound.conf
```

Paste the following configuration:
```
# .asoundrc
pcm.multi {
    type route;
    slave.pcm {
        type multi;
        slaves.a.pcm "output";
        slaves.b.pcm "loopin";
        slaves.a.channels 2;
        slaves.b.channels 2;
        bindings.0.slave a;
        bindings.0.channel 0;
        bindings.1.slave a;
        bindings.1.channel 1;
        bindings.2.slave b;
        bindings.2.channel 0;
        bindings.3.slave b;
        bindings.3.channel 1;
    }

    ttable.0.0 1;
    ttable.1.1 1;
    ttable.0.2 1;
    ttable.1.3 1;
}

pcm.!default {
    type plug
    slave.pcm "multi"
} 

pcm.output {
    type hw
    card ALSA # This has to match HW output
}

pcm.loopin {
    type plug
    slave.pcm "hw:Loopback,0,0"
}

pcm.loopout {
    type plug
    slave.pcm "hw:Loopback,1,0"
}
```

Run `aplay -L` to see the new virtual devices multi, output, loopin and loopout:

```bash
null
    Discard all samples (playback) or generate zero samples (capture)
multi
default
output
loopin
loopout
sysdefault:CARD=ALSA
    bcm2835 ALSA, bcm2835 ALSA
    Default Audio Device
...
```

Run server and select the `loopout` device:

```bash
python3 server.py -A -1
# pick device index for loopout from output:
loopout
	Device index: 8
	Sample rate: 44100.0
	Max input channels: 128
	Max output channels: 128
# Start server with device index:
python3 server.py -A 8
```

Play back the .wav again and check output is coming through your RaspberryPi:
```bash
aplay SomeWav.wav
```

Now the audio should be fed into server and still be playing from RaspberryPi audio output.

Kudos to: https://raspberrypi.stackexchange.com/questions/26810/how-to-use-jack-or-similar-software-to-route-music-played-in-the-pi-as-audio-i

### Known limitations

Non-usb audio breaks LED output when using GPIO Pin 18.
