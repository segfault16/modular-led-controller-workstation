import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import Typography from '@material-ui/core/Typography';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';

import FormGroup from '@material-ui/core/FormGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Switch from '@material-ui/core/Switch';
import VisGraph from '../components/VisGraph'
import './EditProjectPage.css';
import FilterGraphService from '../services/FilterGraphService';

import { Piano, KeyboardShortcuts, MidiNumbers } from 'react-piano';
import 'react-piano/dist/styles.css';

import {firstNote, lastNote, keyboardShortcuts} from '../config/PianoConfig'

const styles = theme => ({
  heading: {
    fontSize: theme.typography.pxToRem(15),
    fontWeight: theme.typography.fontWeightRegular,
  },
});

const EDIT_SWITCH_LED = "edit-switch-led";
const EDIT_ACTIVE_NOTE = "edit-active-note";

class EditProjectPage extends Component {
  constructor(props) {
    super(props)
    this.state = {
      activeNote: null,
      activeNotes: [],
      switchLED: true
    }
  }

  async componentDidMount() {
    var activeNote = localStorage.getItem(EDIT_ACTIVE_NOTE);
    var switchLED = this.state.switchLED;
    var persistentSwitchLED = localStorage.getItem(EDIT_SWITCH_LED);
    if (persistentSwitchLED !== null) {
      switchLED = JSON.parse(persistentSwitchLED);
    }

    return FilterGraphService.getActiveSlot().then(res => {
      var slot = res.slot;
      this.setState(state => {
        if(switchLED) {
          return {
            switchLED: switchLED,
            activeNote: slot,
            activeNotes: [slot]
          }
        } else {
          return {
            switchLED: switchLED,
            activeNote: activeNote !== null ? JSON.parse(activeNote) : slot,
            activeNotes: activeNote !== null ? [JSON.parse(activeNote)] : [slot]
          }
        }
      })
    })
  }

  playNote = midiNumber => {
    if (this.state.activeNote == midiNumber) {
      return
    }
    console.log("play note", midiNumber)
    localStorage.setItem(EDIT_ACTIVE_NOTE, midiNumber);
    if (this.state.switchLED) {
      FilterGraphService.activateSlot(midiNumber)
    }
    this.setState({
      activeNote: midiNumber,
      activeNotes: [midiNumber],
    });
  }

  stopNote = midiNumber => {

    // do nothing
    console.log("stop")
    this.setState(state => {
      return {
        activeNotes: [...state.activeNotes]
      }
    })
  }

  handleSwitchLEDOutput = value => {
    localStorage.setItem(EDIT_SWITCH_LED, value);
    this.setState(state => {
      return {
        switchLED: value
      }
    })
  }

  render() {
    const { classes } = this.props;
    return (
      <div id="content">
        <React.Fragment>
          <VisGraph slot={this.state.activeNote} />
          <ExpansionPanel defaultExpanded={true}>
            <ExpansionPanelSummary expandIcon={<ExpandMoreIcon />}>
              <Typography className={classes.heading}>Configurations</Typography>
            </ExpansionPanelSummary>
            <ExpansionPanelDetails>
              <Grid
                container
                direction="column"
                justify="flex-start"
                alignItems="stretch"
              >
                <div style={{ "height": "100px", "maxWidth": "1000px" }}>
                  <Piano
                    noteRange={{ first: firstNote, last: lastNote }}
                    playNote={this.playNote}
                    stopNote={this.stopNote}
                    activeNotes={this.state.activeNotes}
                    keyboardShortcuts={keyboardShortcuts}
                  />
                </div>
                <FormGroup row>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={this.state.switchLED}
                        onChange={(e, val) => this.handleSwitchLEDOutput(val)}
                        value="checkedB"
                        color="primary"
                      />
                    }
                    label="Switch LED output"
                  />
                </FormGroup>
              </Grid>
            </ExpansionPanelDetails>
          </ExpansionPanel>


        </React.Fragment>
      </div>
    );
  }
}

EditProjectPage.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(EditProjectPage);