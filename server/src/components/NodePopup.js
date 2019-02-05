import React from "react";
import PropTypes, { bool } from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Slider from '@material-ui/lab/Slider';
import Grid from '@material-ui/core/Grid';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import Checkbox from '@material-ui/core/Checkbox';
import Divider from '@material-ui/core/Divider';
import FilterGraphService from "../services/FilterGraphService";
import Typography from '@material-ui/core/Typography';
import Tooltip from '@material-ui/core/Tooltip'

import './NodePopup.css'

const styles = theme => ({
    paper: {
        
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)',
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
                values: [],
                parameterHelp: [],
                description: ""
            },
            effects: [],
            selectedEffect: null,
            slot: props.slot
        }
    }

    async componentDidMount() {
        if (this.state.mode === "edit") {
            await this.showEdit()
        } else if (this.state.mode === "add") {
            await this.showAdd()
        }
    }

    componentWillUnmount() {
        // document.getElementById('node-popUp').style.display = 'none';
    }

    async showEdit() {
        const uid = this.state.nodeUid;
        await FilterGraphService.getNodeEffect(this.state.slot, uid).then(effectName => {
            const nodeJson = FilterGraphService.getNode(this.state.slot, uid);
            const parameterDefinitionJson = FilterGraphService.getNodeParameter(this.state.slot, uid);
            const helpJson = FilterGraphService.getEffectParameterHelp(effectName);
            const description = FilterGraphService.getEffectDescription(effectName);
            return Promise.all([nodeJson, parameterDefinitionJson, helpJson, description])
        }).then(result => {
            var currentParameterValues = result[0]["py/state"]["effect"]["py/state"];
            var parameterDefinition = result[1];
            var helpText = result[2];
            var desc = result[3];
            this.setState(state => {
                return {
                    config: {
                        parameters: parameterDefinition.parameters,
                        values: currentParameterValues,
                        parameterHelp: (helpText !== null && helpText.parameters !== null) ? helpText.parameters : {},
                        description: desc
                    }
                }
            })
        })
    }

    async showAdd() {
        await FilterGraphService.getAllEffects().then(values => {
            let effects = values.map(element => element["py/type"]).sort()
            this.setState(state => {
                return {
                    effects: effects,
                    selectedEffect: effects[0]
                }
            })
            this.updateNodeArgs(effects[0]);
        }).catch(err => {
            console.error("Error fetching effects:", err);
        })
    }

    async updateNodeArgs(selectedEffect) {
        if (selectedEffect == null) {
            return
        }
        const json = await FilterGraphService.getEffectParameters(selectedEffect);
        const defaultJson = await FilterGraphService.getEffectArguments(selectedEffect);
        const helpJson = await FilterGraphService.getEffectParameterHelp(selectedEffect);
        const description = await FilterGraphService.getEffectDescription(selectedEffect);
        Promise.all([json, defaultJson, helpJson, description]).then(result => {
            var parameters = result[0];
            var defaults = result[1];
            var helpText = result[2];
            var desc = result[3];
            return this.setState(state => {
                return {
                    config: {
                        parameters: parameters.parameters,
                        values: defaults,
                        parameterHelp: (helpText !== null && helpText.parameters !== null) ? helpText.parameters : {},
                        description: desc
                    }
                }
            })
        }).catch(err => {
            console.error("Error updating node configuration:", err);
        });
    }

    handleNodeEditCancel = async (event) => {
        this.state.onCancel()
    }

    handleNodeEditSave = async (event) => {
        var selectedEffect = this.state.selectedEffect;
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
            FilterGraphService.updateNode(this.state.slot, this.state.nodeUid, { [parameter]: value })
        }
        this.setState(newState);
    };

    handleEffectChange = (effect) => {
        this.setState(state => {
            return {
                selectedEffect: effect
            }
        })
        this.updateNodeArgs(effect);
    }

    domCreateParameterDropdown = (parameters, values, parameterName) => {
        let items = parameters[parameterName].map((option, idx) => {
            return (
                <MenuItem key={idx} value={option}>{option}</MenuItem>
            )
        })
        return <React.Fragment>

            <Grid item xs={7} >
                <InputLabel htmlFor={parameterName} />
                <Select
                    value={values[parameterName]}
                    fullWidth={true}
                    onChange={(e, val) => this.handleParameterChange(val.props.value, parameterName)}
                    inputProps={{
                        name: parameterName,
                        id: parameterName,
                    }}>
                    {items}
                </Select>
            </Grid>
            <Grid item xs={2}>
            </Grid>
        </React.Fragment>
    }

    domCreateParameterSlider = (parameters, values, parameterName) => {
        return <React.Fragment>
            <Grid item xs={7}> 
                <Slider 
                    id={parameterName} 
                    value={values[parameterName]} 
                    min={parameters[parameterName][1]} 
                    max={parameters[parameterName][2]} 
                    step={parameters[parameterName][3]} 
                    onChange={(e, val) => this.handleParameterChange(val, parameterName)} />
            </Grid>
            <Grid item xs={2}>
            <Typography>
                {values[parameterName] !== null ? values[parameterName].toFixed(Math.abs(Math.log10(parameters[parameterName][3]))) : null}
            </Typography>
            </Grid>
        </React.Fragment>
    }

    domCreateParameterCheckbox = (parameters, values, parameterName) => {
        return <React.Fragment>
            <Grid container xs={7} justify="flex-end">
                <Checkbox
                    checked={values[parameterName]}
                    onChange={(e, val) => this.handleParameterChange(val, parameterName)}
                    value={parameterName}
                    color="primary"
                />
            </Grid>
            <Grid item xs={2}>
            <Typography>
                {values[parameterName]}
            </Typography>
            </Grid>
        </React.Fragment>
    }

    domCreateConfigList = (parameters, values, parameterHelp) => {
        if (parameters) {
            return Object.keys(parameters).map((effectName, index) => {
                let control;
                if (parameters[effectName] instanceof Array) {
                    if (parameters[effectName].some(isNaN)) {
                        // Array of non-numbers -> DropDown
                        control = this.domCreateParameterDropdown(parameters, values, effectName);

                    } else if (!parameters[effectName].some(isNaN)) {
                        // Array of numbers -> Slider
                        control = this.domCreateParameterSlider(parameters, values, effectName);
                    }
                } else if (typeof (parameters[effectName]) === "boolean") {
                    // Simple boolean -> Checkbox
                    control = this.domCreateParameterCheckbox(parameters, values, effectName);
                }
                if (control) {
                    var helpText = (parameterHelp != null && effectName in parameterHelp) ? parameterHelp[effectName] : ""
                    return (
                        <Tooltip title={helpText}>
                        <div>
                        <Grid key={index} container spacing={24}   alignItems="center" justify="center">
                            <Grid item xs={3} >
                            <Typography>
                                {effectName}:
                            </Typography>
                            </Grid>
                            {control}
                        </Grid>
                        </div>
                        </Tooltip>
                    )
                } else {
                    console.error("undefined control for data", parameters[effectName])
                    return null
                }
            });
        }
    }

    domCreateEffectDropdown = () => {
        if (this.state.mode === 'add' && this.state.effects.length > 0) {
            let items = this.state.effects.map((effect, id) => {
                return (
                    <MenuItem key={id} value={effect}>{effect}</MenuItem>
                )
            })
            return <React.Fragment>
                <h3>Select Effect:</h3>
                <InputLabel htmlFor="effect-dropdown" />
                <Select
                    value={this.state.selectedEffect}
                    onChange={(e, val) => this.handleEffectChange(val.props.value)}
                    fullWidth={true}
                    inputProps={{
                        name: "effect-dropdown",
                        id: "effect-dropdown",
                    }}>
                    {items}
                </Select>
            </React.Fragment>
        }
        return null
    }

    render() {
        const { classes } = this.props;
        let parameters = this.state.config.parameters;
        let values = this.state.config.values;
        let parameterHelp = this.state.config.parameterHelp;
        let effectDescription = this.state.config.description;
        let configList = this.domCreateConfigList(parameters, values, parameterHelp);
        let effectDropdown = this.domCreateEffectDropdown();

        return (
            <div className={classes.paper}>
                <h2 id="node-operation">{this.state.mode === "edit" ? "Edit Node" : "Add Node"}</h2>
                <div id="effects">
                    {effectDropdown}
                </div>
                <div><br/>
                    <Typography>
                        {effectDescription}
                    </Typography>
                </div>
                <div id="node-grid">
                    <h3>Parameters:</h3>
                    {configList}
                </div>
                <h3></h3>
                <Divider className={classes.divider} />
                <h3></h3>
                <Grid container spacing={24} justify="flex-end">
                {this.state.mode === "add" ? <Grid item><Button variant="contained" id="node-saveButton" onClick={this.handleNodeEditSave}>save</Button></Grid> : null}
                <Grid item><Button variant="contained" id="node-cancelButton" onClick={this.handleNodeEditCancel}>cancel</Button></Grid>
                </Grid>                
            </div>
        );
    }
}

NodePopup.propTypes = {
    classes: PropTypes.object.isRequired,
    slot: PropTypes.number.isRequired
};

export default withStyles(styles)(NodePopup);