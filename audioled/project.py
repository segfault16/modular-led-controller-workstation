import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)
from typing import List
import audioled.devices
import audioled.audio
import threading
import time
import multiprocessing
import traceback
from timeit import default_timer as timer

import os
import multiprocessing
from functools import wraps


def ensure_parent(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        if os.getpid() != self._creator_pid:
            raise RuntimeError("{} can only be called in the "
                               "parent.".format(func.__name__))
        return func(self, *args, **kwargs)
    return inner

class PublishQueue(object):
    def __init__(self):
        self._queues = []
        self._creator_pid = os.getpid()

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_queues'] = []
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    @ensure_parent
    def register(self):
        q = multiprocessing.Queue()
        self._queues.append(q)
        return q

    @ensure_parent
    def publish(self, val):
        for q in self._queues:
            q.put(val)

def worker(q: PublishQueue, filtergraph: FilterGraph, outputDevice: audioled.devices.LEDController):
    """Worker process for specific filtergraph for outputDevice
    
    Arguments:
        q {PublishQueue} -- [description]
        filtergraph {FilterGraph} -- [description]
        outputDevice {audioled.devices.LEDController} -- [description]
    """
    try:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        filtergraph.propagateNumPixels(outputDevice.getNumPixels(), outputDevice.getNumRows())
        for dt, audioBuffer in iter(q.get, None):
            print("got item {} in process {}".format(dt, os.getpid()))
    
            # TODO: Hack to propagate audio?
            audioled.audio.GlobalAudio.buffer = audioBuffer

            # Update Filtergraph
            filtergraph.update(dt, event_loop)
            filtergraph.process()
            # Propagate to outDevice
            buffer = filtergraph.getLEDOutput()._outputBuffer[0]
            outputDevice.show(buffer)
    except Exception as e:
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
        self._filterGraphForDeviceIndex = {}
        self._outputThreads = {}
        self._publishQueue = PublishQueue()

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
        self.sendUpdateCommand(dt)
        
        # Process preview in this process
        if self._previewDeviceIndex is not None:
            activeFilterGraph = self.getSlot(self.activeSlotId)
            if activeFilterGraph is None:
                return
            previewDevice = self._devices[self._previewDeviceIndex]
            if previewDevice is not None and activeFilterGraph.getLEDOutput() is not None:
                if (previewDevice.getNumPixels() != activeFilterGraph.getLEDOutput().effect.getNumOutputPixels()
                    or previewDevice.getNumRows() != activeFilterGraph.getLEDOutput().effect.getNumOutputRows()):
                    print("propagating {} pixels on {} rows".format(previewDevice.getNumPixels(),
                                                                    previewDevice.getNumRows()))
                    activeFilterGraph.propagateNumPixels(previewDevice.getNumPixels(), previewDevice.getNumRows())
            activeFilterGraph.update(dt, event_loop)

    def process(self):
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
        self._previewDeviceIndex = 0
        self.activeSlotId = sceneId
        
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
                p = multiprocessing.Process(target=worker, args=(self._publishQueue.register(), filterGraph, device))
                p.start()
                self._outputThreads[dIdx] = p
                print('Started process for device {}'.format(dIdx))
            dIdx += 1

    def stopProcessing(self):
        print('Stop processing')
        self._publishQueue.publish(None)
        for p in self._outputThreads.values():
            p.join()
        print('All processes joined')
        self._outputThreads = {}

    def sendUpdateCommand(self, dt):
        self._publishQueue.publish((dt, audioled.audio.GlobalAudio.buffer))

    def previewSlot(self, slotId, deviceId):
        # TODO: Separate preview slot and active slot
        self.activeSlotId = slotId
        print("Activate slot {} with {}".format(slotId, self.slots[slotId]))
        return self.getSlot(slotId)

    def getSlot(self, slotId):
        if self.slots[slotId] is None:
            self.slots[slotId] = FilterGraph()
        return self.slots[slotId]