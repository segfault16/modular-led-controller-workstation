from audioled import project, configs, devices
import uuid
import jsonpickle
import json
import os.path
import hashlib
import io
import multiprocessing
import ctypes

from audioled.devices import MultiOutputWrapper

import logging
logger = logging.getLogger(__name__)

CONFIG_NUM_PIXELS = 'num_pixels'
CONFIG_NUM_ROWS = 'num_rows'
CONFIG_DEVICE = 'device'
CONFIG_DEVICE_CANDY_SERVER = 'device.candy.server'
CONFIG_AUDIO_DEVICE_INDEX = 'audio.device_index'
CONFIG_ACTIVE_PROJECT = 'active_project'
CONFIG_DEVICE_PANEL_MAPPING = 'device.panel.mapping'
CONFIG_ACTIVE_DEVICE_CONFIGURATION = 'active_device_config'
CONFIG_DEVICE_CONFIGS = 'device_configs'
CONFIG_RESET_CONTROLLER_MODULATION = 'reset_controller_modulation'

allowed_configs = [
    CONFIG_NUM_PIXELS, CONFIG_NUM_ROWS, CONFIG_DEVICE, CONFIG_DEVICE_CANDY_SERVER, CONFIG_AUDIO_DEVICE_INDEX,
    CONFIG_ACTIVE_PROJECT, CONFIG_DEVICE_PANEL_MAPPING, CONFIG_ACTIVE_DEVICE_CONFIGURATION, CONFIG_DEVICE_CONFIGS,
    CONFIG_RESET_CONTROLLER_MODULATION
]

allowed_devices = [
    'FadeCandy', 'RaspberryPi'
]


class ServerConfiguration:
    def __init__(self):
        self._config = {}
        # Init default values
        self._config[CONFIG_NUM_PIXELS] = 300
        self._config[CONFIG_NUM_ROWS] = 1
        self._config[CONFIG_DEVICE] = 'FadeCandy'
        self._config[CONFIG_DEVICE_CANDY_SERVER] = '127.0.0.1:7890'
        self._config[CONFIG_DEVICE_PANEL_MAPPING] = ''
        self._config[CONFIG_RESET_CONTROLLER_MODULATION] = False
        self._projects = {}
        self._projectMetadatas = {}
        self._activeProject = None
        self._reusableDevice = None

    def getConfigurationParameters(self):
        return {
            # CONFIG_NUM_PIXELS: [300, 1, 2000, 1],
            # CONFIG_NUM_ROWS: [1, 1, 100, 1],
            # CONFIG_DEVICE: ['FadeCandy', 'RaspberryPi'],
            CONFIG_RESET_CONTROLLER_MODULATION: False,
            CONFIG_ACTIVE_DEVICE_CONFIGURATION: list(self.getConfiguration(CONFIG_DEVICE_CONFIGS).keys())
        }

    def setConfiguration(self, dict):
        """Set configuration

        raises:
        - RuntimeError if config not valid
        """
        for key, value in dict.items():
            self.setConfigurationValue(key, value)

    def setConfigurationValue(self, key, value):
        """Set configuration value

        raises:
        - RuntimeError if config not valid
        """
        logger.info("Updating {} to {}".format(key, value))
        if key not in allowed_configs:
            logger.info("Updating value {} is not allowed.".format(key))

        if not self._assertConfigChangeValid(key, value):
            raise RuntimeError("Error in setting {} to {}: {}".format(key, value, "Unknown error"))
        self._config[key] = value

        if self._activeProject is not None and key in [
                CONFIG_NUM_PIXELS,
                CONFIG_DEVICE,
                CONFIG_DEVICE_CANDY_SERVER,
                CONFIG_NUM_ROWS,
                CONFIG_DEVICE_PANEL_MAPPING,
                CONFIG_DEVICE_CONFIGS,
                CONFIG_RESET_CONTROLLER_MODULATION,
                CONFIG_ACTIVE_DEVICE_CONFIGURATION
        ]:
            logger.info("Renewing device")
            self._reusableDevice = None
            self.getActiveProjectOrDefault().setDevice(self._createOrReuseOutputDevice())
        
    def getConfiguration(self, key):
        if key in self._config:
            return self._config[key]
        return None

    def getFullConfiguration(self):
        return self._config

    def getActiveProjectOrDefault(self):
        activeProjectUid = self.getConfiguration(CONFIG_ACTIVE_PROJECT)
        if activeProjectUid is None:
            logger.info("No active project ID. Initializing new default project")
            activeProjectUid = self.initDefaultProject()
            logger.info("Default project initialized: {}".format(activeProjectUid))
        try:
            activeProj = self.getProject(activeProjectUid)
        except Exception as e:
            logger.error("Error reading project {}: {}".format(activeProjectUid, e))
            raise e
        self._activeProject = activeProj
        # Apply config to project
        activeProj.setResetControllerModulation(self.getConfiguration(CONFIG_RESET_CONTROLLER_MODULATION))
        return activeProj

    def initDefaultProject(self):
        # Initialize default project
        proj = project.Project("Default project", "This is the default project.", self._createOrReuseOutputDevice())
        # Initialize filtergraph
        # fg = configs.createSpectrumGraph(num_pixels, device)
        # fg = configs.createMovingLightGraph(num_pixels, device)
        # fg = configs.createMovingLightsGraph(num_pixels, device)
        # fg = configs.createVUPeakGraph(num_pixels, device)
        initial = configs.createSwimmingPoolGraph()
        second = configs.createDefenceGraph()
        # fg = configs.createKeyboardGraph(num_pixels, device)

        proj.setFiltergraphForSlot(12, initial)
        proj.setFiltergraphForSlot(13, second)
        proj.activateScene(12)
        projectUid = uuid.uuid4().hex
        proj.id = projectUid
        self._projects[projectUid] = proj
        self._projectMetadatas[projectUid] = self._metadataForProject(proj, projectUid)
        self._config[CONFIG_ACTIVE_PROJECT] = projectUid
        activeProjectUid = projectUid
        return activeProjectUid

    def getProject(self, uid):
        if uid in self._projects:
            proj = self._projects[uid]
            proj.setDevice(self._createOrReuseOutputDevice())
            proj.id = uid
            return proj
        return None

    def deleteProject(self, uid):
        if uid in self._projects:
            self._projects.pop(uid)
        if uid in self._projectMetadatas:
            self._projectMetadatas.pop(uid)

    def activateProject(self, uid):
        proj = self.getProject(uid)
        if proj is not None:
            self._config[CONFIG_ACTIVE_PROJECT] = uid
        return self.getActiveProjectOrDefault()

    def getProjectsMetadata(self):
        data = {}
        for key, projData in self._projectMetadatas.items():
            data[key] = self.getProjectMetadata(key)
        return data

    def getProjectMetadata(self, key):
        data = self._projectMetadatas[key]
        data['active'] = (key == self.getConfiguration(CONFIG_ACTIVE_PROJECT))
        return data

    def createEmptyProject(self, title, description):
        proj = project.Project(title, description, self._createOrReuseOutputDevice())
        projectUid = uuid.uuid4().hex
        self._projects[projectUid] = proj
        self._projectMetadatas[projectUid] = self._metadataForProject(proj, projectUid)
        return self.getProjectMetadata(projectUid)

    def importProject(self, json):
        # Generate new uid
        proj = jsonpickle.decode(json)
        if not isinstance(proj, project.Project):
            raise RuntimeError("Imported object is not a project")
        projectUid = uuid.uuid4().hex
        proj.setDevice(self._createOrReuseOutputDevice())
        self._projects[projectUid] = proj
        self._projectMetadatas[projectUid] = self._metadataForProject(proj, projectUid)
        return self.getProjectMetadata(projectUid)

    def updateMd5HashFromFiles(self):
        pass

    def postStore(self):
        pass

    def _store(self):
        pass

    def _load(self):
        pass

    def _createOrReuseOutputDevice(self):
        if self._reusableDevice is not None:
            return self._reusableDevice
        device = self.createOutputDevice()
        self._reusableDevice = device
        return device

    def createOutputDevice(self):
        legacyImpl = False
        if legacyImpl:
            # Single device legacy implementation, TODO: Deprecate or adjust
            return self.createSingleDevice(self.getConfiguration(CONFIG_DEVICE),
                                           self.getConfiguration(CONFIG_NUM_PIXELS),
                                           self.getConfiguration(CONFIG_NUM_ROWS),
                                           candyServer=self.getConfiguration(CONFIG_DEVICE_CANDY_SERVER),
                                           panelMapping=self.getConfiguration(CONFIG_DEVICE_PANEL_MAPPING))

        else:
            deviceConfigName = self.getConfiguration(CONFIG_ACTIVE_DEVICE_CONFIGURATION)
            if deviceConfigName is None:
                deviceConfigName = "default"
                self.setConfigurationValue(
                    CONFIG_DEVICE_CONFIGS, {
                        deviceConfigName: [{
                            "device": self.getConfiguration(CONFIG_DEVICE),
                            "device.candy.server": self.getConfiguration(CONFIG_DEVICE_CANDY_SERVER),
                            "device.num_pixels": self.getConfiguration(CONFIG_NUM_PIXELS),
                            "device.num_rows": self.getConfiguration(CONFIG_NUM_ROWS),
                            "device.panel.mapping": self.getConfiguration(CONFIG_DEVICE_PANEL_MAPPING)
                        }]
                    })
            logger.info("Creating device config {}".format(deviceConfigName))
            deviceConfigs = self.getConfiguration(CONFIG_DEVICE_CONFIGS)
            if deviceConfigs is None:
                # TODO: Error handling
                pass
            if deviceConfigName not in deviceConfigs:
                # TODO: Error handling
                pass
            deviceConfig = deviceConfigs[deviceConfigName]
            if self.getConfiguration(CONFIG_ACTIVE_DEVICE_CONFIGURATION) != deviceConfigName:
                self.setConfigurationValue(CONFIG_ACTIVE_DEVICE_CONFIGURATION, deviceConfigName)
            return self.createOutputDeviceFromConfig(deviceConfig, deviceConfigs)

    def createSingleDevice(self, deviceName, numPixels, numRows, candyServer=None, panelMapping=None):
        # Single device legacy implementation, TODO: Deprecate or adjust
        logger.info("Creating device: {}".format(deviceName))
        if deviceName == devices.RaspberryPi.__name__:
            device = devices.RaspberryPi(numPixels, numRows)
        elif deviceName == devices.FadeCandy.__name__:
            device = devices.FadeCandy(numPixels, numRows, candyServer)
        else:
            logger.info("Unknown device: {}".format(deviceName))
            return None

        if panelMapping and panelMapping:
            mappingFile = panelMapping
            if os.path.exists(mappingFile):
                with open(mappingFile, "r", encoding='utf-8') as f:
                    mapping = json.loads(f.read())
                    device = devices.PanelWrapper(device, mapping)
                    logger.info("Active pixel mapping on real device: {}".format(mappingFile))
            else:
                raise FileNotFoundError("Mapping file {} does not exist.".format(mappingFile))
        return device

    def createVirtualOutput(self, num_pixels, num_rows, real_device, shared_array, shared_lock, start_index, panelMapping):
        device = devices.VirtualOutput(num_pixels=num_pixels,
                                       num_rows=num_rows,
                                       device=real_device,
                                       shared_array=shared_array,
                                       shared_lock=shared_lock,
                                       start_index=start_index)
        if panelMapping and panelMapping:
            mappingFile = panelMapping
            if os.path.exists(mappingFile):
                with open(mappingFile, "r", encoding='utf-8') as f:
                    mapping = json.loads(f.read())
                    device = devices.PanelWrapper(device, mapping)
                    logger.info("Active pixel mapping on virtual device: {}".format(mappingFile))
            else:
                raise FileNotFoundError("Mapping file {} does not exist.".format(mappingFile))
        return device

    def createOutputDeviceFromConfig(self, config, fullConfig):
        """Creates output device(s) from configuration

        Example configuration:
        [
            {
                "device": "FadeCandy",
                "device.candy.server": "raspberrypi.local:7891",
                "device.panel.mapping": "",
                "device.num_pixels": 300,
                "device.num_rows": 1
            },
            {
                "device": "FadeCandy",
                "device.candy.server": "raspberrypi.local:7894",
                "device.panel.mapping": "",
                "device.num_pixels": 200,
                "device.num_rows": 1
            }
        ]

        Other example with sub-strips:
        [
            {
                "device": "VirtualOutput",
                "device.virtual.reference": "oneStrip",
                "device.virtual.start_index": 0,
                "device.panel.mapping": "",
                "device.num_pixels": 300,
                "device.num_rows": 1
            },
            {
                "device": "VirtualOutput",
                "device.virtual.reference": "oneStrip",
                "device.virtual.start_index": 300,
                "device.panel.mapping": "",
                "device.num_pixels": 200,
                "device.num_rows": 1
            }
        ]
        where fullConfig must contain a device called 'oneStrip'
        """
        outputDevices = []
        multiDevices = {}
        multiDeviceLocks = {}
        multiDeviceArrays = {}
        for entry in config:
            # TODO: Support multi output device
            # Get parameters
            deviceName = entry['device']
            pixels = int(entry['device.num_pixels'])
            rows = 1
            if 'device.num_rows' in entry:
                rows = int(entry['device.num_rows'])
            candyServer = None
            if 'device.candy.server' in entry:
                candyServer = entry['device.candy.server']
            panelMapping = None
            if 'device.panel.mapping' in entry:
                panelMapping = entry['device.panel.mapping']
            if deviceName == 'VirtualOutput':
                # Construct output device
                referencedConf = entry['device.virtual.reference']
                start_index = int(entry['device.virtual.start_index'])
                if referencedConf not in multiDevices:
                    ref = fullConfig[referencedConf]
                    deviceWrapper = self.createOutputDeviceFromConfig(ref, fullConfig)  # type: MultiOutputWrapper
                    # TODO: Make sure only one device or support multi
                    firstDevice = deviceWrapper._devices[0]
                    multiDevices[referencedConf] = firstDevice
                    lock = multiprocessing.Lock()
                    multiDeviceArrays[referencedConf] = multiprocessing.Array(ctypes.c_uint8,
                                                                              3 * firstDevice.getNumPixels(),
                                                                              lock=lock)
                    multiDeviceLocks[referencedConf] = lock
                realDevice = multiDevices[referencedConf]
                virtualArray = multiDeviceArrays[referencedConf]
                virtualLock = multiDeviceLocks[referencedConf]

                # Add virtual devices
                device = self.createVirtualOutput(num_pixels=pixels,
                                                  num_rows=rows,
                                                  real_device=realDevice,
                                                  shared_array=virtualArray,
                                                  shared_lock=virtualLock,
                                                  start_index=start_index,
                                                  panelMapping=panelMapping)
            else:
                device = self.createSingleDevice(deviceName, pixels, rows, candyServer=candyServer, panelMapping=panelMapping)
            outputDevices.append(device)
        return MultiOutputWrapper(outputDevices)

    def _metadataForProject(self, project, projectUid):
        return {'name': project.name, 'description': project.description, 'id': projectUid}

    def _assertConfigChangeValid(self, configEntryName, config):
        """ Raises RuntimeError if config change is not valid
        """
        if configEntryName == CONFIG_DEVICE_CONFIGS:
            # Example:
            # "device_configs": {
            #     "oneStrip": [
            #         {
            #             "device": "RaspberryPi",
            #             "device.num_pixels": 490,
            #             "device.num_rows": 1,
            #             "device.panel.mapping": ""
            #         }
            #     ],
            #     "twoInOne": [
            #         {
            #             "device": "VirtualOutput",
            #             "device.num_pixels": 290,
            #             "device.num_rows": 1,
            #             "device.panel.mapping": "",
            #             "device.virtual.reference": "oneStrip",
            #             "device.virtual.start_index": 0
            #         },
            #         {
            #             "device": "VirtualOutput",
            #             "device.num_pixels": 200,
            #             "device.num_rows": 1,
            #             "device.panel.mapping": "",
            #             "device.virtual.reference": "oneStrip",
            #             "device.virtual.start_index": 290
            #         }
            #     ]
            # },
            # Make sure we have a string dict in the beginning:
            for key, value in config.items():
                if not isinstance(key, str):
                    raise RuntimeError("{} must consist of string keys".format(configEntryName))
                if not isinstance(value, list):
                    logger.info(type(value))
                    raise RuntimeError("{} values must consist of dict".format(configEntryName))
            keys = config.keys()
            for key in keys:
                deviceConfigEntries = config[key]
                if not isinstance(deviceConfigEntries, list):
                    raise RuntimeError("{} entry {} must have list of entries, not {}".format(
                        configEntryName, key, type(deviceConfigEntries)))

                deviceConfigItems = deviceConfigEntries
                for deviceConfigItem in deviceConfigItems:
                    # Make sure device exists
                    if 'device' not in deviceConfigItem:
                        raise RuntimeError("{} entry {} must have device".format(configEntryName, key))
                    if 'device.num_pixels' not in deviceConfigItem:
                        raise RuntimeError("{} entry {} must have device.num_pixels".format(configEntryName, key))
                    if 'device.num_rows' not in deviceConfigItem:
                        raise RuntimeError("{} entry {} must have device.num_rows".format(configEntryName, key))
                    # Make sure device.virtual.reference exists
                    if deviceConfigItem['device'] == 'VirtualOutput' and 'device.virtual.reference' not in deviceConfigItem:
                        raise RuntimeError("{} entry {} has VirtualOutput which must have device.virtual.reference".format(
                            configEntryName, key))
                    # Make sure device.virtual.start_index exists
                    if deviceConfigItem['device'] == 'VirtualOutput' and 'device.virtual.start_index' not in deviceConfigItem:
                        raise RuntimeError("{} entry {} has VirtualOutput which must have device.virtual.start_index".format(
                            configEntryName, key))
                    # Make sure device.virtual.reference is valid
                    if deviceConfigItem['device'] == 'VirtualOutput' and deviceConfigItem[
                            'device.virtual.reference'] not in keys:
                        raise RuntimeError("{} entry {} has device.virtual.reference to non-existing {}".format(
                            configEntryName, key, deviceConfigItem['device.virtual.reference']))
                    if deviceConfigItem['device'] == 'VirtualOutput':
                        referencedKey = deviceConfigItem['device.virtual.reference']
                        referencedConfigItem = config[referencedKey]
                        if len(referencedConfigItem) != 1 or referencedConfigItem[0]['device'] == 'VirtualOutput':
                            raise RuntimeError(
                                "{} entry {} referenced device config must have one entry that is no VirtualOutput".format(
                                    configEntryName, key, deviceConfigItem['device.virtual.reference']))
                    # Make sure device.virtual.reference is non-cyclic
                    if deviceConfigItem['device'] == 'VirtualOutput' and deviceConfigItem['device.virtual.reference'] == key:
                        raise RuntimeError(
                            "{} entry {} has device.virtual.reference to self. Circular reference is not allowed".format(
                                configEntryName, key))
        # No error in _isConfigChangeValid()
        return True

    def store(self):
        pass

    def getProjectAsset(self, projectUid, location):
        if os.path.exists(location):
            filename = os.path.basename(location)
            mimetype = None
            if filename.endswith('.gif'):
                mimetype = 'image/gif'
            with open(location, 'rb') as b:
                return [io.BytesIO(b.read()), filename, mimetype]
        logger.info("Cannot find project asset {}".format(location))
        return None

    def addProjectAsset(self, projectUid, file):
        raise RuntimeError("Cannot add project asset for in-memory server configuration")


class PersistentConfiguration(ServerConfiguration):
    def __init__(self, storageLocation, no_store):
        super().__init__()
        self.storageLocation = storageLocation
        self.no_store = no_store
        self.need_write = False
        self._lastHash = None
        self._lastProjectHashs = {}
        self._load()

    def setConfiguration(self, dict):
        super().setConfiguration(dict)

    def setConfigurationValue(self, key, value):
        super().setConfigurationValue(key, value)

    def getConfiguration(self, key):
        return super().getConfiguration(key)

    def _store(self):
        self.need_write = True

    def deleteProject(self, uid):
        """Overrides deleteProject and deletes the corresponding project file from disk
        """
        logger.info("Deleting project {} from disk".format(uid))
        if uid not in self._projectMetadatas:
            logger.info("Cannot delete project {}: No metadata".format(uid))
            return
        projMeta = self._projectMetadatas[uid]
        projFile = projMeta['location']
        if os.path.isfile(projFile):
            os.remove(projFile)
        path = os.path.dirname(projFile)
        if os.path.isdir(path):
            os.removedirs(path)
        super().deleteProject(uid)

    def getProject(self, uid):
        """Overrides getProject and loads the project from disk"""
        if uid is None:
            raise RuntimeError("Error getting project: No project id given")
        if uid in self._projects and self._projects.get(uid) is not None:
            # Project should already be loaded
            return super().getProject(uid)
        else:
            # Load the project from disk
            proj = self._readProject(uid)
            # Update hash
            projHash = self._getProjectHash(proj)
            self._lastProjectHashs[uid] = projHash
            self._projects[uid] = proj
            return super().getProject(uid)

    def store(self):
        # Check and write configuration
        value = self._getStoreConfig()
        m = hashlib.md5()
        m.update(value.encode('utf-8'))
        curHash = m.hexdigest()
        if self._lastHash is None or curHash != self._lastHash:
            self.need_write = True

        if not self.no_store and self.need_write:
            if not os.path.exists(self.storageLocation):
                os.makedirs(self.storageLocation)
            logger.info("Writing configuration to {}".format(os.path.join(self.storageLocation, "configuration.json")))
            with open(os.path.join(self.storageLocation, 'configuration.json'), "w") as f:
                f.write(value)
            self.need_write = False
            self._lastHash = curHash

        # Check and write projects
        for key, proj in self._projects.items():
            projMeta = self._projectMetadatas[key]
            if projMeta is None:
                logger.info("No metadata found. Can't write project {}".format(key))
                continue
            lastProjHash = None
            if key in self._lastProjectHashs:
                lastProjHash = self._lastProjectHashs[key]
            # get hash we have read and check if project needs to be written
            projHash = self._getProjectHash(proj)
            needProjWrite = lastProjHash is None or lastProjHash != projHash
            # Write project
            if not self.no_store and needProjWrite:
                projFile = projMeta['location']
                path = os.path.dirname(projFile)
                if not os.path.exists(path):
                    os.makedirs(path)
                self._writeProject(proj, projFile)
                self._lastProjectHashs[key] = projHash

    def postStore(self):
        for key, proj in self._projects.items():
            projMeta = self._projectMetadatas[key]
            if projMeta is None:
                continue
            if proj._contentRoot is None or proj._contentRoot != os.path.dirname(projMeta['location']):
                logger.info("Adjusting content root for project {}".format(key))
                proj._contentRoot = os.path.dirname(projMeta['location'])

    def updateMd5HashFromFiles(self):
        for key, proj in self._projects.items():
            projMeta = self._projectMetadatas[key]
            fname = projMeta['location']
            hash_md5 = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            self._lastProjectHashs[key] = hash_md5.hexdigest()

    def getProjectAsset(self, projectUid, location):
        projMeta = self._projectMetadatas[projectUid]
        fname = projMeta['location']
        dirname = os.path.dirname(fname)
        return super().getProjectAsset(projectUid, os.path.join(dirname, location))

    def addProjectAsset(self, projectUid, file):
        projMeta = self._projectMetadatas[projectUid]
        fname = projMeta['location']
        dirname = os.path.dirname(fname)
        fullpath = os.path.join(dirname, file.filename)
        file.save(fullpath)
        return file.filename

    def _getStoreConfig(self):
        return json.dumps(self._config, indent=4, sort_keys=True)

    def _load(self):
        # Read configuration file
        configFile = os.path.join(self.storageLocation, "configuration.json")
        if os.path.exists(configFile):
            with open(os.path.join(self.storageLocation, "configuration.json"), "r", encoding='utf-8') as f:
                logger.info("Reading configuration from {}".format(configFile))
                content = f.read()
                config_from_file = json.loads(content)
                # Merge configuration with default config
                self._config.update(config_from_file)
                # Calculate new hash value
                current_config = json.dumps(self._config, indent=4, sort_keys=True)
                m = hashlib.md5()
                m.update(current_config.encode('utf-8'))
                self._lastHash = m.hexdigest()
        else:
            logger.info("Configuration not found. Skipping read.")

        # Read project metadata
        projPath = self._getProjectPath()
        if not os.path.exists(projPath):
            # No projects -> finished
            return
        onlyfiles = [
            f for f in os.listdir(projPath)
            if os.path.isfile(os.path.join(projPath, f)) and os.path.splitext(os.path.basename(f))[1] == '.json'
        ]
        # Backwards compatibility: Move file to new folder
        for f in onlyfiles:
            projUid = os.path.splitext(os.path.basename(f))[0]
            logger.info("Moving project {} to folder".format(f))
            os.makedirs(os.path.join(projPath, projUid))
            os.rename(os.path.join(projPath, f), os.path.join(os.path.join(projPath, projUid), f))
        # Read projects from subfolders
        onlyfolders = [f for f in os.listdir(projPath) if os.path.isdir(os.path.join(projPath, f))]
        for p in onlyfolders:
            path = os.path.join(projPath, p)
            jsonFiles = [
                f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f)) and os.path.splitext(os.path.basename(f))[1] == '.json'
            ]
            if len(jsonFiles) == 1:
                f = os.path.basename(jsonFiles[0])
                logger.info("Reading project metadata from {}/{}".format(path, f))
                projUid = os.path.splitext(os.path.basename(f))[0]
                try:
                    data = self._readProjectMetadata(os.path.join(path, f), projUid)
                    self._projectMetadatas[projUid] = data
                except RuntimeError:
                    pass
            else:
                logger.info("Couldn't read project from {}, only one json file expected".format(p))

    def _getProjectPath(self):
        return os.path.join(self.storageLocation, "projects")

    def _readProjectMetadata(self, filepath, fallbackUid):
        with open(filepath, "r", encoding='utf-8') as fc:
            projData = json.loads(fc.read())
            p = projData.get("py/state")
            if not p:
                raise RuntimeError("Not a project")

            return {
                'name': p.get('name', ''),
                'description': p.get('description', ''),
                'id': p.get('id', fallbackUid),
                'location': filepath
            }

    def _metadataForProject(self, project, projectUid):
        projData = super()._metadataForProject(project, projectUid)
        # Add storage location to metadata
        projData['location'] = os.path.join(os.path.join(self._getProjectPath(), projectUid), "{}.json".format(projectUid))
        logger.info("Storage location for project {}: {}".format(projectUid, projData['location']))
        return projData

    def _readProject(self, uid):
        if uid not in self._projectMetadatas:
            raise RuntimeError("No metadata for project {}. Does the file exist?".format(uid))
        projMeta = self._projectMetadatas[uid]

        filepath = projMeta['location']
        logger.info("Reading project {} from {}".format(uid, filepath))
        with open(filepath, "r", encoding='utf-8') as fc:
            content = fc.read()
            proj = jsonpickle.decode(content)
            proj._contentRoot = os.path.dirname(filepath)
            proj.setDevice(self._createOrReuseOutputDevice())
            return proj

    def _writeProject(self, proj, projFile):
        logger.info("Writing project to {}".format(projFile))
        projJson = json.dumps(json.loads(jsonpickle.encode(proj)), indent=4, sort_keys=True)
        with open(projFile, "w") as f:
            f.write(projJson)

    def _getProjectHash(self, proj):
        projJson = json.dumps(json.loads(jsonpickle.encode(proj)), indent=4, sort_keys=True)
        mp = hashlib.md5()
        mp.update(projJson.encode('utf-8'))
        projHash = mp.hexdigest()
        return projHash
