import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)


class Project(Updateable):
    def __init__(self, name='Empty project', description='', device=None):
        self.slots = [None for i in range(127)]
        self.activeSlotId = 0
        self.name = name
        self.description = description
        self.id = None
        self._device = device
        self._contentRoot = None

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
        for slot in self.slots:
            if slot is not None:
                slot._project = self

    def setDevice(self, device):
        self._device = device

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        """Update active FilterGraph
        
        Arguments:
            dt {[float]} -- Time since last update
        """
        activeFilterGraph = self.getSlot(self.activeSlotId)
        if activeFilterGraph is not None:
            # Propagate num pixels from server configuration
            if self._device is not None and activeFilterGraph.getLEDOutput() is not None:
                if (self._device.getNumPixels() != activeFilterGraph.getLEDOutput().effect.getNumOutputPixels()
                        or self._device.getNumRows() != activeFilterGraph.getLEDOutput().effect.getNumOutputRows()):
                    print("propagating {} pixels on {} rows".format(self._device.getNumPixels(), self._device.getNumRows()))
                    activeFilterGraph.propagateNumPixels(self._device.getNumPixels(), self._device.getNumRows())
                activeFilterGraph.update(dt, event_loop)

    def process(self):
        """Process active FilterGraph
        """
        activeFilterGraph = self.getSlot(self.activeSlotId)
        if activeFilterGraph is not None:
            if self._device is not None and activeFilterGraph.getLEDOutput() is not None:
                activeFilterGraph.process()
                if activeFilterGraph.getLEDOutput()._outputBuffer[0] is not None and self._device is not None:
                    self._device.show(activeFilterGraph.getLEDOutput()._outputBuffer[0])

    def setFiltergraphForSlot(self, slotId, filterGraph):
        print("Set {} for slot {}".format(filterGraph, slotId))
        if isinstance(filterGraph, FilterGraph):
            filterGraph._project = self
            self.slots[slotId] = filterGraph

    def activateSlot(self, slotId):
        self.activeSlotId = slotId
        print("Activate slot {} with {}".format(slotId, self.slots[slotId]))
        return self.getSlot(slotId)

    def getSlot(self, slotId):
        if self.slots[slotId] is None:
            self.slots[slotId] = FilterGraph()
        return self.slots[slotId]
