const ConfigurationService = {
    getConfiguration: function() {
        return fetch('./configuration').then(res => res.json())
    },
    updateConfiguration: function(parameter, value) {
        var postData = {[parameter]: value}
        return fetch('./configuration', {
            method: 'UPDATE', // or 'PUT'
            body: JSON.stringify(postData),
            headers: {
                'Content-Type': 'application/json'
            }
        })
    }
}

export default ConfigurationService;