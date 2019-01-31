import React, { Component } from 'react';
import Typography from '@material-ui/core/Typography';
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

class EditProjectPage extends Component {
  constructor(props) {
    super(props)
      this.state = {
          activeNote: firstNote,
          activeNotes: [firstNote]
      }
  }
  onPlayNoteInput = midiNumber => {
    
    if(this.state.activeNote == midiNumber) {
      return
    }
    console.log("play")
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

  render() {
    console.log(this.state.activeNotes)
    return (
      <div id="content">
      <React.Fragment>
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
            // onPlayNoteInput={this.onPlayNoteInput}
            // onStopNoteInput={this.onStopNoteInput}
          />
        </div>
        <VisGraph slot={this.state.activeNote}/>
        </React.Fragment>
      </div>
    );
  }
}

export default EditProjectPage;