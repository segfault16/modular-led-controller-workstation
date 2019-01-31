import React from "react";
import PropTypes from 'prop-types';
import "@babel/polyfill";
import Button from '@material-ui/core/Button';
import CloudUploadIcon from '@material-ui/icons/CloudUpload';
import SaveIcon from '@material-ui/icons/Save';
import Graph from "react-graph-vis";
import 'vis/dist/vis-network.min.css';
import Modal from '@material-ui/core/Modal';
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
import ConfigurationService from "../services/ConfigurationService";
import FilterGraphService from "../services/FilterGraphService";
import NodePopup from './NodePopup';
import './VisGraph.css';
import Measure from 'react-measure'

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
  'audioled.colors.InterpolateHSV': interpolateHSV

}

class VisGraph extends React.Component {
  
  constructor(props) {
    super(props);
    //this.slot = props.slot
    this.state = {
      slot: props.slot,
      network: {},
      graph: {
        nodes: [],
        edges: []
      },
      style: {
        // flex: "1",
        display: "absolute"
      },
      editNodePopup: {
        isShown: false,
        nodeUid: 0,
      },
      events: {
        select: ({ nodes, edges }) => {
          this.clearNodePopUp()
          if (nodes.length == 1) {
            this.editNode(nodes[0])
          }
        },
        doubleClick: ({ pointer: { canvas } }) => {
          this.addGraphNode();
        }
      },
      options: {
        layout: {
          hierarchical: {
            enabled: true,
            levelSeparation: 100,
            direction: "LR",
            nodeSpacing: 100,
            sortMethod: 'directed',

          },
        },
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -2000,
            centralGravity: 0.3,
            springLength: 25,
            springConstant: 0.5,
            damping: 0.88,
            avoidOverlap: 1
          },
          hierarchicalRepulsion: {
            centralGravity: .05,
            nodeDistance: 150,
            springLength: 100,
            springConstant: 0.5,
            damping: 0.8,
          },
          forceAtlas2Based: {
            gravitationalConstant: -26,
            centralGravity: 0.005,
            springLength: 100,
            springConstant: 0.18
          },
          maxVelocity: 146,
          timestep: 0.35,
          solver: 'barnesHut',
          stabilization: {
            enabled: false,
            onlyDynamicEdges: true
          },
        },
        interaction: {
          navigationButtons: false,
          hover: true
        },
        manipulation: {
          enabled: true,
          addNode: (data, callback) => {
            this.addGraphNode();
          },
          deleteNode: (data, callback) => {
            data.nodes.forEach(id => {
              var node = this.state.graph.nodes.find(node => node.id == id)
              if (node == null) {
                console.error("Cannot find node " + id)
              }
              if (node.nodeType == 'node') {
                // update callback data to include all input and output nodes for this node
                var inputOutputNodes = this.state.graph.nodes.filter(item => item.nodeType == 'channel' && item.nodeUid == id);
                data.nodes = data.nodes.concat(inputOutputNodes.map(x => x.id));
                FilterGraphService.deleteNode(id).finally(() => {
                  this.clearNodePopUp();
                })
              } else {
                console.log("Cannot delete node " + id)
                // Clear callback data
                data.nodes = []
                data.edges = []
                return
              }
              console.debug("Deleted node", id);
            });
            callback(data);

          },
          addEdge: (data, callback) => {
            if (data.from == data.to) {
              callback(null);
              return;
            }
            var fromNode = this.state.graph.nodes.find(item => item.id === data.from);
            var toNode = this.state.graph.nodes.find(item => item.id === data.to);
            if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in') {
              console.log("could add edge")
              FilterGraphService.addConnection(fromNode.nodeUid, fromNode.nodeChannel, toNode.nodeUid, toNode.nodeChannel, data, callback).then(connection => {
                this.updateVisConnection(data, connection)
                callback(data);
              });
            } else {
              console.log("could not add edge")
            }
            return;
          },
          deleteEdge: (data, callback) => {
            data.edges.forEach(edgeUid => {
              var edge = this.state.graph.edges.find(item => item.id === edgeUid);
              var fromNode = this.state.graph.nodes.find(item => item.id === edge.from);
              var toNode = this.state.graph.nodes.find(item => item.id === edge.to);
              if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in') {
                var edge = this.state.graph.edges.find(item => item.id === edgeUid);
                var id = edge.id;
                FilterGraphService.deleteConnection(id);

                console.debug("Deleted edge", edge);
              } else {
                console.log("could not delete edge")
                // Remove edge from callback data
                var index = data.edges.indexOf(edgeUid);
                if (index > -1) {
                  data.edges.splice(index, 1);
                }
              }
            });
            callback(data);
          },
          editEdge: false,
        },
        nodes: {
          borderWidth: 4,
          size: 64,
          color: {
            border: '#222222',
            background: '#666666'
          },
          font: { color: '#eeeeee' }
        },
        edges: {
          color: 'lightgray'
        },
        groups: {
          ok: {
            color: {
              border: '#222222',
              background: '#666666'
            },
            mass: 10
          }, error: {
            color: {
              border: '#ee0000',
              background: '#666666'
            },
            mass: 10
          },
          in: {
            //physics: false
            mass: 1
          },
          out: {
            //physics: false
            mass: 1
          }
        }
      }
    };

  }

  async componentDidMount() {
    await this.resetNetwork();
    window.addEventListener("resize", this.updateDimensions);
    await this.updateDimensions();
    await this.createFromBackend();
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateDimensions);
  }

  async componentWillReceiveProps(nextProps) {
    if(nextProps.slot != this.state.slot) {
      console.log("new props", nextProps)
      await FilterGraphService.configureSlot(nextProps.slot)
      this.setState(state => {
        return {
          slot: nextProps.slot
        }
      })
      this.createFromBackend()
    }
  }


  addStateNodesAndEdges(nodes, edges) {
    this.setState(state => {
      return {
        graph: {
          nodes: [...state.graph.nodes, ...nodes],
          edges: [...state.graph.edges, ...edges]
        }
      }
    })
  }

  async resetNetwork() {
    this.setState(state => {
      return {
        graph: {
          nodes: [],
          edges: [],
        }
      }
    })
  }

  async createFromBackend() {
    
    await this.resetNetwork();
    const nodeCreate = await this.createNodesFromBackend();
    const edgeCreate = await this.createEdgesFromBackend();
    return Promise.all([nodeCreate, edgeCreate]).then(result => {
      console.log(result)
      var nodes = [];
      var edges = [];
      var {allNodes, allEdges} = result[0];
      var additionalEdges = result[1];
      nodes = nodes.concat(allNodes);
      edges = edges.concat(allEdges);
      edges = edges.concat(additionalEdges);
      this.addStateNodesAndEdges(nodes, edges);
      this.state.network.fit();
    })
  }

  async createNodesFromBackend() {
    return FilterGraphService.getAllNodes()
      .then(values => {
        // gather all nodes to add
        var allNodes = [];
        var allEdges = [];
        values.forEach(element => {
          var {nodes, edges} = this.createVisNodesAndEdges(element);
          allNodes = allNodes.concat(nodes);
          allEdges = allEdges.concat(edges);
        })
        
        return {allNodes, allEdges};
      })
  }

  async createEdgesFromBackend() {
    return FilterGraphService.getAllConnections()
      .then(values => {
        var allEdges = [];
        values.forEach(element => {
          var edge = this.createVisConnection(element);
          allEdges.push(edge);
      })
      return allEdges;
    })
  }

  conUid(inout, index, uid) {
    return inout + '_' + index + '_' + uid;
  }

  createVisNode(json) {
    var visNode = {};
    this.updateVisNode(visNode, json);
    return visNode;
  }

  createVisNodesAndEdges(json) {
    var allNodes = [];
    var allEdges = [];
    var visNode = this.createVisNode(json);
    allNodes.push(visNode);
    var {nodes, edges} = this.createInputOutputNodesAndEdges(json, visNode);
    allNodes = allNodes.concat(nodes);
    allEdges = allEdges.concat(edges);
    return {nodes: allNodes, edges: allEdges}
  }

  createInputOutputNodesAndEdges(json, visNode) {
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
        outNode.nodeType = 'channel';
        outNode.nodeUid = visNode.id;
        outNode.nodeChannel = i;
        nodes.push(outNode);
        edges.push({ id: outNode.id, from: visNode.id, to: outNode.id });
    }
    for (var i = 0; i < numInputChannels; i++) {
      var uid = this.conUid('in', i, visNode.id);
        var inNode = {};
        inNode.group = 'in';
        inNode.id = uid;
        inNode.label = `${i}`;
        inNode.shape = 'circle';
        inNode.nodeType = 'channel';
        inNode.nodeUid = visNode.id;
        inNode.nodeChannel = i;
        nodes.push(inNode);
        edges.push({ id: inNode.id, from: inNode.id, to: visNode.id });
    }
    return {nodes, edges};
  }

  updateVisNode(visNode, json) {
    console.debug('Update Vis Node:', json["py/state"]);
    var uid = json["py/state"]["uid"];
    var name = json["py/state"]["effect"]["py/object"];
    visNode.id = uid;
    visNode.label = name;
    visNode.shape = 'circularImage';
    visNode.group = 'ok';
    visNode.nodeType = 'node';
    var icon = icons[name];
    visNode.image = icon ? icon : '';
    
  }

  createVisConnection(con) {
    var edge = {};
    this.updateVisConnection(edge, con);
    return edge;
  }

  updateVisConnection(edge, json) {
    console.debug('Update Vis Connection:', json["py/state"]);
    var state = json["py/state"];
    edge.id = state["uid"];
    //edge.from = state["from_node_uid"];
    edge.from = this.conUid('out', state['from_node_channel'], state['from_node_uid'])
    edge.from_channel = state["from_node_channel"];
    //edge.to = state["to_node_uid"];
    edge.to = this.conUid('in', state['to_node_channel'], state['to_node_uid'])
    edge.to_channel = state["to_node_channel"];
    edge.arrows = 'to'
  }


  addGraphNode() {
    this.setState(state => {
      return {
        editNodePopup: {
          isShown: true,
          mode: "add",
        }
      }
    })
  }

  editNode(uid) {
    var node = this.state.graph.nodes.find(node => node.id === uid);
    if (node == null) {
      console.error("Cannot find node " + node);
      return
    }
    if (node.nodeType != 'node') {
      return
    }
    this.setState(state => {
      return {
        editNodePopup: {
          isShown: true,
          mode: "edit",
          nodeUid: uid
        }
      }
    })
  }

  saveNodeCallback = async (selectedEffect, option) => {
    console.log(option);
    // Save node in backend
    await FilterGraphService.addNode(selectedEffect, option)
      .then(node => {
        console.debug('Create node successful:', JSON.stringify(node));
        //updateVisNode(data, node);
        var {nodes, edges} = this.createVisNodesAndEdges(node);
        this.addStateNodesAndEdges(nodes, edges);
      })
      .catch(error => {
        console.error('Error on creating node:', error);
        this.showError("Error on creating node. See console for details");
      })
      .finally(() => {
        this.clearNodePopUp();
      });
  }

  clearNodePopUp = () => {
    this.setState(state => {
      return {
        editNodePopup: {
          isShown: false
        }
      }
    })
  }

  showError(message) {
    var error = document.getElementById('alert');
    var errorInfo = document.getElementById('alert-info');
    error.style.display = 'inherit';
    errorInfo.innerHTML = "<strong>Danger!</strong> " + message;
  }

  hideError() {
    var error = document.getElementById('alert');
    error.style.display = 'none';
  }

  handleSaveConfig = async (event) => {
    await ConfigurationService.saveConfig();
  }

  handleLoadConfig = async (event) => {
    await ConfigurationService.loadConfig(event).finally(() => this.createFromBackend());
  }

  handleNodeEditCancel = (event) => {
    this.clearNodePopUp();
  }

  updateDimensions = (event) => {
    
    let content = document.getElementById('vis-content');
    let visDiv = content.getElementsByTagName('div')[0]
    visDiv.style.position = "absolute";
    visDiv.style.height = (content.clientHeight) + "px";
    visDiv.style.width = (content.clientWidth) + "px";

    if(this.state.network) {
      this.state.network.redraw();
    }
  }

  render() {
    const graph = this.state.graph;
    const options = this.state.options;
    const events = this.state.events;
    const style = this.state.style;
    return (
      <div id="vis-container">
        <div id="vis-other">
          <Button variant="contained" onClick={this.handleSaveConfig}>
            <SaveIcon />
            Download Config
          </Button>
          <input type="file" id="file-input" onChange={this.handleLoadConfig} style={{ display: 'none' }} />
          <label htmlFor="file-input">
            <Button variant="contained" component="span">
              <CloudUploadIcon />
              Upload Config
          </Button>
          </label>
        </div>
        <Measure onResize={() => this.updateDimensions()}>
          {({ measureRef }) => (
          <div id="vis-content" ref={measureRef}>
            <Graph graph={graph} options={options} events={events} style={style} getNetwork={network => this.setState({ network })} />
          </div>
          )}
        </Measure>
        <Modal open={this.state.editNodePopup.isShown} onClose={this.clearNodePopUp}>
          <NodePopup mode={this.state.editNodePopup.mode} nodeUid={this.state.editNodePopup.nodeUid} onCancel={this.clearNodePopUp} onSave={this.saveNodeCallback} />
        </Modal>
      </div>
    );
  }
}

VisGraph.propTypes = {
  classes: PropTypes.object.isRequired,
  slot: PropTypes.number.isRequired
};

VisGraph.defaultProps = {
  slot: 0
};

export default VisGraph;