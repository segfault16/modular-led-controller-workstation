#!flask/bin/python
import argparse
import asyncio
import atexit
import colorsys
import importlib
import inspect
import json
import os.path
from os.path import expanduser
import threading
import time
from timeit import default_timer as timer
import atexit

import jsonpickle
import numpy as np
from flask import Flask, abort, jsonify, request, send_from_directory, redirect
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.serving import is_running_from_reloader

from audioled import audio, configs, devices, effects, filtergraph, project, serverconfiguration

proj = None
default_values = {}
record_timings = False
serverconfig = None

POOL_TIME = 0.0  # Seconds

# lock to control access to variable
dataLock = threading.Lock()
# thread handler
ledThread = threading.Thread()
event_loop = None
# timing
current_time = None
last_time = None
# errors
errors = []
# count
count = 0

# @app.route('/', methods=['GET'])
# def home():
#     return app.send_static_file('index.html')


def create_app():
    app = Flask(__name__, static_url_path='/')

    def store_configuration():
        global serverconfig
        serverconfig.store()

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(store_configuration, 'interval', seconds=5)
    sched.start()

    def interrupt():
        print('cancelling LED thread')
        global ledThread
        ledThread.cancel()
        ledThread.join()
        print('LED thread cancelled')

    @app.after_request
    def add_header(response):
        response.cache_control.max_age = 0
        return response

    @app.route('/')
    def home():
        return redirect("./index.html", code=302)

    @app.route('/<path:path>')
    def send_js(path):
        return send_from_directory('resources', path)

    @app.route('/slot/<int:slotId>/nodes', methods=['GET'])
    def slot_slotId_nodes_get(slotId):
        global proj
        fg = proj.getSlot(slotId)
        nodes = [node for node in fg._filterNodes]
        return jsonpickle.encode(nodes)

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['GET'])
    def slot_slotId_node_uid_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId)
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return jsonpickle.encode(node)
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['DELETE'])
    def slot_slotId_node_uid_delete(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId)
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            fg.removeEffectNode(node.effect)
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['UPDATE'])
    def slot_slotId_node_uid_update(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId)
        if not request.json:
            abort(400)
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            # data =  json.loads(request.json)
            print(request.json)
            node.effect.updateParameter(request.json)
            return jsonpickle.encode(node)
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/parameter', methods=['GET'])
    def slot_slotId_node_uid_parameter_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId)
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return json.dumps(node.effect.getParameter())
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/effect', methods=['GET'])
    def node_uid_effectname_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId)
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return json.dumps(getFullClassName(node.effect))
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node', methods=['POST'])
    def slot_slotId_node_post(slotId):
        global proj
        fg = proj.getSlot(slotId)
        if not request.json:
            abort(400)
        full_class_name = request.json[0]
        parameters = request.json[1]
        print(parameters)
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        instance = class_(**parameters)
        node = fg.addEffectNode(instance)
        return jsonpickle.encode(node)

    @app.route('/slot/<int:slotId>/connections', methods=['GET'])
    def slot_slotId_connections_get(slotId):
        global proj
        fg = proj.getSlot(slotId)
        connections = [con for con in fg._filterConnections]
        return jsonpickle.encode(connections)

    @app.route('/slot/<int:slotId>/connection', methods=['POST'])
    def slot_slotId_connection_post(slotId):
        global proj
        fg = proj.getSlot(slotId)
        if not request.json:
            abort(400)
        json = request.json
        connection = fg.addNodeConnection(json['from_node_uid'], int(json['from_node_channel']), json['to_node_uid'],
                                          int(json['to_node_channel']))

        return jsonpickle.encode(connection)

    @app.route('/slot/<int:slotId>/connection/<connectionUid>', methods=['DELETE'])
    def slot_slotId_connection_uid_delete(slotId, connectionUid):
        global proj
        fg = proj.getSlot(slotId)
        try:
            connection = next(connection for connection in fg._filterConnections if connection.uid == connectionUid)
            fg.removeConnection(connection.fromNode.effect, connection.fromChannel, connection.toNode.effect,
                                connection.toChannel)
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/configuration', methods=['GET'])
    def slot_slotId_configuration_get(slotId):
        global proj
        fg = proj.getSlot(slotId)
        config = jsonpickle.encode(fg)
        return config

    @app.route('/slot/<int:slotId>/configuration', methods=['POST'])
    def slot_slotId_configuration_post(slotId):
        global proj
        if not request.json:
            abort(400)

        newGraph = jsonpickle.decode(request.json)
        if not isinstance(newGraph, filtergraph.FilterGraph):
            raise RuntimeError("Not a FilterGraph")
        proj.setFiltergraphForSlot(slotId, newGraph)
        return "OK"

    @app.route('/effects', methods=['GET'])
    def effects_get():
        childclasses = inheritors(effects.Effect)
        return jsonpickle.encode([child for child in childclasses])

    @app.route('/effect/<full_class_name>/description', methods=['GET'])
    def effect_effectname_description_get(full_class_name):
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        return class_.getEffectDescription()

    @app.route('/effect/<full_class_name>/args', methods=['GET'])
    def effect_effectname_args_get(full_class_name):
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        argspec = inspect.getargspec(class_.__init__)
        if argspec.defaults is not None:
            argsWithDefaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
        else:
            argsWithDefaults = dict()
        result = argsWithDefaults.copy()
        if argspec.defaults is not None:
            result.update({key: None
                           for key in argspec.args[1:len(argspec.args) - len(argspec.defaults)]})  # 1 removes self

        result.update({key: default_values[key] for key in default_values if key in result})
        print(result)
        return jsonify(result)

    @app.route('/effect/<full_class_name>/parameter', methods=['GET'])
    def effect_effectname_parameters_get(full_class_name):
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        return json.dumps(class_.getParameterDefinition())

    @app.route('/effect/<full_class_name>/parameterHelp', methods=['GET'])
    def effect_effectname_parameterhelp_get(full_class_name):
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        return json.dumps(class_.getParameterHelp())

    def getModuleAndClassName(full_class_name):
        module_name, class_name = full_class_name.rsplit(".", 1)
        if module_name != "audioled.audio" and module_name != "audioled.effects" and module_name != "audioled.devices" and module_name != "audioled.colors" and module_name != "audioled.audioreactive" and module_name != "audioled.generative" and module_name != "audioled.input":
            raise RuntimeError("Not allowed")
        return module_name, class_name
    
    def getFullClassName(o):
        module = o.__class__.__module__
        if module is None or module == str.__class__.__module__:
            return o.__class__.__name__  
        else:
            return module + '.' + o.__class__.__name__

    def inheritors(klass):
        subclasses = set()
        work = [klass]
        while work:
            parent = work.pop()
            for child in parent.__subclasses__():
                if child not in subclasses:
                    subclasses.add(child)
                    work.append(child)
        return subclasses

    @app.route('/errors', methods=['GET'])
    def errors_get():
        result = {}
        for error in errors:
            result[error.node.uid] = error.message
        return json.dumps(result)

    @app.route('/project/activeSlot', methods=['POST'])
    def project_activeSlot_post():
        global proj
        if not request.json:
            abort(400)
        value = request.json['slot']
        # print("Activating slot {}".format(value))
        proj.activateSlot(value)
        return "OK"

    @app.route('/project/activeSlot', methods=['GET'])
    def project_activeSlot_get():
        global proj
        return jsonify({'slot': proj.activeSlotId})

    @app.route('/projects', methods=['GET'])
    def projects_get():
        global serverconfig
        return jsonify(serverconfig.getProjectsMetadata())

    @app.route('/projects', methods=['POST'])
    def projects_post():
        global serverconfig
        if not request.json:
            abort(400)
        title = request.json.get('title', '')
        description = request.json.get('description', '')
        metadata = serverconfig.createEmptyProject(title, description)
        return jsonify(metadata)

    @app.route('/projects/import', methods=['POST'])
    def projects_import_post():
        global serverconfig
        if not request.json:
            abort(400)
        metadata = serverconfig.importProject(request.json)
        return jsonify(metadata)

    @app.route('/projects/<uid>/export', methods=['GET'])
    def projects_project_export(uid):
        global serverconfig
        proj = serverconfig.getProject(uid)
        if proj is not None:
            print("Exporting project {}".format(uid))
            return jsonpickle.encode(proj)
        abort(404)

    @app.route('/projects/<uid>', methods=['DELETE'])
    def projects_project_delete(uid):
        global serverconfig
        serverconfig.deleteProject(uid)
        return "OK"

    @app.route('/projects/activeProject', methods=['POST'])
    def projects_activeProject_post():
        global serverconfig
        global proj
        if not request.json:
            abort(400)
        uid = request.json['project']
        print("Activating project {}".format(uid))
        proj = serverconfig.activateProject(uid)
        return "OK"

    @app.route('/configuration', methods=['GET'])
    def configuration_get():
        global serverconfig
        return jsonify({
            'parameters': serverconfig.getConfigurationParameters(),
            'values': serverconfig.getFullConfiguration()
        })

    @app.route('/configuration', methods=['UPDATE'])
    def configuration_put():
        global serverconfig
        if not request.json:
            abort(400)
        for key, value in request.json.items():
            serverconfig.setConfiguration(key, value)
        return jsonify(serverconfig.getFullConfiguration())

    @app.route('/remote/brightness', methods=['POST'])
    def remote_brightness_post():
        global device
        value = int(request.args.get('value'))
        floatVal = float(value / 100)
        print("Setting brightness: {}".format(floatVal))
        device.setBrightness(floatVal)
        return "OK"

    @app.route('/remote/favorites/<id>', methods=['POST'])
    def remote_favorites_id_post(id):
        filename = "favorites/{}.json".format(id)
        global proj
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                fg = jsonpickle.decode(f.read())
                proj.setFiltergraphForSlot(proj.activeSlotId, fg)
                return "OK"
        else:
            print("Favorite not found: {}".format(filename))

        abort(404)

    def processLED():
        global proj
        global ledThread
        global event_loop
        global last_time
        global current_time
        global errors
        global count
        global record_timings
        dt = 0
        try:
            with dataLock:
                last_time = current_time
                current_time = timer()
                dt = current_time - last_time
                count = count + 1
                if event_loop is None:
                    event_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(event_loop)

                proj.update(dt, event_loop)
                proj.process()
                # clear errors (if any have occured in the current run, we wouldn't reach this)
                errors.clear()

        except filtergraph.NodeException as ne:
            print("NodeError in {}: {}".format(ne.node.effect, ne))
            errors.clear()
            errors.append(ne)
        except Exception as e:
            print("Unknown error: {}".format(e))
        finally:
            # Set the next thread to happen
            real_process_time = timer() - current_time
            timeToWait = max(POOL_TIME, 0.01 - real_process_time)
            if count == 100:
                if record_timings:
                    proj.getSlot(proj.activeSlotId).printProcessTimings()
                    proj.getSlot(proj.activeSlotId).printUpdateTimings()
                    print("Process time: {}".format(real_process_time))
                    print("Waiting {}".format(timeToWait))
                count = 0
            ledThread = threading.Timer(timeToWait, processLED, ())
            ledThread.start()

    def startLEDThread():
        # Do initialisation stuff here
        global ledThread
        global last_time
        global current_time
        # Create your thread
        current_time = timer()
        ledThread = threading.Timer(POOL_TIME, processLED, ())
        print('starting LED thread')
        ledThread.start()

    # Initiate

    if is_running_from_reloader() is False:
        startLEDThread()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    return app


def strandTest(device, num_pixels):
    pixels = np.zeros(int(num_pixels / 2)) * np.array([[255.0], [255.0], [255.0]])
    t = 0.0
    dt = 1.0 / num_pixels
    for i in range(0, int(num_pixels * 1.2)):
        h = t / dt / num_pixels
        r, g, b, = 0, 0, 0
        if i < num_pixels / 2:
            r, g, b = colorsys.hsv_to_rgb(h, 0.5, 1.0)
        pixels = np.roll(pixels, -1, axis=1)
        pixels[0][0] = r * 255.0
        pixels[1][0] = g * 255.0
        pixels[2][0] = b * 255.0
        device.show(np.concatenate((pixels, pixels[:, ::-1]), axis=1))
        t = t + dt
        time.sleep(dt)


if __name__ == '__main__':
    deviceRasp = 'RaspberryPi'
    deviceCandy = 'FadeCandy'

    parser = argparse.ArgumentParser(description='Audio Reactive LED Strip Server')
    parser.add_argument(
        '-C',
        '--config_location',
        dest='config_location',
        default=None,
        help='Location of the server configuration to store. Defaults to $HOME/.ledserver.')
    parser.add_argument(
        '--no_conf', dest='no_conf', action='store_true', default=False, help="Don't load config from file")
    parser.add_argument(
        '--no_store', dest='no_store', action='store_true', default=False, help="Don't save anything to disk")
    parser.add_argument(
        '-N', '--num_pixels', dest='num_pixels', type=int, default=None, help='number of pixels (default: 300)')
    parser.add_argument(
        '-D',
        '--device',
        dest='device',
        default=None,
        choices=[deviceRasp, deviceCandy],
        help='device to send RGB to (default: FadeCandy)')
    parser.add_argument(
        '--device_candy_server', dest='device_candy_server', default=None, help='Server for device FadeCandy')
    parser.add_argument(
        '-A',
        '--audio_device_index',
        dest='audio_device_index',
        type=int,
        default=None,
        help='Audio device index to use')
    parser.add_argument(
        '-P',
        '--process_timing',
        dest='process_timing',
        action='store_true',
        default=False,
        help='Print process timing')

    args = parser.parse_args()
    config_location = None
    if args.config_location is None:
        config_location = os.path.join(os.path.expanduser("~"), '.ledserver')
    else:
        config_location = os.path.join(args.config_location, '.ledserver')

    if args.no_conf:
        print("Using in-memory configuration")
        serverconfig = serverconfiguration.ServerConfiguration()
    else:
        print("Using configuration from {}".format(config_location))
        serverconfig = serverconfiguration.PersistentConfiguration(config_location, args.no_store)

    # Update num pixels
    if args.num_pixels is not None:
        num_pixels = args.num_pixels
        serverconfig.setConfiguration(serverconfiguration.CONFIG_NUM_PIXELS, num_pixels)

    # Update LED device
    if args.device is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_DEVICE, args.device)

    if args.device_candy_server is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_DEVICE_CANDY_SERVER, args.device_candy_server)

    # Update Audio device
    if args.audio_device_index is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX, args.audio_device_index)

    if args.process_timing:
        record_timings = True

    # Adjust from configuration

    # LED Device
    device = None
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_DEVICE) == deviceRasp:
        device = devices.RaspberryPi(serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS))
    elif serverconfig.getConfiguration(serverconfiguration.CONFIG_DEVICE) == deviceCandy:
        device = devices.FadeCandy(serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS), 
            serverconfig.getConfiguration(serverconfiguration.CONFIG_DEVICE_CANDY_SERVER))
    else:
        print("Unknown device: {}".format(serverconfig.getConfiguration(serverconfiguration.CONFIG_DEVICE)))
        exit

    # Audio
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX) is not None:
        audio.AudioInput.overrideDeviceIndex = serverconfig.getConfiguration(
            serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX)

    # strand test
    strandTest(device, serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS))

    # print audio information
    print("The following audio devices are available:")
    audio.print_audio_devices()

    # Initialize project
    proj = serverconfig.getActiveProjectOrDefault()

    # Init defaults
    default_values['fs'] = 48000  # ToDo: How to provide fs information to downstream effects?
    default_values['num_pixels'] = serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS)

    app = create_app()
    app.run(debug=False, host="0.0.0.0")
