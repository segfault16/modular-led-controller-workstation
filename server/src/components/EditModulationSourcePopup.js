import React from "react";
import PropTypes, { bool } from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Divider from '@material-ui/core/Divider';
import FilterGraphService from "../services/FilterGraphService";
import Typography from '@material-ui/core/Typography';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import withMobileDialog, { WithMobileDialog } from '@material-ui/core/withMobileDialog';
import { makeCancelable } from '../util/MakeCancelable';
import Grid from '@material-ui/core/Grid';
import Slider from '@material-ui/core/Slider';
import Checkbox from '@material-ui/core/Checkbox';
import FormControlLabel from '@material-ui/core/FormControlLabel';

import './NodePopup.css'

import Configurator from './Configurator';

const styles = theme => ({
    paper: {
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)',
        width: theme.spacing(80),
        backgroundColor: theme.palette.background.paper,
        boxShadow: theme.shadows[5],
        padding: theme.spacing(4),
        outline: 'none',
    },
});

class EditModulationSourcePopup extends React.Component {

    state = {
        config: null,
        modulations: null
    }

    componentDidMount() {
        this._loadAsyncData(this.props.slot, this.props.modulationUid)
    }

    componentDidUpdate() {
        if (this.config === null) {
            this._loadAsyncData(this.props.slot, this.props.modulationUid)
        }
    }

    componentWillUnmount() {
        if (this._asyncRequest) {
            this._asyncRequest.cancel();
        }
    }

    _loadAsyncData(slot, uid) {
        this._asyncRequest = makeCancelable(FilterGraphService.getModulationSource(slot, uid))

        this._asyncRequest.promise.then(json => {
            var effectName = json['modulator']['py/object']
            var parameterDefinitionJson = FilterGraphService.getEffectParameters(effectName)
            var modulations = FilterGraphService.getAllModulations(slot, uid, null)
            return Promise.all([json, parameterDefinitionJson, modulations])
        }).then(result => {
            var modSource = result[0]
            var currentParameterValues = modSource['modulator']['py/state']
            var parameterDefinition = result[1]
            var modulations = result[2]

            var mods = {}
            if(modulations != null) {
                modulations.forEach(element => {
                    var state = element['py/state']

                    var uid = state['uid']
                    var target = state['target_node_uid']
                    var targetParam = state['target_param']
                    var value = state['amount']
                    var inverted = state['inverted']
                    mods[uid] = {
                        targetNode: target,
                        targetParam: targetParam,
                        value: value,
                        inverted: inverted
                    }
                });
            }
            this._asyncRequest = null;
            this.setState(state => {
                return {
                    config: {
                        parameters: parameterDefinition.parameters,
                        values: currentParameterValues,
                        parameterHelp: null,
                        description: ""
                    },
                    modulations: mods
                }
            })
        })
    }



    handleNodeEditCancel = async (event) => {
        if (this.props.onCancel != null) {
            this.props.onCancel()
        }
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
        if (this._modSrcParamChangeReq && this._modSrcParamChangeCtrl) {
            // Abort previous request
            this._modSrcParamChangeCtrl.abort()
            this._modSrcParamChangeReq = null
        }
        // New request with new AbortController
        this._modSrcParamChangeCtrl = new AbortController()
        this._modSrcParamChangeReq = FilterGraphService.updateModulationSource(this.props.slot, this.props.modulationUid, { [parameter]: value }, this._modSrcParamChangeCtrl.signal)
        this._modSrcParamChangeReq.then(res => {
            this._modSrcParamChangeReq = null;
        }).catch((reason) => reason.name == "AbortError" ? null : console.error(reason));
        this.setState(newState);
    };

    handleModulationValueChange = (value, modUid) => {
        let newState = Object.assign({}, this.state);
        newState.modulations[modUid]['value'] = value;
        if (this._modValueChangeReq && this._modValueChangeCtrl) {
            // Abort previous request
            this._modValueChangeCtrl.abort()
            this._modValueChangeReq = null
        }
        // New request with new AbortController
        this._modValueChangeCtrl = new AbortController()
        this._modValueChangeReq = FilterGraphService.updateModulation(this.props.slot, modUid, {'amount': value}, this._modValueChangeCtrl.signal)
        this._modValueChangeReq.then(res => {
            this._modValueChangeReq = null;
        }).catch((reason) => reason.name == "AbortError" ? null : console.error(reason));
        this.setState(newState);
    }
    handleModulationInvertChange = (value, modUid) => {
        let newState = Object.assign({}, this.state);
        newState.modulations[modUid]['inverted'] = value;
        FilterGraphService.updateModulation(this.props.slot, modUid, {'inverted': value})
        this.setState(newState);
    }

    domCreateDialogContent = (classes, effectDescription, parameters, values, parameterHelp) => {
        return (
            <React.Fragment>
                <div>
                    {effectDescription.length > 0 ?
                        <React.Fragment>
                            <br />
                            {effectDescription.split("\n").map((line, idx) => {
                                return <Typography key={"line" + idx}>
                                    {line}
                                </Typography>
                            })}
                        </React.Fragment>
                        : null}
                </div>
                <div id="node-grid">
                    <h3>Parameters:</h3>
                    <Configurator
                        onChange={(parameter, value) => this.handleParameterChange(value, parameter)}
                        parameters={parameters}
                        values={values}
                        parameterHelp={parameterHelp} />
                </div>
                <h3></h3>
                <Divider className={classes.divider} />
                <h3></h3>
            </React.Fragment>
        )
    }

    domCreateModulationsContent = (mods) => {
        let modContent = this.domCreateModulations(mods)
        return (<React.Fragment>
            <h3>Modulation Destinations:</h3>
            {modContent}

        </React.Fragment>)
    }

    domCreateModulations = (mods) => {
        if (mods) {
            return Object.keys(mods).map((modUid, index) => {
                let mod = mods[modUid];
                var control = this.domCreateModulation(modUid, mod);

                let parameterName = mod['targetParam']
                return (
                    // <Tooltip key={parameterName} title={helpText}>
                    <Grid key={modUid} container spacing={2} alignItems="center" justify="center">
                        <Grid item sm={3} xs={12} >
                            <Typography>
                                {parameterName}:
                        </Typography>
                        </Grid>
                        {control}
                    </Grid>
                    // </Tooltip>
                )
            })
        }
        return null
    }

    domCreateModulation = (modUid, mod) => {
        return <React.Fragment>
            <Grid item sm={7} xs={10}>
                <Slider
                    id={modUid}
                    value={mod['value']}
                    min={0}
                    max={1}
                    step={0.001}
                    onChange={(e, val) => this.handleModulationValueChange(val, modUid)} />
            </Grid>
            <Grid item sm={2} xs={2}>
            <FormControlLabel
                    control={
                        <Checkbox
                        checked={mod['inverted']}
                        onChange={(e, val) => this.handleModulationInvertChange(val, modUid)}
                        value={modUid}
                        color="primary"
                    />
                    }
                    label="inverted:"
                    labelPlacement="start"
                />
                
            </Grid>
        </React.Fragment>
    }

    render() {
        const { classes } = this.props;
        var dialogContent = null;
        if (this.state.config != null) {
            let parameters = this.state.config.parameters;
            let values = this.state.config.values;
            let parameterHelp = this.state.config.parameterHelp;
            let effectDescription = this.state.config.description;
            dialogContent = this.domCreateDialogContent(classes, effectDescription, parameters, values, parameterHelp)
        }
        var dialogModulations = null;
        if (this.state.modulations != null) {
            dialogModulations = this.domCreateModulationsContent(this.state.modulations)
        }
        return (

            <Dialog
                open={this.props.open}
                onClose={this.handleNodeEditCancel}
                aria-labelledby="form-dialog-title"
                maxWidth="xl"
                fullWidth={true}
                fullScreen={this.props.fullScreen}
            >
                <DialogTitle id="form-dialog-title">Edit Modulation Source</DialogTitle>
                <DialogContent>
                    {dialogContent}
                    {dialogModulations}
                </DialogContent>
                <DialogActions>
                    <Button onClick={this.handleNodeEditCancel} color="primary" variant="contained" >
                        Cancel
                </Button>
                </DialogActions>
            </Dialog>
        );
    }
}

EditModulationSourcePopup.propTypes = {
    classes: PropTypes.object.isRequired,
    slot: PropTypes.number.isRequired,
    modulationUid: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired
};

export default withStyles(styles)(withMobileDialog()(EditModulationSourcePopup));