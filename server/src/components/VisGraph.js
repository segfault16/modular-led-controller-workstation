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

import FilterGraphConfigurationService from "../services/FilterGraphConfigurationService";
import FilterGraphService from "../services/FilterGraphService";

import AddNodePopup from './AddNodePopup';
import EditNodePopup from './EditNodePopup';
import EditModulationPopup from './EditModulationPopup';
import EditModulationSourcePopup from './EditModulationSourcePopup';

import './VisGraph.css';
import Measure from 'react-measure'

import {VisGraphLayout, NODETYPE_EFFECT_NODE, NODETYPE_EFFECT_INOUT, NODETYPE_MODULATOR, EDGETYPE_EFFECT_CONNECTION, EDGETYPE_MODULATION, EDGETYPE_EFFECT_INOUT} from "./VisGraphLayout";

const styles = theme => ({
  toggleContainer: {
    height: 56,
    padding: `${theme.spacing(1)}px ${theme.spacing(2)}px`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    position: 'absolute',
    // margin: `${theme.spacing.unit}px 0`,
    // background: theme.palette.background.default,
  },
  helptext: {
    ...theme.mixins.gutters(),
    paddingTop: theme.spacing(1),
    paddingBottom: theme.spacing(1),
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
      editNodePopup: {
        isShown: false,
        mode: "add", // add or edit
        nodeUid: 0,
      },
      editModulationPopup: {
        isShown: false,
      },
      editModulationSourcePopup: {
        isShown: false,
      },
      errorMessage: {
        isShown: true
      },
      events: {
        select: ({ nodes, edges }) => {
          console.debug("selected nodes", nodes)
          console.debug("selected edges:", edges)
          if (this.state.mode === MODE_SELECT || this.state.mode === MODE_CREATE) {
            if (nodes.length == 1) {
              this.editNode(nodes[0])
            } else if (edges.length == 1) {
              this.editModulation(edges[0])
            }
          } else if (this.state.mode === MODE_DELETE) {
            if (nodes.length == 1) {
              this.confirmDeleteNode({ nodes: nodes, edges: edges }, data => {
                this.removeStateNodesAndEdges(data.nodes, data.edges)
              })
            } else if (edges.length > 0) {
              this.deleteEdge({ nodes: nodes, edges: edges }, data => {
                this.removeStateNodesAndEdges(data.nodes, data.edges)
              })
            }
          }
        },
        click: ({ nodes, edges, event, pointer }) => {
          if (this.state.mode === MODE_CREATE) {
            if (nodes.length == 0 && edges.length == 0) {
              let canvasX = pointer.canvas.x;

              this.addGraphNode(canvasX);
            }
          }
        },
        release: () => {
        },
        doubleClick: ({ pointer: { canvas } }) => {
          this.addGraphNode(canvas.x);
        },
        hoverNode: ({ node }) => {
          this.updateHelpText(this.state.mode, node, null);
        },
        blurNode: ({ node }) => {
          this.updateHelpText(this.state.mode, null, null);
        },
        hoverEdge: ({ edge }) => {
          this.updateHelpText(this.state.mode, null, edge);
        },
        blurEdge: ({ edge }) => {
          this.updateHelpText(this.state.mode, null, null);
        },
        dragStart: () => {
          is_dragging = true
        },
        dragEnd: () => {
          is_dragging = false
        },
        afterDrawing: () => {
          if (this.state.network.manipulation.temporaryIds.nodes.length == 0) {
            // Hack for no DragEnd event fired when adding edges
            is_dragging = false
          }
        }
      },
      options: {
        // autoResize: true,
        layout: {
          hierarchical: {
            enabled: true,
            levelSeparation: 100,
            direction: "LR",
            nodeSpacing: 180,
            sortMethod: 'directed',
            shakeTowards: 'leaves',
            blockShifting: true,
            edgeMinimization: true

          },
        },
        physics: {
          enabled: true,
          hierarchicalRepulsion: {
            centralGravity: .5,
            nodeDistance: 100,
            springLength: 10,
            springConstant: 0.5,
            damping: 0.999,
            avoidOverlap: 1,
          },
          maxVelocity: 146,
          timestep: 0.35,
          solver: 'hierarchicalRepulsion',
          stabilization: {
            enabled: true,
            onlyDynamicEdges: true
          },
        },
        interaction: {
          navigationButtons: false,
          hover: true,
          hoverConnectedEdges: false,
          selectConnectedEdges: false
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
            var fromId = data.from
            var toId = data.to
            var fromNode = this.state.graph.nodes.find(item => item.id === fromId);
            var toNode = this.state.graph.nodes.find(item => item.id === toId);
            // Revert fromNode and toNode if the connection was made from input to output
            if (fromNode.nodeType == NODETYPE_EFFECT_INOUT && fromNode.group == 'in' && toNode.nodeType == NODETYPE_EFFECT_INOUT && toNode.group == 'out') {
              var temp = fromNode
              fromNode = toNode
              toNode = temp
              var tempId = fromId
              fromId = toId
              toId = tempId
            }
            if (fromNode.nodeType == NODETYPE_EFFECT_INOUT && fromNode.group == 'out' && toNode.nodeType == NODETYPE_EFFECT_INOUT && toNode.group == 'in') {
              console.log("could add edge")
              // See if we have already a connection to this node. This connection has to be removed
              var foundConnection = this.state.graph.edges.find(item => item.to === toId)
              if (foundConnection) {
                console.log("found connections: ", foundConnection)
                this.deleteEdge({ nodes: [], edges: [foundConnection.id] }, data => {
                  this.removeStateNodesAndEdges(data.nodes, data.edges)
                })
              }
              this.props.enqueueSnackbar("Connection replaced", { variant: 'info' })
              FilterGraphService.addConnection(this.state.slot, fromNode.nodeUid, fromNode.nodeChannel, toNode.nodeUid, toNode.nodeChannel, data).then(connection => {
                VisGraphLayout.updateEffectConnection(data, connection)
                this.addStateNodesAndEdges([], [data])
                // manual drag end
                is_dragging = false
                this.updateHelpText(null, null)
                this.state.network.body.emitter.emit('_dataChanged')
                this.state.network.redraw()
              }).catch(err => {
                console.error(err)
                this.props.enqueueSnackbar("Error creating connection", { variant: 'error' })
              });
            } else if (fromNode.nodeType == NODETYPE_MODULATOR && toNode.nodeType == NODETYPE_EFFECT_NODE) {
              console.log("could add edge")
              FilterGraphService.addModulation(this.state.slot, fromNode.id, toNode.id).then(connection => {
                VisGraphLayout.updateModulationConnection(data, connection)
                this.addStateNodesAndEdges([], [data])
                this.editModulation(connection['py/state']['uid']);
              })
              
            } else {
              console.log("could not add edge")
              this.props.enqueueSnackbar("Connections can only be added from output to input", { variant: 'error' })
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
            physics: false,
            mass: 10
          }, error: {
            color: {
              border: '#ee0000',
              background: '#666666'
            },
            physics: false,
            mass: 10
          },
          in: {
            physics: true,
            mass: 1
          },
          out: {
            physics: true,
            mass: 1
          },
          modulation: {
            color: {
              border: '#222222',
              background: '#666666'
            },
            physics: false,
            mass: 100
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
    if (is_dragging || this.state.network.manipulation.temporaryIds.nodes.length > 0) {
      // Fix for add connection issue in Safari -> don't update state while dragging
      return
    }
    var hoverNode = false
    var hoverEdge = false
    var node = null
    var edge = null
    if (nodeUid != null) {
      node = this.state.graph.nodes.find(item => item.id === nodeUid);
      hoverNode = true
    }
    if (edgeUid != null) {
      edge = this.state.graph.edges.find(item => item.id === edgeUid);
      hoverEdge = true
    }
    if (mode == MODE_SELECT) {
      if (hoverNode) {
        if (node != null && node.nodeType == NODETYPE_EFFECT_NODE) {
          this.setState({ helptext: "Click to edit node" })
        } else if (node.nodeType == NODETYPE_MODULATOR) {
          this.setState({ helptext: "Click to edit modulation source" })
        } else {
          this.setState({ helptext: "" })
        }
      } else if (hoverEdge) {
        if (edge.edgeType === EDGETYPE_MODULATION) {
          this.setState({helptext: "Click to edit modulation"})
        } else {
          this.setState({ helptext: "" })
        }
      } else {
        this.setState({ helptext: "Click and drag to pan" })
      }
    } else if (mode == MODE_CREATE) {
      if (hoverNode) {
        if (node != null && node.group == "out") {
          this.setState({ helptext: "Click and drag to input node to add connection" })
        } else if (node != null && node.nodeType == NODETYPE_EFFECT_NODE) {
          this.setState({ helptext: "Click to edit node" })
        } else if (node.nodeType === NODETYPE_MODULATOR) {
          this.setState({ helptext: "Click and drag to effect to create modulation"})
        } else {
          this.setState({ helptext: "" })
        }
      } else if (hoverEdge) {
        if (edge.edgeType === EDGETYPE_MODULATION) {
          this.setState({helptext: "Click to edit modulation"})
        } else {
          this.setState({ helptext: "" })
        }
      } else {
        this.setState({ helptext: "Click to add node" })
      }
    } else if (mode == MODE_DELETE) {
      if (hoverNode) {
        if (node != null && node.nodeType == NODETYPE_EFFECT_NODE) {
          this.setState({ helptext: "Click to delete node" })
        } else {
          this.setState({ helptext: "" })
        }
      } else if (hoverEdge) {
        if (edge != null && edge.group === "connection")
          this.setState({ helptext: "Click to delete connection" })
      } else {
        this.setState({ helptext: "" })
      }
    }

  }

  confirmDeleteNode = (data, callback) => {
    window.confirm("Are you sure you want to delete the node?") &&
      this.deleteNode(data, callback)
  }

  deleteNode = (data, callback) => {
    console.log("delete nodes", data)
    data.nodes.forEach(id => {
      // find node
      var node = this.state.graph.nodes.find(node => node.id == id)
      if (node == null) {
        console.error("Cannot find node " + id)
      }
      // node is effect
      if (node.nodeType == NODETYPE_EFFECT_NODE) {
        // update callback data to include all input and output nodes for this node
        var inputOutputNodes = this.state.graph.nodes.filter(item => item.nodeType == NODETYPE_EFFECT_INOUT && item.nodeUid == id);
        data.nodes = data.nodes.concat(inputOutputNodes.map(x => x.id));
        // update callback data to include connections from the deleted nodes
        var connectionsFromInputOutputNodes = this.state.graph.edges.filter(item => data.nodes.includes(item.from) || data.nodes.includes(item.to))
        data.edges = data.edges.concat(connectionsFromInputOutputNodes.map(x => x.id))
        // delete node via filtergraphservice
        FilterGraphService.deleteNode(this.state.slot, id).finally(() => {
          this.clearNodePopUp();
        })
      } else if (node.nodeType == NODETYPE_MODULATOR) {
        FilterGraphService.deleteModulationSource(this.state.slot, id).finally(() => {
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
      if (fromNode.nodeType == NODETYPE_EFFECT_INOUT && fromNode.group == 'out' && toNode.nodeType == NODETYPE_EFFECT_INOUT && toNode.group == 'in') {
        var edge = this.state.graph.edges.find(item => item.id === edgeUid);
        var id = edge.id;
        FilterGraphService.deleteConnection(this.state.slot, id);

        console.debug("Deleted edge", edge);
      } else if (fromNode.nodeType == NODETYPE_MODULATOR && toNode.nodeType == NODETYPE_EFFECT_NODE) {
        var edge = this.state.graph.edges.find(item => item.id === edgeUid);
        var id = edge.id;
        FilterGraphService.deleteModulation(this.state.slot,id);
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

  // recalculate levels and add nodes, use this instead of this.setState(...)
  addStateNodesAndEdges(nodes, edges, fixedLevels = {}, reservedLevel = null) {
    console.debug("Adding nodes", nodes);
    console.debug("Fixed levels:", fixedLevels)
    this.setState(state => {
      // Create copy of current nodes and edges
      var newNodes = [];
      state.graph.nodes.map(node => {
        var newNode = Object.assign({}, node);
        newNodes.push(newNode);
      })
      var newEdges = [];
      state.graph.edges.map(edge => {
        var newEdge = Object.assign({}, edge);
        newEdges.push(newEdge);
      })
      // add nodes from arguments
      if(nodes != null) {
        newNodes = [...newNodes, ...nodes]
      }
      if(edges != null) {
        newEdges = [...newEdges, ...edges]
      }
      // calculate node levels
      VisGraphLayout.updateNodeLevels(newNodes, newEdges, reservedLevel)
      Object.keys(fixedLevels).map((key, id) => {
        var node = newNodes.find(n => n.id === key)
        if(node != null) {
          node.level = fixedLevels[key]
        }
      })
      return {
        graph: {
          nodes: newNodes,
          edges: newEdges
        }
      }
    })
  }

  // recalculate levels and add nodes, use this instead of this.setState(...)
  removeStateNodesAndEdges(nodes, edges) {
    this.setState(state => {
      // Create copy of current nodes and edges
      var newNodes = [];
      state.graph.nodes.map(node => {
        var newNode = Object.assign({}, node);
        newNodes.push(newNode);
      })
      var newEdges = [];
      state.graph.edges.map(edge => {
        var newEdge = Object.assign({}, edge);
        newEdges.push(newEdge);
      })
      if (nodes != null) {
        newNodes = newNodes.filter((el) => !nodes.includes(el.id))
      }
      if (edges != null) {
        newEdges = newEdges.filter((el) => !edges.includes(el.id))
      }
      // calculate node levels
      VisGraphLayout.updateNodeLevels(newNodes, newEdges)
      return {
        graph: {
          nodes: newNodes,
          edges: newEdges
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

    const nodeCreate = await this.createEffectNodesFromBackend();
    const edgeCreate = await this.createEffectEdgesFromBackend();
    const modulatorNodeCreate = await this.createModulatorNodesFromBackend();
    const modulationsCreate = await this.createModulatorEdgesFromBackend();
    return this.resetNetwork().then(Promise.all([nodeCreate, edgeCreate, modulatorNodeCreate, modulationsCreate]).then(result => {
      console.log(result)
      var nodes = [];
      var edges = [];
      var { allNodes, allEdges } = result[0];
      var additionalEdges = result[1];
      var modulatorNodes = result[2];
      var modulationEdges = result[3];
      nodes = nodes.concat(allNodes);
      edges = edges.concat(allEdges);
      edges = edges.concat(additionalEdges);
      nodes = nodes.concat(modulatorNodes);
      edges = edges.concat(modulationEdges);
      this.addStateNodesAndEdges(nodes, edges);
      this.state.network.fit();
    }))
  }

  async createEffectNodesFromBackend() {
    return FilterGraphService.getAllNodes(this.state.slot)
      .then(values => {
        // gather all nodes to add
        var allNodes = [];
        var allEdges = [];
        values.forEach(element => {
          var { nodes, edges } = VisGraphLayout.createEffectNodesAndEdges(element);
          allNodes = allNodes.concat(nodes);
          allEdges = allEdges.concat(edges);
        })

        return { allNodes, allEdges };
      })
  }

  async createEffectEdgesFromBackend() {
    return FilterGraphService.getAllConnections(this.state.slot)
      .then(values => {
        var allEdges = [];
        values.forEach(element => {
          var edge = VisGraphLayout.createVisConnection(element);
          allEdges.push(edge);
        })
        return allEdges;
      })
  }

  async createModulatorNodesFromBackend() {
    return FilterGraphService.getAllModulationSources(this.state.slot)
    .then(values => {
      var allNodes = [];
      values.forEach(element => {
        var node = VisGraphLayout.createModulatorNode(element);
        allNodes.push(node);
      })
      return allNodes;
    })
  }

  async createModulatorEdgesFromBackend() {
    return FilterGraphService.getAllModulations(this.state.slot)
    .then(values => {
      var allEdges = [];
      values.forEach(element => {
        var edge = VisGraphLayout.createModulatorConnection(element);
        allEdges.push(edge);
      })
      return allEdges;
    })
  }


  addGraphNode(canvasX) {
    // Find level nearest to click
    let effectNodeIds = this.state.graph.nodes.filter(n => n.nodeType === NODETYPE_EFFECT_NODE).map(n => n.id);
    let positions = this.state.network.getPositions(effectNodeIds);
    let dists = {}
    Object.keys(positions).forEach((key, idx) => {
      dists[key] = Math.pow(canvasX - positions[key].x, 2)
    })
    var minDist = -1;
    var minKey = null;
    Object.keys(dists).forEach((key, idx) => {
      if (minKey == null) {
        minKey = key;
        minDist = dists[key]
      } else if (dists[key] < minDist) {
        minDist = dists[key]
        minKey = key
      }
    })
    var nearestLevel = null
    var nearestNode = this.state.graph.nodes.find(n => n.id === minKey)
    if (nearestNode != null) {
      nearestLevel = nearestNode.level
      // Make sure we insert between nodes
      if(canvasX < positions[minKey].x) {
        nearestLevel = nearestLevel - 3
      }
    }

    this.setState(state => {
      return {
        editNodePopup: {
          isShown: true,
          mode: "add",
        },
        insertLevel: nearestLevel
        }
    })
  }

  editNode(uid) {
    var node = this.state.graph.nodes.find(node => node.id === uid);
    if (node == null) {
      console.error("Cannot find node " + uid);
      return
    }
    if (node.nodeType == NODETYPE_EFFECT_NODE) {
      console.log("Edit Effect Node")
      this.setState(state => {
        return {
          editNodePopup: {
            isShown: true,
            mode: "edit",
            nodeUid: uid
          }
        }
      })
    } else if (node.nodeType == NODETYPE_MODULATOR) {
      console.log("Edit Modulator Node", uid)
      this.setState(state => {
        return {
          editModulationSourcePopup: {
            isShown: true,
            modulationUid: uid
          }
        }
      })
    }
  }

  editModulation(uid) {
    console.log("Edit modulation", uid)
    var edge = this.state.graph.edges.find(edge => edge.id === uid);
    if(edge == null) {
      console.error("Cannot find edge " + uid);
    }
    if (edge.edgeType != EDGETYPE_MODULATION) {
      return
    }
    this.setState(state => {
      return {
        editModulationPopup: {
          isShown: true,
          modulationUid: uid
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
        if (node["py/object"] === "audioled.filtergraph.Node") {
          // Created node is part of the filtergraph
          //updateVisNode(data, node);
          var { nodes, edges } = VisGraphLayout.createEffectNodesAndEdges(node);
          // set reserved level on new nodes
          var fixedLevels = {}
          nodes.filter(n => n.nodeType === NODETYPE_EFFECT_NODE).forEach(n => fixedLevels[n.id] = this.state.insertLevel)
          nodes.filter(n => n.nodeType === NODETYPE_EFFECT_INOUT && n.group === 'in').forEach(n => fixedLevels[n.id] = this.state.insertLevel - 1)
          nodes.filter(n => n.nodeType === NODETYPE_EFFECT_INOUT && n.group === 'out').forEach(n => fixedLevels[n.id] = this.state.insertLevel + 1)
          this.addStateNodesAndEdges(nodes, edges, fixedLevels, this.state.insertLevel);
          this.setState(state => {
            return {
              insertLevel: null
            }
          })
          

        } else if (node["py/object"] === "audioled.filtergraph.ModulationSourceNode") {
          // Created node is a modulation source
          var nodes = []
          var node = VisGraphLayout.createModulatorNode(node);
          // use level on new node
          nodes.push(node);
          var fixedLevels = {}
          fixedLevels[node.id] = this.state.insertLevel
          this.addStateNodesAndEdges(nodes, [], fixedLevels);
          this.setState(state => {
            return {
              insertLevel: null
            }
          })
        }
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
        },
        insertLevel: null
      }
    })
  }

  clearModulationPopUp = () => {
    this.setState(state => {
      return {
        editModulationPopup: {
          isShown: false
        }
      }
    })
  }

  clearModulationSourcePopUp = () => {
    this.setState(state => {
      return {
        editModulationSourcePopup: {
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
    console.log("update dimensions")
    let content = document.getElementById('vis-container');
    this.setState(state => {
      return {
        options: {
          height: content.clientHeight + "px",
          // height: "100%",
          width: content.clientWidth + "px"
          // width: "100%",
        }
      }
    })
  }

  ensureMode = (mode) => {
    if (mode === MODE_CREATE) {
      this.state.network.addEdgeMode()
    } else {
      this.state.network.disableEditMode()
    }
  }

  handleModeChange = (event, mode) => {
    console.log("mode change", mode)
    if (mode != null) {
      this.setState({ mode });
      this.updateHelpText(mode, null, null);
    } else {
      // No new mode given, event is onChange of fileInput
      this.handleLoadConfig(event)
    }
  };

  fetchErrors = async () => fetch('./errors').then(response => response.json()).then(json => {
    // Reset error on nodes
    var changed = false;
    var nodes = [];
    this.state.graph.nodes.map(node => {
      var newNode = Object.assign({}, node);
      if (newNode.group == 'error') {
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
    if (changed) {
      // TODO: Test
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
      
        
        <Measure onResize={() => this.updateDimensions()}>
          {({ measureRef }) => (
            <div id="vis-container" ref={measureRef}>
              <div id="vis-content" >
                
                <Graph graph={graph} options={options} events={events} style={style} getNetwork={network => this.setState({ network })} />
                <div id="vis-tools">
                  <div className={classes.toggleContainer}>
                    <Grid container spacing={2} justify="flex-end" direction="row">
                      <Grid item xs={12} sm={12}>
                        <ToggleButtonGroup value={this.state.mode} exclusive onChange={this.handleModeChange} size="small">
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

                          <Button component="label">
                            <Tooltip title="Upload configuration">
                              <CloudUploadIcon />
                            </Tooltip>
                            <input type="file" id="file-input" onChange={this.handleLoadConfig} style={{ display: 'none' }} />
                          </Button>

                        </ToggleButtonGroup>
                      </Grid>
                    </Grid>
                  </div>

                </div>
                <div id="vis-help" className={classes.toggleContainer}>
                    {this.state.helptext ?
                      <Paper className={classes.helptext} >
                        <Typography>
                          Usage: {this.state.helptext}
                        </Typography>
                      </Paper>
                      : null}
                  </div>
              </div>
              {this.state.editNodePopup.mode == "edit" && this.state.editNodePopup.isShown ? <EditNodePopup open={this.state.editNodePopup.isShown} onClose={this.clearNodePopUp} slot={this.state.slot} nodeUid={this.state.editNodePopup.nodeUid} onCancel={this.clearNodePopUp} onSave={this.saveNodeCallback} /> : null }
              {this.state.editNodePopup.mode == "add" && this.state.editNodePopup.isShown ? <AddNodePopup open={this.state.editNodePopup.isShown} onClose={this.clearNodePopUp} onCancel={this.clearNodePopUp} onSave={this.saveNodeCallback} /> : null }
              {this.state.editModulationPopup.isShown ? <EditModulationPopup open={this.state.editModulationPopup.isShown} slot={this.state.slot} modulationUid={this.state.editModulationPopup.modulationUid} onCancel={this.clearModulationPopUp}/> : null}
              {this.state.editModulationSourcePopup.isShown ? <EditModulationSourcePopup open={this.state.editModulationSourcePopup.isShown} slot={this.state.slot} modulationUid={this.state.editModulationSourcePopup.modulationUid} onCancel={this.clearModulationSourcePopUp}/> : null}
            </div>
          )}
        </Measure>


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