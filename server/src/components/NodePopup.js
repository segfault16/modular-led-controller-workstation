import React from "react";
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Slider from '@material-ui/lab/Slider';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import FormControl from '@material-ui/core/FormControl'
import FormGroup from '@material-ui/core/FormGroup'
import Paper from '@material-ui/core/Paper';
import Grid from '@material-ui/core/Grid';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import FormControlLabel from '@material-ui/core/FormControlLabel'
import FilterGraphService from "../services/FilterGraphService";

import './NodePopup.css'


  
  
  
  const styles = theme => ({
    paper: {
      position: 'absolute',
      top: '350px',
      left: '170px',
      width: theme.spacing.unit * 80,
      backgroundColor: theme.palette.background.paper,
      boxShadow: theme.shadows[5],
      padding: theme.spacing.unit * 4,
      outline: 'none',
    },
  });

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
        // document.getElementById('node-popUp').style.display = 'none';
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
            });
        }
        fetchAndShow();
        document.getElementById('node-effectDropdown').onchange = null;
        // document.getElementById('node-popUp').style.display = 'block';
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

        // document.getElementById('node-popUp').style.display = 'block';
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

        Promise.all([json, defaultJson]).then(result => {
            var parameters = result[0];
            var defaults = result[1];
            console.log(parameters);
            console.log(defaults);
            this.setState(state => {
                return {
                    config: {
                        parameters: parameters.parameters,
                        values: defaults
                    }
                }
            })
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
        var options = this.state.config.values;
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

    handleParameterChange = (value, parameter) => {
        let newState = Object.assign({}, this.state);    //creating copy of object
        newState.config.values[parameter] = value;
        if (this.state.mode === "edit") {
            FilterGraphService.updateNode(this.state.nodeUid, { [parameter]: value })
        }
        this.setState(newState);
    };

    render() {
        const { classes } = this.props;
        let parameters = this.state.config.parameters;
        let values = this.state.config.values;
        let configList = null
        if (parameters) {
            configList = Object.keys(parameters).map((data, index) => {
                let control;
                console.log(data)
                if (parameters[data] instanceof Array) {
                    if (parameters[data].some(isNaN)) {
                        // Array of non-numbers -> DropDown
                        let items = parameters[data].map((option, idx) => {
                            return (
                                <MenuItem value={option}>{option}</MenuItem>
                            )
                        })
                        control = <React.Fragment>
                            <Grid item xs={9}>
                                <InputLabel htmlFor={data} />
                                <Select
                                    value={values[data]}
                                    onChange={(e, val) => this.handleParameterChange(val.props.value, data)}
                                    inputProps={{
                                        name: data,
                                        id: data,
                                    }}>
                                    {items}
                                </Select>
                            </Grid>
                        </React.Fragment>
                    } else if (!parameters[data].some(isNaN)) {
                        // Array of numbers -> Slider
                        console.log("Slider")
                        control = <React.Fragment>
                            <Grid item xs={7}>
                                <Slider id={data} value={values[data]} min={parameters[data][1]} max={parameters[data][2]} step={parameters[data][3]} onChange={(e, val) => this.handleParameterChange(val, data)} />
                            </Grid>
                            <Grid item xs={2}>
                                {values[data]}
                            </Grid>
                        </React.Fragment>
                    }
                }
                if (control) {
                    return (
                        <Grid container spacing={24}>
                            <Grid item xs={3}>
                                {data}:
                    </Grid>
                            {control}
                        </Grid>
                    )
                } else {
                    return "undefined"
                }
            });
        }
        return (
            <div className={classes.paper}>
                <h2 id="node-operation">{this.state.mode}</h2>
                <div id="node-effectTable">
                    <div className="vis-configuration vis-config-header">effect</div>
                    <div className="vis-configuration vis-config-item vis-config-s2"><select className="form-control" id='node-effectDropdown' name='node-effectDropdown'></select></div>
                </div>
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

NodePopup.propTypes = {
    classes: PropTypes.object.isRequired,
  };

export default withStyles(styles)(NodePopup);