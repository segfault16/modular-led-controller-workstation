import React, { Component } from 'react';
import Typography from '@material-ui/core/Typography';
import VisGraph from '../components/VisGraph'
import './EditProjectPage.css';

import { Piano, KeyboardShortcuts, MidiNumbers } from 'react-piano';
import 'react-piano/dist/styles.css';

const firstNote = MidiNumbers.fromNote('c3');
const lastNote = MidiNumbers.fromNote('f5');
const keyboardShortcuts = KeyboardShortcuts.create({
  firstNote: firstNote,
  lastNote: lastNote,
  keyboardConfig: KeyboardShortcuts.HOME_ROW,
});

class EditProjectPage extends Component {
  constructor(props) {
    super(props)
      this.state = {
          activeNotes: [44, 47, 54]
      }
  }
  onPlayNoteInput = midiNumber => {
    console.log("play")
    this.setState({
      activeNotes: [midiNumber],
    });
  
  };
  onStopNoteInput = midiNumber => {
    console.log("stop")
    // do nothing
      this.setState(state => {
        return {
          activeNotes: [...state.activeNotes]
        }
      })
    
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
            playNote={(midiNumber) => {
              // Play a given note - see notes below
            }}
            stopNote={(midiNumber) => {
              // Stop playing a given note - see notes below
            }}
            activeNotes={this.state.activeNotes}
            // keyboardShortcuts={keyboardShortcuts}
            onPlayNoteInput={this.onPlayNoteInput}
            onStopNoteInput={this.onStopNoteInput}
          />
        </div>
        <VisGraph />
        </React.Fragment>
      </div>
    );
  }
}

export default EditProjectPage;