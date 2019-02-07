import { saveAs } from 'file-saver';

const ProjectService = {
    getProjects: function() {
        return fetch('./projects').then(res => res.json())
    },
    deleteProject: function(uid) {
        return fetch('./projects/'+uid, {
            method: 'DELETE'
        }).then(res => {
            console.debug('Delete project successful:', uid);
        }).catch(error => {
            console.error('Error on deleting project:', error)
        })
    },
    exportProject: async function(uid) {
        try {
            var isFileSaverSupported = !!new Blob;
        } catch (e) {
            console.error("FileSaver not supported")
        }
        await fetch('./projects/'+uid+'/export').then(response => response.json()).then(json => {
            var blob = new Blob([JSON.stringify(json, null, 4)], { type: "text/plain;charset=utf-8" });
            saveAs(blob, uid + ".json");
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