import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import CssBaseline from '@material-ui/core/CssBaseline';
import './App.css';
import SideBar from './components/SideBar'
import Routes from './routes/Routes'
import { Switch } from 'react-router-dom';
import { renderRoutes } from 'react-router-config';


const styles = theme => ({

  root: {
    display: 'flex',
    minHeight: '100vh',
  },
  toolbar: theme.mixins.toolbar,
  content: {
    flexGrow: 1,
    backgroundColor: theme.palette.background.default,
    padding: theme.spacing(3),
  },
});

class App extends Component {
  constructor(props) {
    super(props)
  }
  render() {
    const { classes } = this.props;
    return (

      <div className={classes.root}>
        <CssBaseline />
        <SideBar />
        
        <div id="content">
        <div className={classes.toolbar} />

          <Switch>
            {renderRoutes(Routes)}
          </Switch>
        </div>

      </div>
    );
  }
}

App.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(App);