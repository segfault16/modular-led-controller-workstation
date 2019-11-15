import React from "react";
import PropTypes, { bool } from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Divider from '@material-ui/core/Divider';
import FilterGraphService from "../services/FilterGraphService";
import Typography from '@material-ui/core/Typography';
import Select from '@material-ui/core/Select';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import withMobileDialog, { WithMobileDialog } from '@material-ui/core/withMobileDialog';
import {makeCancelable} from '../util/MakeCancelable';

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

class EditModulationPopup extends React.Component {

    state = {
        config: null,
        selectedParameter: null,
        parameters: []
    }

    componentDidMount() {
        this._loadAsyncData(this.props.slot, this.props.modulationUid)
    }

    componentDidUpdate() {
        if(this.config === null) {
            this._loadAsyncData(this.props.slot, this.props.modulationUid)
        }
    }

    componentWillUnmount() {
        if (this._asyncRequest) {
            this._asyncRequest.cancel();
        }
    }

    _loadAsyncData(slot, uid) {
        this._asyncRequest = makeCancelable(FilterGraphService.getModulation(slot, uid))
        
        this._asyncRequest.promise.then(modulation => {
            console.log("Loaded", modulation)
            let nodeUid = modulation['py/state']['target_node_uid']
            let modSourceUid = modulation['py/state']['modulation_source_uid']
            const nodeJson = FilterGraphService.getNode(slot, nodeUid)
            const parameterDefinitionJson = FilterGraphService.getNodeParameterDefinition(slot, nodeUid)
            return Promise.all([modulation, nodeJson, parameterDefinitionJson])
        }).then(result => {
            console.log(result)
            var modulation = result[0]
            var node = result[1]
            var parameterDefinition = result[2]
            console.log(parameterDefinition['parameters'])

            this._asyncRequest = null;
            this.setState(state => {
                return {
                    config: {
                        parameters: { amount: [0, 0, 1, 0.01], inverted: false },
                        values: {amount: modulation['py/state']['amount'], inverted: modulation['py/state']['inverted']},
                        parameterHelp: {},
                        description: ""
                    },
                    parameters: Object.keys(parameterDefinition['parameters']),
                    selectedParameter: modulation['py/state']['target_param']
                }
            })
        })
    }

    

    handleNodeEditCancel = async (event) => {
        if (this.props.onCancel != null) {
            this.props.onCancel()
        } else {
            this.props.open = false
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
        FilterGraphService.updateModulation(this.props.slot, this.props.modulationUid, { [parameter]: value })
        this.setState(newState);
    };

    handleSelectedParameterChange = (value) => {
        console.log("Selected parameter:", value)
        let newState = Object.assign({}, this.state); // create copy of state
        newState.selectedParameter = value;
        FilterGraphService.updateModulation(this.props.slot, this.props.modulationUid, { 'target_param': value})
        this.setState(newState);
    }

    domCreateSelectParameterDropdown = () => {
        if (this.state.parameters.length > 0) {
            let items = this.state.parameters.map((param, id) => {
                return (
                    <MenuItem key={id} value={param}>{param}</MenuItem>
                )
            })
            return <React.Fragment>
                <h3>Select Parameter:</h3>
                <InputLabel htmlFor="effect-dropdown" />
                <Select
                    value={this.state.selectedParameter}
                    onChange={(e, val) => this.handleSelectedParameterChange(val.props.value)}
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

    domCreateDialogContent = (classes, effectDescription, parameters, values, parameterHelp) => {
        return <DialogContent>
        <div id="parameters">
            {this.domCreateSelectParameterDropdown()}
        </div>
        <div>
            {effectDescription.length > 0 ? 
            <React.Fragment>
            <br/>
            {effectDescription.split("\n").map((line, idx) => {
                return <Typography key={"line"+idx}>
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
                parameterHelp={parameterHelp}/>
        </div>
        <h3></h3>
        <Divider className={classes.divider} />
        <h3></h3>
        </DialogContent>
    }

    render() {
        const { classes } = this.props;
        var dialogContent = null
        if(this.state.config != null) {
            let parameters = this.state.config.parameters;
            let values = this.state.config.values;
            let parameterHelp = this.state.config.parameterHelp;
            let effectDescription = this.state.config.description;
            dialogContent = this.domCreateDialogContent(classes,effectDescription, parameters, values, parameterHelp)
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
                <DialogTitle id="form-dialog-title">Edit Modulation</DialogTitle>
                {dialogContent}
                <DialogActions>
                <Button onClick={this.handleNodeEditCancel} color="primary" variant="contained" >
                    Cancel
                </Button>
                </DialogActions>
            </Dialog>
        );
    }
}

EditModulationPopup.propTypes = {
    classes: PropTypes.object.isRequired,
    slot: PropTypes.number.isRequired,
    modulationUid: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired
};

export default withStyles(styles)(withMobileDialog()(EditModulationPopup));