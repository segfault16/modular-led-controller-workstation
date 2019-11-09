import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import Configurator from '../components/Configurator'
import ConfigurationService from '../services/ConfigurationService';
import {makeCancelable} from '../util/MakeCancelable';

const styles = theme => ({
    page: {
        background: theme.palette.background.default,
    },
    pageContent: {
        margin: theme.spacing(2),
        background: theme.palette.background.default,
    }
});



class ConfigurationPage extends Component {
    state = {
        parameters: null,
        values: null
    }
    _paramChangeAbortController = null

    componentDidMount() {
        this._loadAsyncData();
    }

    componentDidUpdate(prevProps, prevState) {
        if (this.state.parameters === null || this.state.values === null) {
          this._loadAsyncData();
        }
      }

    componentWillUnmount() {
        if (this._asyncGetConfigurationRequest) {
            this._asyncGetConfigurationRequest.cancel()
        }
    }

    _loadAsyncData() {
        this._asyncGetConfigurationRequest = makeCancelable(ConfigurationService.getConfiguration())
        
        this._asyncGetConfigurationRequest.promise.then(res => {
            this._asyncGetConfigurationRequest = null;
            this.setState({
                parameters: res.parameters,
                values: res.values
            })
        })
    }

    

    handleParameterChange = (parameter, value) => {
        if(this._asyncParamChangeRequest && this._paramChangeAbortController) {
            // Abort previous request
            this._paramChangeAbortController.abort()
            this._asyncParamChangeRequest = null
        }
        // New request with new AbortController
        this._paramChangeAbortController = new AbortController()
        this._asyncParamChangeRequest = ConfigurationService.updateConfiguration(parameter, value, this._paramChangeAbortController.signal)
        this._asyncParamChangeRequest.then(res => {
            this._asyncParamChangeRequest = null;
        }).catch((reason) => reason.name == "AbortError" ? null : console.error(reason));
    }

    render() {
        const { classes } = this.props;

        let configurator;
        if (this.state.parameters != null && this.state.values != null) {
            configurator = <Configurator
                parameters={this.state.parameters}
                values={this.state.values}
                onChange={(parameter, value) => this.handleParameterChange(parameter, value)}
            />;
        } else {
            configurator = "Loading";
        }
        return (
            <div className={classes.pageContent}>
                <h2>
                    Server Configuration
                </h2>
                {configurator}
            </div>
        )
    }
}

ConfigurationPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ConfigurationPage);