import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)
from typing import List, Dict
import audioled.devices
import audioled.audio
import audioled.filtergraph
import threading
import time
import multiprocessing
import traceback
import json
from timeit import default_timer as timer

import os
import multiprocessing
from functools import wraps


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
    def join(self):
        for q in self._queues:
            q.join()


class UpdateMessage:
    def __init__(self, dt, audioBuffer):
        self.dt = dt
        self.audioBuffer = audioBuffer


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


def worker(q: PublishQueue, filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int):
    """Worker process for specific filtergraph for outputDevice
    
    Arguments:
        q {PublishQueue} -- [description]
        filtergraph {FilterGraph} -- [description]
        outputDevice {audioled.devices.LEDController} -- [description]
        slotId {int} -- [description]
    """
    try:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        filtergraph.propagateNumPixels(outputDevice.getNumPixels(), outputDevice.getNumRows())
        for message in iter(q.get, None):
            try:
                if isinstance(message, UpdateMessage):
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
                            continue
                        fgBuffer = filtergraph.getLEDOutput()._outputBuffer
                        if fgBuffer is None or len(fgBuffer) <= 0:
                            continue
                        outputDevice.show(fgBuffer[0])
                    except Exception as e:
                        print("Error propagating to device: {}".format(e))
                elif isinstance(message, NodeMessage):
                    if message.slotId != slotId:
                        # Message not meant for this slot
                        print("Skipping node message for slot {}".format(message.slotId))
                        continue
                    print("Process node message: {}".format(message))
                    if message.operation == 'add':
                        node = filtergraph.addEffectNode(message.params)
                        node.uid = message.nodeUid
                    elif message.operation == 'remove':
                        filtergraph.removeEffectNode(message.nodeUid)
                    elif message.operation == 'update':
                        filtergraph.updateNodeParameter(message.nodeUid, message.params)
                elif isinstance(message, ModulationMessage):
                    if message.slotId != slotId:
                        print("Skipping modulation message for slot {}".format(message.slotId))
                        continue
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
                elif isinstance(message, ModulationSourceMessage):
                    if message.slotId != slotId:
                        print("Skipping modulation source message for slot {}".format(message.slotId))
                        continue
                    print("Process modulation source message: {}".format(message))
                    if message.operation == 'add':
                        modSource = message.params
                        newModSource = filtergraph.addModulationSource(modSource)
                        newModSource.uid = modSource.uid
                    elif message.operation == 'remove':
                        filtergraph.removeModulationSource(message.modSourceUid)
                    elif message.operation == 'update':
                        filtergraph.updateModulationSourceParameter(message.modSourceUid, message.params)
                elif isinstance(message, ConnectionMessage):
                    if message.slotId != slotId:
                        print("Skipping connection message for slot {}".format(message.slotId))
                        continue
                    print("Process connection message: {}".format(message))
                    if message.operation == 'add':
                        con = message.params  # type: Dict[str, str]
                        newCon = filtergraph.addNodeConnection(con['from_node_uid'], con['from_node_channel'],
                                                               con['to_node_uid'], con['to_node_channel'])
                        newCon.uid = con['uid']
                    elif message.operation == 'remove':
                        filtergraph.removeConnection(message.conUid)
                else:
                    print("Message not supported: {}".format(message))
            except audioled.filtergraph.NodeException:
                print("Continuing on NodeException")
            finally:
                q.task_done()
    except Exception as e:
        traceback.print_exc()
        print("process {} exited due to: {}".format(os.getpid(), e))
    except:
        print("process interrupted")


class Project(Updateable):
    def __init__(self, name='Empty project', description='', device=None):
        self.slots = [None for i in range(127)]
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
        self._previewDevice = None  # type: audioled.devices.LEDController
        self._previewDeviceIndex = 0
        self._contentRoot = None
        self._devices = []
        self._filterGraphForDeviceIndex = {}
        self._outputThreads = {}
        self._publishQueue = PublishQueue()
        self._lock = threading.Lock()
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
        self.__initstate__()
        self.__dict__.update(state)
        for slot in self.slots:
            if slot is not None:
                slot._project = self

    def setDevice(self, device: audioled.devices.MultiOutputWrapper):
        if not isinstance(device, audioled.devices.MultiOutputWrapper):
            raise RuntimeError("Device has to be MultiOutputWrapper")
        else:
            self._devices = device._devices

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        """Update active FilterGraph

        Arguments:
            dt {[float]} -- Time since last update
        """
        # print("project: update")
        if self._processingEnabled:
            aquired = self._lock.acquire(0)
            if not aquired:
                print("Skipping update, couldn't acquire lock")
                return
            try:
                self._sendUpdateCommand(dt)
                self._updatePreviewDevice(dt, event_loop)
                if self._publishQueue is not None:
                    self._publishQueue.join()
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

        # Stop current scene
        self.stopProcessing()

        # TODO: Make configurable
        self._previewDeviceIndex = None
        self.activeSlotId = sceneId

        self._processingEnabled = False
        self._lock.acquire()
        try:
            # Create new publish queue
            self._publishQueue = PublishQueue()

            # Instanciate new scene
            dIdx = 0
            for device in self._devices:
                # Get slot Id associated with this device
                try:
                    slotId = self.outputSlotMatrix[dIdx]
                except Exception:
                    # Backwards compatibility: Init with slotId = sceneId
                    self.outputSlotMatrix[dIdx] = sceneId
                    slotId = sceneId

                # TODO: For testing only, remove once outputSlotMatrix stable
                slotId = sceneId

                # Get filtergraph
                filterGraph = self.getSlot(slotId)

                if dIdx != self._previewDeviceIndex:
                    p = multiprocessing.Process(target=worker,
                                                args=(self._publishQueue.register(), filterGraph, device, slotId))
                    p.start()
                    self._outputThreads[dIdx] = p
                    print('Started process for device {} with device {}'.format(dIdx, device))
                dIdx += 1
        finally:
            self._lock.release()
            self._processingEnabled = True

    def stopProcessing(self):
        print('Stop processing')
        self._processingEnabled = False
        self._lock.acquire()
        try:
            if self._publishQueue is not None:
                self._publishQueue.publish(None)
                self._publishQueue.close()
                self._publishQueue.join_thread()
                print('Queue ended')
                self._publishQueue = None
            for p in self._outputThreads.values():
                p.join()
            print('All processes joined')
            self._outputThreads = {}
        finally:
            self._lock.release()
            self._processingEnabled = True

    def previewSlot(self, slotId):
        # Remove eventing from current previewSlot
        fg = self.getSlot(self.activeSlotId)  # type: FilterGraph
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
            self.slots[slotId] = FilterGraph()
        return self.slots[slotId]

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

    def _updatePreviewDevice(self, dt, event_loop=asyncio.get_event_loop()):
        # Process preview in this process
        if self._previewDeviceIndex is not None:
            activeFilterGraph = self.getSlot(self.activeSlotId)
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

            activeFilterGraph = self.getSlot(self.activeSlotId)
            if activeFilterGraph is None:
                return
            previewDevice = self._devices[self._previewDeviceIndex]
            if previewDevice is not None and activeFilterGraph.getLEDOutput() is not None:
                activeFilterGraph.process()
                if activeFilterGraph.getLEDOutput()._outputBuffer[0] is not None:
                    previewDevice.show(activeFilterGraph.getLEDOutput()._outputBuffer[0])