from audioled import project, configs
import uuid

CONFIG_NUM_PIXELS = 'num_pixels'
CONFIG_DEVICE = 'device'
CONFIG_DEVICE_CANDY_SERVER = 'device.candy.server'
CONFIG_AUDIO_DEVICE_INDEX = 'audio.device_index'


class ServerConfiguration:

    def __init__(self):
        self._config = {}
        # Init default values
        self._config[CONFIG_NUM_PIXELS] = 300
        self._config[CONFIG_DEVICE] = 'FadeCandy'
        self._config[CONFIG_DEVICE_CANDY_SERVER] = '127.0.0.1:7890'
        self._projects = {}
        self._activeProjectUid = None
        proj = project.Project()
        # Initialize filtergraph
        # fg = configs.createSpectrumGraph(num_pixels, device)
        # fg = configs.createMovingLightGraph(num_pixels, device)
        # fg = configs.createMovingLightsGraph(num_pixels, device)
        # fg = configs.createVUPeakGraph(num_pixels, device)
        # initial = configs.createSwimmingPoolGraph(num_pixels, device)
        # second = configs.createDefenceGraph(num_pixels, device)
        # fg = configs.createKeyboardGraph(num_pixels, device)

        # proj.setFiltergraphForSlot(12, initial)
        # proj.setFiltergraphForSlot(13, second)
        # proj.activateSlot(12)
        projectUid = uuid.uuid4().hex
        self._projects[projectUid] = proj
        self._activeProjectUid = projectUid

    def setConfiguration(self, key, value):
        self._config[key] = value
        
    def getConfiguration(self, key):
        if key in self._config:
            return self._config[key]
        return None

    def getProject(self):
        return self._projects[self._activeProjectUid]
        

class PersistentConfiguration(ServerConfiguration):
    def __init__(self, storageLocation, no_store):
        super().__init__()
        self.storageLocation = storageLocation
        self.no_store = no_store
    
    def setConfiguration(self, key, value):
        super().setConfiguration(value)
        self._store()
    
    def getConfiguration(self, key):
        return super().getConfiguration(key)
    
    def _store(self):
        if not self.no_store:
            # ToDo: Store
            pass
