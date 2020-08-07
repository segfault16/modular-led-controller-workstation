import errno
import json
import os
import time
from timeit import default_timer as timer

import jsonpickle

from audioled import configs, devices, filtergraph, audio, runtimeconfiguration, serverconfiguration

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
sortingConf = 'sorting'
gifConf = 'gif'
panelConf = 'panel'
oscilloscopeConf = 'oscilloscope'
configChoices = [
    movingLightConf,
    spectrumConf,
    vu_peakConf,
    movingLightsConf,
    swimmingConf,
    defenceConf,
    proxyConf,
    fallingConf,
    breathingConf,
    heartbeatConf,
    pendulumConf,
    rpendulumConf,
    keyboardConf,
    keyboardSpringConf,
    testblobConf,
    bonfireConf,
    generatewavesConf,
    sortingConf,
    gifConf,
    panelConf,
    oscilloscopeConf,
]

deviceRasp = 'RaspberryPi'
deviceCandy = 'FadeCandy'

parser = runtimeconfiguration.commonRuntimeArgumentParser()
# Add specific arguments
deviceChoices = serverconfiguration.allowed_devices
parser.add_argument(
    '-D',
    '--device',
    dest='device',
    default=devices.FadeCandy.__name__,
    choices=deviceChoices,
    help='device to send RGB to')
parser.add_argument(
    '-C',
    '--config',
    dest='config',
    default='',
    choices=configChoices,
    help='config to use, default is rolling through all configs')
parser.add_argument(
    '-s',
    '--save_config',
    dest='save_config',
    type=bool,
    default=False,
    help='Save config to config/',
)

args = parser.parse_args()

num_pixels = args.num_pixels
num_rows = args.num_rows

# Initialize device
if args.device == deviceRasp:
    device = devices.RaspberryPi(num_pixels, num_rows)
elif args.device == deviceCandy:
    device = devices.FadeCandy(num_pixels, num_rows, server=args.device_candy_server)

if args.device_panel_mapping is not None:
    mappingFile = args.device_panel_mapping
    if os.path.exists(mappingFile):
        with open(mappingFile, "r", encoding='utf-8') as f:
            content = f.read()
            mapping = json.loads(content)
            print("Panel mapping loaded")
            device = devices.PanelWrapper(device, mapping)
    else:
        print("Fatal: Cannot find mapping file {}".format(mappingFile))
        exit(1)

# Initialize Audio device
if args.audio_device_index is not None:
    audio.GlobalAudio.overrideDeviceIndex = args.audio_device_index

# select config to show
config = args.config

print("The following audio devices are available:")
audio.print_audio_devices()

if args.audio_device_index is not None:
    globalAudio = audio.GlobalAudio(args.audio_device_index)
else:
    globalAudio = audio.GlobalAudio()


def createFilterGraph(config, num_pixels):
    print("Creating config {}".format(config))
    if config == movingLightConf:
        return configs.createMovingLightGraph()
    elif config == movingLightsConf:
        return configs.createMovingLightsGraph()
    elif config == spectrumConf:
        return configs.createSpectrumGraph()
    elif config == vu_peakConf:
        return configs.createVUPeakGraph()
    elif config == swimmingConf:
        return configs.createSwimmingPoolGraph()
    elif config == defenceConf:
        return configs.createDefenceGraph()
    elif config == keyboardConf:
        return configs.createKeyboardGraph()
    elif config == keyboardSpringConf:
        return configs.createKeyboardSpringGraph()
    elif config == proxyConf:
        return configs.createProxyServerGraph()
    elif config == fallingConf:
        return configs.createFallingStarsGraph()
    elif config == breathingConf:
        return configs.createBreathingGraph()
    elif config == heartbeatConf:
        return configs.createHeartbeatGraph()
    elif config == pendulumConf:
        return configs.createPendulumGraph()
    elif config == rpendulumConf:
        return configs.createRPendulumGraph()
    elif config == testblobConf:
        return configs.createTestBlobGraph()
    elif config == bonfireConf:
        return configs.createBonfireGraph()
    elif config == generatewavesConf:
        return configs.createGenerateWavesGraph()
    elif config == sortingConf:
        return configs.createSortingGraph()
    elif config == gifConf:
        return configs.createGifPlayerGraph()
    elif config == panelConf:
        return configs.createPanelPendulum()
    elif config == oscilloscopeConf:
        return configs.createOscilloscope()
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
totalTiming = filtergraph.Timing()
config_idx = 0
last_switch_time = current_time
cur_graph = None
if args.config == '':
    cur_graph = createFilterGraph(configChoices[config_idx], num_pixels)
else:
    cur_graph = createFilterGraph(args.config, num_pixels)
    saveAndLoad(args.config, cur_graph)

cur_graph.propagateNumPixels(num_pixels, num_rows)

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
        cur_graph.propagateNumPixels(num_pixels)
        config_idx = config_idx + 1
        last_switch_time = current_time

    cur_graph.update(dt)
    cur_graph.process()
    totalTiming.update(timer() - current_time)
    if cur_graph.getLEDOutput() is not None and cur_graph.getLEDOutput()._outputBuffer[0] is not None:
        device.show(cur_graph.getLEDOutput()._outputBuffer[0])
    if count == 100:
        cur_graph.printProcessTimings()
        cur_graph.printUpdateTimings()
        print(totalTiming.__dict__)
        count = 0
    count = count + 1
    if dt < 0.015:
        sleeptime = 0.015 - dt
        time.sleep(sleeptime)
