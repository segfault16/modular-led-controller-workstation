import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import { Piano } from 'react-piano';

import { firstNote, lastNote, keyboardShortcuts } from '../config/PianoConfig'
import FilterGraphService from '../services/FilterGraphService'

const styles = theme => ({

});

class PerformPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            activeNote: firstNote,
            activeNotes: [firstNote],
            latch: false
        }
    }

    async componentDidMount() {
        return FilterGraphService.getActiveSlot().then(res => {
            var slot = res.slot;
            this.setState(state => {
                return {
                    activeNote: slot,
                    activeNotes: [slot]
                }
            })
        })
    }

    playNote = midiNumber => {
        if (this.state.activeNote == midiNumber) {
            return
        }
        console.log("play note", midiNumber)

        FilterGraphService.activateSlot(midiNumber)

        this.setState({
            activeNote: midiNumber,
            activeNotes: [midiNumber],
        });
    }

    stopNote = midiNumber => {
        if (this.state.latch) {
            // do nothing
            console.log("stop")
            this.setState(state => {
                return {
                    activeNotes: [...state.activeNotes]
                }
            })
        } else {
            FilterGraphService.activateSlot(0)
            this.setState(state => {
                return {
                    activeNotes: [],
                    activeNote: null
                }
            })
        }
    }

    render() {
        return (
            <div style={{ "height": "200px", "maxWidth": "1000px" }}>
                <Piano
                    noteRange={{ first: firstNote, last: lastNote }}
                    playNote={this.playNote}
                    stopNote={this.stopNote}
                    activeNotes={this.state.activeNotes}
                    keyboardShortcuts={keyboardShortcuts}
                />
            </div>
        )
    }
}


PerformPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(PerformPage);