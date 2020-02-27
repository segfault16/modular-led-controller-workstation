# Raspberry Pi Setup

## Install system

* Head over to https://www.raspberrypi.org/documentation/installation/installing-images/ and install. `Raspbian Buster Lite` is sufficient if you don't need a UI.
* Place an empty file called `ssh` into root directory to enable SSH
* Put SD card into Raspberry Pi, let it boot
* `ssh pi@raspberrypi.local` and enter default password (raspberry)
* change password ;)
* `sudo apt-get install git` to install git
* Clone this repository via git `git clone https://github.com/segfault16/modular-led-controller-workstation.git`
* `cd modular-led-controller-workstation`

blacklist the Broadcom audio kernel module by creating a file `/etc/modprobe.d/snd-blacklist.conf` with
````
blacklist snd_bcm2835
````

See https://github.com/jgarff/rpi_ws281x

## Install dependencies 

```
sudo apt-get install python3-pip # to install pip3 on Raspbian Lite
sudo pip3 install pipenv # install pipenv
sudo apt-get install libjpeg8-dev # For pillow
sudo apt-get install portaudio19-dev # For pyaudio
sudo apt-get install libatlas-base-dev # For numpy
sudo pipenv install
```

## Audio configuration

See [Audio setup on RaspberryPi](./audio_setup_pi.md).

## Start MOLECOLE once

On RaspberryPi, `sudo` privileges are required for accessing the GPIO of RaspberryPi.

```
# Run on Raspberry Pi with 300 pixels and strand test at startup:
sudo pipenv run python server.py -D RaspberryPi -N 300 --strand
```

## Run as service

e.g. by copying the following file to `/etc/systemd/system/ledserver.service`

```
[Unit]
Description=Audio-reactive LED Strip
After=network.target

[Service]
ExecStart=/usr/local/bin/pipenv run python server.py -D RaspberryPi --config_location /home/pi/
WorkingDirectory=/home/pi/modular-led-controller-workstation
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

and starting the service with `sudo systemctl start ledserver`.
To start at login do `sudo systemctl enable ledserver`.
The service can be restarted with `sudo systemctl restart ledserver`.
Adjust `--config_location` for a different configuration location.
