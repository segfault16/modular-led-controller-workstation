#!flask/bin/python
import asyncio
import atexit
import colorsys
import importlib
import inspect
import json
import os.path
import sys
import threading
import time
import multiprocessing
import traceback
from timeit import default_timer as timer
import logging
import mido
import signal
import grpc
from functools import wraps
from concurrent import futures

import jsonpickle
import numpy as np
from flask import Flask, abort, jsonify, request, send_from_directory, redirect, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers import interval
from werkzeug.serving import is_running_from_reloader

from audioled import audio, effects, filtergraph, serverconfiguration, runtimeconfiguration, modulation, project, version
from audioled_controller import midi_full, grpc_server

# configure logging here
orig_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = orig_factory(*args, **kwargs)
    record.sname = record.name[-10:] if len(record.name) > 10 else record.name
    if record.threadName and len(record.threadName) > 10:
        record.sthreadName = record.threadName[:10]
    elif not record.threadName:
        record.sthreadName = ""
    else:
        record.sthreadName = record.threadName
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='[%(relativeCreated)6d %(sthreadName)10s  ] %(sname)10s:%(levelname)s %(message)s')
logging.debug("Global debug log enabled")
# Adjust loglevels
logging.getLogger('apscheduler').setLevel(logging.ERROR)
logging.getLogger('audioled').setLevel(logging.INFO)
logging.getLogger('audioled.audio').setLevel(logging.INFO)
logging.getLogger('audioled_controller').setLevel(logging.DEBUG)
logging.getLogger('audioled_controller.bluetooth').setLevel(logging.DEBUG)
logging.getLogger('root').setLevel(logging.INFO)
logging.getLogger('audioled.audio.libasound').setLevel(logging.INFO)  # Silence!
logging.getLogger('pyupdater').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

libnames = ['audioled_controller.bluetooth']
for libname in libnames:
    try:
        lib = __import__(libname)
    except Exception as e:
        logger.error("Import for bluetooth failed. {}".format(e))
        logger.debug("Error importing bluetooth", exc_info=1)
    else:
        globals()[libname] = lib

proj = None  # type: project.Project
default_values = {}
record_timings = False
serverconfig = None

POOL_TIME = 0.0  # Seconds

# lock to control access to variable
dataLock = threading.Lock()
# thread handler
ledThread = threading.Thread()
midiThread = threading.Thread()
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

preview_lock = multiprocessing.Lock()

stop_lock = multiprocessing.Lock()

midiController = []
midiBluetooth = None  # type: audioled_controller.bluetooth.BluetoothMidiLELevelCharacteristic # noqa: F821
midiCtrlPortIn = None
midiCtrlPortOut = None
midiGRPCService = None

def lock_preview(fn):
    @wraps(fn)
    def wrapper(*arg, **kwarg):
        print("Wrapped {} {}".format(arg, kwarg))
        result = None
        try:
            preview_lock.acquire()
            result = fn(*arg, **kwarg)
        except Exception as e:
            print(e)
        finally:
            preview_lock.release()
        return result

    return wrapper


def multiprocessing_func(sc):
    global stop_signal
    if not stop_signal:
        sc.store()


def create_app():
    logger.info("Creating app")
    app = Flask(__name__)
    logger.debug("App created")

    def store_configuration():
        if stop_signal:
            return
        try:
            global serverconfig
            p = multiprocessing.Process(target=multiprocessing_func, args=(serverconfig, ))
            p.start()
            p.join(30)
            if p.is_alive():
                app.logger.warning("Storing configuration took too long")
            # Update MD5 hashes from file, since data was written in separate process
            serverconfig.updateMd5HashFromFiles()
            serverconfig.postStore()
        except Exception as e:
            app.logger.error("ERROR on storing configuration: {}".format(e))

    sched = BackgroundScheduler(daemon=True)
    trigger = interval.IntervalTrigger(seconds=5)
    sched.add_job(store_configuration, trigger=trigger, id='store_config_job', replace_existing=True)
    # sched.add_job(check_midi, 'interval', seconds=1)
    sched.start()

    def interrupt():
        try:
            global stop_lock
            global stop_signal
            stop_signal = True
            app.logger.debug("Waiting for stop lock")
            stop_lock.acquire()
            app.logger.debug("Interrupt")
            app.logger.info('cancelling LED thread')
            global ledThread
            global midiThread
            global proj
            global midiBluetooth
            global midiCtrlPortOut
            global server
            if server is not None:
                server.stop(2)
            if midiCtrlPortOut is not None:
                for channel in range(16):
                    midiCtrlPortOut.send(mido.Message('control_change', channel=channel, control=121))
                midiCtrlPortOut.close()
                midiCtrlPortOut = None
            try:
                if midiBluetooth is not None:
                    midiBluetooth.shutdown()
            except Exception as e:
                app.logger.error("Midi bluetooth shutdown error: {}".format(e))
            # stop_signal = True
            try:
                app.logger.warning("Shutting down Midi Thread")
                midiThread.join(2)
                if midiThread.is_alive():
                    logger.warning("Midi thread not joined. Terminating")
                    midiThread.terminate()
                app.logger.warning("Shutdown MIDI thread complete")
            except Exception as e:
                app.logger.error("MIDI thread cancelled: {}".format(e))

            try:
                app.logger.warning("Shutting down LED Thread")
                ledThread.join(2)
                if ledThread.is_alive():
                    logger.warning("LED thread not joined. Terminating")
                    ledThread.terminate()
                app.logger.warning("Shutdown LED Thread complete")
            except Exception as e:
                app.logger.error("LED thread cancelled: {}".format(e))

            try:
                app.logger.warning("Stopping processing of current project")
                proj.stopProcessing()
                app.logger.warning("Project stopped")
            except Exception as e:
                app.logger.error("LED thread cancelled: {}".format(e))

            try:
                app.logger.warning("Shutting down background scheduler")
                # TODO: This contains a thread join and blocks
                # sched._thread.join(2)
                sched.shutdown(wait=True)
                app.logger.warning('Background scheduler shutdown')
            except Exception as e:
                app.logger.error("LED thread cancelled: {}".format(e))
            stop_lock.release()
            app.logger.debug("stop lock released")
        except Exception as e:
            app.logger.error("Unhandled exception in signal: {}".format(e))

    def sigStop(sig, frame):
        interrupt()
        sys.exit(1)

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
    # @lock_preview
    def slot_slotId_nodes_get(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        nodes = [node for node in fg.getNodes()]
        return jsonpickle.encode(nodes)

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['GET'])
    # @lock_preview
    def slot_slotId_node_uid_get(slotId, nodeUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg.getNodes() if node.uid == nodeUid)
            return jsonpickle.encode(node)
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['DELETE'])
    @lock_preview
    def slot_slotId_node_uid_delete(slotId, nodeUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg.getNodes() if node.uid == nodeUid)
            fg.removeEffectNode(node.uid)
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>', methods=['PUT'])
    @lock_preview
    def slot_slotId_node_uid_update(slotId, nodeUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        try:
            app.logger.debug(request.json)
            node = fg.updateNodeParameter(nodeUid, request.json)
            return jsonpickle.encode(node)
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/parameterDefinition', methods=['GET'])
    # @lock_preview
    def slot_slotId_node_uid_parameter_get(slotId, nodeUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg.getNodes() if node.uid == nodeUid)
            return json.dumps(node.effect.getParameterDefinition())
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/modulateableParameters', methods=['GET'])
    # @lock_preview
    def slot_slotId_node_uid_parameterModulations_get(slotId, nodeUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg.getNodes() if node.uid == nodeUid)
            return json.dumps(node.effect.getModulateableParameters())
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node/<nodeUid>/effect', methods=['GET'])
    # @lock_preview
    def node_uid_effectname_get(slotId, nodeUid):
        global proj
        print("Getting slot {}".format(slotId))
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            node = next(node for node in fg.getNodes() if node.uid == nodeUid)
            return json.dumps(getFullClassName(node.effect))
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/node', methods=['POST'])
    @lock_preview
    def slot_slotId_node_post(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        full_class_name = request.json[0]
        parameters = request.json[1]
        app.logger.debug(parameters)
        module_name, class_name = None, None
        try:
            module_name, class_name = getModuleAndClassName(full_class_name)
        except RuntimeError:
            abort(403)
        class_ = getattr(importlib.import_module(module_name), class_name)
        instance = class_(**parameters)
        node = None
        if module_name == 'audioled.modulation':
            app.logger.info("Adding modulation source")
            node = fg.addModulationSource(instance)
        else:
            app.logger.info("Adding effect node")
            node = fg.addEffectNode(instance)
        return jsonpickle.encode(node)

    @app.route('/slot/<int:slotId>/connections', methods=['GET'])
    # @lock_preview
    def slot_slotId_connections_get(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        connections = [con for con in fg.getConnections()]
        return jsonpickle.encode(connections)

    @app.route('/slot/<int:slotId>/connection', methods=['POST'])
    @lock_preview
    def slot_slotId_connection_post(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
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
    @lock_preview
    def slot_slotId_connection_uid_delete(slotId, connectionUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            connection = next(connection for connection in fg.getConnections() if connection.uid == connectionUid)
            fg.removeConnection(connection.uid)
            return "OK"
        except StopIteration:
            abort(404, "Node not found")

    @app.route('/slot/<int:slotId>/modulationSources', methods=['GET'])
    # @lock_preview
    def slot_slotId_modulationSources_get(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        mods = [mod for mod in fg.getModulationSources()]
        return jsonpickle.encode(mods)

    @app.route('/slot/<int:slotId>/modulationSource/<modulationSourceUid>', methods=['DELETE'])
    @lock_preview
    def slot_slotId_modulationSourceUid_delete(slotId, modulationSourceUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg.getModulationSources() if mod.uid == modulationSourceUid)
            fg.removeModulationSource(mod.uid)
            return "OK"
        except StopIteration:
            abort(404, "Modulation Source not found")

    @app.route('/slot/<int:slotId>/modulationSource/<modulationUid>', methods=['PUT'])
    @lock_preview
    def slot_slotId_modulationSourceUid_update(slotId, modulationUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        try:
            app.logger.debug(request.json)
            mod = fg.updateModulationSourceParameter(modulationUid, request.json)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulationSource/<modulationSourceUid>', methods=['GET'])
    # @lock_preview
    def slot_slotId_modulationSourceUid_get(slotId, modulationSourceUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg.getModulationSources() if mod.uid == modulationSourceUid)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation Source not found")

    @app.route('/slot/<int:slotId>/modulations', methods=['GET'])
    # @lock_preview
    def slot_slotId_modulations_get(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        modSourceId = request.args.get('modulationSourceUid', None)
        modDestinationId = request.args.get('modulationDestinationUid', None)
        mods = [mod for mod in fg.getModulations()]
        if modSourceId is not None:
            # for specific modulation source
            mods = [mod for mod in mods if mod.modulationSource.uid == modSourceId]
        if modDestinationId is not None:
            # for specific modulation destination".format(modDestinationId))
            mods = [mod for mod in mods if mod.targetNode.uid == modDestinationId]
        encVal = jsonpickle.encode(mods)
        return encVal

    @app.route('/slot/<int:slotId>/modulation', methods=['POST'])
    @lock_preview
    def slot_slotId_modulation_post(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        json = request.json
        newMod = fg.addModulation(json['modulationsource_uid'], json['target_uid'])
        return jsonpickle.encode(newMod)

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['GET'])
    # @lock_preview
    def slot_slotId_modulationUid_get(slotId, modulationUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg.getModulations() if mod.uid == modulationUid)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['PUT'])
    @lock_preview
    def slot_slotId_modulationUid_update(slotId, modulationUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        if not request.json:
            abort(400)
        try:
            app.logger.debug(request.json)
            mod = fg.updateModulationParameter(modulationUid, request.json)
            return jsonpickle.encode(mod)
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/modulation/<modulationUid>', methods=['DELETE'])
    @lock_preview
    def slot_slotId_modulationUid_delete(slotId, modulationUid):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
        try:
            mod = next(mod for mod in fg.getModulations() if mod.uid == modulationUid)
            if mod is not None:
                fg.removeModulation(modulationUid)
                return "OK"
            else:
                abort(404, "Modulation not found")
        except StopIteration:
            abort(404, "Modulation not found")

    @app.route('/slot/<int:slotId>/configuration', methods=['GET'])
    # @lock_preview
    def slot_slotId_configuration_get(slotId):
        global proj
        fg = proj.previewSlot(slotId)  # type: filtergraph.FilterGraph
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
        argspec = inspect.getfullargspec(class_.__init__)
        if argspec.defaults is not None:
            argsWithDefaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
        else:
            argsWithDefaults = dict()
        result = argsWithDefaults.copy()
        if argspec.defaults is not None:
            result.update({key: None for key in argspec.args[1:len(argspec.args) - len(argspec.defaults)]})  # 1 removes self

        result.update({key: default_values[key] for key in default_values if key in result})
        app.logger.debug(result)
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

    @app.route('/project/activeScene', methods=['POST'])
    def project_activeScene_post():
        global proj
        if not request.json:
            abort(400)
        value = request.json['slot']
        app.logger.info("Activating scene {}".format(value))
        if proj.activeSceneId != value:
            proj.activateScene(value)
        # proj.previewSlot(value)
        return "OK"

    @app.route('/project/activeScene', methods=['GET'])
    def project_activeSlot_get():
        global proj
        app.logger.debug(proj.outputSlotMatrix)
        return jsonify({
            'activeSlot': proj.previewSlotId,  # TODO: Change in FE
            'activeScene': proj.activeSceneId,
        })

    @app.route('/project/sceneMatrix', methods=['PUT'])
    def project_sceneMatrix_put():
        global proj
        if not request.json:
            abort(400)
        value = request.json
        app.logger.debug(value)
        proj.setSceneMatrix(value)
        return "OK"

    @app.route('/project/activateSlot', methods=['POST'])
    # @lock_preview
    def project_activateSlot_post():
        global proj
        if not request.json:
            abort(400)
        value = request.json['slot']
        app.logger.info("Activating slot {}".format(value))
        proj.previewSlot(value)
        return "OK"

    @app.route('/project/sceneMatrix', methods=['GET'])
    def project_sceneMatrix_get():
        global proj
        return json.dumps(proj.getSceneMatrix())

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
            app.logger.warn("No file in request")
            abort(400)
        file = request.files['file']
        if file.filename == '':
            app.logger.warn("File has no filename")
            abort(400)
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ['gif']:
            app.logger.info("Adding asset to proj {}".format(proj.id))
            filename = serverconfig.addProjectAsset(proj.id, file)
            return jsonify({'filename': filename})
        app.logger.error("Unknown content for asset: {}".format(file.filename))
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
            app.logger.info("Exporting project {}".format(uid))
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
        app.logger.info("Activating project {}".format(uid))
        try:
            proj = serverconfig.activateProject(uid)
        except Exception as e:
            app.logger.error("Error opening project: {}".format(e))
            if serverconfig._activeProject is None:
                newProj = serverconfig.initDefaultProject()
                serverconfig.activateProject(newProj.id)
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
        try:
            serverconfig.setConfiguration(request.json)
        except RuntimeError as e:
            app.logger.error("ERROR updating configuration: {}".format(e))
            abort(400, str(e))
        return jsonify(serverconfig.getFullConfiguration())

    @app.route('/remote/brightness', methods=['POST'])
    def remote_brightness_post():
        global proj
        value = int(request.args.get('value'))
        floatVal = float(value / 100)
        app.logger.info("Setting brightness: {}".format(floatVal))
        proj.setBrightness(floatVal)
        return "OK"

    @app.route('/remote/favorites/<id>', methods=['POST'])
    def remote_favorites_id_post(id):
        filename = "favorites/{}.json".format(id)
        global proj
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                fg = jsonpickle.decode(f.read())
                proj.setFiltergraphForSlot(proj.previewSlotId, fg)
                return "OK"
        else:
            app.logger.info("Favorite not found: {}".format(filename))

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
        if stop_signal:
            return
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
            if count == 100:
                app.logger.error("NodeError in {}: {}".format(ne.node.effect, ne))
                app.logger.info("Skipping next 100 errors...")
                count = 0
            errors.clear()
            errors.append(ne)
        except Exception as e:
            app.logger.error("Unknown error: {}".format(e))
            traceback.print_tb(e.__traceback__)
        finally:
            # Set the next thread to happen
            real_process_time = timer() - current_time
            timeToWait = max(POOL_TIME, 0.01 - real_process_time)
            if count == 100:
                if record_timings:
                    # proj.previewSlot(proj.activeSlotId).printProcessTimings() # TODO:
                    # proj.previewSlot(proj.activeSlotId).printUpdateTimings() # TODO:
                    app.logger.info("Process time: {}".format(real_process_time))
                    app.logger.info("Waiting {}".format(timeToWait))
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
        app.logger.info('starting LED thread')
        ledThread.start()
    
    # Initiate
    if is_running_from_reloader() is False:
        startLEDThread()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    signal.signal(signal.SIGINT, sigStop)
    signal.signal(signal.SIGUSR1, sigStop)
    return app



def strandTest(dev, num_pixels):
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
        dev.show(np.concatenate((pixels, pixels[:, ::-1]), axis=1))
        t = t + dt
        time.sleep(dt)

def startMIDIThread():
    global midiThread
    midiThread = threading.Thread(target=processMidi)
    midiThread.start()

def processMidi():
    global stop_signal
    while not stop_signal:
        for msg in midiCtrlPortIn.iter_pending():
            handleMidiIn(msg)
        time.sleep(0.01)

def handleMidiIn(msg: mido.Message):
    global proj
    global midiController
    global serverconfig
    global midiCtrlPortOut
    # if serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_OUT) and (midiCtrlPortOut is None or midiCtrlPortOut.closed):
    #     try:
    #         midiCtrlPortOut = mido.open_output(serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_OUT))
    #     except Exception as e:
    #         logger.error(e)
    for c in midiController:
        c = c  # type: midi_full.MidiProjectController
        c.handleMidiMsg(msg, serverconfig, proj)


def handleMidiOut(msg: mido.Message):
    global midiBluetooth
    if midiBluetooth is not None:
        logger.debug("Writing midi {} to bluetooth".format(msg))
        midiBluetooth.send(msg)
    if midiCtrlPortOut is not None:
        logger.debug("Writing midi {} to port".format(msg))
        midiCtrlPortOut.send(msg)
    if midiGRPCService is not None:
        midiGRPCService.send(msg)


if __name__ == '__main__':
    logger.info("Running MOLECOLE version {}".format(version.get_version()))
    parser = runtimeconfiguration.commonRuntimeArgumentParser()
    # Adjust defaults from commonRuntimeArgumentParser
    parser.set_defaults(
        device_candy_server=None,
        num_rows=None,
        num_pixels=None,
    )
    runtimeconfiguration.addServerRuntimeArguments(parser)

    # print audio information
    logger.info("The following audio devices are available:")
    audio.print_audio_devices()

    args = parser.parse_args()
    config_location = None
    if args.config_location is None:
        config_location = os.path.join(os.path.expanduser("~"), '.ledserver')
    else:
        config_location = os.path.join(args.config_location, '.ledserver')

    if args.no_conf:
        logger.info("Using in-memory configuration")
        serverconfig = serverconfiguration.ServerConfiguration()
    else:
        logger.info("Using configuration from {}".format(config_location))
        serverconfig = serverconfiguration.PersistentConfiguration(config_location, args.no_store)

    logger.info("Applying arguments {}".format(args))

    # Update num pixels
    if args.num_pixels is not None:
        num_pixels = args.num_pixels
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_NUM_PIXELS, num_pixels)

    # Update num rows
    if args.num_rows is not None:
        num_rows = args.num_rows
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_NUM_ROWS, num_rows)

    # Update LED device
    if args.device is not None:
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_DEVICE, args.device)

    if args.device_candy_server is not None:
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_DEVICE_CANDY_SERVER, args.device_candy_server)

    if args.device_panel_mapping is not None:
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_DEVICE_PANEL_MAPPING, args.device_panel_mapping)

    # Update Audio device
    if args.audio_device_index is not None:
        serverconfig.setConfigurationValue(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX, args.audio_device_index)

    if args.process_timing:
        record_timings = True

    # Adjust from configuration

    # Audio
    maxChannels = 2
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_MAX_CHANNELS) is not None:
        maxChannels = serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_MAX_CHANNELS)

    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX) is not None:
        logger.info("Overriding Audio device with device index {}".format(
            serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX)))
        audio.AudioInput.overrideDeviceIndex = serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX)
        # Initialize global audio
        globalAudio = audio.GlobalAudio(serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_DEVICE_INDEX), num_channels=maxChannels)
    else:
        globalAudio = audio.GlobalAudio(num_channels=maxChannels)
    
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_ENABLED) is not None:
        audio.GlobalAudio.global_autogain_enabled = serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_ENABLED)
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_MAXGAIN) is not None:
        audio.GlobalAudio.global_autogain_maxgain = serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_MAXGAIN)
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_TIME) is not None:
        audio.GlobalAudio.global_autogain_time = serverconfig.getConfiguration(serverconfiguration.CONFIG_AUDIO_AUTOADJUST_TIME)
    
    # strand test
    if args.strand:
        strandTest(serverconfig.createOutputDevice(), serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS))

    # Initialize project
    proj = serverconfig.getActiveProjectOrDefault()
    proj.activate()

    # Init defaults
    default_values['fs'] = 48000  # ToDo: How to provide fs information to downstream effects?
    default_values['num_pixels'] = serverconfig.getConfiguration(serverconfiguration.CONFIG_NUM_PIXELS)
    
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_ADVERTISE_BLUETOOTH):
        logger.debug("Adding bluetooth server to the mix")
        midiAdvertiseName = serverconfig.getConfiguration(serverconfiguration.CONFIG_ADVERTISE_BLUETOOTH_NAME)
        try:
            from audioled_controller import bluetooth
            fullMidiController = midi_full.MidiProjectController(callback=handleMidiOut)
            midiController.append(fullMidiController)
            midiBluetooth = bluetooth.MidiBluetoothService(callback=handleMidiIn)
        except Exception as e:
            logger.warning("Ignoring Bluetooth error. Bluetooth not available on all plattforms")
            logger.error(e)
            logger.debug("Bluetooth error", exc_info=1)
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_IN):
        fullMidiController = midi_full.MidiProjectController(callback=handleMidiOut)
        midiController.append(fullMidiController)
        midiCtrlPortIn = mido.open_input(serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_IN), virtual=True)
        logger.info("Added virtual MIDI port {}".format(serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_IN)))
        startMIDIThread()
    if serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_OUT):
        try:
            midiCtrlPortOut = mido.open_output(serverconfig.getConfiguration(serverconfiguration.CONFIG_MIDI_CTRL_PORT_OUT))
        except Exception as e:
            logger.error("Error creating midi out port: {}".format(e))

    logger.info("Creating server")
    server, midiGRPCService = grpc_server.create_server(handleMidiIn)
    server.add_insecure_port('[::]:5001')
    server.start()

    if serverconfig.getConfiguration(serverconfiguration.CONFIG_SERVER_EXPOSE):
        app = create_app()
        app.run(debug=False, host="0.0.0.0", port=args.port)
    else:
        app = create_app()
        app.run(debug=False, host="localhost", port=args.port)
    
    proj.stopProcessing()
    stop_signal = True
    logger.info("App shut down")
