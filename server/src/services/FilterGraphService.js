const FilterGraphService = {
    getAllConnections: function() {
        return fetch('./connections').then(res => res.json())
    },
    addConnection: function (from_node_uid, from_node_channel, to_node_uid, to_node_channel, data, callback) {
        var postData = { from_node_uid: from_node_uid, from_node_channel: from_node_channel, to_node_uid: to_node_uid, to_node_channel: to_node_channel };

        // Save node in backend
        return fetch('./connection', {
            method: 'POST', // or 'PUT'
            body: JSON.stringify(postData), // data can be `string` or {object}!
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(res => res.json()
        ).then(connection => {
            console.debug('Create connection successful:', data);
            return connection
        }).catch(error => {
            console.error('Error on creating connection:', error);
        });
    },
    deleteConnection: function (id) {
        return fetch('./connection/' + id, {
            method: 'DELETE'
        }).then(res => {
            console.debug('Delete connection successful:', id);
        }).catch(error => {
            console.error('Error on deleting connection:', error)
        })
    },
    getAllNodes: function() {
        return fetch('./nodes').then(res => res.json());
    },
    deleteNode: function (id) {
        return fetch('./node/' + id, {
            method: 'DELETE'
        }).then(res => {
            console.debug('Delete node successful:', id);
        }).catch(error => {
            console.error('Error on deleting node:', error)
        })
    }
}

export default FilterGraphService;
