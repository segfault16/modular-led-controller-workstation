import asyncio

from audioled.filtergraph import (FilterGraph, Updateable)


class Project(Updateable):
    def __init__(self):
        self.slots = [None for i in range(127)]
        self.activeSlotId = 0

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        """Update active FilterGraph
        
        Arguments:
            dt {[float]} -- Time since last update
        """
        if self.getSlot(self.activeSlotId) is not None:
            self.getSlot(self.activeSlotId).update(dt, event_loop)

    def process(self):
        """Process active FilterGraph
        """
        if self.getSlot(self.activeSlotId) is not None:
            self.getSlot(self.activeSlotId).process()

    def setFiltergraphForSlot(self, slotId, filterGraph):
        print("Set {} for slot {}".format(filterGraph, slotId))
        if isinstance(filterGraph, FilterGraph):
            self.slots[slotId] = filterGraph

    def activateSlot(self, slotId):
        self.activeSlotId = slotId
        print("Activate slot {} with {}".format(slotId, self.slots[slotId]))
        return self.getSlot(slotId)

    def getSlot(self, slotId):
        if self.slots[slotId] is None:
            self.slots[slotId] = FilterGraph()
        return self.slots[slotId]
