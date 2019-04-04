# Raspberry Pi Setup


## Install dependencies
```
sudo apt-get remove python2.7
sudo apt-get autoremove
sudo apt-get update
sudo apt-get install python3-numpy python3-scipy python3-pyaudio python3-matplotlib python3-jsonpickle libasound-dev libjack-dev
sudo pip3 install mido python-rtmidi apscheduler
```

## Install rpi_ws281x
```
git clone https://github.com/rpi-ws281x/rpi-ws281x-python
cd rpi-ws281x-python
git submodule update --init --recursive
cd library
sudo python3.5 setup.py install
```

## Audio configuration

See [Audio setup on RaspberryPi](./audio_setup_pi.md).

## Start MOLECOLE once

On RaspberryPi, `sudo` privileges are required for accessing the GPIO of RaspberryPi.

```
# Run on Raspberry Pi 
sudo python3 server.py -D RaspberryPi
```

## Run as service

e.g. by copying the following file to `/etc/systemd/system/ledserver.service`

```
[Unit]
Description=Audio-reactive LED Strip
After=network.target

[Service]
ExecStart=/usr/bin/python3 server.py -D RaspberryPi
WorkingDirectory=/home/pi/projects/audio-reactive-led-strip
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

and starting the service with `sudo systemctl start ledserver`.