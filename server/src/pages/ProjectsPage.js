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
            projects: {
                "asjdkfjaskldf": {
                    active: true,
                    title: "Project",
                    description: "Description"
                }
            }
        }
    }

    componentDidMount() {
        ProjectService.getProjects().then(res => {
            this.setState({
                projects: res
            })
        })
    }

    handleProjectLoad = (proj) => {
        console.log("load", proj)
        ProjectService.activateProject(proj).then(ProjectService.getProjects().then(res => {
            console.log(res)
            this.setState({
                projects: res
            })
        }))
    }

    handleProjectExport = async (proj) => {
        console.log("export", proj)
        return ProjectService.exportProject(proj)
    }

    handleProjectDelete = (proj) => {
        console.log("delete", proj)
        ProjectService.deleteProject(proj).then(ProjectService.getProjects().then(res => {
            console.log(res)
            this.setState({
                projects: res
            })
        }))
    }

    handleProjectCreate = async () => {
        console.log("create project")
        await ProjectService.createProject('TODO', 'TODO')
        await ProjectService.getProjects().then(res => {
            this.setState({
                projects: res
            })
        })
    }

    render() {
        const { classes } = this.props;
        const projects = this.state.projects;
        return (
            <div>
                <Button variant="contained" onClick={() => this.handleProjectCreate()}>New Project</Button>
                <Button variant="contained" onClick={() => this.handleProjectImport()}>Import Project</Button>
                <GridList cellHeight={160} className={classes.gridList} cols={3} >
                {Object.keys(projects).map((proj, key) => {
                    return (
                        <GridListTile className={classes.tile} key={key}>
                            <Card className={classes.card}  >
                                <CardContent>
                                    <Typography variant="h5" component="h2">
                                         {projects[proj].active ? "Active: " : null}
                                         {projects[proj].title}
                                    </Typography>
                                    <Typography>
                                         {projects[proj].description}
                                    </Typography>
                                </CardContent>
                                <CardActions>
                                     <Button size="small" onClick={() => this.handleProjectLoad(proj)}>Load</Button>
                                     <Button size="small" onClick={() => this.handleProjectExport(proj)}>Export</Button>
                                       <Button size="small" onClick={() => this.handleProjectDelete(proj)} disabled={projects[proj].active}>Delete</Button>
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