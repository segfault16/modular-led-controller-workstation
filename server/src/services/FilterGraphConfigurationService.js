import { saveAs } from 'file-saver';

const FilterGraphConfigurationService = {
    loadConfig: async function (slotId, e) {
        var file = e.target.files[0];
        if (!file) {
            return;
        }
        await this._readUploadedFileAsText(file).then(contents => this._loadConfig(slotId, contents))
    },
    _loadConfig: async function (slotId, contents) {
        console.log("Load config from service")
        return fetch('./slot/'+slotId+'/configuration', {
            method: 'POST', // or 'PUT'
            body: JSON.stringify(contents), // data can be `string` or {object}!
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(
            () => {
                console.log("Successfully loaded");
            })
        .catch(error => {
            console.error('Error on loading configuration:', error);
        })

    },
    saveConfig: async function (slotId) {
        try {
            var isFileSaverSupported = !!new Blob;
        } catch (e) {
            console.error("FileSaver not supported")
        }
        await fetch('./slot/'+slotId+'/configuration').then(response => response.json()).then(json => {
            var blob = new Blob([JSON.stringify(json, null, 4)], { type: "text/plain;charset=utf-8" });
            saveAs(blob, "configuration.json");
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
    }
}

export default FilterGraphConfigurationService;