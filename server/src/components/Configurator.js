import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Button from '@material-ui/core/Button';
import Slider from '@material-ui/lab/Slider';
import Grid from '@material-ui/core/Grid';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import Checkbox from '@material-ui/core/Checkbox';
import Typography from '@material-ui/core/Typography';

const styles = theme => ({

});

class Configurator extends Component {
    constructor(props) {
        super(props)
        this.state = {
            parameters: props.parameters,
            values: props.values
        }
    }

    componentWillReceiveProps(nextProps) {
        this.setState({
            parameters: nextProps.parameters,
            values: nextProps.values
        })
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

    domCreateConfigList = (parameters, values) => {
        if (parameters) {
            return Object.keys(parameters).map((data, index) => {
                let control;
                if (parameters[data] instanceof Array) {
                    if (parameters[data].some(isNaN)) {
                        // Array of non-numbers -> DropDown
                        control = this.domCreateParameterDropdown(parameters, values, data);

                    } else if (!parameters[data].some(isNaN)) {
                        // Array of numbers -> Slider
                        control = this.domCreateParameterSlider(parameters, values, data);
                    }
                } else if (typeof (parameters[data]) === "boolean") {
                    // Simple boolean -> Checkbox
                    control = this.domCreateParameterCheckbox(parameters, values, data);
                }
                if (control) {
                    return (
                        <Grid key={index} container spacing={24}   alignItems="center" justify="center">
                            <Grid item xs={3} >
                            <Typography>
                                {data}:
                            </Typography>
                            </Grid>
                            {control}
                        </Grid>
                    )
                } else {
                    console.error("undefined control for data", parameters[data])
                    return null
                }
            });
        }
    }

    render() {
        return (
            <React.Fragment>
                {this.domCreateConfigList(this.state.parameters, this.state.values)}
            </React.Fragment>
        )
    }
}

Configurator.propTypes = {
    classes: PropTypes.object.isRequired,
    parameters: PropTypes.object.isRequired,
    values: PropTypes.object.isRequired,
    onChange: PropTypes.func
};

export default withStyles(styles)(Configurator);