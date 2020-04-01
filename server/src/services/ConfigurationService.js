function handleErrors(response) {
    if (!response.ok) {
        console.error(response.text())
        throw Error(response.text());
    }
    return response;
}

const ConfigurationService = {
    getConfiguration: function(abortSignal = null) {
        return fetch('./configuration', {signal: abortSignal}).then(handleErrors).then(res => res.json())
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
        }).then(response => Promise.all([response, response.ok, response.text()]))
        .then(([response, responseOk, body]) => {
          if (responseOk) {
            // handle success case
            return response
          } else {
            throw new Error(body);
          }
        })
    }
}

export default ConfigurationService;