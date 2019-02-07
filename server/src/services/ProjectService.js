const ProjectService = {
    getProjects: function() {
        return fetch('./projects').then(res => res.json())
    },
    deleteProject: function(uid) {
        return fetch('./projects/'+uid, {
            method: 'DELETE'
        }).then(res => {
            console.debug('Delete project successful:', id);
        }).catch(error => {
            console.error('Error on deleting project:', error)
        })
    },
    exportProject: function(uid) {
        return fetch('./projects/'+uid+'/export', {
            method: 'GET'
        }).then(res => res.json()
        ).catch(error => {
            console.error("Error on exporting project:", error)
        })
    },
    activateProject: function(uid) {
        var postData = {project: uid}
        return fetch('./projects/activeProject', {
            method: 'POST', // or 'PUT'
            body: JSON.stringify(postData),
            headers: {
                'Content-Type': 'application/json'
            }
        })
    }
}

export default ProjectService;