import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)
from typing import List, Dict
import audioled.devices
import audioled.audio
import audioled.filtergraph
import time
import multiprocessing
import traceback
import json
from timeit import default_timer as timer
import ctypes

import os
import multiprocessing
from functools import wraps
import numpy as np


def ensure_parent(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        if os.getpid() != self._creator_pid:
            raise RuntimeError("{} can only be called in the " "parent.".format(func.__name__))
        return func(self, *args, **kwargs)

    return inner

class PublishQueue(object):
    def __init__(self):
        self._queues = []  # type: List[multiprocessing.JoinableQueue]
        self._creator_pid = os.getpid()

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_queues'] = []
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    @ensure_parent
    def register(self):
        q = multiprocessing.JoinableQueue()
        self._queues.append(q)
        return q
    
    @ensure_parent
    def unregister(self, q):
        self._queues = [queue for queue in self._queues if queue is not q]

    @ensure_parent
    def publish(self, val):
        for q in self._queues:
            q.put(val, True, 1)

    @ensure_parent
    def close(self):
        for q in self._queues:
            q.close()

    @ensure_parent
    def join_thread(self):
        for q in self._queues:
            q.join_thread()

    @ensure_parent
    def join(self, timeout=None):
        # Join without timeout
        if timeout is None:
            for q in self._queues:
                q.join()
            return
        # Join with timeout
        stop = time.time() + timeout
        all_done = False
        while not all_done and time.time() < stop:
            time.sleep(0.001)
            all_done = True
            for q in self._queues:
                if not q._unfinished_tasks._semlock._is_zero():
                    all_done = False
        if all_done:
            for q in self._queues:
                q.join()
            return
        raise TimeoutError


class UpdateMessage:
    def __init__(self, dt, audioBuffer):
        self.dt = dt
        self.audioBuffer = audioBuffer

class ReplaceFiltergraphMessage:
    def __init__(self, deviceId, slotId, filtergraph):
        self.filtergraph = filtergraph
        self.slotId = slotId
        self.deviceId = deviceId

    def __str__(self):
        return "FiltergraphMessage - deviceId: {}, slotId: {}, filtergraph: {}".format(self.deviceId, self.slotId, self.filtergraph)

class NodeMessage:
    def __init__(self, slotId, nodeUid, operation, params=None):
        self.slotId = slotId
        self.nodeUid = nodeUid
        self.operation = operation
        self.params = params

    def __str__(self):
        return "NodeMessage - slotId: {}, uid: {}, operation: {}, params: {}".format(self.slotId, self.nodeUid, self.operation,
                                                                                     self.params)


class ModulationMessage:
    def __init__(self, slotId, modUid, operation, params=None):
        self.slotId = slotId
        self.modUid = modUid
        self.operation = operation
        self.params = params

    def __str__(self):
        return "ModulationMessage - slotId: {}, uid: {}, operation: {}, params: {}".format(
            self.slotId, self.modUid, self.operation, self.params)


class ModulationSourceMessage:
    def __init__(self, slotId, modSourceUid, operation, params=None):
        self.slotId = slotId
        self.modSourceUid = modSourceUid
        self.operation = operation
        self.params = params

    def __str__(self):
        return "ModulationSourceMessage - slotId: {}, uid: {}, operation: {}, params: {}".format(
            self.slotId, self.modSourceUid, self.operation, self.params)


class ConnectionMessage:
    def __init__(self, slotId, conUid, operation, params=None):
        self.slotId = slotId
        self.conUid = conUid
        self.operation = operation
        self.params = params

    def __str__(self):
        return "ConnectionMessage - slotId: {}, uid: {}, operation: {}, params: {}".format(
            self.slotId, self.conUid, self.operation, self.params)


def worker_process_updateMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                                 event_loop, message: UpdateMessage):
    dt = message.dt
    audioBuffer = message.audioBuffer
    # print("got item {} in process {}".format(dt, os.getpid()))

    # TODO: Hack to propagate audio?
    audioled.audio.GlobalAudio.buffer = audioBuffer

    # Update Filtergraph
    filtergraph.update(dt, event_loop)
    filtergraph.process()
    # Propagate to outDevice
    try:
        if filtergraph.getLEDOutput() is None:
            return
        fgBuffer = filtergraph.getLEDOutput()._outputBuffer
        if fgBuffer is None or len(fgBuffer) <= 0:
            return
        outputDevice.show(fgBuffer[0])
    except Exception as e:
        print("Error propagating to device: {}".format(e))


def worker_process_nodeMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                               message: NodeMessage):
    if message.slotId != slotId:
        # Message not meant for this slot
        print("Skipping node message for slot {}".format(message.slotId))
        return
    print("Process node message: {}".format(message))
    if message.operation == 'add':
        node = filtergraph.addEffectNode(message.params)
        node.uid = message.nodeUid
    elif message.operation == 'remove':
        filtergraph.removeEffectNode(message.nodeUid)
    elif message.operation == 'update':
        filtergraph.updateNodeParameter(message.nodeUid, message.params)


def worker_process_modulationMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                                     message: ModulationMessage):
    if message.slotId != slotId:
        print("Skipping modulation message for slot {}".format(message.slotId))
        return
    print("Process modulation message: {}".format(message))
    if message.operation == 'add':
        mod = message.params  # type: audioled.filtergraph.Modulation
        newMod = filtergraph.addModulation(modSourceUid=mod.modulationSource.uid,
                                           targetNodeUid=mod.targetNode.uid,
                                           targetParam=mod.targetParameter,
                                           amount=mod.amount,
                                           inverted=mod.inverted)
        newMod.uid = mod.uid
    elif message.operation == 'remove':
        filtergraph.removeModulation(message.modUid)
    elif message.operation == 'update':
        filtergraph.updateModulationParameter(message.modUid, message.params)


def worker_process_modulationSourceMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                                           message: ModulationSourceMessage):
    if message.slotId != slotId:
        print("Skipping modulation source message for slot {}".format(message.slotId))
        return
    print("Process modulation source message: {}".format(message))
    if message.operation == 'add':
        modSource = message.params
        newModSource = filtergraph.addModulationSource(modSource)
        newModSource.uid = modSource.uid
    elif message.operation == 'remove':
        filtergraph.removeModulationSource(message.modSourceUid)
    elif message.operation == 'update':
        filtergraph.updateModulationSourceParameter(message.modSourceUid, message.params)


def worker_process_connectionMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                                     message: ConnectionMessage):
    if message.slotId != slotId:
        print("Skipping connection message for slot {}".format(message.slotId))
        return
    print("Process connection message: {}".format(message))
    if message.operation == 'add':
        con = message.params  # type: Dict[str, str]
        newCon = filtergraph.addNodeConnection(con['from_node_uid'], con['from_node_channel'], con['to_node_uid'],
                                               con['to_node_channel'])
        newCon.uid = con['uid']
    elif message.operation == 'remove':
        filtergraph.removeConnection(message.conUid)


def worker(q: PublishQueue, filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, deviceId: int, slotId: int):
    """Worker process for specific filtergraph for outputDevice
    
    Arguments:
        q {PublishQueue} -- [description]
        filtergraph {FilterGraph} -- [description]
        outputDevice {audioled.devices.LEDController} -- [description]
        slotId {int} -- [description]
    """
    try:
        print("process {} start".format(os.getpid()))
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        filtergraph.propagateNumPixels(outputDevice.getNumPixels(), outputDevice.getNumRows()) 
        for message in iter(q.get, None):
            try:
                if isinstance(message, UpdateMessage):
                    worker_process_updateMessage(filtergraph, outputDevice, slotId, event_loop, message)
                elif isinstance(message, NodeMessage):
                    worker_process_nodeMessage(filtergraph, outputDevice, slotId, message)
                elif isinstance(message, ModulationMessage):
                    worker_process_modulationMessage(filtergraph, outputDevice, slotId, message)
                elif isinstance(message, ModulationSourceMessage):
                    worker_process_modulationSourceMessage(filtergraph, outputDevice, slotId, message)
                elif isinstance(message, ConnectionMessage):
                    worker_process_connectionMessage(filtergraph, outputDevice, slotId, message)
                elif isinstance(message, ReplaceFiltergraphMessage):
                    if message.deviceId == deviceId:
                        filtergraph = message.filtergraph
                        slotId = message.slotId
                        filtergraph.propagateNumPixels(outputDevice.getNumPixels(), outputDevice.getNumRows())
                else:
                    print("Message not supported: {}".format(message))
            except audioled.filtergraph.NodeException:
                print("Continuing on NodeException")
            finally:
                # print("{} done".format(os.getpid()))
                # q.task_done()
                # TODO: Investigate the task_done() called too many times error further
                # Quick fix seems to be:
                with q._cond:
                    if not q._unfinished_tasks.acquire(True):
                        raise ValueError('task_done() called too many times')
                    if q._unfinished_tasks._semlock._is_zero():
                        q._cond.notify_all()
                
        print("process {} exit".format(os.getpid()))
    except Exception as e:
        traceback.print_exc()
        print("process {} exited due to: {}".format(os.getpid(), e))
    except:
        print("process interrupted")

def output(q, outputDevice: audioled.devices.LEDController, virtualDevice: audioled.devices.VirtualOutput):
    try:
        print("output process {} start".format(os.getpid()))
        for message in iter(q.get, None):
            npArray = np.ctypeslib.as_array(virtualDevice._shared_array.get_obj()).reshape(3, -1)
            outputDevice.show(npArray.reshape(3, -1, order='C'))
            q.task_done()
        print("output process {} exit".format(os.getpid()))
    except Exception as e:
        traceback.print_exc()
        print("process {} exited due to: {}".format(os.getpid(), e))
    except:
        print("process interrupted")

class Project(Updateable):
    def __init__(self, name='Empty project', description='', device=None):
        self.slots = [None for i in range(127)]
        self.activeSceneId = 0
        self.activeSlotId = 0
        self.name = name
        self.description = description
        self.id = None
        self.outputSlotMatrix = {}
        self.__initstate__()

    def __initstate__(self):
        try:
            self.outputSlotMatrix
        except AttributeError:
            self.outputSlotMatrix = {}
        try:
            self.activeSceneId
        except AttributeError:
            self.activeSceneId = self.activeSlotId
        self._previewDevice = None  # type: audioled.devices.LEDController
        self._previewDeviceIndex = 0
        self._contentRoot = None
        self._devices = []
        self._filterGraphForDeviceIndex = {}
        self._filtergraphProcesses = {}
        self._outputProcesses = {}
        self._publishQueue = PublishQueue()
        self._showQueue = PublishQueue()
        self._lock = multiprocessing.Lock()
        self._processingEnabled = True

    def __cleanState__(self, stateDict):
        """
        Cleans given state dictionary from state objects beginning with _
        """
        for k in list(stateDict.keys()):
            if k.startswith('_'):
                stateDict.pop(k)
        return stateDict

    def __getstate__(self):
        """
        Default implementation of __getstate__ that deletes buffer, call __cleanState__ when overloading
        """
        state = self.__dict__.copy()
        self.__cleanState__(state)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__initstate__()
        idx = -1
        for slot in self.slots:
            idx += 1
            # Initialize Project Callback
            if slot is not None:
                slot._project = self
        # Activate loaded scene
        if self.activeSceneId is not None:
            print("Active scene {}".format(self.activeSceneId))
            self.activateScene(self.activeSceneId)

    def setDevice(self, device: audioled.devices.MultiOutputWrapper):
        if not isinstance(device, audioled.devices.MultiOutputWrapper):
            raise RuntimeError("Device has to be MultiOutputWrapper")
        self._devices = device._devices
        print("Devices updated. Renewing active scene...")
        self.stopProcessing()
        if self.activeSceneId is not None:
            self.activateScene(self.activeSceneId)

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        """Update active FilterGraph

        Arguments:
            dt {[float]} -- Time since last update
        """
        # print("project: update")
        if self._processingEnabled:
            aquired = self._lock.acquire(block=True, timeout=0)
            if not aquired:
                print("Skipping update, couldn't acquire lock")
                return
            try:
                self._sendUpdateCommand(dt)
                self._updatePreviewDevice(dt, event_loop)
                # Wait for previous show command done
                if self._showQueue is not None:
                    self._showQueue.join(1)
                # Wait for all updates
                if self._publishQueue is not None:
                    self._publishQueue.join(1)
                # Send show command and return
                self._sendShowCommand()

            except TimeoutError:
                print("Update timeout")
                # TODO: Error handling

                # self.stopProcessing()
                # self.activateScene(self.activeSceneId)
            finally:
                self._lock.release()
        else:
            time.sleep(0.01)
            print("Waiting...")

    def process(self):
        """Process active FilterGraph
        """
        self._processPreviewDevice()

    def setFiltergraphForSlot(self, slotId, filterGraph):
        print("Set {} for slot {}".format(filterGraph, slotId))
        if isinstance(filterGraph, FilterGraph):
            filterGraph._project = self
            self.slots[slotId] = filterGraph

    def activateScene(self, sceneId):
        """Activates a scene

        Scene: Project Slot per Output Device
        """
        print("activate scene {}".format(sceneId))

        # TODO: Make configurable
        self._previewDeviceIndex = None
        self.activeSceneId = sceneId

        self._processingEnabled = False
        self._lock.acquire()
        try:
            # Create new publish queue
            if self._publishQueue is None:
                self._publishQueue = PublishQueue()
            # Create new show queue
            if self._showQueue is None:
                self._showQueue = PublishQueue()

            # Instanciate new scene
            dIdx = 0
            for device in self._devices:
                # Get slot Id associated with this device
                try:
                    slotId = self.outputSlotMatrix[str(dIdx)][str(sceneId)]
                except Exception:
                    # Backwards compatibility: Init with slotId = sceneId
                    if str(dIdx) not in self.outputSlotMatrix:
                        self.outputSlotMatrix[str(dIdx)] = {}
                    if sceneId not in self.outputSlotMatrix[str(dIdx)]:
                        self.outputSlotMatrix[str(dIdx)][str(sceneId)] = sceneId
                    slotId = sceneId

                # Get filtergraph
                filterGraph = self.getSlot(slotId)

                if dIdx == self._previewDeviceIndex:
                    dIdx += 1
                    continue
                
                self._createOrUpdateProcess(dIdx, device, slotId, filterGraph)
                dIdx += 1
        finally:
            self._processingEnabled = True
            print("activate scene - releasing lock")
            self._lock.release()

    def _createOrUpdateProcess(self, dIdx, device, slotId, filterGraph):
        if dIdx in self._filtergraphProcesses:
            # Send command
            self._sendReplaceFiltergraphCommand(dIdx, slotId, filterGraph)
            return
        # Create device
        outputDevice = None
        if isinstance(device, audioled.devices.VirtualOutput):
            # Reuse virtual output, construct output process if not already present
            realDevice = device.device
            if realDevice not in self._outputProcesses:
                outputDevice = realDevice
            pass
        else:
            # New virtual output
            outputDevice = device
            lock = multiprocessing.Lock()
            array = multiprocessing.Array(ctypes.c_uint8, 3*device.getNumPixels(), lock)
            device = audioled.devices.VirtualOutput(device=device,
                                                    num_pixels=device.getNumPixels(),
                                                    shared_array=array,
                                                    shared_lock=lock,
                                                    num_rows=device.getNumRows(),
                                                    start_index=0)
                                                    
        
        # Start filtergraph process
        successful = False
        while not successful:
            q = self._publishQueue.register()
            p = multiprocessing.Process(target=worker, args=(q, filterGraph, device, dIdx, slotId))
            p.start()
            # Process sometimes doesn't start...
            q.put(123)
            time.sleep(0.1)
            if not q._unfinished_tasks._semlock._is_zero():
                print("Process didn't respond in time!")
                self._publishQueue.unregister(q)
                p.join(0.1)
                if p.is_alive():
                    p.terminate()
            else:
                successful = True
        self._filtergraphProcesses[dIdx] = p
        print('Started process for device {} with device {}'.format(dIdx, device))

        # Start output process
        if outputDevice is not None:
            outSuccessful = False
            while not outSuccessful:
                q = self._showQueue.register()
                p = multiprocessing.Process(target=output, args=(q, outputDevice, device))
                p.start()
                # Make sure process starts
                q.put("test")
                time.sleep(0.1)
                if not q._unfinished_tasks._semlock._is_zero():
                    print("Output process didn't respond in time!")
                    self._showQueue.unregister(p)
                    p.join(0.1)
                    if p.is_alive():
                        p.terminate()
                else:
                    outSuccessful = True
                    q.put("first")
            self._outputProcesses[outputDevice] = p
            print("Started output process for device {}".format(outputDevice))

    def stopProcessing(self):
        print('Stop processing')
        self._processingEnabled = False
        aquire = self._lock.acquire(block=True, timeout=1)
        if not aquire:
            print("Couldn't get lock")
            self._lock.acquire()
        try:
            print("Ending queue")
            if self._publishQueue is not None:
                self._publishQueue.publish(None)
                self._publishQueue.close()
                self._publishQueue.join_thread()
                print('Publish queue ended')
                self._publishQueue = None
            if self._showQueue is not None:
                self._showQueue.publish(None)
                self._showQueue.close()
                self._showQueue.join_thread()
                print("Show queue ended")
                self._showQueue = None
            print("Ending processes")
            for p in self._filtergraphProcesses.values():
                p.join()
            print("Filtergraph processes joined")
            self._filtergraphProcesses = {}
            for p in self._outputProcesses.values():
                p.join()
            print("Output processes joined")
            self._outputProcesses = {}
            print('All processes joined')
        finally:
            print("stop processing - releasing lock")
            self._lock.release()
            self._processingEnabled = True

    def previewSlot(self, slotId):
        # Remove eventing from current previewSlot
        fg = self.getSlot(self.activeSceneId)  # type: FilterGraph
        fg._onConnectionAdded = None
        fg._onConnectionRemoved = None
        fg._onModulationAdded = None
        fg._onModulationRemoved = None
        fg._onModulationSourceAdded = None
        fg._onModulationSourceRemoved = None
        fg._onModulationSourceUpdate = None
        fg._onModulationUpdate = None
        fg._onNodeAdded = None
        fg._onNodeRemoved = None
        fg._onNodeUpdate = None
        # TODO: Separate preview slot and active slot
        self.activeSlotId = slotId
        print("Activate slot {} with {}".format(slotId, self.slots[slotId]))
        fg = self.getSlot(slotId)  # type: FilterGraph
        fg._onNodeAdded = self._handleNodeAdded
        fg._onNodeRemoved = self._handleNodeRemoved
        fg._onNodeUpdate = self._handleNodeUpdate
        fg._onModulationAdded = self._handleModulationAdded
        fg._onModulationRemoved = self._handleModulationRemoved
        fg._onModulationUpdate = self._handleModulationUpdate
        fg._onModulationSourceAdded = self._handleModulationSourceAdded
        fg._onModulationSourceRemoved = self._handleModulationSourceRemoved
        fg._onModulationSourceUpdate = self._handleModulationSourceUpdate
        fg._onConnectionAdded = self._handleConnectionAdded
        fg._onConnectionRemoved = self._handleConnectionRemoved

    def getSlot(self, slotId):
        if self.slots[slotId] is None:
            print("Initializing slot {}".format(slotId))
            self.slots[slotId] = FilterGraph()
        return self.slots[slotId]

    def getSceneMatrix(self):
        return self.outputSlotMatrix
    
    def setSceneMatrix(self, value):
        #matrix = json.loads(value, object_hook=lambda d: {int(k): {int(i):j for i,j in v.items()} if isinstance(v, dict) else v for k, v in d.items()})
        self.outputSlotMatrix = value
        self.activateScene(self.activeSceneId)

    def _handleNodeAdded(self, node: audioled.filtergraph.Node):
        self._lock.acquire()
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'add', node.effect))
        finally:
            self._lock.release()

    def _handleNodeRemoved(self, node: audioled.filtergraph.Node):
        self._lock.acquire()
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'remove'))
        finally:
            self._lock.release()

    def _handleNodeUpdate(self, node: audioled.filtergraph.Node, updateParameters):
        self._lock.acquire()
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'update', updateParameters))
        finally:
            self._lock.release()

    def _handleModulationAdded(self, mod: audioled.filtergraph.Modulation):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'add', mod))
        finally:
            self._lock.release()

    def _handleModulationRemoved(self, mod: audioled.filtergraph.Modulation):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'remove'))
        finally:
            self._lock.release()

    def _handleModulationUpdate(self, mod: audioled.filtergraph.Modulation, updateParameters):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'update', updateParameters))
        finally:
            self._lock.release()

    def _handleModulationSourceAdded(self, modSource: audioled.filtergraph.ModulationSourceNode):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'add', modSource))
        finally:
            self._lock.release()

    def _handleModulationSourceRemoved(self, modSource: audioled.filtergraph.ModulationSourceNode):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'remove'))
        finally:
            self._lock.release()

    def _handleModulationSourceUpdate(self, modSource: audioled.filtergraph.ModulationSourceNode, updateParameters):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'update', updateParameters))
        finally:
            self._lock.release()

    def _handleConnectionAdded(self, con: audioled.filtergraph.Connection):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ConnectionMessage(self.activeSlotId, con.uid, 'add', con.__getstate__()))
        finally:
            self._lock.release()

    def _handleConnectionRemoved(self, con: audioled.filtergraph.Connection):
        self._lock.acquire()
        try:
            self._publishQueue.publish(ConnectionMessage(self.activeSlotId, con.uid, 'remove'))
        finally:
            self._lock.release()

    def _sendUpdateCommand(self, dt):
        if self._publishQueue is None:
            print("No publish queue. Possibly exiting")
            return
        self._publishQueue.publish(UpdateMessage(dt, audioled.audio.GlobalAudio.buffer))
    
    def _sendShowCommand(self):
        if self._showQueue is None:
            print("No show queue. Possibly exiting")
            return
        self._showQueue.publish("show!")
    
    def _sendReplaceFiltergraphCommand(self, dIdx, slotId, filtergraph):
        self._publishQueue.publish(ReplaceFiltergraphMessage(dIdx, slotId, filtergraph))


    def _updatePreviewDevice(self, dt, event_loop=asyncio.get_event_loop()):
        # Process preview in this process
        if self._previewDeviceIndex is not None:
            activeFilterGraph = self.getSlot(self.activeSceneId)
            if activeFilterGraph is None:
                return
            previewDevice = self._devices[self._previewDeviceIndex]
            if previewDevice is not None and activeFilterGraph.getLEDOutput() is not None:
                if (previewDevice.getNumPixels() != activeFilterGraph.getLEDOutput().effect.getNumOutputPixels()
                        or previewDevice.getNumRows() != activeFilterGraph.getLEDOutput().effect.getNumOutputRows()):
                    print("propagating {} pixels on {} rows".format(previewDevice.getNumPixels(), previewDevice.getNumRows()))
                    activeFilterGraph.propagateNumPixels(previewDevice.getNumPixels(), previewDevice.getNumRows())
            activeFilterGraph.update(dt, event_loop)

    def _processPreviewDevice(self):
        """Process active FilterGraph
        """
        # Process preview in this process
        if self._previewDeviceIndex is not None:

            activeFilterGraph = self.getSlot(self.activeSceneId)
            if activeFilterGraph is None:
                return
            previewDevice = self._devices[self._previewDeviceIndex]
            if previewDevice is not None and activeFilterGraph.getLEDOutput() is not None:
                activeFilterGraph.process()
                if activeFilterGraph.getLEDOutput()._outputBuffer[0] is not None:
                    previewDevice.show(activeFilterGraph.getLEDOutput()._outputBuffer[0])