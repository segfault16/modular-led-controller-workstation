// Helper service for layout
export const NODETYPE_EFFECT_NODE = "effect_node";
export const NODETYPE_EFFECT_INOUT = "effect_channel";
export const NODETYPE_MODULATOR = "modulator";

export const EDGETYPE_MODULATION = "modulation";
export const EDGETYPE_EFFECT_INOUT = "effect_inout";
export const EDGETYPE_EFFECT_CONNECTION = "effect_connection";

import audioInputIcon from '../../img/audioled.audio.AudioInput.png';
import movingIcon from '../../img/audioled.audioreactive.MovingLight.png';
import spectrumIcon from '../../img/audioled.audioreactive.Spectrum.png';
import vuIcon from '../../img/audioled.audioreactive.VUMeterPeak.png';
import colorIcon from '../../img/audioled.colors.Color.png';
import colorWheelIcon from '../../img/audioled.colors.ColorWheel.png';
import interpolateHSV from '../../img/audioled.colors.InterpolateHSV.png';
import ledIcon from '../../img/audioled.devices.LEDOutput.png';
import glowIcon from '../../img/audioled.effects.AfterGlow.png';
import appendIcon from '../../img/audioled.effects.Append.png';
import combineIcon from '../../img/audioled.effects.Combine.png';
import mirrorIcon from '../../img/audioled.effects.Mirror.png';
import shiftIcon from '../../img/audioled.effects.Shift.png';
import defenceIcon from '../../img/audioled.generative.DefenceMode.png';
import swimmingPoolIcon from '../../img/audioled.generative.SwimmingPool.png';
import springCombineIcon from '../../img/audioled.effects.SpringCombine.png';
import fallingStarsIcon from '../../img/audioled.generative.FallingStars.png';
import pendulumIcon from '../../img/audioled.generative.Pendulum.png'
import bonfireIcon from '../../img/audioled.audioreactive.Bonfire.png'
import swingIcon from '../../img/audioled.effects.Swing.png'
import squareIcon from '../../img/audioled.panelize.MakeSquare.png'
import diamondIcon from '../../img/audioled.panelize.MakeDiamond.png'
import rubyIcon from '../../img/audioled.panelize.MakeRuby.png'
import batmanIcon from '../../img/audioled.panelize.MakeBatman.png'
import labyrinthIcon from '../../img/audioled.panelize.MakeLabyrinth.png'
import keyboardIcon from '../../img/audioled.generative.MidiKeyboard.png'
import candyIcon from '../../img/audioled.input.CandyServer.png'
import gifIcon from '../../img/audioled.generative.GIFPlayer.png'

var icons = {
  'audioled.audio.AudioInput': audioInputIcon,
  'audioled.audioreactive.Spectrum': spectrumIcon,
  'audioled.audioreactive.MovingLight': movingIcon,
  'audioled.audioreactive.VUMeterPeak': vuIcon,
  'audioled.audioreactive.VUMeterRMS': vuIcon,
  'audioled.colors.ColorWheel': colorWheelIcon,
  'audioled.colors.StaticRGBColor': colorIcon,
  'audioled.devices.LEDOutput': ledIcon,
  'audioled.effects.Combine': combineIcon,
  'audioled.effects.Append': appendIcon,
  'audioled.effects.AfterGlow': glowIcon,
  'audioled.effects.Mirror': mirrorIcon,
  'audioled.generative.SwimmingPool': swimmingPoolIcon,
  'audioled.effects.Shift': shiftIcon,
  'audioled.generative.DefenceMode': defenceIcon,
  'audioled.colors.InterpolateHSV': interpolateHSV,
  'audioled.effects.SpringCombine': springCombineIcon,
  'audioled.generative.FallingStars': fallingStarsIcon,
  'audioled.generative.Pendulum': pendulumIcon,
  'audioled.audioreactive.Bonfire': bonfireIcon,
  'audioled.effects.Swing': swingIcon,
  'audioled.panelize.MakeSquare': squareIcon,
  'audioled.panelize.MakeDiamond': diamondIcon,
  'audioled.panelize.MakeRuby': rubyIcon,
  'audioled.panelize.MakeBatman': batmanIcon,
  'audioled.panelize.MakeLabyrinth': labyrinthIcon,
  'audioled.generative.MidiKeyboard': keyboardIcon,
  'audioled.input.CandyServer': candyIcon,
  'audioled.generative.GIFPlayer': gifIcon,

}

export const VisGraphLayout = {
  updateNodeLevels: function (nodes, edges, reservedLevel = null) {
    const effectNodes = nodes.filter(n => n.nodeType === NODETYPE_EFFECT_NODE);
    const outNodes = nodes.filter(n => n.nodeType === NODETYPE_EFFECT_INOUT && n.group === 'out')
    const inNodes = nodes.filter(n => n.nodeType === NODETYPE_EFFECT_INOUT && n.group === 'in')
    const modNodes = nodes.filter(n => n.nodeType == NODETYPE_MODULATOR);

    // Find effect nodes without output
    const startWith = effectNodes.filter(n => outNodes.filter(o => o.nodeUid == n.id).length == 0)
    var processed = []
    var unprocessed = [...effectNodes]

    // scale reservedLevel
    
    var reserved = null
    if(reservedLevel != null) {
      reserved = (reservedLevel -1) / -3
    }

    nodes.forEach(n => {
      n.level = 0
    })

    startWith.forEach(sN => {
      var level = 0;
      sN.level = level;
      level++;
      if (reserved != null && reserved == level) {
        level++
      }
      var idx = unprocessed.indexOf(sN)
      if (idx > -1) {
        unprocessed.splice(idx, 1)
      }
      processed.push(sN)
      var go_ahead = unprocessed.length > 0
      while (go_ahead) {
        var before = unprocessed.length
        var curUnprocessed = [...unprocessed]
        var curPocessed = [...processed]
        curUnprocessed.forEach(n => {
          // find connections from this node
          var cons = edges.filter(e => e.from_node === n.id);
          // check all nodes after this node have been processed (or find one that isn't)
          if (cons.find(c => (curPocessed.find(t => t.id === c.to_node) == null)) == null) {
            n.level = level
            processed.push(n)
            var idx = unprocessed.indexOf(n)
            if (idx > -1) {
              unprocessed.splice(idx, 1)
            }
          }
        })
        // increase level
        level++;
        if (reserved != null && reserved == level) {
          level++
        }
        go_ahead = before != unprocessed.length
      }
    })
    // invert levels, scale to 3
    effectNodes.forEach(n => {
      n.level = - 3 * n.level + 1
    })

    // process input and output nodes
    inNodes.forEach(n => {
      var effectNode = nodes.find(t => t.id === n.nodeUid)
      if (effectNode != null) {
        n.level = effectNode.level - 1
      }
    })
    outNodes.forEach(n => {
      var effectNode = nodes.find(t => t.id === n.nodeUid)
      if (effectNode != null) {
        n.level = effectNode.level + 1
      }
    })

    // process modulator nodes
    modNodes.forEach(n => {
      // get edges for this node
      var firstEdge = edges.find(e => e.from === n.id);
      if (firstEdge != null) {
        var toNode = nodes.find(t => t.id === firstEdge.to)
        if (toNode != null) {
          n.level = toNode.level
        }
      }
    })
  },
  conUid: function(inout, index, uid) {
    return inout + '_' + index + '_' + uid;
  },

  createEffectNode: function(json) {
    var visNode = {};
    this.updateEffectNode(visNode, json);
    return visNode;
  },

  createModulatorNode: function(json) {
    var visNode = {};
    this.updateModulatorNode(visNode, json);
    return visNode;
  },

  createEffectNodesAndEdges: function(json) {
    var allNodes = [];
    var allEdges = [];
    var visNode = this.createEffectNode(json);
    allNodes.push(visNode);
    var { nodes, edges } = this.createInputOutputNodesAndEdges(json, visNode);
    allNodes = allNodes.concat(nodes);
    allEdges = allEdges.concat(edges);
    return { nodes: allNodes, edges: allEdges }
  },

  createInputOutputNodesAndEdges: function(json, visNode) {
    // update input and output nodes
    var numOutputChannels = json['py/state']['numOutputChannels'];
    var numInputChannels = json['py/state']['numInputChannels'];
    var nodes = [];
    var edges = [];
    for (var i = 0; i < numOutputChannels; i++) {
      var uid = this.conUid('out', i, visNode.id);
      var outNode = {};
      outNode.group = 'out';
      outNode.id = uid;
      outNode.label = `${i}`;
      outNode.shape = 'circle';
      outNode.nodeType = NODETYPE_EFFECT_INOUT;
      outNode.nodeUid = visNode.id;
      outNode.nodeChannel = i;
      outNode.level = visNode.level != null ? (visNode.level + 1) : 0;
      nodes.push(outNode);
      edges.push({ id: outNode.id, from: visNode.id, to: outNode.id, width: 4, arrows: { to: { enabled: false } }, edgeType: EDGETYPE_EFFECT_INOUT });
    }
    for (var i = 0; i < numInputChannels; i++) {
      var uid = this.conUid('in', i, visNode.id);
      var inNode = {};
      inNode.group = 'in';
      inNode.id = uid;
      inNode.label = `${i}`;
      inNode.shape = 'circle';
      inNode.nodeType = NODETYPE_EFFECT_INOUT;
      inNode.nodeUid = visNode.id;
      inNode.nodeChannel = i;
      inNode.level = visNode.level != null ? (visNode.level - 1) : 0;
      nodes.push(inNode);
      edges.push({ id: inNode.id, from: inNode.id, to: visNode.id, width: 4, arrows: { to: { enabled: false } }, edgeType: EDGETYPE_EFFECT_INOUT });
    }
    return { nodes, edges };
  },

  updateEffectNode: function(visNode, json) {
    console.debug('Update Effect Node:', json["py/state"]);
    var uid = json["py/state"]["uid"];
    var name = json["py/state"]["effect"]["py/object"];
    visNode.id = uid;
    visNode.level = 0;
    visNode.label = name;
    visNode.shape = 'circularImage';
    visNode.group = 'ok';
    visNode.nodeType = NODETYPE_EFFECT_NODE;
    var icon = icons[name];
    visNode.image = icon ? icon : '';

  },

  updateModulatorNode: function(visNode, json) {
    console.debug('Update Modulator Node:', json);
    var uid = json["uid"];
    visNode.id = uid;
    visNode.level = 0;
    visNode.label = "modulator"
    visNode.shape = 'ellipse';
    visNode.group = 'ok';
    visNode.nodeType = NODETYPE_MODULATOR;
  },

  createVisConnection: function(con) {
    var edge = {};
    this.updateEffectConnection(edge, con);
    return edge;
  },

  createModulatorConnection: function(con) {
    var edge = {};
    this.updateModulationConnection(edge, con);
    return edge;
  },

  updateEffectConnection: function(edge, json) {
    console.debug('Update Vis Connection:', json["py/state"]);
    var state = json["py/state"];
    edge.id = state["uid"];
    
    edge.from = this.conUid('out', state['from_node_channel'], state['from_node_uid'])
    edge.from_channel = state["from_node_channel"];
    edge.from_node = state['from_node_uid']
    
    edge.to = this.conUid('in', state['to_node_channel'], state['to_node_uid'])
    edge.to_channel = state["to_node_channel"];
    edge.to_node = state['to_node_uid']
    edge.arrows = 'middle'
    edge.group = "connection"
    
    edge.width = 4
    edge.physics = false
    edge.edgeType = EDGETYPE_EFFECT_CONNECTION;
  },

  updateModulationConnection: function(edge, json) {
    console.debug('Update Mod Connection:', json);
    var state = json["py/state"];
    edge.from = state['modulation_source_uid'];
    edge.to = state['target_node_uid'];
    edge.id = state['uid'];
    edge.edgeType = EDGETYPE_MODULATION;
  }
}

export default VisGraphLayout;