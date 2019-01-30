import React, { Component } from 'react';
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

  render() {
    return (
      <div id="content">
      <React.Fragment>
        <div style={{ "height": "150px", "maxWidth":"1000px" }}>
          <Piano
            noteRange={{ first: firstNote, last: lastNote }}
            playNote={(midiNumber) => {
              // Play a given note - see notes below
            }}
            stopNote={(midiNumber) => {
              // Stop playing a given note - see notes below
            }}
            keyboardShortcuts={keyboardShortcuts}
          />
        </div>
        <VisGraph />
        </React.Fragment>
      </div>
    );
  }
}

export default EditProjectPage;