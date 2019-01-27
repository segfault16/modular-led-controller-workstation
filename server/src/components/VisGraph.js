import Graph from "react-graph-vis";
// import Graph from "../../lib";
import React from "react";
import ReactDOM from "react-dom";
import './VisGraph.css'
import { DataSet, Network } from 'vis/index-network';
import 'vis/dist/vis-network.min.css';
var Configurator = require("vis/lib/shared/Configurator").default;
let util = require('vis/lib/util');
import { saveAs } from 'file-saver';
import "@babel/polyfill";
import Button from '@material-ui/core/Button';
import SaveIcon from '@material-ui/icons/Save';
import CloudUploadIcon from '@material-ui/icons/CloudUpload';
import audioInputIcon from '../../img/audioled.audio.AudioInput.png'
import spectrumIcon from '../../img/audioled.audioreactive.Spectrum.png'
import vuIcon from '../../img/audioled.audioreactive.VUMeterPeak.png'
import movingIcon from '../../img/audioled.audioreactive.MovingLight.png'
import colorWheelIcon from '../../img/audioled.colors.ColorWheel.png'
import colorIcon from '../../img/audioled.colors.Color.png'
import ledIcon from '../../img/audioled.devices.LEDOutput.png'
import combineIcon from '../../img/audioled.effects.Combine.png'
import appendIcon from '../../img/audioled.effects.Append.png'
import glowIcon from '../../img/audioled.effects.AfterGlow.png'
import mirrorIcon from '../../img/audioled.effects.Mirror.png'
import swimmingPoolIcon from '../../img/audioled.generative.SwimmingPool.png'
import shiftIcon from '../../img/audioled.effects.Shift.png'
import defenceIcon from '../../img/audioled.generative.DefenceMode.png'
import interpolateHSV from '../../img/audioled.colors.InterpolateHSV.png'

var icons = {
  'audioled.audio.AudioInput':audioInputIcon,
  'audioled.audioreactive.Spectrum':spectrumIcon,
  'audioled.audioreactive.MovingLight':movingIcon,
  'audioled.audioreactive.VUMeterPeak':vuIcon,
  'audioled.audioreactive.VUMeterRMS':vuIcon,
  'audioled.colors.ColorWheel': colorWheelIcon,
  'audioled.colors.StaticRGBColor': colorIcon,
  'audioled.devices.LEDOutput':ledIcon,
  'audioled.effects.Combine':combineIcon,
  'audioled.effects.Append':appendIcon,
  'audioled.effects.AfterGlow':glowIcon,
  'audioled.effects.Mirror':mirrorIcon,
  'audioled.generative.SwimmingPool':swimmingPoolIcon,
  'audioled.effects.Shift':shiftIcon,
  'audioled.generative.DefenceMode':defenceIcon,
  'audioled.colors.InterpolateHSV':interpolateHSV

}

var configurator = null

class Emitter {
  constructor(emit) {
    this.emit = emit
  }
}

class Body {
  constructor(emit) {
    this.emitter = new Emitter(emit);
  }
}

class ConfigurationWrapper {
  constructor(nodeUid, body, parameters, state, callback) {
    this.nodeUid = nodeUid;
    this.body = new Body(this.emit);
    this.configurator = new Configurator(this, body, parameters);
    this.configurator.setOptions(true);
    this.configurator.setModuleOptions(state);
    this.state = state;
    this.callback = callback;
  }

  async emit(identifier, data) {
    
  }

  clear() {
    util.recursiveDOMDelete(this.configurator.wrapper);
  }

  getState() {
    return this.state;
  }

  // is called by Configurator once values change
  async setOptions(data) {
    util.deepExtend(this.state, data['parameters']);
    this.callback(this.nodeUid, data);
  }

}

class VisGraph extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      counter: 0,
      network: {},
      graph: {
        nodes: [],
        edges: []
      },
      style: { 
        flex: "1",
        display: "block"
       },
      events: {
        select: ({ nodes, edges }) => {
          if(nodes.length == 1) {
            this.editNode(nodes[0], this.clearNodePopUp, this.clearNodePopUp)
          }
          console.log("Selected nodes:");
          console.log(nodes);
          console.log("Selected edges:");
          console.log(edges);
        },
        doubleClick: ({ pointer: { canvas } }) => {
          this.createNode(canvas.x, canvas.y);
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
          hover:true
        },
        manipulation: {
          enabled: true,
          addNode: (data, callback) => {
            // filling in the popup DOM elements
            document.getElementById('node-operation').innerHTML = "Add Node";
            this.addGraphNode(data, this.clearNodePopUp, callback);
          },
          deleteNode: (data, callback) => {
            data.nodes.forEach(id => {
              var node = this.state.graph.nodes.find(node => node.id == id)
              if(node == null) {
                console.error("Cannot find node " + id)
              }
              if(node.nodeType == 'node') {
                // update callback data to include all input and output nodes for this node
                var inputOutputNodes = this.state.graph.nodes.filter( item => item.nodeType == 'channel' && item.nodeUid == id );
                data.nodes = data.nodes.concat(inputOutputNodes.map(x => x.id));
                this.deleteNodeData(id);
              } else {
                console.log("Cannot delete node " + id)
                // Clear callback data
                data.nodes = []
                data.edges = []
                return
              }
              console.debug("Deleted node",id);
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
            if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in' ) {
              console.log("could add edge")
              this.postEdgeData(fromNode.nodeUid, fromNode.nodeChannel, toNode.nodeUid, toNode.nodeChannel, data, callback )
            } else {
              console.log("could not add edge")
            }
            return;
            document.getElementById('edge-operation').innerHTML = "Add Edge";
            this.editEdgeWithoutDrag(data, callback);
          },
          deleteEdge: (data, callback) => {
            data.edges.forEach(edgeUid => {
              var edge = this.state.graph.edges.find(item => item.id === edgeUid);
              var fromNode = this.state.graph.nodes.find(item => item.id === edge.from);
              var toNode = this.state.graph.nodes.find(item => item.id === edge.to);
              if (fromNode.nodeType == 'channel' && fromNode.group == 'out' && toNode.nodeType == 'channel' && toNode.group == 'in' ) {
              
                this.deleteEdgeData(edgeUid);
                
                console.debug("Deleted edge",edge);
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
          borderWidth:4,
          size:64,
          color: {
            border: '#222222',
            background: '#666666'
          },
          font:{color:'#eeeeee'}
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
    await this.createNetwork();
    window.addEventListener("resize", this.updateDimensions);
    await this.updateDimensions()
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateDimensions);
  }

  addStateNode(node) {
    this.setState(state => {
      return {
        graph: {
          nodes: [...state.graph.nodes, node],
          edges: [...state.graph.edges]
        }
      }
    })
  }

  addStateEdge(edge) {
    this.setState(state => {
      return {
        graph: {
          nodes: [...state.graph.nodes],
          edges: [...state.graph.edges, edge]
        }
      }
    })
  }

  createNode(x, y) {
    const color = randomColor();
    this.setState(({ graph: { nodes, edges }, counter }) => {
      const id = counter + 1;
      const from = Math.floor(Math.random() * (counter - 1)) + 1;
      return {
        graph: {
          nodes: [
            ...nodes,
            { id, label: `Node ${id}`, color, x, y }
          ],
          edges: [
            ...edges,
            { from, to: id }
          ]
        },
        counter: id
      }
    });
  }

  async createNetwork() {
    this.setState(state => {
      return {
        graph: {
          nodes: [],
          edges: [],
        }
      }
    })
    await this.createNodesFromBackend();
    await this.createEdgesFromBackend();
  }

  async createNodesFromBackend() {
    const response = await fetch('./nodes');
    const json = response.json();
    json.then(values => values.forEach(element => {
      this.addVisNode(element);
    }));
  }
  
  async createEdgesFromBackend() {
    const response = await fetch('./connections');
    const json = response.json();
    json.then(values => values.forEach(element => {
      this.addVisConnection(element);
    }));
  }
  
  conUid(inout, index, uid) {
    return inout + '_' + index + '_' + uid;
  }
  
  addVisNode(json) {
    var visNode = {};
    this.updateVisNode(visNode, json);
    this.addStateNode(visNode);
    
    
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
    // update input and output nodes
    var numOutputChannels = json['py/state']['numOutputChannels'];
    var numInputChannels = json['py/state']['numInputChannels'];
    for(var i=0; i<numOutputChannels; i++) {
      uid = this.conUid('out', i, visNode.id);
      if(!this.state.graph.nodes.some(el => el.uid === uid)) {
        var outNode = {};
        outNode.group = 'out';
        outNode.id = uid;
        outNode.label = `${i}`;
        outNode.shape = 'circle';
        outNode.nodeType = 'channel';
        outNode.nodeUid = visNode.id;
        outNode.nodeChannel = i;
        this.addStateNode(outNode);
        this.addStateEdge({id: outNode.id, from: visNode.id, to: outNode.id});
      }
    }
    for(var i=0; i < numInputChannels; i++) {
      uid = this.conUid('in', i, visNode.id);
      if(!this.state.graph.nodes.some(el => el.uid === uid)) {
        var inNode = {};
        inNode.group = 'in';
        inNode.id = uid;
        inNode.label = `${i}`;
        inNode.shape = 'circle';
        inNode.nodeType = 'channel';
        inNode.nodeUid = visNode.id;
        inNode.nodeChannel = i;
        this.addStateNode(inNode);
        this.addStateEdge({id: inNode.id, from:inNode.id, to: visNode.id});
      }
    }
  }
  
  addVisConnection(con) {
    var edge = {};
    this.updateVisConnection(edge, con);
    this.addStateEdge(edge)
  }
  
  updateVisConnection(edge, json) {
    console.debug('Update Vis Connection:',json["py/state"]);
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
  
  
  addGraphNode(data, cancelAction, callback) {
    var effectDropdown = document.getElementById('node-effectDropdown');
    effectDropdown.style.display = 'inherit';
    var effectTable = document.getElementById('node-effectTable');
    effectTable.style.display = 'inherit';
    var saveBtn = document.getElementById('node-saveButton');
    saveBtn.style.display='inherit';
    var i;
    for(i = effectDropdown.options.length - 1 ; i >= 0 ; i--)
    {
      effectDropdown.remove(i);
    }
    const fetchEffects = async() => {
      const response = await fetch('./effects');
      const json = response.json();
  
      json.then(values => {
        values.forEach(element => {
          effectDropdown.add(new Option(element["py/type"]))
        });
        sortSelect(effectDropdown);
        effectDropdown.selectedIndex = 0;
        this.updateNodeArgs();
      }).catch( err => {
        this.showError("Error fetching effects. See console for details");
        console.error("Error fetching effects:",err);
      })
    }
    fetchEffects();
  
    document.getElementById('node-saveButton').onclick = this.saveNodeData.bind(this, data, callback);
    document.getElementById('node-cancelButton').onclick = cancelAction.bind(this, callback);
    document.getElementById('node-popUp').style.display = 'block';
    document.getElementById('node-effectDropdown').onchange = this.updateNodeArgs.bind(this);
    this.updateNodeArgs();
  
  }
  
  editNode(uid, cancelAction, callback) {
    var node = this.state.graph.nodes.find( node => node.id === uid);
    if(node == null) {
      console.error("Cannot find node " + node);
      return
    }
    if(node.nodeType != 'node') {
      return
    }
  
    var effectDropdown = document.getElementById('node-effectDropdown');
    effectDropdown.style.display = 'none';
    var effectTable = document.getElementById('node-effectTable');
    effectTable.style.display = 'none';
    var saveBtn = document.getElementById('node-saveButton');
    saveBtn.style.display='none';
    
    const fetchAndShow = async () => {
      const stateResponse = await fetch('/node/'+uid);
      const stateJson = stateResponse.json();
      const response = await fetch('./node/'+uid+'/parameter');
      const json = response.json();
      Promise.all([stateJson, json]).then(result => { 
        var effect = result[0]["py/state"]["effect"]["py/state"];
        var values = result[1];
        configurator = new ConfigurationWrapper(uid, document.getElementById('node-configuration'), values, effect, async (nodeUid, data) => {
          console.log("emitting", data['parameters']);
          await fetch('./node/'+nodeUid, {
            method: 'UPDATE', // or 'PUT'
            body: JSON.stringify(data['parameters']), // data can be `string` or {object}!
            headers:{
              'Content-Type': 'application/json'
            }
          }).then(res => res.json())
          .then(node => {
            console.debug('Update node successful:', JSON.stringify(node));
            // updateVisNode(data, node); // TODO: Needed?
          })
          .catch(error => {
            showError("Error on updating node. See console for details.")
            console.error('Error on updating node:', error);
          })
        });
        
      }) ;
    }
    fetchAndShow();
    document.getElementById('node-cancelButton').onclick = cancelAction.bind(this, callback);
    document.getElementById('node-effectDropdown').onchange = null;
    document.getElementById('node-popUp').style.display = 'block';
  }
  
  sortSelect(selElem) {
    var tmpAry = new Array();
    for (var i=0;i<selElem.options.length;i++) {
        tmpAry[i] = new Array();
        tmpAry[i][0] = selElem.options[i].text;
        tmpAry[i][1] = selElem.options[i].value;
    }
    tmpAry.sort();
    while (selElem.options.length > 0) {
        selElem.options[0] = null;
    }
    for (var i=0;i<tmpAry.length;i++) {
        var op = new Option(tmpAry[i][0], tmpAry[i][1]);
        selElem.options[i] = op;
    }
    return;
  }
  
  async saveNodeData(data, callback) {
    // gather data
    var effectDropdown = document.getElementById('node-effectDropdown')
    var selectedEffect = effectDropdown.options[effectDropdown.selectedIndex].value;
    var options = configurator.getState();
    console.log(options);
    // Save node in backend
    await fetch('./node', {
      method: 'POST', // or 'PUT'
      body: JSON.stringify([selectedEffect, options]), // data can be `string` or {object}!
      headers:{
        'Content-Type': 'application/json'
      }
    }).then(res => res.json())
    .then(node => {
      console.debug('Create node successful:', JSON.stringify(node));
      //updateVisNode(data, node);
      this.addVisNode(node);
      callback(null); // can't use callback since we alter nodes in updateVisNode
    })
    .catch(error => {
      showError("Error on creating node. See console for details");
      console.error('Error on creating node:', error);
    })
    .finally(() => {
      this.clearNodePopUp();
    });
  }
  
  async updateNodeData(data, callback) {
    var options = document.getElementById('node-args').value;
    // Save node in backend
    await fetch('./node/'+data, {
      method: 'UPDATE', // or 'PUT'
      body: JSON.stringify(options), // data can be `string` or {object}!
      headers:{
        'Content-Type': 'application/json'
      }
    }).then(res => res.json())
    .then(node => {
      console.debug('Update node successful:', JSON.stringify(node));
      // updateVisNode(data, node); // TODO: Needed?
      callback(data);
    })
    .catch(error => {
      console.error('Error on updating node:', error);
    })
    .finally(() => {
      clearNodePopUp();
    });
  }
  
  async deleteNodeData(id) {
    await fetch('./node/'+id, {
      method: 'DELETE'
    }).then(res => {
      console.debug('Delete node successful:', id);
    }).catch(error => {
      console.error('Error on deleting node:', error)
    }).finally(() => {
      this.clearNodePopUp();
    })
  }
  
  
  
  clearNodePopUp() {
    if(configurator) {
      configurator.clear();
    }
    document.getElementById('node-saveButton').onclick = null;
    document.getElementById('node-cancelButton').onclick = null;
    document.getElementById('node-popUp').style.display = 'none';
  }
  
  async fetchNode(uid) {
    return fetch('./node/'+uid).then(response => response.json())
  }
  
  editEdgeWithoutDrag(data, callback) {
    // clean up
    var fromChannelDropdown = document.getElementById('edge-fromChannelDropdown');
    var i;
    for(i = fromChannelDropdown.options.length - 1 ; i >= 0 ; i--)
    {
      fromChannelDropdown.remove(i);
    }
    var toChannelDropdown = document.getElementById('edge-toChannelDropdown');
    var i;
    for(i = toChannelDropdown.options.length - 1 ; i >= 0 ; i--)
    {
      toChannelDropdown.remove(i);
    }
  
    var fromNodeUid = data.from;
    var toNodeUid = data.to;
  
    const fetchFromNode = async() => {
      var node = await fetchNode(fromNodeUid);
      var numFromChannels = node['py/state']['numOutputChannels'];
      for(var i=0; i<numFromChannels; i++) {
        fromChannelDropdown.add(new Option(i));
      }
    }
    fetchFromNode();
    const fetchToNode = async() => {
      var node = await fetchNode(toNodeUid);
      var numToChannels = node['py/state']['numInputChannels'];
      for(var i=0; i<numToChannels; i++) {
        toChannelDropdown.add(new Option(i));
      }
    }
    fetchToNode();
  
    // filling in the popup DOM elements
    document.getElementById('edge-saveButton').onclick = saveEdgeData.bind(this, data, callback);
    document.getElementById('edge-cancelButton').onclick = cancelEdgeEdit.bind(this,callback);
    document.getElementById('edge-popUp').style.display = 'block';
  }
  
  
  
  async saveEdgeData(data, callback) {
    if (typeof data.to === 'object') {
      data.to = data.to.id
    }
    if (typeof data.from === 'object') {
      data.from = data.from.id
    }
  
    var fromChannelDropdown = document.getElementById('edge-fromChannelDropdown');
    var from_node_channel = fromChannelDropdown.options[fromChannelDropdown.selectedIndex].value;
    var toChannelDropdown = document.getElementById('edge-toChannelDropdown');
    var to_node_channel = toChannelDropdown.options[toChannelDropdown.selectedIndex].value;
    await postEdgeData(data.from, from_node_channel, data.to, to_node_channel, data, callback);
  }
  async postEdgeData(from_node_uid, from_node_channel, to_node_uid, to_node_channel, data, callback) {
    var postData = {from_node_uid: from_node_uid, from_node_channel: from_node_channel, to_node_uid: to_node_uid, to_node_channel: to_node_channel};
  
    // Save node in backend
    await fetch('./connection', {
      method: 'POST', // or 'PUT'
      body: JSON.stringify(postData), // data can be `string` or {object}!
      headers:{
        'Content-Type': 'application/json'
      }
    })
    .then(res => res.json())
    .then(
      connection => {
        console.debug('Create connection successful:',data);
        this.updateVisConnection(data, connection)
        callback(data);
      })
    .catch(error => {
      console.error('Error on creating connection:', error);
    });
  }
  
  async deleteEdgeData(data) {
    var edge = this.state.graph.edges.find(item => item.id === data);
    var id = edge.id;
    await fetch('./connection/'+id, {
      method: 'DELETE'
    }).then(res => {
      console.debug('Delete connection successful:', id);
    }).catch(error => {
      console.error('Error on deleting connection:', error)
    })
  }
  
  async updateNodeArgs() {
    var effectDropdown = document.getElementById('node-effectDropdown');
    var selectedEffect = effectDropdown.options[effectDropdown.selectedIndex].value;
  
    const response = await fetch('./effect/'+selectedEffect+'/parameter');
    const json = response.json();
    const defaultReponse = await fetch('./effect/'+selectedEffect+'/args');
    const defaultJson = defaultReponse.json();
  
    if(configurator) {
      configurator.clear();
    }
  
    Promise.all([json,defaultJson]).then(result => { 
      var parameters = result[0];
      var defaults = result[1];
      console.log(parameters);
      console.log(defaults);
      configurator = new ConfigurationWrapper(selectedEffect, document.getElementById('node-configuration'), parameters, defaults, async (nodeUid, data) => {
        // do nothing
      });
    }).catch(err => {
      showError("Error updating node configuration. See console for details.");
      console.err("Error updating node configuration:",err);
    });
  }
  
  readSingleFile(e) {
    var file = e.target.files[0];
    if (!file) {
      return;
    }
    var reader = new FileReader();
    reader.onload = e => {
      var contents = e.target.result;
      this.loadConfig(contents);
    };
    reader.readAsText(file);
  }
  
  async saveConfig() {
    try {
      var isFileSaverSupported = !!new Blob;
    } catch (e) {
      console.error("FileSaver not supported")
    }
    await fetch('./configuration').then(response => response.json()).then(json => {
      var blob = new Blob([JSON.stringify(json, null, 4)], {type: "text/plain;charset=utf-8"});
      saveAs(blob, "configuration.json");
    })
  }
  
  loadConfig(contents) {
    console.log(contents);
    const postData = async () => fetch('./configuration', {
      method: 'POST', // or 'PUT'
      body: JSON.stringify(contents), // data can be `string` or {object}!
      headers:{
        'Content-Type': 'application/json'
      }
    })
    .then(
      () => {
        console.log("Successfully loaded");
        this.createNetwork()
      })
    .catch(error => {
      console.error('Error on loading configuration:', error);
    })
    postData();
  }
  
  showError(message) {
    var error = document.getElementById('alert');
    var errorInfo = document.getElementById('alert-info');
    error.style.display='inherit';
    errorInfo.innerHTML = "<strong>Danger!</strong> "+ message;
  }
  
  hideError() {
    var error = document.getElementById('alert');
    error.style.display='none';
  }

  handleSaveClick = async (event) => {
    await this.saveConfig();
  }

  handleLoadConfig = (event) => {
    this.readSingleFile(event)
  }

  handleNodeEditCancel = (event) => {
    this.clearNodePopUp();
  }

  updateDimensions = (event) => {

    let content = document.getElementById('vis-content');
    content.getElementsByTagName('div')[0].style.height = (content.clientHeight)+"px"
    this.state.network.redraw();
    this.state.network.fit();
  }

  render() {
    const graph = this.state.graph;
    const options = this.state.options;
    const events = this.state.events;
    const style = this.state.style;
    return (
      <div id="vis-container">
        <div id="vis-other">
          <h1>FilterGraph:</h1>
          <Button variant="contained" onClick={this.handleSaveClick}>
            <SaveIcon />
            Download Config
          </Button>
          <input type="file" id="file-input" onChange={this.handleLoadConfig} style={{ display: 'none' }}/>
          <label htmlFor="file-input">
            <Button variant="contained" component="span">
            <CloudUploadIcon />
            Upload Config
          </Button>
      </label>
        </div>
        <div id="vis-content">
          <Graph graph={graph} options={options} events={events} style={style} getNetwork={network => this.setState({network })} />
        </div>
        <div id="node-popUp">
          <h2 id="node-operation">node</h2>
          <div id="node-effectTable">
            <div className="vis-configuration vis-config-header">effect</div>
            <div className="vis-configuration vis-config-item vis-config-s2"><select className="form-control" id='node-effectDropdown' name='node-effectDropdown'></select></div>
          </div>
          <div id="node-configuration"></div>
          <table style={{margin: "auto"}}>
            <tbody>
              <tr>
                <td><input type="button" value="save" id="node-saveButton" /></td>
                <td><input type="button" value="cancel" id="node-cancelButton" onClick={this.handleNodeEditCancel} /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }
}

export default VisGraph;