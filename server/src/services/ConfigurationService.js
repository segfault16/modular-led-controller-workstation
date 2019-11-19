const ConfigurationService = {
    getConfiguration: function(abortSignal = null) {
        return fetch('./configuration', {signal: abortSignal}).then(res => res.json())
    },
    updateConfiguration: function(parameter, value, abortSignal = null) {
        var postData = {[parameter]: value}
        return fetch('./configuration', {
            method: 'PUT', // or 'PUT'
            body: JSON.stringify(postData),
            headers: {
                'Content-Type': 'application/json'
            },
            signal: abortSignal
        })
    }
}

export default ConfigurationService;