import React from "react";
import PropTypes, { bool } from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import MenuItem from '@material-ui/core/MenuItem';
import Divider from '@material-ui/core/Divider';
import FilterGraphService from "../services/FilterGraphService";
import Typography from '@material-ui/core/Typography';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import withMobileDialog, { WithMobileDialog } from '@material-ui/core/withMobileDialog';
import TextField from '@material-ui/core/TextField';
import Autocomplete from '@material-ui/lab/Autocomplete';
import { makeCancelable } from '../util/MakeCancelable';

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

class AddNodePopup extends React.Component {
    state = {
        config: null,
        effects: [],
        selectedEffect: null
    }

    componentDidMount() {
        this._loadAsyncData()
    }

    componentDidUpdate() {
        if (this.config === null) {
            this._loadAsyncData()
        }
    }

    componentWillUnmount() {
        if (this._asyncRequest) {
            this._asyncRequest.cancel()
        }
    }


    _loadAsyncData() {
        this._asyncRequest = makeCancelable(FilterGraphService.getAllEffects())

        this._asyncRequest.promise.then(values => {
            let effects = values.map(element => element["py/type"]).sort()
            this._asyncRequest = null
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
        if (this.props.onCancel != null) {
            this.props.onCancel()
        }
    }

    handleNodeEditSave = async (event) => {
        var selectedEffect = this.state.selectedEffect;
        var options = this.state.config.values;
        if (this.props.onSave != null) {
            this.props.onSave(selectedEffect, options)
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
        this.setState(newState);
    };

    handleEffectChange = (effect) => {
        console.log("selected effect", effect)
        this.setState(state => {
            return {
                selectedEffect: effect
            }
        })
        this.updateNodeArgs(effect);
    }

    domCreateEffectDropdown = () => {
        if (this.state.effects.length > 0) {
            let items = this.state.effects.map((effect, id) => {
                return (
                    <MenuItem key={id} value={effect}>{effect}</MenuItem>
                )
            })
            return <React.Fragment>
                <h3>Select Effect:</h3>
                <Autocomplete
                    id="combo-box-demo"
                    options={this.state.effects}
                    value={this.state.selectedEffect}
                    onChange={(e, val) => this.handleEffectChange(val)}
                    disableClearable
                    renderInput={params => (
                        <TextField {...params} variant="outlined" fullWidth />
                    )}
                />
            </React.Fragment>
        }
        return null
    }

    domCreateDialogContent = (classes, effectDescription, parameters, values, parameterHelp) => {
        return <DialogContent>
            <div id="effects">
                {this.domCreateEffectDropdown()}
            </div>
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
        </DialogContent>
    }

    render() {
        const { classes } = this.props;
        var dialogContent = null
        if (this.state.config != null) {
            let parameters = this.state.config.parameters;
            let values = this.state.config.values;
            let parameterHelp = this.state.config.parameterHelp;
            let effectDescription = this.state.config.description;
            dialogContent = this.domCreateDialogContent(classes, effectDescription, parameters, values, parameterHelp)
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
                <DialogTitle id="form-dialog-title">Add Node</DialogTitle>
                {dialogContent}
                <DialogActions>
                    <Button onClick={this.handleNodeEditCancel} color="primary" variant="contained" >
                        Cancel
                </Button>
                    <Button onClick={this.handleNodeEditSave} variant="contained" id="node-saveButton" >
                        Save
                </Button>
                </DialogActions>
            </Dialog>
        );
    }
}

AddNodePopup.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(withMobileDialog()(AddNodePopup));