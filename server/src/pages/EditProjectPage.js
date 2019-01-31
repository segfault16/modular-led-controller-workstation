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

const firstNote = MidiNumbers.fromNote('c0');
const lastNote = MidiNumbers.fromNote('f2');
const keyboardShortcuts = KeyboardShortcuts.create({
  firstNote: firstNote,
  lastNote: lastNote,
  keyboardConfig: KeyboardShortcuts.HOME_ROW,
});

const styles = theme => ({
  heading: {
    fontSize: theme.typography.pxToRem(15),
    fontWeight: theme.typography.fontWeightRegular,
  },
});

class EditProjectPage extends Component {
  constructor(props) {
    super(props)
      this.state = {
          activeNote: firstNote,
          activeNotes: [firstNote],
          switchLED: true
      }
  }
  onPlayNoteInput = midiNumber => {
    
    if(this.state.activeNote == midiNumber) {
      return
    }
    console.log("play note", midiNumber)
    if(this.state.switchLED) {
      FilterGraphService.activateSlot(midiNumber)
    }
    this.setState({
      activeNote: midiNumber,
      activeNotes: [midiNumber],
    });
  
  };
  onStopNoteInput = midiNumber => {
    
    // do nothing
    console.log("stop")
      this.setState(state => {
        return {
          activeNotes: [...state.activeNotes]
        }
      })
    
  }

  playNote = midiNumber => {
    //console.log("playNote", midiNumber)
    this.onPlayNoteInput(midiNumber)
  }

  stopNote = midiNumber => {
    //console.log("stopNote", midiNumber)
    this.onStopNoteInput(midiNumber)
  }

  handleSwitchLEDOutput = value => {
    this.setState(state => {
      return {
        switchLED: value
      }
    })
  }

  render() {
    const { classes } = this.props;
    console.log(this.state.activeNotes)
    return (
      <div id="content">
      <React.Fragment>
      <ExpansionPanel>
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
        <Typography>
          Select note to configure:
        </Typography>
        <div style={{ "height": "150px", "maxWidth":"1000px" }}>
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
        
        <VisGraph slot={this.state.activeNote}/>
        </React.Fragment>
      </div>
    );
  }
}

EditProjectPage.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(EditProjectPage);