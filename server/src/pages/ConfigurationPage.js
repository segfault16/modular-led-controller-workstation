import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import ProjectService from '../services/ProjectService'

const styles = theme => ({

});

class ConfigurationPage extends Component {
    render() {
        return (
            <React.Fragment>
            </React.Fragment>
        )
    }
}

ConfigurationPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ConfigurationPage);