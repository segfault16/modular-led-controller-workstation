import { saveAs } from 'file-saver';

const ProjectService = {
    getProjects: function() {
        return fetch('./projects').then(res => res.json()).then(dict => this._toArrayData(dict))
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
    },
    createProject: function(title, description) {
        var postData = {
            title: title,
            description: description
        }
        return fetch('./projects', {
            method: 'POST',
            body: JSON.stringify(postData),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(res => res.json())
    },
    importProject: async function (e) {
        var file = e.target.files[0];
        if (!file) {
            return;
        }
        return this._readUploadedFileAsText(file).then(contents => this._importProject(contents)).then(res => res.json())

    },
    _importProject: async function (contents) {
        console.log("Load config from service")
        return fetch('./projects/import', {
            method: 'POST', // or 'PUT'
            body: JSON.stringify(contents), // data can be `string` or {object}!
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(
            (res) => {
                console.log("Successfully loaded");
                return res
            })
        .catch(error => {
            console.error('Error on loading configuration:', error);
        })

    },
    _readUploadedFileAsText: function (inputFile) {
        const temporaryFileReader = new FileReader();

        return new Promise((resolve, reject) => {
            temporaryFileReader.onerror = () => {
                temporaryFileReader.abort();
                reject(new DOMException("Problem parsing input file."));
            };

            temporaryFileReader.onload = () => {
                resolve(temporaryFileReader.result);
            };
            temporaryFileReader.readAsText(inputFile);
        });
    },
    _toArrayData: function(projDict) {
        return Object.keys(projDict).map((proj, key) => {
            var entry = projDict[proj]
            entry['id'] = proj
            return entry
        })
    }
}

export default ProjectService;