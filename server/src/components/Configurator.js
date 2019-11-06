import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Slider from '@material-ui/core/Slider';
import Grid from '@material-ui/core/Grid';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import Checkbox from '@material-ui/core/Checkbox';
import Typography from '@material-ui/core/Typography';
import Tooltip from '@material-ui/core/Tooltip'
import { withSnackbar } from 'notistack';

import ProjectService from '../services/ProjectService'

const styles = theme => ({
    image : {
        maxWidth: '100px',
        maxHeight: '100px'
      }
});


class Configurator extends Component {
    state = {
        parameters: this.props.parameters,
        values: this.props.values,
        parameterHelp: this.props.parameterHelp
    }

    handleParameterChange = (value, parameter) => {
        let newState = Object.assign({}, this.state);    //creating copy of object
        newState.values[parameter] = value;
        this.setState(newState);
        this.props.onChange(parameter, value)
    };

    domCreateParameterDropdown = (parameters, values, parameterName) => {
        let items = parameters[parameterName].map((option, idx) => {
            return (
                <MenuItem key={idx} value={option}>{option}</MenuItem>
            )
        })
        return <React.Fragment>

            <Grid item sm={7} xs={10}>
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
            <Grid item sm={2} xs={2}>
            </Grid>
        </React.Fragment>
    }

    domCreateParameterSlider = (parameters, values, parameterName) => {
        return <React.Fragment>
            <Grid item sm={7} xs={10}>
                <Slider 
                    id={parameterName} 
                    value={values[parameterName]} 
                    min={parameters[parameterName][1]} 
                    max={parameters[parameterName][2]} 
                    step={parameters[parameterName][3]} 
                    onChange={(e, val) => this.handleParameterChange(val, parameterName)} />
            </Grid>
            <Grid item sm={2} xs={2}>
            <Typography align="right">
                {values[parameterName] !== null ? values[parameterName].toFixed(Math.abs(Math.log10(parameters[parameterName][3]))) : null}
            </Typography>
            </Grid>
        </React.Fragment>
    }

    domCreateParameterCheckbox = (parameters, values, parameterName) => {
        return <React.Fragment>
            <Grid item sm={7} xs={10}></Grid>
            <Grid item sm={2} xs={2}>
                <Checkbox
                    checked={values[parameterName]}
                    onChange={(e, val) => this.handleParameterChange(val, parameterName)}
                    value={parameterName}
                    color="primary"
                />
            </Grid>
        </React.Fragment>
    }

    handleGifUpload = async (event, parameterName) => {
        await ProjectService.uploadProjectAsset(event).then( res => this.handleParameterChange(res['filename'], parameterName)).catch(err => {
            console.error("Error uploading asset:", err);
            this.props.enqueueSnackbar("Error uploading asset. Check console for details.", { variant: 'error' })
        })
    }

    domCreateParameterGif = (parameters, values, parameterName) => {
        return <React.Fragment>
            <Grid container justify="flex-end">
                <img src={"project/assets/" + values[parameterName]} role="presentation" style={{maxWidht: '100px', maxHeight: '100px'}} />
            </Grid>
            <Grid item sm={2} xs={2}>
            <Typography>
            <input type="file" id="gif-input" onChange={(e) => this.handleGifUpload(e, parameterName)} style={{ display: 'none' }} />
                  <label htmlFor="gif-input">
                  
                  <Button component="span" variant="contained" size="small">
                  Upload
                      
                    </Button>                    
                  </label>
            </Typography>
            </Grid>
        </React.Fragment>
    }

    domCreateConfigList = (parameters, values, parameterHelp) => {
        if (parameters) {
            return Object.keys(parameters).map((parameterName, index) => {
                let control;
                try {
                    if (parameters[parameterName] instanceof Array) {
                        if (parameters[parameterName].length >= 2 && parameters[parameterName][0] == 'gif') {
                            control = this.domCreateParameterGif(parameters, values, parameterName);
                        }
                        else if (parameters[parameterName].length == 4 && !parameters[parameterName].some(isNaN)) {
                            // Array of numbers -> Slider
                            control = this.domCreateParameterSlider(parameters, values, parameterName);
                        }
                        else if (parameters[parameterName].some(isNaN)) {
                            // Array of non-numbers -> DropDown
                            control = this.domCreateParameterDropdown(parameters, values, parameterName);
                        } 
                    } else if (typeof (parameters[parameterName]) === "boolean") {
                        // Simple boolean -> Checkbox
                        control = this.domCreateParameterCheckbox(parameters, values, parameterName);
                    }
                } catch (error) {
                    console.error("Cannot create configurator entry for "+parameterName, error)
                }
                if (control) {
                    var helpText = (parameterHelp != null && parameterName in parameterHelp) ? parameterHelp[parameterName] : "";
                    return (
                        <Tooltip key={parameterName} title={helpText}>
                        <Grid key={parameterName} container spacing={2}   alignItems="center" justify="center">
                            <Grid item sm={3} xs={12} >
                            <Typography>
                                {parameterName}:
                            </Typography>
                            </Grid>
                            {control}
                        </Grid>
                        </Tooltip>
                    )
                } else {
                    console.error("undefined control for data", parameters[parameterName])
                    return null
                }
            });
        }
    }

    render() {
        const { classes } = this.props;
        return (
            <div>
                {this.domCreateConfigList(this.props.parameters, this.props.values, this.props.parameterHelp)}
            </div>
        )
    }
}

Configurator.propTypes = {
    classes: PropTypes.object.isRequired,
    // TODO: Validate property types
    // parameters: PropTypes.object,
    // parameterHelp: PropTypes.object,
    // values: PropTypes.object,
    onChange: PropTypes.func
};

export default withSnackbar(withStyles(styles)(Configurator));