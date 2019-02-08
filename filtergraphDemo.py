import argparse
import errno
import json
import os
import time
from timeit import default_timer as timer

import jsonpickle

from audioled import configs, devices, filtergraph, audio

num_pixels = 300
device = None
switch_time = 10  # seconds

# define configs (add other configs here)
movingLightConf = 'movingLight'
movingLightsConf = 'movingLights'
spectrumConf = 'spectrum'
vu_peakConf = 'vu_peak'
swimmingConf = 'swimming'
defenceConf = 'defence'
keyboardConf = 'keyboard'
keyboardSpringConf = 'keyboardSpring'
proxyConf = 'proxy'
fallingConf = 'falling'
breathingConf = 'breathing'
heartbeatConf = 'heartbeat'
pendulumConf = 'pendulum'
rpendulumConf = 'rpendulum'
testblobConf = 'testblob'
bonfireConf = 'bonfire'
generatewavesConf = 'generatewaves'
configChoices = [
    movingLightConf, spectrumConf, vu_peakConf, movingLightsConf, swimmingConf, defenceConf, proxyConf, fallingConf,
    breathingConf, heartbeatConf, pendulumConf, rpendulumConf, keyboardConf, keyboardSpringConf, testblobConf,
    bonfireConf, generatewavesConf
]

deviceRasp = 'RaspberryPi'
deviceCandy = 'FadeCandy'

parser = argparse.ArgumentParser(description='Audio Reactive LED Strip')

parser.add_argument(
    '-N', '--num_pixels', dest='num_pixels', type=int, default=300, help='number of pixels (default: 300)')
parser.add_argument(
    '-D',
    '--device',
    dest='device',
    default=deviceCandy,
    choices=[deviceRasp, deviceCandy],
    help='device to send RGB to')
parser.add_argument(
    '--device_candy_server', dest='device_candy_server', default='127.0.0.1:7890', help='Server for device FadeCandy')
parser.add_argument(
    '-C',
    '--config',
    dest='config',
    default='',
    choices=configChoices,
    help='config to use, default is rolling through all configs')
parser.add_argument('-s', '--save_config', dest='save_config', type=bool, default=False, help='Save config to config/')
parser.add_argument(
    '-A', '--audio_device_index', dest='audio_device_index', type=int, default=None, help='Audio device index to use')
args = parser.parse_args()

num_pixels = args.num_pixels

# Initialize device
if args.device == deviceRasp:
    device = devices.RaspberryPi(num_pixels)
elif args.device == deviceCandy:
    device = devices.FadeCandy(args.device_candy_server)

# Initialize Audio device
if args.audio_device_index is not None:
    audio.AudioInput.overrideDeviceIndex = args.audio_device_index

# select config to show
config = args.config

print("The following audio devices are available:")
audio.print_audio_devices()


def createFilterGraph(config, num_pixels):
    if config == movingLightConf:
        return configs.createMovingLightGraph(num_pixels)
    elif config == movingLightsConf:
        return configs.createMovingLightsGraph(num_pixels)
    elif config == spectrumConf:
        return configs.createSpectrumGraph(num_pixels)
    elif config == vu_peakConf:
        return configs.createVUPeakGraph(num_pixels)
    elif config == swimmingConf:
        return configs.createSwimmingPoolGraph(num_pixels)
    elif config == defenceConf:
        return configs.createDefenceGraph(num_pixels)
    elif config == keyboardConf:
        return configs.createKeyboardGraph(num_pixels)
    elif config == keyboardSpringConf:
        return configs.createKeyboardSpringGraph(num_pixels)
    elif config == proxyConf:
        return configs.createProxyServerGraph(num_pixels)
    elif config == fallingConf:
        return configs.createFallingStarsGraph(num_pixels)
    elif config == breathingConf:
        return configs.createBreathingGraph(num_pixels)
    elif config == heartbeatConf:
        return configs.createHeartbeatGraph(num_pixels)
    elif config == pendulumConf:
        return configs.createPendulumGraph(num_pixels)
    elif config == rpendulumConf:
        return configs.createRPendulumGraph(num_pixels)
    elif config == testblobConf:
        return configs.createTestBlobGraph(num_pixels)
    elif config == bonfireConf:
        return configs.createBonfireGraph(num_pixels)
    elif config == generatewavesConf:
        return configs.createGenerateWavesGraph(num_pixels)
    else:
        raise NotImplementedError("Config not implemented")


def saveAndLoad(config, fg):
    if (args.save_config):
        # save filtergraph to json
        filename = "configs/{}.json".format(config)
        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        saveJson = jsonpickle.encode(fg)
        temp = json.loads(saveJson)
        saveJson = json.dumps(temp, sort_keys=True)

        with open(filename, "w") as f:
            f.write(saveJson)

        # load filtergraph from json in case there are any issues with saving/loading
        fg = jsonpickle.decode(saveJson)
    return fg


current_time = timer()
count = 0
updateTiming = filtergraph.Timing()
config_idx = 0
last_switch_time = current_time
cur_graph = None
if args.config == '':
    cur_graph = createFilterGraph(configChoices[config_idx], num_pixels)
else:
    cur_graph = createFilterGraph(args.config, num_pixels)
    saveAndLoad(args.config, cur_graph)

while True:
    last_time = current_time
    current_time = timer()
    dt = current_time - last_time
    if args.config == '' and current_time - last_switch_time > switch_time:
        # switch configuration
        print('---switching configuration---')
        config_idx = (config_idx) % len(configChoices)
        cur_graph = createFilterGraph(configChoices[config_idx], num_pixels)
        cur_graph = saveAndLoad(configChoices[config_idx], cur_graph)
        config_idx = config_idx + 1
        last_switch_time = current_time

    cur_graph.update(dt)
    updateTiming.update(timer() - current_time)
    cur_graph.process()
    if cur_graph.getLEDOutput() is not None:
        device.show(cur_graph.getLEDOutput()._outputBuffer[0])
    if count == 100:
        cur_graph.printProcessTimings()
        print(updateTiming.__dict__)
        count = 0
    count = count + 1
    if dt < 0.015:
        sleeptime = 0.015 - dt
        time.sleep(sleeptime)
