import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import Typography from '@material-ui/core/Typography';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';
import Button from '@material-ui/core/Button';

import FormGroup from '@material-ui/core/FormGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Switch from '@material-ui/core/Switch';
import VisGraph from '../components/VisGraph'
import './EditProjectPage.css';
import FilterGraphService from '../services/FilterGraphService';

import { Piano, KeyboardShortcuts, MidiNumbers } from 'react-piano';
import 'react-piano/dist/styles.css';

import { firstNote, lastNote, keyboardShortcuts } from '../config/PianoConfig'

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
      activeScene: null,  // activated scene
      activeSlot: null,   // activated slot
      activeNotes: [],    // activated scene for piano
      switchLED: true,
      sceneMatrix: null,
    }
  }

  async componentDidMount() {
    var activeNote = localStorage.getItem(EDIT_ACTIVE_NOTE);
    var switchLED = this.state.switchLED;
    var persistentSwitchLED = localStorage.getItem(EDIT_SWITCH_LED);
    if (persistentSwitchLED !== null) {
      switchLED = JSON.parse(persistentSwitchLED);
    }

    return Promise.all([FilterGraphService.getActiveScene(), FilterGraphService.getSceneMatrix()]).then(
      res => {
        let activeScene = res[0];
        let sceneMatrix = res[1];
        var sceneId = activeScene.activeScene;
        var slotId = activeScene.activeSlot
        this.setState(state => {
          if (switchLED) {
            return {
              switchLED: switchLED,
              activateScene: sceneId,
              activeNotes: [sceneId],
              activeSlot: slotId,
              sceneMatrix: sceneMatrix
            }
          } else {
            return {
              switchLED: switchLED,
              activeScene: activeNote !== null ? JSON.parse(activeNote) : sceneId,
              activeNotes: activeNote !== null ? [JSON.parse(activeNote)] : [sceneId],
              activeSlot: slotId,
              sceneMatrix: sceneMatrix
            }
          }
        })
      }
    )
  }

  playNote = midiNumber => {
    if (this.state.activeScene == midiNumber) {
      return
    }
    console.log("play note", midiNumber)
    localStorage.setItem(EDIT_ACTIVE_NOTE, midiNumber);
    if (this.state.switchLED) {
      FilterGraphService.activateScene(midiNumber).then(res => 
        {
          console.log(res)
          res.json['toString']
          FilterGraphService.activateSlot()
        }
        ).then(res =>
        FilterGraphService.getSceneMatrix()).then(
          res => {
            console.log(res)
            let activeSlot = res[0][midiNumber]
            console.log('active slot', activeSlot)
            if (activeSlot) {
              FilterGraphService.activateSlot(activeSlot)
            }
            this.setState({
              activeSlot: activeSlot,
              activeScene: midiNumber,
              activeNotes: [midiNumber],
              sceneMatrix: res
            })
          }
        )
    } else {
      // Get slot for first device
      var activeSlot = null
      if(this.state.sceneMatrix && Object.keys(this.state.sceneMatrix).length > 0) {
        activeSlot = this.state.sceneMatrix[0][midiNumber]
      }
      if(activeSlot) {
        FilterGraphService.activateSlot(activeSlot).then(this.setState({
          activeScene: midiNumber,
          activeNotes: [midiNumber],
          activeSlot: activeSlot
        }))
      } else {
        this.setState({
          activeScene: midiNumber,
          activeNotes: [midiNumber],
        });
      }
    }
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

  handleSlotMatrixChanged = (rowIdx, colIdx) => {
    let matrix = this.state.sceneMatrix;
    matrix[rowIdx][this.state.activeScene] = colIdx
    Promise.all([FilterGraphService.updateSceneMatrix(matrix), FilterGraphService.activateSlot(colIdx)]).then(res => {
      this.setState({
        sceneMatrix: matrix,
        activeSlot: colIdx
      })
    })
  }

  domCreateSquare = (rowIdx, colIdx) => {
    let sqrColor = "primary"
    let sqrStyle = {
      maxWidth: '25px',
      minWidth: '25px',
      maxHeight: '25px',
      minHeight: '25px',
      margin: '2px'
    }
    let sqrVariant = "outlined"
    if (this.state.sceneMatrix[rowIdx][this.state.activeScene] == colIdx) {
      sqrVariant = "contained"
    }
    if (this.state.activeSlot == colIdx) {
      sqrColor = "secondary"
      // sqrVariant = "contained"
    }
    return (
      <Button variant={sqrVariant} color={sqrColor} style={sqrStyle} onClick={() => this.handleSlotMatrixChanged(rowIdx, colIdx)}></Button>
    )
  }

  domCreateRow = (rowIdx, numCols, startIndex=0) => {
    let cols = [];
    for (var i = 0; i < numCols; i++) {
      cols.push(this.domCreateSquare(rowIdx, startIndex + i));
    }
    return <div>{cols}</div>;
  }

  domCreateSlotMatrix = (numRows, numCols, startIndex=0) => {
    let rows = [];
    for (var i = 0; i < numRows; i++) {
      rows.push(this.domCreateRow(i, numCols, startIndex));
    }
    return <div>{rows}</div>
  }

  render() {
    const { classes } = this.props;
    var matrix = null;
    console.log(this.state.sceneMatrix)
    if (this.state.sceneMatrix != null) {
      let rows = Object.keys(this.state.sceneMatrix).length;
      matrix = this.domCreateSlotMatrix(rows, 30, 12);
    }
    return (
      <div id="content">
        <React.Fragment>
          <VisGraph slot={this.state.activeSlot} />
          <ExpansionPanel defaultExpanded={true}>
            <ExpansionPanelSummary expandIcon={<ExpandMoreIcon />}>
              <Typography className={classes.heading}>Configurations</Typography>
            </ExpansionPanelSummary>
            <ExpansionPanelDetails>

              <Grid container direction="column" justify="flex-start" alignItems="stretch">
                Slots:
                {matrix}
                Scenes:
                <div style={{ "height": "100px", "maxWidth": "1000px" }}>
                  
                  <Piano
                    noteRange={{ first: firstNote, last: lastNote }}
                    playNote={this.playNote}
                    stopNote={this.stopNote}
                    activeNotes={this.state.activeNotes}
                  // keyboardShortcuts={keyboardShortcuts}
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