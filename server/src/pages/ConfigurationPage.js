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

    componentDidMount() {
        this._loadAsyncData();
    }

    componentDidUpdate(prevProps, prevState) {
        if (this.state.parameters === null || this.state.values === null) {
          this._loadAsyncData();
        }
      }

    componentWillUnmount() {
        if (this._asyncRequest) {
            this._asyncRequest.cancel();
        }
    }

    _loadAsyncData() {
        this._asyncRequest = makeCancelable(ConfigurationService.getConfiguration())
        
        this._asyncRequest.promise.then(res => {
            this._asyncRequest = null;
            this.setState({
                parameters: res.parameters,
                values: res.values
            })
        }).catch((reason) => console.log('isCanceled', reason.isCanceled));
    }

    

    handleParameterChange = (parameter, value) => {
        if(this._asyncUpdateRequest) {
            this._asyncUpdateRequest.cancel()
            this._asyncUpdateRequest = null
        }
        this._asyncUpdateRequest = makeCancelable(ConfigurationService.updateConfiguration(parameter, value))
        this._asyncUpdateRequest.promise.then(res => {
            this._asyncUpdateRequest = null;
        }).catch((reason) => console.log('isCanceled', reason.isCanceled));
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