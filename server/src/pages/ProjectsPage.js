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

import ProjectService from '../services/ProjectService'

const styles = {
    gridList: {
        width: '100%'
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
};

class ProjectsPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            projects: [
            ],
            activeProject: null
        }
    }

    componentDidMount() {
        ProjectService.getProjects().then(res => {
            var activeProj = res.find(p => p.active)
            this.setState({
                projects: res,
                activeProject: activeProj ? activeProj.id : null
            })
        })
    }

    handleProjectLoad = (proj) => {
        console.log("load", proj)
        ProjectService.activateProject(proj.id).then(
            this.setState({
                activeProject: proj.id
            })
        )
    }

    handleProjectExport = async (proj) => {
        console.log("export", proj)
        return ProjectService.exportProject(proj.id)
    }

    handleProjectDelete = (proj) => {
        console.log("delete", proj)
        ProjectService.deleteProject(proj.id).then(() => {
            this.setState(oldState => {
                return {
                    projects: oldState.projects.filter(p => p.id != proj.id)
                }
            })
        })
    }

    handleProjectCreate = async () => {
        console.log("create project")
        await ProjectService.createProject('TODO', 'TODO').then(res => {
            this.setState(oldState => {
                return {
                    projects: [...oldState.projects, res]
                }
            })
        })
    }

    handleProjectImport = async (event) => {
        console.log("import")
        return ProjectService.importProject(event).then(res => {
            console.log("metadata", res)
            this.setState(oldState => {
                return {
                    projects: [...oldState.projects, res]
                }
            })
        })
    }

    render() {
        const { classes } = this.props;
        const projects = this.state.projects;
        console.log(projects)
        return (
            <div>
                <Button variant="contained" onClick={() => this.handleProjectCreate()}>New Project</Button>
                <input type="file" id="file-input" onChange={this.handleProjectImport} style={{ display: 'none' }} />
                <label htmlFor="file-input">
                    <Button variant="contained" component="span">Import Project</Button>                    
                </label>
                
                <GridList cellHeight={160} className={classes.gridList} cols={3} >
                {projects.map((proj, key) => {
                    console.log(proj)
                    console.log(key)
                    return (
                        <GridListTile className={classes.tile} key={key}>
                            <Card className={classes.card}  >
                                <CardContent>
                                    <Typography variant="h5" component="h2">
                                         {proj.id == this.state.activeProject ? "Active: " : null}
                                         {proj.title}
                                    </Typography>
                                    <Typography>
                                         {proj.description}
                                    </Typography>
                                </CardContent>
                                <CardActions>
                                     <Button size="small" onClick={() => this.handleProjectLoad(proj)}>Load</Button>
                                     <Button size="small" onClick={() => this.handleProjectExport(proj)}>Export</Button>
                                     <Button size="small" onClick={() => this.handleProjectDelete(proj)} disabled={proj.active}>Delete</Button>
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

export default withStyles(styles)(ProjectsPage);