import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import CssBaseline from '@material-ui/core/CssBaseline';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import Typography from '@material-ui/core/Typography';
import './App.css';
import SideBar from './components/SideBar'
import Routes from './routes/Routes'
import { Switch } from 'react-router-dom';
import { renderRoutes } from 'react-router-config';

const drawerWidth = 240;

const styles = theme => ({

  root: {
    display: 'flex',
    minHeight: '100vh',
  },
  appBar: {
    width: `calc(100% - ${drawerWidth}px)`,
    marginLeft: drawerWidth,
  },
  drawer: {
    width: drawerWidth,
    flexShrink: 0,
  },
  drawerPaper: {
    width: drawerWidth,
  },
  toolbar: theme.mixins.toolbar,
  content: {
    flexGrow: 1,
    backgroundColor: theme.palette.background.default,
    padding: theme.spacing.unit * 3,
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
        <AppBar position="fixed" className={classes.appBar}>
          <Toolbar>
            <Typography variant="h6" color="inherit" noWrap>
              Permanent drawer
          </Typography>
          </Toolbar>
        </AppBar>
        <SideBar />
        <div className={classes.toolbar} />
        <div id="content">

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