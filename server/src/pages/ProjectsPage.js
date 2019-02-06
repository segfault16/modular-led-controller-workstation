import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Card from '@material-ui/core/Card';
import CardActions from '@material-ui/core/CardActions';
import CardContent from '@material-ui/core/CardContent';
import Button from '@material-ui/core/Button';
import Typography from '@material-ui/core/Typography';

import ProjectService from '../services/ProjectService'

const styles = {
    card: {
        minWidth: 275,
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
            projects: [{
                active: true,
                title: "Project",
                description: "Description",
                id: "ajsfkajsfklasjkf"
            }]
        }
    }

    handleProjectLoad = (proj) => {
        console.log("load", proj)
    }

    handleProjectExport = (proj) => {
        console.log("export", proj)
    }

    handleProjectDelete = (proj) => {
        console.log("delete", proj)
    }

    render() {
        const { classes } = this.props;
        const projects = this.state.projects;
        return (
            <React.Fragment>
                {projects.map((proj, key) => {
                    return (
                <Card key={key} className={classes.card}>
                    <CardContent>
                        <Typography variant="h5" component="h2">
                            {proj.title}
                        </Typography>
                        <Typography>
                            {proj.description}
                        </Typography>
                    </CardContent>
                    <CardActions>
                        <Button size="small" onClick={() => this.handleProjectLoad(proj)}>Load</Button>
                        <Button size="small" onClick={() => this.handleProjectExport(proj)}>Export</Button>
                        <Button size="small" onClick={() => this.handleProjectDelete(proj)}>Delete</Button>
                    </CardActions>
                </Card>         
                    )
                })}
            </React.Fragment>
        )
    }
}

ProjectsPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(ProjectsPage);