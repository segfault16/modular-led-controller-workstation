import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Card from '@material-ui/core/Card';
import CardActions from '@material-ui/core/CardActions';
import CardContent from '@material-ui/core/CardContent';
import Button from '@material-ui/core/Button';
import Typography from '@material-ui/core/Typography';
import GridList from '@material-ui/core/GridList';
import GridListTile from '@material-ui/core/GridListTile';
import CloudUploadIcon from '@material-ui/icons/CloudUpload';
import SaveIcon from '@material-ui/icons/Save';
import CreateIcon from '@material-ui/icons/Create';
import AddIcon from '@material-ui/icons/Add';
import TextField from '@material-ui/core/TextField';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';

import ProjectService from '../services/ProjectService';
import ConfigurationService from '../services/ConfigurationService';
import { withSnackbar } from 'notistack';

const styles = theme => ({
    toggleContainer: {
        height: 32,
        padding: `${theme.spacing(1)}px ${theme.spacing(2)}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',
        margin: `${theme.spacing(1)}px`,
        background: theme.palette.background.default,
    },
    gridList: {
        width: '100%',
        padding: theme.spacing(1)
    },

    tile: {
        minWidth: 275,
        maxWidth: 300,

    },
    title: {
        fontSize: 14,
    },
    pos: {
        marginBottom: 12,
    },
});

class ProjectsPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            projects: [
            ],
            activeProject: null,

            addProjTitle: "",
            addProjDescription: "",
            addProjOpen: false,
        }
    }

    componentDidMount() {
        ProjectService.getProjects().then(res => {
            var activeProj = res.find(p => p.active)
            this.setState({
                projects: res,
                activeProject: activeProj ? activeProj.id : null
            })
        }).catch(err => {
            console.error("Error getting projects:", err);
            this.props.enqueueSnackbar("Error getting projects. Check console for details.", { variant: 'error' })
        })
    }

    handleProjectLoad = (proj) => {
        console.log("load", proj)
        ProjectService.activateProject(proj.id).then(res => {
            this.setState({
                activeProject: proj.id
            })
        }
        ).catch(err => {
            console.error("Error loading project:", err);
            this.props.enqueueSnackbar("Error loading project. Check console for details.", { variant: 'error' })
        })
    }

    handleProjectExport = async (proj) => {
        console.log("export", proj)
        return ProjectService.exportProject(proj.id).catch(err => {
            console.error("Error exporting project project:", err);
            this.props.enqueueSnackbar("Error exporting project. Check console for details.", { variant: 'error' })
        })
    }

    handleProjectDelete = (proj) => {
        console.log("delete", proj)
        ProjectService.deleteProject(proj.id).then(() => {
            this.setState(oldState => {
                return {
                    projects: oldState.projects.filter(p => p.id != proj.id)
                }
            })
        }).catch(err => {
            console.error("Error deleting project:", err);
            this.props.enqueueSnackbar("Error deleting project. Check console for details.", { variant: 'error' })
        })
    }

    handleProjectCreate = async (title, description) => {
        console.log("create project")
        await ProjectService.createProject(title, description).then(res => {
            this.setState(oldState => {
                return {
                    projects: [...oldState.projects, res]
                }
            })
        }).catch(err => {
            console.error("Error creating project:", err);
            this.props.enqueueSnackbar("Error creating project. Check console for details.", { variant: 'error' })
        })
    }

    handleProjectImport = async (event) => {
        console.log("import")
        return ProjectService.importProject(event).then(res => {
            this.setState(oldState => {
                return {
                    projects: [...oldState.projects, res]
                }
            })
        }).catch(err => {
            console.error("Error importing project:", err);
            this.props.enqueueSnackbar("Error importing project. Check console for details.", { variant: 'error' })
        })
    }

    handleClickOpen = () => {
        this.setState({ addProjOpen: true });
    };

    handleClose = () => {
        this.setState({ addProjOpen: false, addProjDescription: '', addProjTitle: '' });
    };


    handleChange = name => event => {
        this.setState({
            [name]: event.target.value,
        });
    };


    render() {
        const { classes } = this.props;
        const projects = this.state.projects;
        return (
            <div id="content-dark">
                <div className={classes.toggleContainer}>

                    <Button size="small" onClick={this.handleClickOpen}>
                        <AddIcon />
                    </Button>
                    <Dialog
                        open={this.state.addProjOpen}
                        onClose={this.handleClose}
                        aria-labelledby="form-dialog-title">
                        <DialogTitle id="form-dialog-title">Add New Project</DialogTitle>
                        <DialogContent>
                            <DialogContentText>

                            </DialogContentText>
                            <TextField
                                autoFocus
                                margin="dense"
                                id="title"
                                label="Title"
                                fullWidth
                                value={this.state.addProjTitle}
                                onChange={this.handleChange('addProjTitle')} />
                            <TextField
                                margin="dense"
                                id="description"
                                label="Description"
                                fullWidth
                                value={this.state.addProjDescription}
                                onChange={this.handleChange('addProjDescription')} />
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={this.handleClose} color="primary">Cancel</Button>
                            <Button onClick={() => { this.handleProjectCreate(this.state.addProjTitle, this.state.addProjDescription); this.handleClose(); }} color="primary">Add</Button>
                        </DialogActions>
                    </Dialog>


                    <input type="file" id="file-input" onChange={this.handleProjectImport} style={{ display: 'none' }} onClick={(event) => { event.target.value = null }} />
                    <label htmlFor="file-input">
                        <Button size="small" component="span">
                            <CloudUploadIcon />
                        </Button>
                    </label>
                </div>
                <GridList cellHeight={160} className={classes.gridList} cols={3} spacing={8} >
                    {projects.map((proj, key) => {
                        return (
                            <GridListTile className={classes.tile} key={key} >
                                <Card className={classes.card}  >
                                    <CardContent>
                                        <Typography variant="h5" component="h2">
                                            {proj.id == this.state.activeProject ? "Active: " : null}
                                            {proj.name}
                                        </Typography>
                                        <Typography>
                                            {proj.description}
                                        </Typography>
                                    </CardContent>
                                    <CardActions>
                                        <Button size="small" onClick={() => this.handleProjectLoad(proj)}>Load</Button>
                                        <Button size="small" onClick={() => this.handleProjectExport(proj)}>Export</Button>
                                        <Button size="small" onClick={() => this.handleProjectDelete(proj)} disabled={proj.id == this.state.activeProject}>Delete</Button>
                                    </CardActions>
                                </Card>
                            </GridListTile>
                        )
                    })}
                </GridList>
            </div>
        )
    }
}

ProjectsPage.propTypes = {
    classes: PropTypes.object.isRequired,
};
export default withSnackbar(withStyles(styles)(ProjectsPage));