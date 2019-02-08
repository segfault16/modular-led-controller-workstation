from audioled import project, configs, devices
import uuid
import jsonpickle
import os.path
import hashlib

CONFIG_NUM_PIXELS = 'num_pixels'
CONFIG_DEVICE = 'device'
CONFIG_DEVICE_CANDY_SERVER = 'device.candy.server'
CONFIG_AUDIO_DEVICE_INDEX = 'audio.device_index'
CONFIG_ACTIVE_PROJECT = 'active_project'


class ServerConfiguration:

    def __init__(self):
        self._config = {}
        # Init default values
        self._config[CONFIG_NUM_PIXELS] = 300
        self._config[CONFIG_DEVICE] = 'FadeCandy'
        self._config[CONFIG_DEVICE_CANDY_SERVER] = '127.0.0.1:7890'
        self._projects = {}

    @staticmethod
    def getConfigurationParameters():
        return {
            CONFIG_NUM_PIXELS: [300, 1, 2000, 1],
            CONFIG_DEVICE: ['FadeCandy', 'RaspberryPi']
        }

    def setConfiguration(self, key, value):
        print("Updating {} to {}".format(key, value))
        self._config[key] = value
        if key in [CONFIG_NUM_PIXELS, CONFIG_DEVICE, CONFIG_DEVICE_CANDY_SERVER]:
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
            # Initialize default project
            proj = project.Project("Default project", "This is the default project.", self._createOutputDevice())
            # Initialize filtergraph
            # fg = configs.createSpectrumGraph(num_pixels, device)
            # fg = configs.createMovingLightGraph(num_pixels, device)
            # fg = configs.createMovingLightsGraph(num_pixels, device)
            # fg = configs.createVUPeakGraph(num_pixels, device)
            initial = configs.createSwimmingPoolGraph(self.getConfiguration(CONFIG_NUM_PIXELS))
            second = configs.createDefenceGraph(self.getConfiguration(CONFIG_NUM_PIXELS))
            # fg = configs.createKeyboardGraph(num_pixels, device)

            proj.setFiltergraphForSlot(12, initial)
            proj.setFiltergraphForSlot(13, second)
            proj.activateSlot(12)
            projectUid = uuid.uuid4().hex
            self._projects[projectUid] = proj
            self._config[CONFIG_ACTIVE_PROJECT] = projectUid
            activeProjectUid = projectUid
        return self._projects[activeProjectUid]

    def getProject(self, uid):
        if uid in self._projects:
            return self._projects[uid]
        return None

    def deleteProject(self, uid):
        if uid in self._projects:
            self._projects.pop(uid)

    def activateProject(self, uid):
        self._config[CONFIG_ACTIVE_PROJECT] = uid
        return self.getActiveProjectOrDefault()

    def getProjectsMetadata(self):
        data = {}
        for key, proj in self._projects.items():
            data[key] = self.getProjectMetadata(key)[key]
        return data
    
    def getProjectMetadata(self, key):
        data = {}
        proj = self._projects[key]
        data[key] = {
            "title": proj.name,
            "description": proj.description,
            "active": key == self.getConfiguration(CONFIG_ACTIVE_PROJECT)
        }
        
        return data

    def createEmptyProject(self, title, description):
        proj = project.Project("Empty Project", "", self._createOutputDevice())
        projectUid = uuid.uuid4().hex
        self._projects[projectUid] = proj
        return self.getProjectMetadata(projectUid)
    
    def _store(self):
        pass

    def _load(self):
        pass

    def _createOutputDevice(self):
        device = None
        if self.getConfiguration(CONFIG_DEVICE) == devices.RaspberryPi.__name__:
            device = devices.RaspberryPi(self.getConfiguration(CONFIG_NUM_PIXELS))
        elif self.getConfiguration(CONFIG_DEVICE) == devices.FadeCandy.__name__:
            device = devices.FadeCandy(self.getConfiguration(CONFIG_DEVICE_CANDY_SERVER))
        else:
            print("Unknown device: {}".format(self.getConfiguration(CONFIG_DEVICE)))
        return device
        

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
        print("Deleting project {} from disk".format(uid))
        path = os.path.join(self.storageLocation, "projects", "{}.json".format(uid))
        if os.path.isfile(path):
            os.remove(path)
        super().deleteProject(uid)

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
            lastProjHash = None
            if key in self._lastProjectHashs:
                lastProjHash = self._lastProjectHashs[key]
            projJson = jsonpickle.encode(proj)
            mp = hashlib.md5()
            mp.update(projJson.encode('utf-8'))
            projHash = mp.hexdigest()
            needProjWrite = lastProjHash is None or lastProjHash != projHash
            if not self.no_store and needProjWrite:
                path = os.path.join(self.storageLocation, "projects")
                if not os.path.exists(path):
                    os.makedirs(path)
                projFile = os.path.join(path, "{}.json".format(key))
                print("Writing project to {}".format(projFile))
                with open(projFile, "w") as f:
                    f.write(projJson)
                self._lastProjectHashs[key] = projHash
                
    def _getStoreConfig(self):
        return jsonpickle.encode(self._config)

    def _load(self):
        # Read configuration file
        configFile = os.path.join(self.storageLocation, "configuration.json")
        if os.path.exists(configFile):
            with open(os.path.join(self.storageLocation, "configuration.json"), "r", encoding='utf-8') as f:
                print("Reading configuration from {}".format(configFile))
                content = f.read()
                self._config = jsonpickle.decode(content)
                m = hashlib.md5()
                m.update(content.encode('utf-8'))
                self._lastHash = m.hexdigest() 
        else:
            print("Configuration not found. Skipping read.")

        # Read projects
        projPath = os.path.join(self.storageLocation, "projects")
        if not os.path.exists(projPath):
            os.makedirs(projPath)
        onlyfiles = [f for f in os.listdir(projPath) if os.path.isfile(os.path.join(projPath, f))]
        for f in onlyfiles:
            print("Reading project {}".format(f))
            with open(os.path.join(projPath, f), "r", encoding='utf-8') as fc:
                content = fc.read()
                projUid = os.path.splitext(os.path.basename(f))[0]
                proj = jsonpickle.decode(content)
                proj.setDevice(self._createOutputDevice())
                self._projects[projUid] = proj
                m = hashlib.md5()
                m.update(content.encode('utf-8'))
                self._lastProjectHashs[projUid] = m.hexdigest()


