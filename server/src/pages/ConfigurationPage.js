import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import Configurator from '../components/Configurator'
import ProjectService from '../services/ProjectService'

const styles = theme => ({

});

class ConfigurationPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            parameters: {},
            values: {}
        }
    }

    handleParameterChange = (parameter, value) => {

    }

    render() {
        return (
            <React.Fragment>
                <Configurator
                    parameters={this.state.parameters}
                    values={this.state.values}
                    onChange={(parameter, value) => this.handleParameterChange(parameter, value)}
                />
            </React.Fragment>
        )
    }
}

ConfigurationPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ConfigurationPage);