import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';

import Configurator from '../components/Configurator'
import ConfigurationService from '../services/ConfigurationService';
import { makeCancelable } from '../util/MakeCancelable';
import MaterialTable from 'material-table';

import { forwardRef } from 'react';

import AddBox from '@material-ui/icons/AddBox';
import ArrowDownward from '@material-ui/icons/ArrowDownward';
import Check from '@material-ui/icons/Check';
import ChevronLeft from '@material-ui/icons/ChevronLeft';
import ChevronRight from '@material-ui/icons/ChevronRight';
import Clear from '@material-ui/icons/Clear';
import DeleteOutline from '@material-ui/icons/DeleteOutline';
import Edit from '@material-ui/icons/Edit';
import FilterList from '@material-ui/icons/FilterList';
import FirstPage from '@material-ui/icons/FirstPage';
import LastPage from '@material-ui/icons/LastPage';
import Remove from '@material-ui/icons/Remove';
import SaveAlt from '@material-ui/icons/SaveAlt';
import Search from '@material-ui/icons/Search';
import ViewColumn from '@material-ui/icons/ViewColumn';
import Typography from '@material-ui/core/Typography';

import { withSnackbar } from 'notistack';

const tableIcons = {
    Add: forwardRef((props, ref) => <AddBox {...props} ref={ref} />),
    Check: forwardRef((props, ref) => <Check {...props} ref={ref} />),
    Clear: forwardRef((props, ref) => <Clear {...props} ref={ref} />),
    Delete: forwardRef((props, ref) => <DeleteOutline {...props} ref={ref} />),
    DetailPanel: forwardRef((props, ref) => <ChevronRight {...props} ref={ref} />),
    Edit: forwardRef((props, ref) => <Edit {...props} ref={ref} />),
    Export: forwardRef((props, ref) => <SaveAlt {...props} ref={ref} />),
    Filter: forwardRef((props, ref) => <FilterList {...props} ref={ref} />),
    FirstPage: forwardRef((props, ref) => <FirstPage {...props} ref={ref} />),
    LastPage: forwardRef((props, ref) => <LastPage {...props} ref={ref} />),
    NextPage: forwardRef((props, ref) => <ChevronRight {...props} ref={ref} />),
    PreviousPage: forwardRef((props, ref) => <ChevronLeft {...props} ref={ref} />),
    ResetSearch: forwardRef((props, ref) => <Clear {...props} ref={ref} />),
    Search: forwardRef((props, ref) => <Search {...props} ref={ref} />),
    SortArrow: forwardRef((props, ref) => <ArrowDownward {...props} ref={ref} />),
    ThirdStateCheck: forwardRef((props, ref) => <Remove {...props} ref={ref} />),
    ViewColumn: forwardRef((props, ref) => <ViewColumn {...props} ref={ref} />)
};

const styles = theme => ({
    page: {
        background: theme.palette.background.default,
    },
    pageContent: {
        margin: theme.spacing(2),
        background: theme.palette.background.default,
    }
});

function createData(name, calories, fat, carbs, protein) {
    return { name, calories, fat, carbs, protein };
}

const rows = [
    createData('Frozen yoghurt', 159, 6.0, 24, 4.0),
    createData('Ice cream sandwich', 237, 9.0, 37, 4.3),
    createData('Eclair', 262, 16.0, 24, 6.0),
    createData('Cupcake', 305, 3.7, 67, 4.3),
    createData('Gingerbread', 356, 16.0, 49, 3.9),
];


class ConfigurationPage extends Component {
    state = {
        parameters: null,
        values: null,
        device_configs: null,
        columns: [
            { title: 'Output group', field: 'config' },
            { title: 'Device', field: 'device', lookup: { FadeCandy: 'FadeCandy', RaspberryPi: 'RaspberryPi', VirtualOutput: 'VirtualOutput' }, },
            { title: 'Candy Server (if device is CandyServer)', field: 'candyserver' },
            { title: 'Num Pixel', field: 'num_pixel', type: 'numeric' },
            { title: 'Num Rows', field: 'num_rows', type: 'numeric' },
            { title: 'Panel mapping file', field: 'mapping' },
            { title: 'Virtual reference', field: 'virtual_reference' },
            { title: 'Virtual start index', field: 'virtual_startindex', type: 'numeric' }
        ],
        data: [
            { config: 'default', device: 'FadeCandy', candyserver: 'localhost', num_pixel: 63 },
        ],
    }
    _paramChangeAbortController = null

    componentDidMount() {
        this._loadAsyncData();
    }

    componentDidUpdate(prevProps, prevState) {
        if (this.state.parameters === null || this.state.values === null) {
            this._loadAsyncData();
        }
    }

    componentWillUnmount() {
        if (this._asyncGetConfigurationRequest) {
            this._asyncGetConfigurationRequest.cancel()
        }
    }

    _loadAsyncData() {
        this._asyncGetConfigurationRequest = makeCancelable(ConfigurationService.getConfiguration())

        this._asyncGetConfigurationRequest.promise.then(res => {
            this._asyncGetConfigurationRequest = null;
            console.log(res)
            this.setState({
                parameters: res.parameters,
                values: res.values,
                device_configs: res.device_configs,
                data: this.configToTableData(res.values.device_configs)
            })
        })
    }

    createTableRow = (name, config) => {
        console.log(config)
        return {
            config: name,
            device: config.device,
            candyserver: config['device.candy.server'],
            num_pixel: config['device.num_pixels'],
            num_rows: config['device.num_rows'],
            mapping: config['device.panel.mapping'],
            virtual_startindex: config['device.virtual.start_index'],
            virtual_reference: config['device.virtual.reference']
        }
    }

    configToTableData = (device_configs) => {
        var newData = []
        Object.keys(device_configs).forEach(element => {
            let configName = element
            device_configs[element].forEach(entry => {
                let row = this.createTableRow(configName, entry)
                newData.push(row)
            })
        });
        console.log(newData)
        return newData
    }

    tableDataToConfig = (data) => {
        var configs = {}
        data.forEach(entry => {
            let configName = entry.config
            if (!(configName in configs)) {
                configs[configName] = []
            }

            let config = {
                device: entry.device,
                'device.candy.server': entry.candyserver,
                'device.num_pixels': entry.num_pixel,
                'device.num_rows': entry.num_rows,
                'device.panel.mapping': entry.mapping,
                'device.virtual.start_index': entry.virtual_startindex,
                'device.virtual.reference': entry.virtual_reference
            }
            configs[configName].push(config)
        })
        return configs
    }



    handleParameterChange = (parameter, value) => {
        if (this._asyncParamChangeRequest && this._paramChangeAbortController) {
            // Abort previous request
            this._paramChangeAbortController.abort()
            this._asyncParamChangeRequest = null
        }
        // New request with new AbortController
        this._paramChangeAbortController = new AbortController()
        this._asyncParamChangeRequest = ConfigurationService.updateConfiguration(parameter, value, this._paramChangeAbortController.signal)
        this._asyncParamChangeRequest.then(res => {
            this._asyncParamChangeRequest = null;
        }).catch((reason) => reason.name == "AbortError" ? null : console.error(reason));
    }

    handleOutputConfigChange = (newData, oldData) => {
        const data = [...this.state.data];
        if (newData != null && oldData != null) {
            // update
            data[data.indexOf(oldData)] = newData
        } else if (newData != null) {
            // add
            data.push(newData)
        } else if (oldData != null) {
            data.splice(data.indexOf(oldData), 1);
        }
        const config = this.tableDataToConfig(data)
        console.log(config)
        if (this._asyncParamChangeRequest && this._paramChangeAbortController) {
            // Abort previous request
            this._paramChangeAbortController.abort()
            this._asyncParamChangeRequest = null
        }
        // New request with new AbortController
        this._paramChangeAbortController = new AbortController()
        this._asyncParamChangeRequest = ConfigurationService.updateConfiguration('device_configs', config, this._paramChangeAbortController.signal)
        return this._asyncParamChangeRequest.then(res => {
            this._asyncParamChangeRequest = null;
            console.log(res)

        }).then(() => {

            this.setState((prevState) => {
                return { ...prevState, data };
            });

        }).catch((reason) => {
            if (reason.name == "AbortError") {

            } else {
                var res = reason.message
                console.log(res)
                this.props.enqueueSnackbar("Error updating device config: " + res, { variant: 'error' })
            }
         
            this._asyncParamChangeRequest = null;
        });
    }

    render() {
        const { classes } = this.props;

        let configurator;
        if (this.state.parameters != null && this.state.values != null) {
            configurator = <Configurator
                parameters={this.state.parameters}
                values={this.state.values}
                onChange={(parameter, value) => this.handleParameterChange(parameter, value)}
            />;
        } else {
            configurator = "Loading";
        }
        return (
            <div className={classes.pageContent}>
                <h2>
                    Server Configuration
                </h2>
                {configurator}
                <h2>
                    Device Configuration
                </h2>
                <Typography>
                    In the following section you can figure one or more outputs for LED strips and panels.
                    Multiple devices can be can be grouped in one output group and will be visible as separate slots in Edit View.
                    If multiple slots for a single hardware device are required, create an output group with VirtualOutputs.
                    They must refer to the same non-virtual output group via Virtual reference.
                </Typography>
                <Typography>
                    Please note: Changing output configuration might require a restart for some devices
                </Typography>
                <MaterialTable
                    icons={tableIcons}
                    title="Output configuration"
                    columns={this.state.columns}
                    data={this.state.data}
                    editable={{
                        onRowAdd: (newData) => {
                            return this.handleOutputConfigChange(newData, null)
                        },
                        onRowUpdate: (newData, oldData) => {
                            return this.handleOutputConfigChange(newData, oldData)
                        },
                        onRowDelete: (oldData) => {
                            return this.handleOutputConfigChange(null, oldData)
                        }
                    }}
                />
            </div>
        )
    }
}

ConfigurationPage.propTypes = {
    classes: PropTypes.object.isRequired,
};

export default withSnackbar(withStyles(styles)(ConfigurationPage));