import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import Typography from '@material-ui/core/Typography';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';
import FormGroup from '@material-ui/core/FormGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Switch from '@material-ui/core/Switch';


import { Piano } from 'react-piano';

import { firstNote, lastNote, keyboardShortcuts } from '../config/PianoConfig'
import FilterGraphService from '../services/FilterGraphService'

const styles = theme => ({

});

const PERFORM_LATCH = "perform-latch";

class PerformPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            activeNote: null,
            activeNotes: [],
            latch: false
        }
    }

    async componentDidMount() {
        var latch = localStorage.getItem(PERFORM_LATCH);
        if(latch !== null) {
            this.setState(state => {
                return {
                    latch: JSON.parse(latch)
                }
            })
        }
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

    handleLatch = (val) => {
        localStorage.setItem(PERFORM_LATCH, val);
        this.setState(state => {
            return {
                latch: val
            }
        })
    }

    render() {
        console.log(this.state)
        const { classes } = this.props;
        return (
            <div id="content-dark">
            <div style={{ "height": "200px", "maxWidth": "1000px" }}>
                <Piano
                    noteRange={{ first: firstNote, last: lastNote }}
                    playNote={this.playNote}
                    stopNote={this.stopNote}
                    activeNotes={this.state.activeNotes}
                    keyboardShortcuts={keyboardShortcuts}
                />
            </div>
            <ExpansionPanel defaultExpanded={true}>
            <ExpansionPanelSummary expandIcon={<ExpandMoreIcon />}>
              <Typography className={classes.heading}>Configurations</Typography>
            </ExpansionPanelSummary>
            <ExpansionPanelDetails>
            <FormGroup row>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={this.state.latch}
                        onChange={(e, val) => this.handleLatch(val)}
                        value="checkedB"
                        color="primary"
                      />
                    }
                    label="Latch"
                  />
                </FormGroup>
            </ExpansionPanelDetails>
            </ExpansionPanel>
            </div>
        )
    }
}


PerformPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(PerformPage);