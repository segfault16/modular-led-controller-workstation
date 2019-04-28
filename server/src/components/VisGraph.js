import React from "react";
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import "@babel/polyfill";
import Button from '@material-ui/core/Button';
import CloudUploadIcon from '@material-ui/icons/CloudUpload';
import SaveIcon from '@material-ui/icons/Save';
import CreateIcon from '@material-ui/icons/Create';
import AddIcon from '@material-ui/icons/Add';
import ClearIcon from '@material-ui/icons/Clear';
import InfoIcon from '@material-ui/icons/Info';
import CloseIcon from '@material-ui/icons/Close';
import ToggleButtonGroup from '@material-ui/lab/ToggleButtonGroup';
import ToggleButton from '@material-ui/lab/ToggleButton';
import Modal from '@material-ui/core/Modal';
import Grid from '@material-ui/core/Grid';
import Typography from '@material-ui/core/Typography';
import Paper from '@material-ui/core/Paper';
import Tooltip from '@material-ui/core/Tooltip'
import { withSnackbar } from 'notistack';
import IconButton from '@material-ui/core/IconButton';

import Graph from "react-graph-vis";
import 'vis/dist/vis-network.min.css';

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

import FilterGraphConfigurationService from "../services/FilterGraphConfigurationService";
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

const styles = theme => ({
  toggleContainer: {
    height: 56,
    padding: `${theme.spacing.unit}px ${theme.spacing.unit * 2}px`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    // margin: `${theme.spacing.unit}px 0`,
    // background: theme.palette.background.default,
  },
  helptext: {
    ...theme.mixins.gutters(),
    paddingTop: theme.spacing.unit,
    paddingBottom: theme.spacing.unit,
  },
});

const MODE_SELECT = 'select';
const MODE_CREATE = 'create';
const MODE_DELETE = 'delete';

var is_dragging = false;

class VisGraph extends React.Component {

  constructor(props) {
    super(props);
    //this.slot = props.slot
    this.state = {
      mode: MODE_SELECT,
      helptext: "",
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
      errorMessage: {
        isShown: true
      },
      events: {
        select: ({ nodes, edges }) => {
          if (this.state.mode === MODE_SELECT || this.state.mode === MODE_CREATE) {
            this.clearNodePopUp()
            if (nodes.length == 1) {
              this.editNode(nodes[0])
            }
          } else if (this.state.mode === MODE_DELETE) {
            if (nodes.length == 1) {
              this.confirmDeleteNode({ nodes: nodes, edges: edges }, data => {
                this.setState(oldState => {
                  return {
                    graph: {
                      nodes: oldState.graph.nodes.filter((el) => !data.nodes.includes(el.id)),
                      edges: oldState.graph.edges.filter((el) => !data.edges.includes(el.id))
                    }
                  }
                })
              })
            } else if (edges.length > 0) {
              this.deleteEdge({ nodes: nodes, edges: edges }, data => {
                this.setState(oldState => {
                  return {
                    graph: {
                      nodes: oldState.graph.nodes.filter((el) => !data.nodes.includes(el.id)),
                      edges: oldState.graph.edges.filter((el) => !data.edges.includes(el.id))
                    }
                  }
                })
              })
            }
          }
        },
        click: ({ nodes, edges }) => {
          if (this.state.mode === MODE_CREATE) {
            if (nodes.length == 0) {
              this.addGraphNode();
            }
          }
        },
        release: () => {
        },
        doubleClick: ({ pointer: { canvas } }) => {
          this.addGraphNode();
        },
        hoverNode: ({node}) => {
          this.updateHelpText(this.state.mode, node, null);
        },
        blurNode: ({node}) => {
          this.updateHelpText(this.state.mode, null, null);
        },
        hoverEdge: ({edge}) => {
          this.updateHelpText(this.state.mode, null, edge);
        },
        blurEdge: ({edge}) => {
          this.updateHelpText(this.state.mode, null, null);
        },
        dragStart: () => {
          is_dragging = true
        },
        dragEnd: () => {
          is_dragging = false
        },
        afterDrawing: () => {
          if(this.state.network.manipulation.temporaryIds.nodes.length == 0) {
            // Hack for no DragEnd event fired when adding edges
            is_dragging = false
          }
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
          hover: true,
          hoverConnectedEdges: false,
          selectedConnectedEdges: false
        },
        manipulation: {
          enabled: false,
          addNode: (data, callback) => {
            this.addGraphNode();
          },
          addEdge: (data, callback) => {
            console.log("add edge")
            if (data.from == data.to) {
              callback(null);
              return;
            }
            var fromNode = this.state.graph.nodes.find(item => item.id === data.from);
            var toNode = this.state.graph.nodes.find(item => item.id === data.to);
            if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in') {
              console.log("could add edge")
              FilterGraphService.addConnection(this.state.slot, fromNode.nodeUid, fromNode.nodeChannel, toNode.nodeUid, toNode.nodeChannel, data, callback).then(connection => {
                this.updateVisConnection(data, connection)
                this.addStateNodesAndEdges([],[data])
                // manual drag end
                is_dragging = false
                this.updateHelpText(null, null)
              }).catch(err => {
                console.error(err)
                this.props.enqueueSnackbar("Error creating connection", { variant: 'error' })
              });
            } else {
              console.log("could not add edge")
            }
            return;
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
    this.intervalID = setInterval(
      () => this.fetchErrors(),
      2000
    );
    await this.createFromBackend();
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateDimensions);
    clearInterval(this.intervalID);
  }

  async componentWillReceiveProps(nextProps) {
    if (nextProps.slot != this.state.slot) {
      console.log("new props", nextProps)
      this.state.slot = nextProps.slot
      this.setState(state => {
        return {
          slot: nextProps.slot
        }
      })
      this.createFromBackend()
    }
  }

  componentDidUpdate() {
    this.ensureMode(this.state.mode)
  }

  updateHelpText = (mode, nodeUid, edgeUid) => {
    if(is_dragging || this.state.network.manipulation.temporaryIds.nodes.length > 0) {
      // Fix for add connection issue in Safari -> don't update state while dragging
      return
    }
    var hoverNode = false
    var hoverEdge = false
    var node = null 
    var edge = null
    if(nodeUid != null) {
      node = this.state.graph.nodes.find(item => item.id === nodeUid);
      hoverNode = true
    }
    if(edgeUid != null) {
      edge = this.state.graph.edges.find(item => item.id === edgeUid);
      hoverEdge = true
    }
    if(mode == MODE_SELECT) {
      if(hoverNode) {
        if(node != null && node.nodeType == "node") {
          this.setState({helptext: "Click to edit node"})
        } else {
          this.setState({helptext: ""})
        }
      } else if(hoverEdge) {
        this.setState({helptext: ""})
      } else {
        this.setState({helptext: "Click and drag to pan"})
      }
    } else if(mode == MODE_CREATE) {
      if(hoverNode) {
        if(node != null && node.group == "out") {
          this.setState({helptext: "Click and drag to input node to add connection"})
        } else if(node != null && node.nodeType == "node") {
          this.setState({helptext: "Click to edit node"})
        } else {
          this.setState({helptext: ""})
        }
      } else if(hoverEdge) {
        this.setState({helptext: ""})
      } else {
        this.setState({helptext: "Click to add node"})
      }
    } else if(mode == MODE_DELETE) {
      if(hoverNode) {
        if(node != null && node.nodeType == "node") {
          this.setState({helptext: "Click to delete node"})
        } else {
          this.setState({helptext: ""})
        }
      } else if(hoverEdge) {
        if(edge != null && edge.group === "connection")
        this.setState({helptext: "Click to delete connection"})
      } else {
        this.setState({helptext: ""})
      }
    }
    
  }

  confirmDeleteNode = (data, callback) => {
    window.confirm("Are you sure you want to delete the node?") &&
          this.deleteNode(data, callback)
  }

  deleteNode = (data, callback) => {
    data.nodes.forEach(id => {
      var node = this.state.graph.nodes.find(node => node.id == id)
      if (node == null) {
        console.error("Cannot find node " + id)
      }
      if (node.nodeType == 'node') {
        // update callback data to include all input and output nodes for this node
        var inputOutputNodes = this.state.graph.nodes.filter(item => item.nodeType == 'channel' && item.nodeUid == id);
        data.nodes = data.nodes.concat(inputOutputNodes.map(x => x.id));
        FilterGraphService.deleteNode(this.state.slot, id).finally(() => {
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
    if (callback != null) {
      callback(data);
    }
  }

  deleteEdge = (data, callback) => {
    data.edges.forEach(edgeUid => {
      var edge = this.state.graph.edges.find(item => item.id === edgeUid);
      var fromNode = this.state.graph.nodes.find(item => item.id === edge.from);
      var toNode = this.state.graph.nodes.find(item => item.id === edge.to);
      if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in') {
        var edge = this.state.graph.edges.find(item => item.id === edgeUid);
        var id = edge.id;
        FilterGraphService.deleteConnection(this.state.slot, id);

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
    if (callback != null) {
      callback(data);
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

    const nodeCreate = await this.createNodesFromBackend();
    const edgeCreate = await this.createEdgesFromBackend();
    return this.resetNetwork().then(Promise.all([nodeCreate, edgeCreate]).then(result => {
      console.log(result)
      var nodes = [];
      var edges = [];
      var { allNodes, allEdges } = result[0];
      var additionalEdges = result[1];
      nodes = nodes.concat(allNodes);
      edges = edges.concat(allEdges);
      edges = edges.concat(additionalEdges);
      this.addStateNodesAndEdges(nodes, edges);
      this.state.network.fit();
    }))
  }

  async createNodesFromBackend() {
    return FilterGraphService.getAllNodes(this.state.slot)
      .then(values => {
        // gather all nodes to add
        var allNodes = [];
        var allEdges = [];
        values.forEach(element => {
          var { nodes, edges } = this.createVisNodesAndEdges(element);
          allNodes = allNodes.concat(nodes);
          allEdges = allEdges.concat(edges);
        })

        return { allNodes, allEdges };
      })
  }

  async createEdgesFromBackend() {
    return FilterGraphService.getAllConnections(this.state.slot)
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
    var { nodes, edges } = this.createInputOutputNodesAndEdges(json, visNode);
    allNodes = allNodes.concat(nodes);
    allEdges = allEdges.concat(edges);
    return { nodes: allNodes, edges: allEdges }
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
    return { nodes, edges };
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
    edge.group = "connection"
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
    await FilterGraphService.addNode(this.state.slot, selectedEffect, option)
      .then(node => {
        console.debug('Create node successful:', JSON.stringify(node));
        //updateVisNode(data, node);
        var { nodes, edges } = this.createVisNodesAndEdges(node);
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
    await FilterGraphConfigurationService.saveConfig(this.state.slot);
  }

  handleLoadConfig = async (event) => {
    console.log("load", event)
    await FilterGraphConfigurationService.loadConfig(this.state.slot, event).finally(() => this.createFromBackend());
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

    if (this.state.network) {
      this.state.network.redraw();
    }
  }

  ensureMode = (mode) => {
    if (mode === MODE_SELECT) {
      this.state.network.disableEditMode()
    }
    if (mode === MODE_CREATE) {
      this.state.network.addEdgeMode()
    }
  }

  handleModeChange = (event, mode) => {
    console.log("mode change", mode)
    if(mode != null) {
      this.setState({ mode });
      this.updateHelpText(mode, null, null);
    } else {
      // No new mode given, event is onChange of fileInput
      this.handleLoadConfig(event)
    }
  };

  fetchErrors = async() => fetch('./errors').then(response => response.json()).then(json => {
    // Reset error on nodes
    var changed = false;
    var nodes = [];
    this.state.graph.nodes.map( node => {
      var newNode = Object.assign({}, node);
      if(newNode.group == 'error') {
        newNode.group = 'ok';
        changed = true;
      }
      nodes.push(newNode);
    })
    for (var key in json) {
      // check if the property/key is defined in the object itself, not in parent
      if (json.hasOwnProperty(key)) {
        var node = nodes.find(node => node.id === key);
        if (node != null) {
          node.group = 'error';
          changed = true
        }
        this.props.enqueueSnackbar(json[key], { variant: 'error' })
      }
    }
    if(changed) {  
    this.setState(oldState => {
      return {
        graph: {
          nodes: nodes,
          edges: oldState.graph.edges,
        },
      }
    })
  }
    
  }); 

  render() {
    const { classes, theme } = this.props;
    const graph = this.state.graph;
    const options = this.state.options;
    const events = this.state.events;
    const style = this.state.style;
    return (
      <div id="vis-container">
        <div id="vis-other">
          <div className={classes.toggleContainer}>
            <Grid container spacing={16} justify="flex-end" direction="row">
              <Grid item xs={12} sm={12}>
                <ToggleButtonGroup value={this.state.mode} exclusive onChange={this.handleModeChange}>
                  <ToggleButton value={MODE_SELECT}>
                    <Tooltip title="Select mode">
                    <InfoIcon />
                    </Tooltip>
                  </ToggleButton>
                  
                  
                  <ToggleButton value={MODE_CREATE}>
                  <Tooltip title="Create mode">
                    <CreateIcon />
                    </Tooltip>
                  </ToggleButton>
                  
                  
                  <ToggleButton value={MODE_DELETE}>
                  <Tooltip title="Delete mode">
                    <ClearIcon />
                    </Tooltip>
                  </ToggleButton>
                  
                  
                  <Button onClick={this.handleSaveConfig} size="small">
                  <Tooltip title="Download configuration">
                    <SaveIcon />
                    </Tooltip>
                  </Button>
                  
                  
                  <input type="file" id="file-input" onChange={this.handleLoadConfig} style={{ display: 'none' }} />
                  <label htmlFor="file-input">
                  
                  <Button component="span" size="small">
                  <Tooltip title="Upload configuration">
                      <CloudUploadIcon />
                      </Tooltip>
                    </Button>                    
                  </label>
                  
                </ToggleButtonGroup>
              </Grid>
            </Grid>
          </div>

        </div>
        <Measure onResize={() => this.updateDimensions()}>
          {({ measureRef }) => (
            <div id="vis-content" ref={measureRef}>
              <Graph graph={graph} options={options} events={events} style={style} getNetwork={network => this.setState({ network })} />
            </div>
          )}
        </Measure>
        <div className={classes.toggleContainer}>
            {this.state.helptext ? 
          <Paper className={classes.helptext} >
              <Typography>
                Usage: {this.state.helptext}
              </Typography>
              </Paper>
              : null}
          </div>
        <Modal open={this.state.editNodePopup.isShown} onClose={this.clearNodePopUp}>
          <NodePopup mode={this.state.editNodePopup.mode} slot={this.state.slot} nodeUid={this.state.editNodePopup.nodeUid} onCancel={this.clearNodePopUp} onSave={this.saveNodeCallback} />
        </Modal>
      </div>
    );
  }
}

VisGraph.propTypes = {
  classes: PropTypes.object.isRequired,
  slot: PropTypes.number
};

VisGraph.defaultProps = {
  slot: 0
};

export default withSnackbar(withStyles(styles)(VisGraph));