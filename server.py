#!flask/bin/python
import asyncio
import atexit
import colorsys
import importlib
import inspect
import json
import os.path
import threading
import time
import multiprocessing
import traceback
from timeit import default_timer as timer

import jsonpickle
import numpy as np
from flask import Flask, abort, jsonify, request, send_from_directory, redirect, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.serving import is_running_from_reloader

from audioled import audio, devices, effects, filtergraph, serverconfiguration, runtimeconfiguration, modulation

proj = None
default_values = {}
record_timings = False
serverconfig = None

POOL_TIME = 0.0  # Seconds

# lock to control access to variable
dataLock = threading.Lock()
# thread handler
ledThread = threading.Thread()
stop_signal = False
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


def multiprocessing_func(sc):
    sc.store()


def create_app():
    app = Flask(__name__)

    def store_configuration():
        global serverconfig
        p = multiprocessing.Process(target=multiprocessing_func, args=(serverconfig, ))
        p.start()
        p.join()
        # Update MD5 hashes from file, since data was written in separate process
        serverconfig.updateMd5HashFromFiles()
        serverconfig.postStore()

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(store_configuration, 'interval', seconds=5)
    sched.start()

    def interrupt():
        print('cancelling LED thread')
        global ledThread
        stop_signal = True
        try:
            ledThread.join()
        except RuntimeError:
            pass

        print('LED thread cancelled')
        sched.shutdown()
        print('Background scheduler shutdown')

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
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        nodes = [node for node in fg._filterNodes]
        return jsonpickle.encode(nodes)

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['GET'])
    def slot_slotId_node_uid_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return jsonpickle.encode(node)
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['DELETE'])
    def slot_slotId_node_uid_delete(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            fg.removeEffectNode(node.effect)
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['PUT'])
    def slot_slotId_node_uid_update(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
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

    @app.route('/slot/<int:slotId>/node/<nodeUid>/parameterDefinition', methods=['GET'])
    def slot_slotId_node_uid_parameter_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return json.dumps(node.effect.getParameterDefinition())
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/effect', methods=['GET'])
    def node_uid_effectname_get(slotId, nodeUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg._filterNodes if node.uid == nodeUid)
            return json.dumps(getFullClassName(node.effect))
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node', methods=['POST'])
    def slot_slotId_node_post(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
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
        node = None
        if module_name == 'audioled.modulation':
            print("Adding modulation source")
            node = fg.addModulationSource(instance)
        else:
            print("Adding effect node")
            node = fg.addEffectNode(instance)
        return jsonpickle.encode(node)

    @app.route('/slot/<int:slotId>/connections', methods=['GET'])
    def slot_slotId_connections_get(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        connections = [con for con in fg._filterConnections]
        return jsonpickle.encode(connections)

    @app.route('/slot/<int:slotId>/connection', methods=['POST'])
    def slot_slotId_connection_post(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        json = request.json
        connection = fg.addNodeConnection(
            json['from_node_uid'],
            int(json['from_node_channel']),
            json['to_node_uid'],
            int(json['to_node_channel']),
        )

        return jsonpickle.encode(connection)

    @app.route('/slot/<int:slotId>/connection/<connectionUid>', methods=['DELETE'])
    def slot_slotId_connection_uid_delete(slotId, connectionUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            connection = next(connection for connection in fg._filterConnections if connection.uid == connectionUid)
            fg.removeConnection(
                connection.fromNode.effect,
                connection.fromChannel,
                connection.toNode.effect,
                connection.toChannel,
            )
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/modulationSources', methods=['GET'])
    def slot_slotId_modulationSources_get(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        mods = [mod for mod in fg._modulationSources]
        return jsonpickle.encode(mods)

    @app.route('/slot/<int:slotId>/modulationSource/<modulationSourceUid>', methods=['DELETE'])
    def slot_slotId_modulationSourceUid_delete(slotId, modulationSourceUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg._modulationSources if mod.uid == modulationSourceUid)
            fg.removeModulationSource(mod.uid)
            return "OK"
        except StopIteration:
            abort(404, "Modulation Source not found")

    @app.route('/slot/<int:slotId>/modulationSource/<modulationUid>', methods=['PUT'])
    def slot_slotId_modulationSourceUid_update(slotId, modulationUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        try:
            mod = next(mod for mod in fg._modulationSources if mod.uid == modulationUid) # type: filtergraph.ModulationSourceNode
            # data =  json.loads(request.json)
            print(request.json)
            mod = mod.modulator.updateParameter(request.json)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulationSource/<modulationSourceUid>', methods=['GET'])
    def slot_slotId_modulationSourceUid_get(slotId, modulationSourceUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg._modulationSources if mod.uid == modulationSourceUid)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation Source not found")
    
    @app.route('/slot/<int:slotId>/modulations', methods=['GET'])
    def slot_slotId_modulations_get(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        modSourceId = request.args.get('modulationSourceUid', None)
        modDestinationId = request.args.get('modulationDestinationUid', None)
        mods = [mod for mod in fg._modulations]
        if modSourceId is not None:
            # for specific modulation source
            mods = [mod for mod in mods if mod.modulationSource.uid == modSourceId]
        if modDestinationId is not None:
            # for specific modulation destination".format(modDestinationId))
            mods = [mod for mod in mods if mod.targetNode.uid == modDestinationId]
            
        return jsonpickle.encode(mods)
    
    @app.route('/slot/<int:slotId>/modulation', methods=['POST'])
    def slot_slotId_modulation_post(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        json = request.json
        newMod = fg.addModulation(json['modulationsource_uid'], json['target_uid'])
        return jsonpickle.encode(newMod)

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['GET'])
    def slot_slotId_modulationUid_get(slotId, modulationUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try: 
            mod = next(mod for mod in fg._modulations if mod.uid == modulationUid)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['PUT'])
    def slot_slotId_modulationUid_update(slotId, modulationUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        try:
            mod = next(mod for mod in fg._modulations if mod.uid == modulationUid) # type: filtergraph.Modulation
            # data =  json.loads(request.json)
            print(request.json)
            mod.updateParameter(request.json)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['DELETE'])
    def slot_slotId_modulationUid_delete(slotId, modulationUid):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
        try: 
            mod = next(mod for mod in fg._modulations if mod.uid == modulationUid)
            fg.removeModulation(modulationUid)
            return "OK"
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/configuration', methods=['GET'])
    def slot_slotId_configuration_get(slotId):
        global proj
        fg = proj.getSlot(slotId) # type: filtergraph.FilterGraph
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
        """Returns all effects and modulators
        """
        childclasses = []
        childclasses.extend(inheritors(effects.Effect))
        childclasses.extend(inheritors(modulation.ModulationSource))
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
        if (module_name != "audioled.audio" and module_name != "audioled.effects" and module_name != "audioled.devices"
                and module_name != "audioled.colors" and module_name != "audioled.audioreactive"
                and module_name != "audioled.generative" and module_name != "audioled.input"
                and module_name != "audioled.panelize" and module_name != "audioled.modulation"):
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

    @app.route('/project/assets/<path:path>', methods=['GET'])
    def project_assets_get(path):
        global serverconfig
        global proj
        asset = serverconfig.getProjectAsset(proj.id, path)
        return send_file(asset[0], attachment_filename=asset[1], mimetype=asset[2])

    @app.route('/project/assets', methods=['POST'])
    def project_assets_post():
        global serverconfig
        global proj
        if 'file' not in request.files:
            print("No file in request")
            abort(400)
        file = request.files['file']
        if file.filename == '':
            print("File has no filename")
            abort(400)
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ['gif']:
            print("Adding asset to proj {}".format(proj.id))
            filename = serverconfig.addProjectAsset(proj.id, file)
            return jsonify({'filename': filename})
        print("Unknown content for asset: {}".format(file.filename))
        abort(400)

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
        try:
            proj = serverconfig.activateProject(uid)
        except Exception as e:
            print("Error opening project: {}".format(e))
            if serverconfig._activeProject is None:
                serverconfig.initDefaultProject()
                abort(500, "Could not active project. No other project found. Initializing default.")
            else:
                abort(500, "Project could not be activated. Reason: {}".format(e))
        return "OK"

    @app.route('/configuration', methods=['GET'])
    def configuration_get():
        global serverconfig
        return jsonify({
            'parameters': serverconfig.getConfigurationParameters(),
            'values': serverconfig.getFullConfiguration()
        })

    @app.route('/configuration', methods=['PUT'])
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
        global stop_signal
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
            traceback.print_tb(e.__traceback__)
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
            if not stop_signal:
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
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        pixels = np.roll(pixels, -1, axis=1)
        pixels[0][0] = r * 255.0
        pixels[1][0] = g * 255.0
        pixels[2][0] = b * 255.0
        device.show(np.concatenate((pixels, pixels[:, ::-1]), axis=1))
        t = t + dt
        time.sleep(dt)


if __name__ == '__main__':
    parser = runtimeconfiguration.commonRuntimeArgumentParser()
    # Adjust defaults from commonRuntimeArgumentParser
    parser.set_defaults(
        device_candy_server=None,
        num_rows=None,
        num_pixels=None,
    )
    # Add specific arguments
    parser.add_argument(
        '-p',
        '--port',
        dest='port',
        default='5000',
        help='Port to listen on',
    )
    parser.add_argument(
        '-C',
        '--config_location',
        dest='config_location',
        default=None,
        help='Location of the server configuration to store. Defaults to $HOME/.ledserver.')
    parser.add_argument(
        '--no_conf',
        dest='no_conf',
        action='store_true',
        default=False,
        help="Don't load config from file",
    )
    parser.add_argument(
        '--no_store',
        dest='no_store',
        action='store_true',
        default=False,
        help="Don't save anything to disk",
    )
    deviceChoices = serverconfiguration.ServerConfiguration.getConfigurationParameters().get('device')
    parser.add_argument(
        '-D',
        '--device',
        dest='device',
        default=None,
        choices=deviceChoices,
        help='device to send RGB to (default: FadeCandy)')
    parser.add_argument(
        '-P',
        '--process_timing',
        dest='process_timing',
        action='store_true',
        default=False,
        help='Print process timing')
    parser.add_argument(
        '--strand',
        dest='strand',
        action='store_true',
        default=False,
        help="Perform strand test at start of server.",
    )

    # print audio information
    print("The following audio devices are available:")
    audio.print_audio_devices()

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

    print("Applying arguments")

    # Update num pixels
    if args.num_pixels is not None:
        num_pixels = args.num_pixels
        serverconfig.setConfiguration(serverconfiguration.CONFIG_NUM_PIXELS, num_pixels)

    # Update num rows
    if args.num_rows is not None:
        num_rows = args.num_rows
        serverconfig.setConfiguration(serverconfiguration.CONFIG_NUM_ROWS, num_rows)

    # Update LED device
    if args.device is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_DEVICE, args.device)

    if args.device_candy_server is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_DEVICE_CANDY_SERVER, args.device_candy_server)

    if args.device_panel_mapping is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_DEVICE_PANEL_MAPPING, args.device_panel_mapping)

    # Update Audio device
    if args.audio_device_index is not None:
        serverconfig.setConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX, args.audio_device_index)

    if args.process_timing:
        record_timings = True

    # Adjust from configuration

    # Audio
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX) is not None:
        print("Overriding Audio device with device index {}".format(
            serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX)))
        audio.AudioInput.overrideDeviceIndex = serverconfig.getConfiguration(
            serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX)
        # Initialize global audio
        globalAudio = audio.GlobalAudio(serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX))
    else:
        globalAudio = audio.GlobalAudio()

    # strand test
    if args.strand:
        strandTest(serverconfig.createOutputDevice(),
                   serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS))

    # Initialize project
    proj = serverconfig.getActiveProjectOrDefault()

    # Init defaults
    default_values['fs'] = 48000  # ToDo: How to provide fs information to downstream effects?
    default_values['num_pixels'] = serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS)

    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=args.port)
    print("End of server main")
    stop_signal = True
