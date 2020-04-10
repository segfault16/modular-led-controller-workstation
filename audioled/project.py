import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)
from typing import List, Dict
import audioled.devices
import audioled.audio
import audioled.filtergraph
import time
import multiprocessing as mp
import traceback
import ctypes
import logging
import threading

import os
from functools import wraps
import numpy as np

import logging
logger = logging.getLogger(__name__)

def ensure_parent(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        #if os.getpid() != self._creator_pid:
        #    raise RuntimeError("{} can only be called in the " "parent.".format(func.__name__))
        return func(self, *args, **kwargs)

    return inner


class PublishQueue(object):
    def __init__(self):
        self._queues = []  # type: List[mp.JoinableQueue]
        self._creator_pid = os.getpid()

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_queues'] = []
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    @ensure_parent
    def register(self):
        q = mp.JoinableQueue()
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

class BrightnessMessage:
    def __init__(self, value):
        self.value = value

class ShowMessage:
    def __init(self):
        pass


class ReplaceFiltergraphMessage:
    def __init__(self, deviceId, slotId, filtergraph):
        self.filtergraph = filtergraph
        self.slotId = slotId
        self.deviceId = deviceId

    def __str__(self):
        return "FiltergraphMessage - deviceId: {}, slotId: {}, filtergraph: {}".format(self.deviceId, self.slotId,
                                                                                       self.filtergraph)

class UpdateModulationSourceValueMessage:
    def __init__(self, deviceMask, controller, newValue):
        self.controller = controller
        self.newValue = newValue
        self.deviceMask = deviceMask

    def __str__(self):
        return "UpdateModulationSourceValueMessage - deviceMask: {}, controller: {}, newValue: {}".format(self.deviceMask, self.controller,
                                                                                       self.newValue)


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
    # logger.info("got item {} in process {}".format(dt, os.getpid()))

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
        logger.error("Error propagating to device: {}".format(e))


def worker_process_nodeMessage(filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, slotId: int,
                               message: NodeMessage):
    if message.slotId != slotId:
        # Message not meant for this slot
        logger.debug("Skipping node message for slot {}".format(message.slotId))
        return
    logger.info("Process node message: {}".format(message))
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
        logger.info("Skipping modulation message for slot {}".format(message.slotId))
        return
    logger.info("Process modulation message: {}".format(message))
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
        logger.info("Skipping modulation source message for slot {}".format(message.slotId))
        return
    logger.info("Process modulation source message: {}".format(message))
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
        logger.info("Skipping connection message for slot {}".format(message.slotId))
        return
    logger.info("Process connection message: {}".format(message))
    if message.operation == 'add':
        con = message.params  # type: Dict[str, str]
        newCon = filtergraph.addNodeConnection(con['from_node_uid'], con['from_node_channel'], con['to_node_uid'],
                                               con['to_node_channel'])
        newCon.uid = con['uid']
    elif message.operation == 'remove':
        filtergraph.removeConnection(message.conUid)


def worker(q: PublishQueue, filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController, deviceId: int,
           slotId: int):
    """Worker process for specific filtergraph for outputDevice
    
    Arguments:
        q {PublishQueue} -- [description]
        filtergraph {FilterGraph} -- [description]
        outputDevice {audioled.devices.LEDController} -- [description]
        slotId {int} -- [description]
    """
    try:
        threading.current_thread().name = 'WorkerThread'
        logger.info("filtergraph process {} start".format(os.getpid()))
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
                elif isinstance(message, UpdateModulationSourceValueMessage):
                    message = message  # type: UpdateModulationSourceValueMessage
                    dMask = 2 << deviceId
                    if dMask & message.deviceMask:
                        logger.debug("Device mask match for device {}".format(deviceId))
                        filtergraph.updateModulationSourceValue(message.controller, message.newValue)
                else:
                    logger.warning("Message not supported: {}".format(message))
            except audioled.filtergraph.NodeException:
                logger.info("Continuing on NodeException")
            finally:
                # logger.info("{} done".format(os.getpid()))
                # q.task_done()
                # TODO: Investigate the task_done() called too many times error further
                # Quick fix seems to be:
                with q._cond:
                    if not q._unfinished_tasks.acquire(True):
                        raise ValueError('task_done() called too many times')
                    if q._unfinished_tasks._semlock._is_zero():
                        q._cond.notify_all()
        outputDevice.shutdown()
        logger.info("filtergraph process {} exit".format(os.getpid()))
    except Exception as e:
        traceback.print_exc()
        logger.error("filtergraph process {} exited due to: {}".format(os.getpid(), e))
    except:
        logger.info("filtergraph process interrupted")


def output(q, outputDevice: audioled.devices.LEDController, virtualDevice: audioled.devices.VirtualOutput):
    try:
        threading.current_thread().name = 'OutputThread'
        logger.info("output process {} start".format(os.getpid()))
        for message in iter(q.get, None):
            if isinstance(message, ShowMessage):
                npArray = np.ctypeslib.as_array(virtualDevice._shared_array.get_obj()).reshape(3, -1)
                outputDevice.show(npArray.reshape(3, -1, order='C'))
            elif isinstance(message, BrightnessMessage):
                bm = message  # type: BrightnessMessage
                outputDevice.setBrightness(bm.value)
            q.task_done()
        outputDevice.shutdown()
        logger.error("output process {} exit".format(os.getpid()))
    except Exception as e:
        traceback.print_exc()
        logger.info("process {} exited due to: {}".format(os.getpid(), e))
    except:
        logger.info("process interrupted")


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
            self._last_t
        except AttributeError:
            self._last_t = 0
        try:
            self._cur_t
        except AttributeError:
            self._cur_t = 0
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
        self._lock = mp.Lock()
        self._handlerLock = mp.Lock() 
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
                slot._contentRoot = self._contentRoot
        # Activate loaded scene
        if self.activeSceneId is not None:
            logger.debug("Active scene {} from setstate".format(self.activeSceneId))
            # TODO: Needs to be revised?
            self.activateScene(self.activeSceneId)
            self.previewSlot(self.activeSceneId)

    def setDevice(self, device: audioled.devices.MultiOutputWrapper):
        logging.debug("setting device")
        if not isinstance(device, audioled.devices.MultiOutputWrapper):
            raise RuntimeError("Device has to be MultiOutputWrapper")
        if self._devices == device._devices:
            return
        self._devices = device._devices
        logger.info("Devices updated. Renewing active scene...")
        self.stopProcessing()
        if self.activeSceneId is not None:
            self.activateScene(self.activeSceneId)

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        """Update active FilterGraph

        Arguments:
            dt {[float]} -- Time since last update
        """
        # logger.info("project: update")
        if self._processingEnabled:
            aquired = self._lock.acquire(block=True, timeout=0)
            if not aquired:
                logger.info("Skipping update, couldn't acquire lock")
                return
            try:
                self._cur_t = self._cur_t + dt
                self._sendUpdateCommand(dt)
                if(self._cur_t - self._last_t > 1 ):
                    # logger.debug("Updating preview device")
                    self._updatePreviewDevice(dt, event_loop)
                    self._last_t = self._cur_t
                # Wait for previous show command done
                if self._showQueue is not None:
                    self._showQueue.join(1)
                # Wait for all updates
                if self._publishQueue is not None:
                    self._publishQueue.join(1)
                # Send show command and return
                self._sendShowCommand()

            except TimeoutError:
                logger.error("Update timeout. Forcing reset")
                self.stopProcessing()
                if self.activeSceneId is not None:
                    logger.debug("No scene active. Activating.")
                    self.activateScene(self.activeSceneId)
            else:
                self._lock.release()
        else:
            time.sleep(0.01)
            logger.debug("Waiting...")

    def process(self):
        """Process active FilterGraph
        """
        self._processPreviewDevice()

    def setFiltergraphForSlot(self, slotId, filterGraph):
        logger.info("Set {} for slot {}".format(filterGraph, slotId))
        if isinstance(filterGraph, FilterGraph):
            filterGraph._contentRoot = self._contentRoot
            self.slots[slotId] = filterGraph

    def activateScene(self, sceneId):
        """Activates a scene

        Scene: Project Slot per Output Device
        """
        logger.info("Activating scene {}".format(sceneId))

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
            logger.debug("activate scene - releasing lock")
            self._lock.release()

    def updateModulationSourceValue(self, deviceMask, controller, newValue):
        self._sendModulationSourceValueUpdateCommand(deviceMask, controller, newValue)

    def setBrightness(self, value):
        self._sendBrightnessCommand(value)
        
        
    def _createOrUpdateProcess(self, dIdx, device, slotId, filterGraph):
        if dIdx in self._filtergraphProcesses:
            # Send command
            self._sendReplaceFiltergraphCommand(dIdx, slotId, filterGraph)
            return
        # Create device
        outputDevice = None
        virtualDevice = None
        fgDevice = None
        if isinstance(device, audioled.devices.VirtualOutput):
            # Reuse virtual output, construct output process if not already present
            virtualDevice = device
            realDevice = virtualDevice.device
            fgDevice = device
            if realDevice not in self._outputProcesses:
                outputDevice = realDevice
            pass
        elif isinstance(device, audioled.devices.PanelWrapper):
            if isinstance(device.device, audioled.devices.VirtualOutput):
                fgDevice = device  # PanelWrapper
                virtualDevice = fgDevice.device  # VirtualDevice
                realDevice = virtualDevice.device  # Select real device in virtualoutput
                if realDevice not in self._outputProcesses:
                    outputDevice = realDevice
            else:
                oldPanelWrapper = device
                
                # Construct virtual output, TODO: Make sure device is realDevice...
                realDevice = oldPanelWrapper.device

                lock = mp.Lock()
                array = mp.Array(ctypes.c_uint8, 3 * device.getNumPixels(), lock=lock)
                virtualDevice = audioled.devices.VirtualOutput(device=realDevice,
                                                        num_pixels=realDevice.getNumPixels(),
                                                        shared_array=array,
                                                        shared_lock=lock,
                                                        num_rows=realDevice.getNumRows(),
                                                        start_index=0)

                oldPanelWrapper.setDevice(virtualDevice)
                fgDevice = oldPanelWrapper

            
        else:
            # New virtual output
            outputDevice = device
            lock = mp.Lock()
            array = mp.Array(ctypes.c_uint8, 3 * device.getNumPixels(), lock=lock)
            virtualDevice = audioled.devices.VirtualOutput(device=device,
                                                    num_pixels=device.getNumPixels(),
                                                    shared_array=array,
                                                    shared_lock=lock,
                                                    num_rows=device.getNumRows(),
                                                    start_index=0)
            fgDevice = virtualDevice
            realDevice =  device

        # Start filtergraph process
        successful = False
        while not successful:
            q = self._publishQueue.register()
            p = mp.Process(target=worker, args=(q, filterGraph, fgDevice, dIdx, slotId))
            p.start()
            # Process sometimes doesn't start...
            q.put(123)
            time.sleep(0.1)
            if not q._unfinished_tasks._semlock._is_zero():
                logger.warning("Process didn't respond in time!")
                self._publishQueue.unregister(q)
                p.join(0.1)
                if p.is_alive():
                    p.terminate()
            else:
                successful = True
        self._filtergraphProcesses[dIdx] = p
        logger.debug('Started process for device {} with device {}'.format(dIdx, fgDevice))

        # Start output process
        if outputDevice is not None:
            outSuccessful = False
            while not outSuccessful:
                q = self._showQueue.register()
                p = mp.Process(target=output, args=(q, outputDevice, virtualDevice))
                p.start()
                # Make sure process starts
                q.put("test")
                time.sleep(0.1)
                if not q._unfinished_tasks._semlock._is_zero():
                    logger.warning("Output process didn't respond in time!")
                    self._showQueue.unregister(p)
                    p.join(0.1)
                    if p.is_alive():
                        p.terminate()
                else:
                    outSuccessful = True
                    q.put("first")
            self._outputProcesses[outputDevice] = p
            logger.info("Started output process for device {}".format(outputDevice))

    def stopProcessing(self):
        logger.info('Stop processing')
        self._processingEnabled = False
        aquire = self._lock.acquire(block=True, timeout=1)
        if not aquire:
            logger.warning("Couldn't get lock. Force shutdown")
            try:
                for p in self._filtergraphProcesses.values():
                    p.join(0.1)
                    if p.is_alive():
                        p.terminate()
                for p in self._outputProcesses.values():
                    p.join(0.1)
                    if p.is_alive():
                        p.terminate()
                self._lock.release()
            finally:
                self._filtergraphProcesses = {}
                self._outputProcesses = {}
                self._publishQueue = None
                self._showQueue = None
                self._processingEnabled = True
            return
        # Normal shutdown
        try:
            logger.debug("Ending queue")
            if self._publishQueue is not None:
                self._publishQueue.publish(None)
                self._publishQueue.close()
                self._publishQueue.join_thread()
                logger.debug('Publish queue ended')
                self._publishQueue = None
            if self._showQueue is not None:
                self._showQueue.publish(None)
                self._showQueue.close()
                self._showQueue.join_thread()
                logger.debug("Show queue ended")
                self._showQueue = None
            logger.debug("Ending processes")
            for p in self._filtergraphProcesses.values():
                p.join()
            logger.debug("Filtergraph processes joined")
            self._filtergraphProcesses = {}
            for p in self._outputProcesses.values():
                p.join()
            logger.debug("Output processes joined")
            self._outputProcesses = {}
            logger.debug('All processes joined')
        finally:
            logger.debug("stopped processing - releasing lock")
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
        self.activeSlotId = slotId
        logger.info("Edit slot {} with {}".format(slotId, self.slots[slotId]))
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
            logger.info("Initializing slot {}".format(slotId))
            self.slots[slotId] = FilterGraph()
        fg = self.slots[slotId]
        fg._contentRoot = self._contentRoot
        return fg

    def getSceneMatrix(self):
        return self.outputSlotMatrix

    def setSceneMatrix(self, value):
        # TODO: Validate
        if self.outputSlotMatrix is not None:
            # Check if slot matrix stayed the same
            if self.outputSlotMatrix == value:
                logger.debug("No change to scene matrix")
                return
        self.outputSlotMatrix = value
        logger.debug("Updating scene matrix")
        self.activateScene(self.activeSceneId)

    def _sendBrightnessCommand(self, value):
        self._showQueue.publish(BrightnessMessage(value))

    def _handleNodeAdded(self, node: audioled.filtergraph.Node, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'add', node.effect))
        finally:
            self._handlerLock.release()

    def _handleNodeRemoved(self, node: audioled.filtergraph.Node, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'remove'))
        finally:
            self._handlerLock.release()

    def _handleNodeUpdate(self, node: audioled.filtergraph.Node, updateParameters, niceness = 0.1):
        """
        updates can come rapidly, default niceness 0.1
        """
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(NodeMessage(self.activeSlotId, node.uid, 'update', updateParameters))
        finally:
            self._handlerLock.release()

    def _handleModulationAdded(self, mod: audioled.filtergraph.Modulation, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'add', mod))
        finally:
            self._handlerLock.release()

    def _handleModulationRemoved(self, mod: audioled.filtergraph.Modulation, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'remove'))
        finally:
            self._handlerLock.release()

    def _handleModulationUpdate(self, mod: audioled.filtergraph.Modulation, updateParameters, niceness = 0.1):
        """
        updates can come rapidly, default niceness 0.1
        """
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationMessage(self.activeSlotId, mod.uid, 'update', updateParameters))
        finally:
            self._handlerLock.release()

    def _handleModulationSourceAdded(self, modSource: audioled.filtergraph.ModulationSourceNode, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'add', modSource))
        finally:
            self._handlerLock.release()

    def _handleModulationSourceRemoved(self, modSource: audioled.filtergraph.ModulationSourceNode, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'remove'))
        finally:
            self._handlerLock.release()

    def _handleModulationSourceUpdate(self, modSource: audioled.filtergraph.ModulationSourceNode, updateParameters, niceness = 0.1):
        """
        updates can come rapidly, default niceness 0.1
        """
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ModulationSourceMessage(self.activeSlotId, modSource.uid, 'update', updateParameters))
        finally:
            self._handlerLock.release()

    def _handleConnectionAdded(self, con: audioled.filtergraph.Connection, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ConnectionMessage(self.activeSlotId, con.uid, 'add', con.__getstate__()))
        finally:
            self._handlerLock.release()

    def _handleConnectionRemoved(self, con: audioled.filtergraph.Connection, niceness = 0.0):
        self._handlerLock.acquire()
        time.sleep(niceness)
        try:
            self._publishQueue.publish(ConnectionMessage(self.activeSlotId, con.uid, 'remove'))
        finally:
            self._handlerLock.release()

    def _sendUpdateCommand(self, dt):
        if self._publishQueue is None:
            logger.info("No publish queue. Possibly exiting")
            return
        self._publishQueue.publish(UpdateMessage(dt, audioled.audio.GlobalAudio.buffer))

    def _sendShowCommand(self):
        if self._showQueue is None:
            logger.info("No show queue. Possibly exiting")
            return
        self._showQueue.publish(ShowMessage())

    def _sendReplaceFiltergraphCommand(self, dIdx, slotId, filtergraph):
        if self._publishQueue is not None:
            self._publishQueue.publish(ReplaceFiltergraphMessage(dIdx, slotId, filtergraph))

    def _sendModulationSourceValueUpdateCommand(self, deviceMask, controller, newValue):
        if self._publishQueue is not None:
            self._publishQueue.publish(UpdateModulationSourceValueMessage(deviceMask, controller, newValue))

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
                    logger.info("propagating {} pixels on {} rows".format(previewDevice.getNumPixels(), previewDevice.getNumRows()))
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
