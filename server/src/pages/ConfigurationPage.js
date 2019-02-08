import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import Configurator from '../components/Configurator'
import ProjectService from '../services/ProjectService'
import ConfigurationService from '../services/ConfigurationService';

const styles = theme => ({
    page: {
        background: theme.palette.background.default,
        height: '100%',
    },
    pageContent: {
        margin: theme.spacing.unit,
        background: theme.palette.background.default
    }
});

class ConfigurationPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            parameters: {},
            values: {}
        }
    }

    componentDidMount() {
        ConfigurationService.getConfiguration().then(res => {
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
        return (
            <div className={classes.page}>
                <div className={classes.pageContent}>
                    <Configurator
                        parameters={this.state.parameters}
                        values={this.state.values}
                        onChange={(parameter, value) => this.handleParameterChange(parameter, value)}
                    />
                </div>
            </div>
        )
    }
}

ConfigurationPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ConfigurationPage);