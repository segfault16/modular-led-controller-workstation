import React from "react";
import Button from '@material-ui/core/Button';
import Slider from '@material-ui/lab/Slider';
import FormControl from '@material-ui/core/FormControl'
import FormGroup from '@material-ui/core/FormGroup'
import Paper from '@material-ui/core/Paper';
import Grid from '@material-ui/core/Grid';
import FormControlLabel from '@material-ui/core/FormControlLabel'
import FilterGraphService from "../services/FilterGraphService";
import './NodePopup.css'
var Configurator = require("vis/lib/shared/Configurator").default;
let util = require('vis/lib/util');

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

var configurator = null

class NodePopup extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            mode: props.mode,
            nodeUid: props.nodeUid,
            onSave: props.onSave,
            onCancel: props.onCancel,
            config: {
                parameters: [],
                values: []
            }
        }
    }

    componentDidMount() {
        if (this.state.mode === "edit") {
            this.showEdit()
        } else if (this.state.mode === "add") {
            this.showAdd()
        }
    }

    componentWillUnmount() {
        if (configurator) {
            configurator.clear();
        }
        document.getElementById('node-saveButton').onclick = null;
        document.getElementById('node-cancelButton').onclick = null;
        document.getElementById('node-popUp').style.display = 'none';
    }

    showEdit() {

        const uid = this.state.nodeUid;

        var effectDropdown = document.getElementById('node-effectDropdown');
        effectDropdown.style.display = 'none';
        var effectTable = document.getElementById('node-effectTable');
        effectTable.style.display = 'none';
        var saveBtn = document.getElementById('node-saveButton');
        saveBtn.style.display = 'none';

        const fetchAndShow = async () => {
            const stateJson = await FilterGraphService.getNode(uid);
            const json = await FilterGraphService.getNodeParameter(uid);
            Promise.all([stateJson, json]).then(result => {
                var effect = result[0]["py/state"]["effect"]["py/state"];
                var values = result[1];
                console.log(effect)
                console.log(values)
                this.setState(state => {
                    return {
                        config: {
                            parameters: values.parameters,
                            values: effect
                        }
                    }
                })
                configurator = new ConfigurationWrapper(uid, document.getElementById('node-configuration'), values, effect, async (nodeUid, data) => {
                    console.log("emitting", data['parameters']);
                    await FilterGraphService.updateNode(nodeUid, data['parameters'])
                        .then(node => {
                            console.debug('Update node successful:', JSON.stringify(node));
                            // updateVisNode(data, node); // TODO: Needed?
                        })
                        .catch(error => {
                            //showError("Error on updating node. See console for details.")
                            console.error('Error on updating node:', error);
                        })
                });

            });
        }
        fetchAndShow();
        document.getElementById('node-effectDropdown').onchange = null;
        document.getElementById('node-popUp').style.display = 'block';
    }

    showAdd() {
        var effectDropdown = document.getElementById('node-effectDropdown');
        effectDropdown.style.display = 'inherit';
        var effectTable = document.getElementById('node-effectTable');
        effectTable.style.display = 'inherit';
        var saveBtn = document.getElementById('node-saveButton');
        saveBtn.style.display = 'inherit';
        var i;
        for (i = effectDropdown.options.length - 1; i >= 0; i--) {
            effectDropdown.remove(i);
        }
        const fetchEffects = async () => {
            await FilterGraphService.getAllEffects().then(values => {
                values.forEach(element => {
                    effectDropdown.add(new Option(element["py/type"]))
                });
                this.sortSelect(effectDropdown);
                effectDropdown.selectedIndex = 0;
                this.updateNodeArgs();
            }).catch(err => {
                console.error("Error fetching effects:", err);
            })
        }
        fetchEffects();

        document.getElementById('node-popUp').style.display = 'block';
        document.getElementById('node-effectDropdown').onchange = this.updateNodeArgs.bind(this);
        this.updateNodeArgs();
    }

    async updateNodeArgs() {
        var effectDropdown = document.getElementById('node-effectDropdown');
        if (effectDropdown.selectedIndex <= 0) {
            return
        }
        var selectedEffect = effectDropdown.options[effectDropdown.selectedIndex].value;
        const json = await FilterGraphService.getEffectParameters(selectedEffect);
        const defaultJson = await FilterGraphService.getEffectArguments(selectedEffect);
        if (configurator) {
            configurator.clear();
        }

        Promise.all([json, defaultJson]).then(result => {
            var parameters = result[0];
            var defaults = result[1];
            console.log(parameters);
            console.log(defaults);
            configurator = new ConfigurationWrapper(selectedEffect, document.getElementById('node-configuration'), parameters, defaults, async (nodeUid, data) => {
                // do nothing
            });
        }).catch(err => {
            showError("Error updating node configuration. See console for details.");
            console.err("Error updating node configuration:", err);
        });
    }

    handleNodeEditCancel = async (event) => {
        this.state.onCancel()
    }
    handleNodeEditSave = async (event) => {
        var effectDropdown = document.getElementById('node-effectDropdown')
        var selectedEffect = effectDropdown.options[effectDropdown.selectedIndex].value;
        var options = configurator.getState();
        this.state.onSave(selectedEffect, options)
    }

    sortSelect(selElem) {
        var tmpAry = new Array();
        for (var i = 0; i < selElem.options.length; i++) {
            tmpAry[i] = new Array();
            tmpAry[i][0] = selElem.options[i].text;
            tmpAry[i][1] = selElem.options[i].value;
        }
        tmpAry.sort();
        while (selElem.options.length > 0) {
            selElem.options[0] = null;
        }
        for (var i = 0; i < tmpAry.length; i++) {
            var op = new Option(tmpAry[i][0], tmpAry[i][1]);
            selElem.options[i] = op;
        }
        return;
    }

    handleChange = (value, parameter) => {
      };

    render() {
        console.log(Object.keys(this.state.config.parameters))
        let parameters = this.state.config.parameters;
        let values = this.state.config.values;
        let configList = Object.keys(parameters).map( (data, index) => {
            return (
                <Grid container spacing={24}>
                
                {/* <div className="vis-configuration vis-config-item vis-config-s2"> */}
                <Grid item xs={3}>
                {data}:
                </Grid>
                <Grid item xs={7}>
                    <Slider id={data} value={values[data]} min={parameters[data][1]} max={parameters[data][2]} step={parameters[data][3]} onChange={(e, val)=>this.handleChange(val, data)}/> 
                </Grid>
                <Grid item xs={2}>
                {values[data]}
                </Grid>
                {/* </div> */}
                
                </Grid>
            )
        });
        return (
            <div id="node-popUp">
                <h2 id="node-operation">{this.state.mode}</h2>
                <div id="node-effectTable">
                    <div className="vis-configuration vis-config-header">effect</div>
                    <div className="vis-configuration vis-config-item vis-config-s2"><select className="form-control" id='node-effectDropdown' name='node-effectDropdown'></select></div>
                </div>
                <div id="node-configuration"></div>
                <div id="node-grid">
                {configList}
                </div>
                <table style={{ margin: "auto" }}>
                    <tbody>
                        <tr>
                            <td><Button variant="contained" id="node-saveButton" onClick={this.handleNodeEditSave}>save</Button></td>
                            <td><Button variant="contained" id="node-cancelButton" onClick={this.handleNodeEditCancel}>cancel</Button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        );
    }
}

export default NodePopup;