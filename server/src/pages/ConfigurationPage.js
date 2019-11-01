import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import Configurator from '../components/Configurator'
import ConfigurationService from '../services/ConfigurationService';

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
    constructor(props) {
        super(props)
        this.state = {
            parameters: {},
            values: {}
        }
    }

    componentDidMount() {
        this._loadAsyncData()
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
        this._asyncRequest = ConfigurationService.getConfiguration().then(res => {
            this._asyncRequest = null;
            this.setState({
                parameters: res.parameters,
                values: res.values
            })
        })
    }

    handleParameterChange = (parameter, value) => {
        ConfigurationService.updateConfiguration(parameter, value)
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