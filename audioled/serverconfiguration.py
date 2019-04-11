from audioled import project, configs, devices
import uuid
import jsonpickle
import json
import os.path
import hashlib

CONFIG_NUM_PIXELS = 'num_pixels'
CONFIG_NUM_ROWS = 'num_rows'
CONFIG_DEVICE = 'device'
CONFIG_DEVICE_CANDY_SERVER = 'device.candy.server'
CONFIG_AUDIO_DEVICE_INDEX = 'audio.device_index'
CONFIG_ACTIVE_PROJECT = 'active_project'
CONFIG_DEVICE_PANEL_MAPPING = 'device.panel.mapping'


class ServerConfiguration:
    def __init__(self):
        self._config = {}
        # Init default values
        self._config[CONFIG_NUM_PIXELS] = 300
        self._config[CONFIG_NUM_ROWS] = 1
        self._config[CONFIG_DEVICE] = 'FadeCandy'
        self._config[CONFIG_DEVICE_CANDY_SERVER] = '127.0.0.1:7890'
        self._config[CONFIG_DEVICE_PANEL_MAPPING] = ''
        self._projects = {}
        self._projectMetadatas = {}
        self._activeProject = None

    @staticmethod
    def getConfigurationParameters():
        return {
            CONFIG_NUM_PIXELS: [300, 1, 2000, 1], 
            CONFIG_NUM_ROWS: [1, 1, 100, 1],
            CONFIG_DEVICE: ['FadeCandy', 'RaspberryPi'],
        }

    def setConfiguration(self, key, value):
        print("Updating {} to {}".format(key, value))
        self._config[key] = value
        if self._activeProject is not None and key in [CONFIG_NUM_PIXELS, CONFIG_DEVICE, CONFIG_DEVICE_CANDY_SERVER, CONFIG_NUM_ROWS, CONFIG_DEVICE_PANEL_MAPPING]:
            print("Renewing device")
            self.getActiveProjectOrDefault().setDevice(self._createOutputDevice())

    def getConfiguration(self, key):
        if key in self._config:
            return self._config[key]
        return None

    def getFullConfiguration(self):
        return self._config

    def getActiveProjectOrDefault(self):
        activeProjectUid = self.getConfiguration(CONFIG_ACTIVE_PROJECT)
        if activeProjectUid is None:
            print("No active project ID. Initializing new default project")
            activeProjectUid = self.initDefaultProject()
            print("Default project initialized: {}".format(activeProjectUid))
        try:
            activeProj = self.getProject(activeProjectUid)
        except Exception as e:
            print("Error reading project {}: {}".format(activeProjectUid, e))
            print("Initializing new default project")
            activeProjectUid = self.initDefaultProject()
            activeProj = self.getProject(activeProjectUid)
            print("Default project initialized: {}".format(activeProjectUid))
        self._activeProject = activeProj
        return activeProj

    def initDefaultProject(self):
        # Initialize default project
        proj = project.Project("Default project", "This is the default project.", self._createOutputDevice())
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
        proj.activateSlot(12)
        projectUid = uuid.uuid4().hex
        self._projects[projectUid] = proj
        self._projectMetadatas[projectUid] = self._metadataForProject(proj, projectUid)
        self._config[CONFIG_ACTIVE_PROJECT] = projectUid
        activeProjectUid = projectUid
        return activeProjectUid

    def getProject(self, uid):
        if uid in self._projects:
            proj = self._projects[uid]
            proj.setDevice(self._createOutputDevice())
            return proj
        print("Get project from non-persistent")
        return None

    def deleteProject(self, uid):
        if uid in self._projects:
            self._projects.pop(uid)
        if uid in self._projectMetadatas:
            self._projectMetadatas.pop(uid)

    def activateProject(self, uid):
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
        proj = project.Project(title, description, self._createOutputDevice())
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
        proj.setDevice(self._createOutputDevice())
        self._projects[projectUid] = proj
        self._projectMetadatas[projectUid] = self._metadataForProject(proj, projectUid)
        return self.getProjectMetadata(projectUid)

    def _store(self):
        pass

    def _load(self):
        pass

    def _createOutputDevice(self):
        device = None
        if self.getConfiguration(CONFIG_DEVICE) == devices.RaspberryPi.__name__:
            device = devices.RaspberryPi(self.getConfiguration(CONFIG_NUM_PIXELS), self.getConfiguration(CONFIG_NUM_ROWS))
        elif self.getConfiguration(CONFIG_DEVICE) == devices.FadeCandy.__name__:
            device = devices.FadeCandy(self.getConfiguration(CONFIG_NUM_PIXELS), self.getConfiguration(CONFIG_NUM_ROWS), self.getConfiguration(CONFIG_DEVICE_CANDY_SERVER))
        else:
            print("Unknown device: {}".format(self.getConfiguration(CONFIG_DEVICE)))
        if self.getConfiguration(CONFIG_DEVICE_PANEL_MAPPING) is not None and self.getConfiguration(CONFIG_DEVICE_PANEL_MAPPING) != '':
            mappingFile = self.getConfiguration(CONFIG_DEVICE_PANEL_MAPPING)
            if os.path.exists(mappingFile):
                with open(mappingFile, "r", encoding='utf-8') as f:
                    content = f.read()
                    mapping = json.loads(content)
                    wrapper = devices.PanelWrapper(device, mapping)
                    device = wrapper
                    print("Active pixel mapping: {}".format(mappingFile))
            else:
                raise FileNotFoundError("Mapping file {} does not exist.".format(mappingFile))
        return device

    def _metadataForProject(self, project, projectUid):
        data = {}
        data['name'] = project.name
        data['description'] = project.description
        data['id'] = projectUid
        return data

    def store(self):
        pass


class PersistentConfiguration(ServerConfiguration):
    def __init__(self, storageLocation, no_store):
        super().__init__()
        self.storageLocation = storageLocation
        self.no_store = no_store
        self.need_write = False
        self._lastHash = None
        self._lastProjectHashs = {}
        self._load()

    def setConfiguration(self, key, value):
        super().setConfiguration(key, value)

    def getConfiguration(self, key):
        return super().getConfiguration(key)

    def _store(self):
        self.need_write = True

    def deleteProject(self, uid):
        """Overrides deleteProject and deletes the corresponding project file from disk
        """
        print("Deleting project {} from disk".format(uid))
        if uid not in self._projectMetadatas:
            print("Cannot delete project {}: No metadata".format(uid))
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
            print("Writing configuration to {}".format(os.path.join(self.storageLocation, "configuration.json")))
            with open(os.path.join(self.storageLocation, 'configuration.json'), "w") as f:
                f.write(value)
            self.need_write = False
            self._lastHash = curHash

        # Check and write projects
        for key, proj in self._projects.items():
            projMeta = self._projectMetadatas[key]
            if projMeta is None:
                print("No metadata found. Can't write project {}".format(key))
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

    def updateMd5HashFromFiles(self):
        for key, proj in self._projects.items():
            projMeta = self._projectMetadatas[key]
            fname = projMeta['location']
            hash_md5 = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            self._lastProjectHashs[key] = hash_md5.hexdigest()
            

    def _getStoreConfig(self):
        return json.dumps(self._config, indent=4, sort_keys=True)

    def _load(self):
        # Read configuration file
        configFile = os.path.join(self.storageLocation, "configuration.json")
        if os.path.exists(configFile):
            with open(os.path.join(self.storageLocation, "configuration.json"), "r", encoding='utf-8') as f:
                print("Reading configuration from {}".format(configFile))
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
            print("Configuration not found. Skipping read.")

        # Read project metadata
        projPath = self._getProjectPath()
        if not os.path.exists(projPath):
            # No projects -> finished
            return
        onlyfiles = [f for f in os.listdir(projPath) if os.path.isfile(os.path.join(projPath, f)) and os.path.splitext(os.path.basename(f))[1] == '.json']
        # Backwards compatibility: Move file to new folder
        for f in onlyfiles:
            projUid = os.path.splitext(os.path.basename(f))[0]
            print("Moving project {} to folder".format(f))
            os.makedirs(os.path.join(projPath, projUid))
            os.rename(os.path.join(projPath, f), os.path.join(os.path.join(projPath, projUid), f))
        # Read projects from subfolders
        onlyfolders = [f for f in os.listdir(projPath) if os.path.isdir(os.path.join(projPath, f))]
        for p in onlyfolders:
            path = os.path.join(projPath, p)
            jsonFiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and os.path.splitext(os.path.basename(f))[1] == '.json']
            if len(jsonFiles) == 1:
                f = os.path.basename(jsonFiles[0])
                print("Reading project metadata from {}/{}".format(path, f))
                projUid = os.path.splitext(os.path.basename(f))[0]
                try:
                    data = self._readProjectMetadata(os.path.join(path, f), projUid)
                    self._projectMetadatas[projUid] = data
                except RuntimeError:
                    pass
            else:
                print("Couldn't read project from {}, only one json file expected".format(p))

    def _getProjectPath(self):
        return os.path.join(self.storageLocation, "projects")

    def _readProjectMetadata(self, filepath, projUid):
        with open(filepath, "r", encoding='utf-8') as fc:
            content = fc.read()
            projData = json.loads(content)
            p = projData.get("py/state")
            data = {}
            if p is None:
                raise RuntimeError("Not a project")
            name = p.get("name")
            if name is not None:
                data['name'] = name
            else:
                data['name'] = ''
            description = p.get("description")
            if description is not None:
                data['description'] = description
            else:
                data['description'] = ''
            data['id'] = projUid
            data['location'] = filepath
            return data
    
    def _metadataForProject(self, project, projectUid):
        projData = super()._metadataForProject(project, projectUid)
        # Add storage location to metadata
        projData['location'] = os.path.join(os.path.join(self._getProjectPath(), projectUid), "{}.json".format(projectUid))
        print("Storage location for project {}: {}".format(projectUid, projData['location']))
        return projData

    def _readProject(self, uid):
        if uid not in self._projectMetadatas:
            raise RuntimeError("No metadata for project {}. Does the file exist?".format(uid))
        projMeta = self._projectMetadatas[uid]

        filepath = projMeta['location']
        print("Reading project {} from {}".format(uid, filepath))
        with open(filepath, "r", encoding='utf-8') as fc:
            content = fc.read()
            proj = jsonpickle.decode(content)
            proj.setDevice(self._createOutputDevice())
            return proj

    def _writeProject(self, proj, projFile):
        print("Writing project to {}".format(projFile))
        projJson = json.dumps(json.loads(jsonpickle.encode(proj)), indent=4, sort_keys=True)
        with open(projFile, "w") as f:
            f.write(projJson)

    def _getProjectHash(self, proj):
        projJson = json.dumps(json.loads(jsonpickle.encode(proj)), indent=4, sort_keys=True)
        mp = hashlib.md5()
        mp.update(projJson.encode('utf-8'))
        projHash = mp.hexdigest()
        return projHash
