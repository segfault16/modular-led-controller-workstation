import asyncio
import uuid
import traceback
from timeit import default_timer as timer
from typing import List

from audioled import modulation
from audioled import devices
from audioled import effect


class NodeException(Exception):
    def __init__(self, message, node, error):
        self.node = node
        self.error = error
        self.message = message
        super(NodeException, self).__init__(message)

class Node(object):
    def __init__(self, effect):
        self.effect = effect  # type: effect.Effect
        self.uid = None
        # TODO: Improve consistency with numInputChannels and numOutputChannels
        self.numInputChannels = 0
        self.numOutputChannels = 0
        self.__initstate__()
        self.numInputChannels = self.effect.numInputChannels()
        self.numOutputChannels = self.effect.numOutputChannels()

    def __initstate__(self):

        self.effect.numOutputChannels()

        self._outputBuffer = [None for i in range(0, self.effect.numOutputChannels())]
        self._inputBuffer = [None for i in range(0, self.effect.numInputChannels())]
        self._incomingConnections = []

        self.effect.setOutputBuffer(self._outputBuffer)
        self.effect.setInputBuffer(self._inputBuffer)

    def process(self):
        # reset input buffer
        for i in range(self.numInputChannels):
            self._inputBuffer[i] = None
        # propagate values
        for con in self._incomingConnections:
            self._inputBuffer[con.toChannel] = con.fromNode._outputBuffer[con.fromChannel]
        # process
        try:
            self.effect.process()
        except Exception as e:
            traceback.print_exc()
            raise NodeException("{}".format(e), self, e)

    async def update(self, dt):
        try:
            await self.effect.update(dt)
        except Exception as e:
            traceback.print_exc()
            raise NodeException("{}".format(e), self, e)

    def __cleanState__(self, stateDict):
        """
        Cleans given state dictionary from state objects beginning with __
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


class Connection(object):
    def __init__(self, from_node, from_channel, to_node, to_channel):
        self.fromChannel = from_channel
        self.fromNode = from_node
        self.toChannel = to_channel
        self.toNode = to_node
        self.uid = None

    def __getstate__(self):
        state = {}
        state['from_node_uid'] = self.fromNode.uid
        state['from_node_channel'] = self.fromChannel
        state['to_node_uid'] = self.toNode.uid
        state['to_node_channel'] = self.toChannel
        state['uid'] = self.uid
        return state


class ModulationSourceNode(object):
    """Wraps a source of modulation
    """
    def __init__(self, modulator):
        self.modulator = modulator  # type: modulation.ModulationSource
        self.uid = None

    def update(self, dt):
        if self.modulator is not None:
            self.modulator.update(dt)


class Modulation(object):
    """Defines a parameter modulation based on a ModulationSourceNode
    """
    def __init__(self, modulationSourceNode, amount, inverted, targetNode, targetParameter):
        assert isinstance(modulationSourceNode, ModulationSourceNode)
        assert isinstance(targetNode, Node)
        self.modulationSource = modulationSourceNode  # type: ModulationSourceNode
        self.amount = amount
        self.inverted = inverted
        self.targetNode = targetNode  # type: Node
        self.targetEffect = targetNode.effect  # type: effect.Effect
        self.targetParameter = targetParameter
        self.uid = None

    def __getstate__(self):
        state = {}
        state['modulation_source_uid'] = self.modulationSource.uid
        state['target_node_uid'] = self.targetNode.uid
        state['target_param'] = self.targetParameter
        state['amount'] = self.amount
        state['inverted'] = self.inverted
        state['uid'] = self.uid
        return state

    def __setstate__(self, state):
        targetParam = state.get('target_param', None)
        if targetParam is not None:
            state['targetParameter'] = targetParam
        self.__dict__.update(state)

    def updateParameter(self, stateDict):
        self.__setstate__(stateDict)

    def propagate(self):
        if self.modulationSource is None or self.targetEffect is None or self.targetParameter is None:
            return
        # Get current value
        curValue = self.modulationSource.modulator.getValue()
        # Propagate change
        # calculate and propagate new offset for this parameter
        curOffset = self.targetEffect.getParameterOffset(self.targetParameter)
        if curOffset is None:
            curOffset = 0
        newOffset = curValue * self.amount
        if self.inverted:
            newOffset = -1 * newOffset
        newOffset = curOffset + newOffset
        self.targetEffect.setParameterOffset(self.targetParameter, self.targetEffect.getParameterDefinition(), newOffset)
        self._lastValue = curValue


class Timing(object):
    def __init__(self):
        self._max = None
        self._min = None
        self._avg = None
        self._count = 0

    def update(self, timing):
        if self._count % 100 == 0:
            self._max = timing
            self._min = timing
            self._avg = timing
            self._count = 0
        else:
            self._max = max(self._max, timing)
            self._min = min(self._min, timing)
            self._avg = (self._avg * self._count + timing) / (self._count + 1)
        self._count = self._count + 1
        self._count = min(100, self._count)


class Updateable(object):
    def update(self, dt, event_loop):
        raise NotImplementedError("Update not implemented")

    def process(self):
        raise NotImplementedError("Process not implemented")


class FilterGraph(Updateable):
    def __init__(self, recordTimings=False, asyncUpdate=True):
        self.recordTimings = recordTimings
        self.asyncUpdate = asyncUpdate
        self._filterConnections = []  # type: List[Connection]
        self._filterNodes = []  # type: List[Node]
        self._processOrder = []  # type: List[Node]
        self._updateTimings = {}
        self._processTimings = {}
        self._outputNode = None
        self._project = None
        self._modulationSources = []  # type: List[ModulationSourceNode]
        self._modulations = []  # type: List[Modulation]

    def update(self, dt, event_loop=asyncio.get_event_loop()):
        if self._outputNode is None:
            # Pass the update, since no num_pixels can be provided to the effects
            return
        # Update modulation sources
        for modSource in self._modulationSources:
            modSource.update(dt)
        # Reset parameter offsets
        for modCon in self._modulations:
            modCon.targetEffect.resetParameterOffsets()
        # Propagate modulated parameters to effects
        for modCon in self._modulations:
            modCon.propagate()
        # The actual update on the FilterGraph
        if self.asyncUpdate:
            time = timer()
            # gather all async updates
            asyncio.set_event_loop(event_loop)

            async def handle_async_exception(node, func, param):
                await func(param)

            all_tasks = asyncio.gather(
                *[asyncio.ensure_future(handle_async_exception(node, node.update, dt)) for node in self._processOrder])
            # wait for completion
            event_loop.run_until_complete(all_tasks)
            self.updateUpdateTiming("all_async", timer() - time)
        else:
            for node in self._processOrder:

                if self.recordTimings:
                    time = timer()
                event_loop.run_until_complete(node.update(dt))
                if self.recordTimings:
                    self.updateUpdateTiming(str(node.effect), timer() - time)

    def process(self):
        time = None

        if self._outputNode is None:
            # Pass the process, since no num_pixels can be provided to the effects
            return

        for node in self._processOrder:

            if self.recordTimings:
                time = timer()
            node.process()
            if self.recordTimings:
                self.updateProcessTiming(node, timer() - time)

    def updateProcessTiming(self, node, timing):
        if node not in self._processTimings:
            self._processTimings[node] = Timing()

        self._processTimings[node].update(timing)

    def updateUpdateTiming(self, node, timing):
        if node not in self._updateTimings:
            self._updateTimings[node] = Timing()

        self._updateTimings[node].update(timing)

    def printUpdateTimings(self):
        if self._updateTimings is None:
            print("No metrics collected")
            return
        print("Update timings:")
        for key, val in self._updateTimings.items():
            print("{0:30s}: min {1:1.8f}, max {2:1.8f}, avg {3:1.8f}".format(key[0:30], val._min, val._max, val._avg))

    def printProcessTimings(self):
        if self._processTimings is None:
            print("No metrics collected")
            return
        print("Process timings:")
        for key, val in self._processTimings.items():
            print("{0:30s}: min {1:1.8f}, max {2:1.8f}, avg {3:1.8f}".format(
                str(key.effect)[0:30], val._min, val._max, val._avg))

    def addEffectNode(self, effect):
        """Adds a filter node to the graph

        Parameters
        ----------
        filterNode: node to add
        """
        effect._filterGraph = self
        node = Node(effect)
        node.uid = uuid.uuid4().hex
        if isinstance(effect, devices.LEDOutput):
            if self._outputNode is None:
                self._outputNode = node
            else:
                raise RuntimeError("Filtergraph can only have one LED Output")

        self._filterNodes.append(node)
        self._updateProcessOrder()
        return node

    def removeEffectNode(self, effect):
        """Removes a filter node from the graph

        Parameters
        ----------
        filterNode: node to remove
        """
        # Remove connections
        connections = [con for con in self._filterConnections if con.fromNode.effect == effect or con.toNode.effect == effect]
        for con in connections:
            self._filterConnections.remove(con)
        # Remove Node
        node = next(node for node in self._filterNodes if node.effect == effect)
        if node is not None:
            self._filterNodes.remove(node)
            if node == self._outputNode:
                self._outputNode = None
            if node in self._processOrder:
                self._processOrder.remove(node)
                self._updateProcessOrder()

    def addConnection(self, fromEffect, fromEffectChannel, toEffect, toEffectChannel):
        """Adds a connection between two filters
        """
        # find fromNode
        fromNode = next(node for node in self._filterNodes if node.effect == fromEffect)  # type: Node
        # find toNode
        toNode = next(node for node in self._filterNodes if node.effect == toEffect)  # type: Node
        # construct connection
        newConnection = Connection(fromNode, fromEffectChannel, toNode, toEffectChannel)
        newConnection.uid = uuid.uuid4().hex
        if self._connectionWillMakeGraphCyclic(newConnection):
            raise RuntimeError("Connection would make graph cyclic")
        self._filterConnections.append(newConnection)
        toNode._incomingConnections.append(newConnection)
        self._updateProcessOrder()
        return newConnection

    def addNodeConnection(self, fromNodeUid, fromEffectChannel, toNodeUid, toEffectChannel):
        """Adds a connection between two filters based on node uid
        """
        fromNode = next(node for node in self._filterNodes if node.uid == fromNodeUid)
        toNode = next(node for node in self._filterNodes if node.uid == toNodeUid)
        newConnection = Connection(fromNode, fromEffectChannel, toNode, toEffectChannel)
        newConnection.uid = uuid.uuid4().hex
        if self._connectionWillMakeGraphCyclic(newConnection):
            raise RuntimeError("Connection would make graph cyclic")
        self._filterConnections.append(newConnection)
        toNode._incomingConnections.append(newConnection)
        self._updateProcessOrder()
        return newConnection

    def removeConnection(self, fromEffect, fromEffectChannel, toEffect, toEffectChannel):
        """Removes a connection between two filters
        """
        # find connection
        con = next(con for con in self._filterConnections
                   if con.fromNode.effect == fromEffect and con.toNode.effect == toEffect
                   and con.fromChannel == fromEffectChannel and con.toChannel == toEffectChannel)
        if con is not None:
            self._filterConnections.remove(con)
            con.toNode._incomingConnections.remove(con)
        None

    def getLEDOutput(self):
        return self._outputNode

    def addModulationSource(self, modulationSource):
        """Adds a modulation source
        """
        modSourceNode = ModulationSourceNode(modulationSource)
        modSourceNode.uid = uuid.uuid4().hex
        self._modulationSources.append(modSourceNode)
        return modSourceNode

    def removeModulationSource(self, modSourceUid):
        """Removes a modulation source with the given uid
        """
        modSourceNode = next(modSource for modSource in self._modulationSources if modSource.uid == modSourceUid)

        if modSourceNode is None:
            return

        mods = [mod for mod in self._modulations if mod.modulationSource == modSourceNode]
        # delete mods
        for mod in mods:
            self.removeModulation(mod.uid)

        # delete modSourceNode
        self._modulationSources.remove(modSourceNode)

    def addModulation(self, modSourceUid, targetNodeUid, targetParam=None, amount=0, inverted=False):
        """Adds a modulation driven by a modulationSource
        """
        modSource = next(modSource for modSource in self._modulationSources if modSource.uid == modSourceUid)
        targetNode = next(node for node in self._filterNodes if node.uid == targetNodeUid)
        newMod = Modulation(modSource, amount, inverted, targetNode, targetParam)
        newMod.uid = uuid.uuid4().hex
        self._modulations.append(newMod)
        return newMod

    def removeModulation(self, modUid):
        """Removes a modulation driven by a modulationSource
        """
        mod = next(mod for mod in self._modulations if mod.uid == modUid)  # type: Modulation
        if mod is not None:
            # Reset parameter offset
            if mod.targetParameter is not None:
                mod.targetEffect.setParameterOffset(mod.targetParameter, mod.targetEffect.getParameterDefinition(), 0)

            # Remove modulation
            self._modulations.remove(mod)

    def _updateProcessOrder(self):
        processOrder = []
        if self._outputNode is None:
            print("No output node")
            return

        unprocessedNodes = self._filterNodes.copy()
        processOrder.append(self._outputNode)
        unprocessedNodes.remove(self._outputNode)

        fatalError = False

        while not fatalError and len(unprocessedNodes) > 0:
            sizeBefore = len(unprocessedNodes)
            curProcessOrder = processOrder.copy()

            for node in unprocessedNodes.copy():
                # find connections
                cons = [con for con in self._filterConnections if con.fromNode == node]
                # check all nodes after this node have been processed
                satisfied = True
                for con in cons:
                    if con.toNode not in curProcessOrder:
                        satisfied = False
                        continue

                if satisfied:
                    processOrder.append(node)
                    unprocessedNodes.remove(node)

            sizeAfter = len(unprocessedNodes)
            fatalError = sizeAfter == sizeBefore

        # Check remaining unprocessed nodes for circular connections
        # for node in unprocessedNodes:
        #     cons = [con for con in self._filterConnections if con.fromNode == node]
        #     for con in cons:
        #         if con.toNode in self._processOrder:
        #             raise RuntimeError("Circular connection detected")

        processOrder.reverse()

        # Reset number of pixels
        for node in self._filterNodes:
            if node is not self.getLEDOutput():
                node.effect.setNumOutputPixels(None)
        # Propagate num pixels and num cols
        for node in reversed(processOrder):
            # find connections to the current node
            inputConnections = [con for con in self._filterConnections if con.toNode == node]
            # print("{} input connections found for node {}".format(len(inputConnections), node.effect))
            for con in inputConnections:
                num_pixels = node.effect.getNumInputPixels(con.toChannel)
                num_rows = node.effect.getNumInputRows(con.toChannel)
                # find node
                iNode = con.fromNode
                # propagate pixels
                if iNode is not None:
                    iNode.effect.setNumOutputRows(num_rows)
                    iNode.effect.setNumOutputPixels(num_pixels)

        # Debug output
        for node in processOrder.copy():
            if node.effect._num_pixels is None:
                processOrder.remove(node)
        # persist
        self._processOrder = processOrder

    def __getstate__(self):
        state = {}
        nodes = [node for node in self._filterNodes]
        state['nodes'] = nodes
        connections = []
        for con in self._filterConnections:
            connections.append(con.__getstate__())
        state['connections'] = connections
        state['recordTimings'] = self.recordTimings
        state['modulationSources'] = [mod for mod in self._modulationSources]
        state['modulations'] = [con.__getstate__() for con in self._modulations]
        return state

    def __setstate__(self, state):
        self.__init__()
        if 'recordTimings' in state:
            self.recordTimings = state['recordTimings']
        if 'nodes' in state:
            nodes = state['nodes']
            for node in nodes:
                newnode = self.addEffectNode(node.effect)
                newnode.uid = node.uid
        if 'connections' in state:
            connections = state['connections']
            for con in connections:
                fromChannel = con['from_node_channel']
                toChannel = con['to_node_channel']
                newcon = self.addNodeConnection(con['from_node_uid'], fromChannel, con['to_node_uid'], toChannel)
                newcon.uid = con['uid']
        if 'modulationSources' in state:
            modSources = state['modulationSources']
            for mod in modSources:
                newModSource = self.addModulationSource(mod.modulator)
                newModSource.uid = mod.uid
        if 'modulations' in state:
            mods = state['modulations']
            for mod in mods:
                newMod = self.addModulation(mod['modulation_source_uid'], mod['target_node_uid'], mod['target_param'],
                                            mod['amount'], mod['inverted'])
                newMod.uid = mod['uid']

    def propagateNumPixels(self, num_pixels, num_rows=1):
        if self.getLEDOutput() is not None:
            self.getLEDOutput().effect.setNumOutputPixels(num_pixels)
            self.getLEDOutput().effect.setNumOutputRows(num_rows)
            self._updateProcessOrder()

    def _connectionWillMakeGraphCyclic(self, connection):
        targetNode = connection.toNode
        curNode = connection.fromNode
        if targetNode == curNode:
            return True
        # traverse predecessors and check if connection.toNode is one of them
        return self._checkHasPredecessor(curNode, targetNode, [])

    def _checkHasPredecessor(self, curNode, targetNode, visitedNodes):
        if targetNode == curNode:
            return True
        predecessors = [con for con in self._filterConnections if con.toNode == curNode]
        furtherNodes = []
        for con in predecessors:
            node = con.fromNode
            if node is targetNode:
                return True
            if node not in visitedNodes:
                furtherNodes.append(node)
        visitedNodes.append(curNode)
        for node in furtherNodes:
            if self._checkHasPredecessor(node, targetNode, visitedNodes):
                return True
        return False
